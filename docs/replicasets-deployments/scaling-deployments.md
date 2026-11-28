# Scaling Deployments

> Change the replica count, see why scaling isn't a rollout, and get the file ready for an autoscaler.

---

You've scaled before: a ReplicaSet in [Creating and Managing ReplicaSets](creating-replicasets.md#3-scale-it), and, without success, a Deployment's ReplicaSet in [Creating and Managing Deployments](creating-deployments.md#scale-it), where the Deployment put the count straight back. The right layer to scale is the **Deployment**, and that's what this chapter does.

The basics carry over from ReplicaSets unchanged: you change `replicas`, Pods are added or removed from the same template, and the file wins over `kubectl scale`. What's new is how scaling fits with everything a Deployment adds: revisions, rollouts, and rollbacks.

Start from a fresh copy, and create the Deployment:

```bash
mkdir -p /tmp/deploy
cp manifests/replicasets-deployments/nginx-deployment.yaml /tmp/deploy/
kubectl apply -f /tmp/deploy/nginx-deployment.yaml
kubectl rollout status deployment/nginx-deployment
```

## 1. Scale with the file

Change `replicas` from `3` to `5`, and preview it:

```bash
sed -i 's/replicas: 3$/replicas: 5/' /tmp/deploy/nginx-deployment.yaml
kubectl diff -f /tmp/deploy/nginx-deployment.yaml
```

```diff
-  replicas: 3
+  replicas: 5
```

Apply it:

```bash
kubectl apply -f /tmp/deploy/nginx-deployment.yaml
kubectl get deploy nginx-deployment
kubectl get rs -l app=nginx
```

```text
NAME               READY   UP-TO-DATE   AVAILABLE   AGE
nginx-deployment   5/5     5            5           40s

NAME                          DESIRED   CURRENT   READY   AGE
nginx-deployment-86d7c4cfc4   5         5         5       40s
```

Two new Pods, and still **one** ReplicaSet. The Deployment didn't create anything new; it told its existing ReplicaSet to be bigger, and the ReplicaSet did the rest.

## 2. Scaling isn't a rollout

Look at the history and the Events:

```bash
kubectl rollout history deployment/nginx-deployment
kubectl get events --field-selector involvedObject.name=nginx-deployment --sort-by=.metadata.creationTimestamp
```

```text
REVISION  CHANGE-CAUSE
1         <none>

LAST SEEN   TYPE     REASON              OBJECT                        MESSAGE
45s         Normal   ScalingReplicaSet   deployment/nginx-deployment   Scaled up replica set nginx-deployment-86d7c4cfc4 to 3
5s          Normal   ScalingReplicaSet   deployment/nginx-deployment   Scaled up replica set nginx-deployment-86d7c4cfc4 to 5 from 3
```

(`--field-selector` keeps only the Deployment's own events, the same ones `kubectl describe` lists at the bottom. `--sort-by` puts them in order, oldest first.)

Still revision 1. `replicas` sits **outside** the Pod template, and only [template changes](updating-pod-template.md#4-which-changes-cause-a-rollout) start a rollout. That has three consequences:

- **No new revision and no new ReplicaSet.** The existing Pods aren't touched; the extra ones come from the same template.
- **`maxSurge` and `maxUnavailable` don't apply.** Those pace the replacement of old Pods with new ones. Scaling up just creates all the new Pods at once.
- **A rollback doesn't change the count.** `kubectl rollout undo` restores an old template, and `replicas` isn't part of one. If you scale to 6 and then roll back, you still have 6.

One thing scaling does share with a rollout is **readiness**. A new Pod counts as available, and gets traffic, only once it's [ready](../running-and-operating/health-checks.md). So the capacity you add arrives after the image is pulled and the app has started, not the moment you change the number. If you know load is coming, scale before it arrives.

## 3. `kubectl scale`, and why the file still wins

For a quick experiment, set the count directly:

```bash
kubectl scale deployment/nginx-deployment --replicas=2
kubectl get pods -l app=nginx
```

```text
deployment.apps/nginx-deployment scaled

NAME                                READY   STATUS    RESTARTS   AGE
nginx-deployment-86d7c4cfc4-7xkqp   1/1     Running   0          60s
nginx-deployment-86d7c4cfc4-tq9wz   1/1     Running   0          60s
```

Three Pods were removed, the newest first, by the same rules as in [Creating and Managing ReplicaSets](creating-replicasets.md#the-imperative-way-kubectl-scale). Now ask what the next `apply` would do:

```bash
kubectl diff -f /tmp/deploy/nginx-deployment.yaml
```

```diff
-  replicas: 2
+  replicas: 5
```

`replicas` is in your file, so `apply` would put it back to 5. That's the rule from [Declarative Object Management](../object-management/declarative-management.md#dont-mix-approaches-on-one-object) again: use `kubectl scale` for experiments or an emergency, then put the count you actually want in the file.

Say the count you want is 3. Change the file, and apply:

```bash
sed -i 's/replicas: 5$/replicas: 3/' /tmp/deploy/nginx-deployment.yaml
kubectl apply -f /tmp/deploy/nginx-deployment.yaml
kubectl get deploy nginx-deployment
```

```text
NAME               READY   UP-TO-DATE   AVAILABLE   AGE
nginx-deployment   3/3     3            3           70s
```

File and cluster agree again, at 3.

## 4. Scale to zero

`replicas: 0` is allowed. All the Pods go, and everything else stays:

```bash
kubectl scale deployment/nginx-deployment --replicas=0
kubectl get deploy,rs -l app=nginx
```

```text
NAME                               READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/nginx-deployment   0/0     0            0           2m

NAME                                          DESIRED   CURRENT   READY   AGE
replicaset.apps/nginx-deployment-86d7c4cfc4   0         0         0       2m
```

The Deployment, its ReplicaSet, and its revision history are all still there; only the Pods are gone. It's a way to **park** an app, say a test environment overnight, and bring it back exactly as it was, without deleting anything.

`kubectl scale` keeps this demo short. To park an app for real, set `replicas: 0` in the file and apply. Otherwise the next `apply`, from you, a teammate, or a CI pipeline, quietly starts it again, the same way the one below does. Bring it back with the file:

```bash
kubectl apply -f /tmp/deploy/nginx-deployment.yaml
kubectl rollout status deployment/nginx-deployment
```

## 5. Hand the count to an autoscaler

A [HorizontalPodAutoscaler](../running-and-operating/scaling.md#autoscaling-hpa) changes `replicas` for you, based on load. That clashes with a file that also sets `replicas`: every `apply` would reset the count to `3`, and the HPA would change it again. Once an autoscaler owns the count, the file should stop setting it.

The obvious move is to delete the line. Check what that would do first:

```bash
sed -i '/^  replicas: 3$/d' /tmp/deploy/nginx-deployment.yaml
kubectl diff -f /tmp/deploy/nginx-deployment.yaml
```

```diff
-  replicas: 3
+  replicas: 1
```

That's the trap from [Declarative Object Management](../object-management/declarative-management.md#5-deleting-a-line-deletes-the-field). `replicas` is in the last-applied copy, so a missing line means "delete this field", the default fills in **1**, and the app would drop to one Pod until the autoscaler noticed.

What you want is "stop managing this field". Update the last-applied copy to match your edited file, without changing anything in the cluster:

```bash
kubectl apply set-last-applied -f /tmp/deploy/nginx-deployment.yaml
kubectl diff -f /tmp/deploy/nginx-deployment.yaml
kubectl apply -f /tmp/deploy/nginx-deployment.yaml
kubectl get deploy nginx-deployment
```

```text
deployment.apps/nginx-deployment configured
deployment.apps/nginx-deployment unchanged

NAME               READY   UP-TO-DATE   AVAILABLE   AGE
nginx-deployment   3/3     3            3           3m
```

`set-last-applied` only rewrote the annotation, which now has no `replicas`. So `diff` prints nothing, `apply` changes nothing, and the count stays at 3, no longer managed by your file. An HPA can take it from here. (For a brand-new Deployment, just leave `replicas` out of the file from the start.)

## Clean up

```bash
kubectl delete deployment nginx-deployment
rm -rf /tmp/deploy
```

## Best practices

- **Scale the Deployment, never its ReplicaSet.** The Deployment sets the count on its ReplicaSets and will undo yours.
- **Keep the count in the file.** Use `kubectl scale` for experiments or an emergency, then update the file, or the next `apply` undoes it.
- **Remember that scaling isn't a rollout, and a rollback isn't a scale.** `rollout undo` restores a template and leaves `replicas` alone.
- **Scale ahead of load.** New Pods only help once they're ready, which takes as long as an image pull and a startup.
- **Scale to zero to park an app**, rather than deleting it. The history and ReplicaSets stay, ready to scale back up.
- **When an autoscaler takes over, remove `replicas` from the file with `kubectl apply set-last-applied` first**, and check with `kubectl diff` that the count isn't about to drop to 1.

---

[← Understanding Rollouts](understanding-rollouts.md) · [↑ Contents](../../README.md) · [Troubleshooting Failed Rollouts →](troubleshooting-rollouts.md)
