# Creating and Managing Deployments

> Create a Deployment, read its status, and see why you manage it, not its ReplicaSet.

---

In [Introduction to Deployments](introduction-to-deployments.md) you took a quick peek at the three layers a Deployment creates. Now you'll work with one properly: read what its status columns and `describe` tell you, watch self-healing from the Deployment's point of view, and find out what happens if you reach past the Deployment and touch its ReplicaSet directly.

You'll use [`nginx-deployment.yaml`](../../manifests/replicasets-deployments/nginx-deployment.yaml) from the repo as-is. Changing the template and scaling come in the next chapters.

## 1. Create it, and read its status

```bash
kubectl apply -f manifests/replicasets-deployments/nginx-deployment.yaml
kubectl get deploy nginx-deployment
```

```text
NAME               READY   UP-TO-DATE   AVAILABLE   AGE
nginx-deployment   0/3     3            0           1s
```

The Pods are still starting. Rather than polling, let kubectl wait until the Deployment is done:

```bash
kubectl rollout status deployment/nginx-deployment
```

```text
Waiting for deployment "nginx-deployment" rollout to finish: 0 of 3 updated replicas are available...
Waiting for deployment "nginx-deployment" rollout to finish: 1 of 3 updated replicas are available...
Waiting for deployment "nginx-deployment" rollout to finish: 2 of 3 updated replicas are available...
deployment "nginx-deployment" successfully rolled out
```

`rollout status` exits when the rollout succeeds, which makes it the right command for scripts too. Now the status reads:

```bash
kubectl get deploy nginx-deployment -o wide
```

```text
NAME               READY   UP-TO-DATE   AVAILABLE   AGE   CONTAINERS   IMAGES       SELECTOR
nginx-deployment   3/3     3            3           2s    nginx        nginx:1.27   app=nginx
```

The columns are different from a ReplicaSet's, because a Deployment also tracks **versions**:

| Column | Means |
|---|---|
| `READY` | Ready Pods / desired Pods. `3/3` is what you want. |
| `UP-TO-DATE` | Pods running the **current** template. During an upgrade, it climbs as new Pods replace old ones. |
| `AVAILABLE` | Pods that are ready and serving. It's what your users actually get. |

Right now there's only one version, so all three agree. You'll see them pull apart in [Updating the Pod Template](updating-pod-template.md).

## 2. Read `describe`

```bash
kubectl describe deploy nginx-deployment
```

The output is long. These are the parts that matter (trimmed):

```text
Replicas:               3 desired | 3 updated | 3 total | 3 available | 0 unavailable
StrategyType:           RollingUpdate
RollingUpdateStrategy:  25% max unavailable, 25% max surge
Conditions:
  Type           Status  Reason
  ----           ------  ------
  Available      True    MinimumReplicasAvailable
  Progressing    True    NewReplicaSetAvailable
OldReplicaSets:  <none>
NewReplicaSet:   nginx-deployment-86d7c4cfc4 (3/3 replicas created)
Events:
  Type    Reason             Age   From                   Message
  ----    ------             ----  ----                   -------
  Normal  ScalingReplicaSet  2s    deployment-controller  Scaled up replica set nginx-deployment-86d7c4cfc4 to 3
```

- **`Replicas`** is the same picture as the columns, in words.
- **`RollingUpdateStrategy`** shows the defaults from [Introduction to Deployments](introduction-to-deployments.md#what-happens-when-you-change-the-template): 25% max unavailable, 25% max surge.
- **`Conditions`**: `Available` says enough Pods are up; `Progressing` says the last rollout completed. When a rollout gets stuck, this is where it shows ([Troubleshooting Failed Rollouts](troubleshooting-rollouts.md)).
- **`NewReplicaSet` / `OldReplicaSets`**: the current version's ReplicaSet, and any previous ones still around.
- **`Events`** talk about **ReplicaSets**, not Pods: "Scaled up replica set … to 3". The Deployment never creates a Pod itself; it only tells ReplicaSets how big to be. For events about individual Pods, `describe` the ReplicaSet.

## 3. Follow the chain of owners

You saw in [Creating and Managing ReplicaSets](creating-replicasets.md#1-create-it) that a Pod records its owner. A ReplicaSet does too. Save the ReplicaSet's name, and ask:

```bash
RS=$(kubectl get rs -l app=nginx -o jsonpath='{.items[0].metadata.name}')
kubectl get rs $RS -o jsonpath='{.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}'
```

```
Deployment/nginx-deployment
```

So the chain is **Pod → ReplicaSet → Deployment**, each one pointing at the layer above. That's what lets Kubernetes delete everything below a Deployment when you delete it, and what lets the Deployment recognize "its" ReplicaSets.

## 4. Self-healing still works

Delete a Pod:

```bash
POD=$(kubectl get pods -l app=nginx -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod $POD
kubectl get pods -l app=nginx
```

```text
NAME                                READY   STATUS              RESTARTS   AGE
nginx-deployment-86d7c4cfc4-cjf7x   0/1     ContainerCreating   0          0s
nginx-deployment-86d7c4cfc4-fp6nv   1/1     Running             0          7s
nginx-deployment-86d7c4cfc4-l6fqw   1/1     Running             0          7s
```

A replacement is already starting. This is exactly the ReplicaSet behavior from the earlier chapters. The **ReplicaSet** replaced the Pod; the Deployment wasn't involved, and its Events don't mention it. Each layer handles its own job.

## 5. Don't manage the ReplicaSet yourself

The ReplicaSet is right there, and it's tempting to change it directly. Try it. First make sure the replacement Pod from step 4 is ready, so its startup doesn't muddle what you see next:

```bash
kubectl rollout status deployment/nginx-deployment
```

### Scale it

```bash
kubectl scale rs $RS --replicas=5
kubectl get rs $RS
```

```text
replicaset.apps/nginx-deployment-86d7c4cfc4 scaled

NAME                          DESIRED   CURRENT   READY   AGE
nginx-deployment-86d7c4cfc4   3         3         3       8s
```

`scaled`, and yet `DESIRED` is already back to **3**. The Deployment noticed its ReplicaSet no longer matched `replicas: 3`, and set it back before you could even look. Its Events record the correction:

```text
Normal  ScalingReplicaSet  6s   deployment-controller  Scaled down replica set nginx-deployment-86d7c4cfc4 to 3 from 5
```

### Delete it

```bash
kubectl delete rs $RS
kubectl get deploy nginx-deployment
```

```text
replicaset.apps "nginx-deployment-86d7c4cfc4" deleted

NAME               READY   UP-TO-DATE   AVAILABLE   AGE
nginx-deployment   0/3     3            0           3s
```

`AVAILABLE 0`: deleting the ReplicaSet deleted its Pods, and **nothing is serving**. Wait for the Deployment to recover, then look:

```bash
kubectl rollout status deployment/nginx-deployment
kubectl get rs -l app=nginx
kubectl get pods -l app=nginx
```

```text
NAME                          DESIRED   CURRENT   READY   AGE
nginx-deployment-86d7c4cfc4   3         3         3       3s

NAME                                READY   STATUS    RESTARTS   AGE
nginx-deployment-86d7c4cfc4-4xtkc   1/1     Running   0          2s
nginx-deployment-86d7c4cfc4-w8tth   1/1     Running   0          2s
nginx-deployment-86d7c4cfc4-x2d75   1/1     Running   0          2s
```

The Deployment created the ReplicaSet again, with the **same name**: the name comes from a hash of the template, and the template didn't change. But all three Pods are new, two seconds old. You caused an outage, and ended up exactly where you started.

Both experiments point the same way. The Deployment owns its ReplicaSets and keeps them matching its own spec. **Change the Deployment**, and let it change the ReplicaSets for you.

## 6. Delete it

```bash
kubectl delete deploy nginx-deployment
kubectl get deploy,rs,pods -l app=nginx
```

```text
deployment.apps "nginx-deployment" deleted

NAME                                    READY   STATUS        RESTARTS   AGE
pod/nginx-deployment-86d7c4cfc4-4xtkc   1/1     Terminating   0          2s
pod/nginx-deployment-86d7c4cfc4-w8tth   1/1     Terminating   0          2s
pod/nginx-deployment-86d7c4cfc4-x2d75   1/1     Terminating   0          2s
```

The Deployment and its ReplicaSet are already gone; the Pods are shutting down. Run the `get` again a few seconds later, and it reports `No resources found`. Following the chain of owners, the Deployment took its ReplicaSet with it, and the ReplicaSet took its Pods.

## Best practices

- **Wait with `kubectl rollout status`**, not by re-running `get`. It exits when the rollout is done, and with an error if it fails.
- **Read `UP-TO-DATE` and `AVAILABLE`, not just `READY`.** They tell you whether you're running the version you think, and how much of it users can reach.
- **Make every change through the Deployment**: its manifest and `kubectl apply`. Scaling or deleting its ReplicaSets is undone at best, and an outage at worst.
- **Look at `describe deploy` Events for what the Deployment did**, and at `describe rs` for what happened to individual Pods.

---

[← Introduction to Deployments](introduction-to-deployments.md) · [↑ Contents](../../README.md) · [Updating the Pod Template →](updating-pod-template.md)
