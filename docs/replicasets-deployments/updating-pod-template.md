# Updating the Pod Template

> Change the Pod template, and watch the Deployment replace its Pods.

---

This is the task that went wrong in [ReplicaSets Can't Update Pods](replicaset-updates.md): upgrade nginx from `1.27` to `1.28`. With a ReplicaSet, the running Pods ignored the change, and forcing it meant an outage. Now you'll do the same with a Deployment, and watch it replace every Pod without ever dropping below three serving.

Then you'll find out exactly which changes trigger that replacement, and which don't.

Start from a fresh copy, since you'll edit it, and create the Deployment:

```bash
mkdir /tmp/deploy
cp manifests/replicasets-deployments/nginx-deployment.yaml /tmp/deploy/
kubectl apply -f /tmp/deploy/nginx-deployment.yaml
kubectl rollout status deployment/nginx-deployment
kubectl get rs -l app=nginx
```

```text
NAME                          DESIRED   CURRENT   READY   AGE
nginx-deployment-86d7c4cfc4   3         3         3       2s
```

One ReplicaSet, for the `1.27` template.

## 1. Change the image

Change the image in your copy, and preview:

```bash
sed -i 's/image: nginx:1.27$/image: nginx:1.28/' /tmp/deploy/nginx-deployment.yaml
kubectl diff -f /tmp/deploy/nginx-deployment.yaml
```

```diff
-      - image: nginx:1.27
+      - image: nginx:1.28
```

Before you apply, start a watch on the Deployment in a second terminal, so you can see the rollout happen:

```bash
kubectl get deploy nginx-deployment -w
```

Now apply, and wait for it to finish:

```bash
kubectl apply -f /tmp/deploy/nginx-deployment.yaml
kubectl rollout status deployment/nginx-deployment
```

```text
deployment.apps/nginx-deployment configured
Waiting for deployment "nginx-deployment" rollout to finish: 1 out of 3 new replicas have been updated...
Waiting for deployment "nginx-deployment" rollout to finish: 2 out of 3 new replicas have been updated...
Waiting for deployment "nginx-deployment" rollout to finish: 1 old replicas are pending termination...
deployment "nginx-deployment" successfully rolled out
```

## 2. Read the watch

Your watch terminal recorded the whole rollout:

```text
NAME               READY   UP-TO-DATE   AVAILABLE   AGE
nginx-deployment   3/3     3            3           2s
nginx-deployment   3/3     0            3           4s
nginx-deployment   3/3     1            3           4s
nginx-deployment   4/3     1            4           5s
nginx-deployment   3/3     1            3           5s
nginx-deployment   3/3     2            3           5s
nginx-deployment   4/3     2            4           6s
nginx-deployment   3/3     2            3           6s
nginx-deployment   3/3     3            3           6s
nginx-deployment   4/3     3            4           7s
nginx-deployment   3/3     3            3           7s
```

Here's where the three columns from [Creating and Managing Deployments](creating-deployments.md#1-create-it-and-read-its-status) pull apart:

- **`UP-TO-DATE`** drops to `0` the moment the template changes (no Pod runs `1.28` yet), then climbs `1`, `2`, `3` as new Pods replace old ones.
- **`AVAILABLE`** never goes below `3`. Users always had three Pods to talk to.
- **`READY`** briefly shows `4/3`: the one extra Pod that `maxSurge` allows, as in [Introduction to Deployments](introduction-to-deployments.md#what-happens-when-you-change-the-template).

Compare that with the ReplicaSet chapter, where forcing the same upgrade dropped `READY` to `0`.

## 3. Look at the ReplicaSets and Pods

```bash
kubectl get rs -l app=nginx -o wide
```

```text
NAME                          DESIRED   CURRENT   READY   AGE   CONTAINERS   IMAGES       SELECTOR
nginx-deployment-7b848bf6bc   3         3         3       6s    nginx        nginx:1.28   app=nginx,pod-template-hash=7b848bf6bc
nginx-deployment-86d7c4cfc4   0         0         0       9s    nginx        nginx:1.27   app=nginx,pod-template-hash=86d7c4cfc4
```

Two ReplicaSets now: a new one for `1.28` with all three Pods, and the old one for `1.27`, scaled to zero but kept. Each has its own `pod-template-hash` in its selector, so neither can claim the other's Pods.

```bash
kubectl get pods -l app=nginx
```

```text
NAME                                READY   STATUS    RESTARTS   AGE
nginx-deployment-7b848bf6bc-dhxwj   1/1     Running   0          4s
nginx-deployment-7b848bf6bc-rxprg   1/1     Running   0          3s
nginx-deployment-7b848bf6bc-sch4j   1/1     Running   0          6s
```

Every Pod is new, and named after the new ReplicaSet. No Pod was "upgraded in place": each old Pod was replaced by a new one, made from the new template.

## 4. Which changes cause a rollout?

A Deployment starts a rollout when the **Pod template** changes, meaning anything under `spec.template`. Changes anywhere else don't touch the Pods. Try a few, counting the ReplicaSets after each:

**Scale to 4** (`replicas` is outside the template):

```bash
sed -i 's/replicas: 3$/replicas: 4/' /tmp/deploy/nginx-deployment.yaml
kubectl apply -f /tmp/deploy/nginx-deployment.yaml
kubectl rollout status deployment/nginx-deployment
kubectl get rs -l app=nginx
```

```text
NAME                          DESIRED   CURRENT   READY   AGE
nginx-deployment-7b848bf6bc   4         4         4       18s
nginx-deployment-86d7c4cfc4   0         0         0       21s
```

Still two ReplicaSets. The current one was simply scaled to 4: one new Pod, no Pods replaced. Set it back to 3 the same way before continuing:

```bash
sed -i 's/replicas: 4$/replicas: 3/' /tmp/deploy/nginx-deployment.yaml
kubectl apply -f /tmp/deploy/nginx-deployment.yaml
```

**Add an environment variable** (inside the template). Open `/tmp/deploy/nginx-deployment.yaml` in your editor, and add the three `env` lines under the image, lined up with `image:`:

```yaml
      containers:
        - name: nginx
          image: nginx:1.28
          env:                       # add these three lines
            - name: GREETING
              value: hello
```

(Or do it in one go with GNU `sed`, which is fine on the node but not on a Mac: `sed -i '/^          image: nginx:1.28$/a\          env:\n            - name: GREETING\n              value: hello' /tmp/deploy/nginx-deployment.yaml`.)

```bash
kubectl apply -f /tmp/deploy/nginx-deployment.yaml
kubectl rollout status deployment/nginx-deployment
kubectl get rs -l app=nginx
```

```text
NAME                          DESIRED   CURRENT   READY   AGE
nginx-deployment-69d97f8956   3         3         3       3s
nginx-deployment-7b848bf6bc   0         0         0       22s
nginx-deployment-86d7c4cfc4   0         0         0       25s
```

A third ReplicaSet, and all three Pods replaced, even though the image didn't change. To the Deployment, any change to the template is a new version.

**Go back to the original template** (`1.28` → `1.27`, and remove the `env` lines):

```bash
sed -i 's/image: nginx:1.28$/image: nginx:1.27/; /env:/,/value: hello/d' /tmp/deploy/nginx-deployment.yaml
kubectl apply -f /tmp/deploy/nginx-deployment.yaml
kubectl rollout status deployment/nginx-deployment
kubectl get rs -l app=nginx
```

```text
NAME                          DESIRED   CURRENT   READY   AGE
nginx-deployment-69d97f8956   0         0         0       7s
nginx-deployment-7b848bf6bc   0         0         0       26s
nginx-deployment-86d7c4cfc4   3         3         3       29s
```

No fourth ReplicaSet. The template is identical to the first one, so its hash is identical too, and the Deployment scaled the **original** ReplicaSet, `86d7c4cfc4`, back up. This is how [rollbacks](understanding-rollouts.md) work.

In summary:

| You change… | Part of the template? | Rollout? |
|---|---|---|
| A container's `image` | Yes | ✅ New ReplicaSet, Pods replaced |
| A container's `env`, ports, command, resources… | Yes | ✅ New ReplicaSet, Pods replaced |
| Labels or annotations under `spec.template.metadata` | Yes | ✅ New ReplicaSet, Pods replaced |
| `replicas` | No | ❌ The current ReplicaSet is scaled |
| The Deployment's own `metadata` labels | No | ❌ Nothing happens to the Pods |
| The template, back to an earlier version | Yes | ✅ The earlier ReplicaSet is reused |

## The imperative shortcut

`kubectl set image` changes the image without editing a file:

```bash
kubectl set image deployment/nginx-deployment nginx=nginx:1.28
```

It triggers exactly the same rollout. But as in [Declarative Object Management](../object-management/declarative-management.md#dont-mix-approaches-on-one-object), your file still says `1.27`, so the next `kubectl apply` rolls it straight back. Use it for experiments; for anything you keep, change the file.

## Clean up

```bash
kubectl delete -f /tmp/deploy/nginx-deployment.yaml
rm -rf /tmp/deploy
```

## Best practices

- **Update an app by changing its template in the manifest**, then `kubectl diff` and `kubectl apply`.
- **Watch the rollout** with `kubectl rollout status`, and keep an eye on `AVAILABLE`: it should never drop below what you need.
- **Remember that any template change is a rollout.** Adding an environment variable or a label to the template replaces every Pod, just like a new image.
- **Don't delete old ReplicaSets.** Going back to an earlier template reuses them.

---

[← Creating and Managing Deployments](creating-deployments.md) · [↑ Contents](../../README.md) · [Understanding Rollouts →](understanding-rollouts.md)
