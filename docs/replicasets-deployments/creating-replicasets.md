# Creating and Managing ReplicaSets

> Write a ReplicaSet, watch it create Pods, and see it heal and scale.

---

[What Are ReplicaSets](what-are-replicasets.md) described the loop: count the Pods that match the selector, and create or delete until the count is right. Now you'll watch it run. You'll create the nginx ReplicaSet, delete one of its Pods, scale it up and down, and delete it.

Work on a copy, since you'll edit it:

```bash
mkdir /tmp/rs
cp manifests/replicasets-deployments/nginx-replicaset.yaml /tmp/rs/
```

It's the manifest from the previous chapter: three Pods, selector `app: nginx`, image `nginx:1.27`.

## 1. Create it

```bash
kubectl apply -f /tmp/rs/nginx-replicaset.yaml
kubectl get rs
```

```text
NAME               DESIRED   CURRENT   READY   AGE
nginx-replicaset   3         3         0       1s
```

`rs` is the short name for `replicasets`. The three numbers are the loop at a glance:

| Column | Means |
|---|---|
| `DESIRED` | `replicas` from the spec: what you asked for |
| `CURRENT` | How many Pods it has created and still counts |
| `READY` | How many of those are ready to serve |

A moment later, `READY` reaches `3`. Look at the Pods:

```bash
kubectl get pods -l app=nginx
```

```text
NAME                     READY   STATUS    RESTARTS   AGE
nginx-replicaset-5cs2x   1/1     Running   0          2s
nginx-replicaset-cgrvm   1/1     Running   0          2s
nginx-replicaset-hpn8m   1/1     Running   0          2s
```

Each name is the ReplicaSet's name plus a random suffix, so yours will differ. Save the first one in a variable, so the next commands work as-is:

```bash
POD=$(kubectl get pods -l app=nginx -o jsonpath='{.items[0].metadata.name}')
echo $POD                     # e.g. nginx-replicaset-5cs2x
```

Each Pod records who created it, in `metadata.ownerReferences`:

```bash
kubectl get pod $POD -o jsonpath='{.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}'
```

```
ReplicaSet/nginx-replicaset
```

That's how you can always tell a bare Pod from one a controller manages.

## 2. Delete a Pod, and watch it come back

> 💡 First, start `kubectl get pods -l app=nginx -w` in a second terminal (or [k9s](../cluster-setup/k9s.md) on `:pods`). When you delete, you'll see the old Pod go `Terminating` and the new one appear almost at the same moment.

Delete the Pod you saved:

```bash
kubectl delete pod $POD
kubectl get pods -l app=nginx
```

```text
NAME                     READY   STATUS    RESTARTS   AGE
nginx-replicaset-cgrvm   1/1     Running   0          4s
nginx-replicaset-hpn8m   1/1     Running   0          4s
nginx-replicaset-krzmk   1/1     Running   0          1s
```

Three Pods again. The deleted Pod (`5cs2x` here) is gone for good, and a **new** Pod (`krzmk`) took its place: new name, new IP, one second old. The ReplicaSet didn't bring the old Pod back; it saw two Pods where it wanted three, and made a third.

The ReplicaSet's Events tell the same story:

```bash
kubectl describe rs nginx-replicaset
```

```text
Events:
  Type    Reason            Age   From                   Message
  ----    ------            ----  ----                   -------
  Normal  SuccessfulCreate  4s    replicaset-controller  Created pod: nginx-replicaset-5cs2x
  Normal  SuccessfulCreate  4s    replicaset-controller  Created pod: nginx-replicaset-cgrvm
  Normal  SuccessfulCreate  4s    replicaset-controller  Created pod: nginx-replicaset-hpn8m
  Normal  SuccessfulCreate  1s    replicaset-controller  Created pod: nginx-replicaset-krzmk
```

## 3. Scale it

### The declarative way: change the file

Change `replicas` in your copy from `3` to `5`, and preview it:

```bash
sed -i 's/replicas: 3$/replicas: 5/' /tmp/rs/nginx-replicaset.yaml
kubectl diff -f /tmp/rs/nginx-replicaset.yaml
```

```diff
-  replicas: 3
+  replicas: 5
```

(`diff` also shows `generation` going from `1` to `2`: the cluster counts every change to the spec.) Apply it:

```bash
kubectl apply -f /tmp/rs/nginx-replicaset.yaml
kubectl get rs nginx-replicaset
```

```text
NAME               DESIRED   CURRENT   READY   AGE
nginx-replicaset   5         5         5       12s
```

Two new Pods, made from the same template.

### The imperative way: `kubectl scale`

For a quick experiment, you can set the count directly:

```bash
kubectl scale rs nginx-replicaset --replicas=2
kubectl get pods -l app=nginx
```

```text
NAME                     READY   STATUS    RESTARTS   AGE
nginx-replicaset-cgrvm   1/1     Running   0          15s
nginx-replicaset-hpn8m   1/1     Running   0          15s
```

Three Pods were deleted (`describe rs` shows a `SuccessfulDelete` event for each). Notice **which** three: the two survivors are the oldest Pods. When it scales down, a ReplicaSet prefers to remove the newest ones, along with any that aren't ready yet.

### The file still wins

Your file still says `5`. Apply it again:

```bash
kubectl apply -f /tmp/rs/nginx-replicaset.yaml
kubectl get rs nginx-replicaset
```

```text
NAME               DESIRED   CURRENT   READY   AGE
nginx-replicaset   5         5         5       18s
```

Back to five. This is the rule from [Declarative Object Management](../object-management/declarative-management.md#dont-mix-approaches-on-one-object): `replicas` is in your file, so the next `apply` overwrites whatever `kubectl scale` set. Use `scale` for experiments, and change the file for anything you mean to keep.

## 4. Delete it

Deleting a ReplicaSet deletes its Pods too:

```bash
kubectl delete -f /tmp/rs/nginx-replicaset.yaml
kubectl get pods -l app=nginx
```

```text
NAME                     READY   STATUS        RESTARTS   AGE
nginx-replicaset-bm9z4   1/1     Terminating   0          4s
nginx-replicaset-cgrvm   1/1     Terminating   0          19s
...
```

A few seconds later, they're all gone. The Pods' `ownerReferences` are what tie them to the ReplicaSet, so Kubernetes cleans them up with it.

> If you ever want to remove a ReplicaSet but **keep** its Pods running, add `--cascade=orphan`. The Pods lose their `ownerReferences` and become bare Pods again. What happens when a new ReplicaSet with a matching selector meets them is the subject of [ReplicaSets and Existing Pods](replicaset-existing-pods.md).

## Clean up

The ReplicaSet and its Pods are already deleted. Remove the copy:

```bash
rm -rf /tmp/rs
```

## Best practices

- **Read `DESIRED`, `CURRENT`, and `READY` together.** If they stay apart, `kubectl describe rs` shows in its Events why Pods aren't being created or aren't ready.
- **Scale by changing the file**, then `apply`. `kubectl scale` is fine for experiments, but the next `apply` undoes it.
- **Don't try to fix a managed Pod by hand.** Delete it, and the ReplicaSet replaces it with a fresh one from the template.
- **Check `ownerReferences`** when you're not sure whether a Pod is bare or managed, and by what.

---

[← What Are ReplicaSets](what-are-replicasets.md) · [↑ Contents](../../README.md) · [ReplicaSets Can't Update Pods →](replicaset-updates.md)
