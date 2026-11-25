# ReplicaSets and Existing Pods

> How a ReplicaSet's selector adopts Pods it didn't create, and releases the ones that stop matching.

---

A ReplicaSet doesn't keep a list of "its" Pods. As [What Are ReplicaSets](what-are-replicasets.md#labels-and-selectors) put it, it **asks**, over and over: "which Pods match my selector?" That has a side effect that surprises almost everyone: it counts Pods it never created, as long as their labels match.

This chapter walks through what that means in practice, using the same [`nginx-replicaset.yaml`](../../manifests/replicasets-deployments/nginx-replicaset.yaml) as before (three Pods, selector `app: nginx`). You won't edit it, so apply it straight from the repo.

To see which Pods a ReplicaSet has claimed, you'll use this a lot:

```bash
kubectl get pods -l app=nginx -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[0].image,OWNER:.metadata.ownerReferences[0].name
```

`OWNER` comes from the `ownerReferences` you met in [Creating and Managing ReplicaSets](creating-replicasets.md#1-create-it). `<none>` means a bare Pod.

## 1. A Pod that was there first

Start a bare Pod that happens to carry `app=nginx`. To make the point, it isn't even nginx: it's busybox, sleeping.

```bash
kubectl run stray --image=busybox:1.36 --labels=app=nginx -- sleep 3600
kubectl wait --for=condition=Ready pod/stray --timeout=60s
```

Now create the ReplicaSet, which wants three Pods:

```bash
kubectl apply -f manifests/replicasets-deployments/nginx-replicaset.yaml
kubectl get pods -l app=nginx -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[0].image,OWNER:.metadata.ownerReferences[0].name
```

```text
NAME                     IMAGE          OWNER
nginx-replicaset-bvffx   nginx:1.27     nginx-replicaset
nginx-replicaset-trjrg   nginx:1.27     nginx-replicaset
stray                    busybox:1.36   nginx-replicaset
```

It created only **two** Pods. `stray` matched the selector and had no owner, so the ReplicaSet **adopted** it: it wrote itself into `stray`'s `ownerReferences` and counted it as one of its three. `kubectl describe rs nginx-replicaset` shows just two `SuccessfulCreate` events.

The ReplicaSet looked only at the label. It didn't check the image, or whether the Pod resembles its template at all. Your "three nginx replicas" are really two nginx Pods and a busybox that serves nothing. And since `stray` now belongs to the ReplicaSet, deleting the ReplicaSet will delete `stray` too.

## 2. A Pod that arrives later

The ReplicaSet now has its three. Start `kubectl get pods -l app=nginx -w` in a second terminal to watch, then start one more bare Pod with the same label:

```bash
kubectl run extra --image=nginx:1.27 --labels=app=nginx
```

In the watch terminal, `extra` appears and is `Terminating` almost at once. Give it a couple of seconds, then look for it:

```bash
kubectl get pod extra
```

```
Error from server (NotFound): pods "extra" not found
```

Gone. The ReplicaSet adopted it, counted **four**, and deleted one to get back to three. It picked the newest Pod, `extra`:

```bash
kubectl describe rs nginx-replicaset
```

```text
  Normal  SuccessfulDelete  2s    replicaset-controller  Deleted pod: extra
```

Imagine `extra` was someone else's Pod, labeled `app=nginx` because that seemed like a sensible name. It would vanish the moment it started, and the only clue is an event on a ReplicaSet they've never heard of.

## 3. Taking a Pod out by removing its label

It works the other way too. Remove the `app` label from one of the ReplicaSet's Pods (the trailing `-` deletes a label):

```bash
POD=$(kubectl get pods -l app=nginx -o jsonpath='{.items[0].metadata.name}')
kubectl label pod $POD app-
kubectl get pods --show-labels
```

```text
NAME                     READY   STATUS    RESTARTS   AGE   LABELS
nginx-replicaset-bvffx   1/1     Running   0          17s   <none>
nginx-replicaset-t8wmz   1/1     Running   0          4s    app=nginx
nginx-replicaset-trjrg   1/1     Running   0          17s   app=nginx
stray                    1/1     Running   0          19s   app=nginx
```

`bvffx` no longer matches, so the ReplicaSet **released** it: its `ownerReferences` are now empty, and the ReplicaSet created `t8wmz` to get back to three. `bvffx` keeps running as a bare Pod.

This one is actually useful. If a Pod misbehaves and you want to investigate, take it out by removing its label: the ReplicaSet replaces it right away, so your app keeps its full count, and you can `exec` into the released Pod and read its logs at your leisure. (A [Service](../services/what-are-services.md) that selects `app=nginx` stops sending it traffic too.)

## 4. Deleting the ReplicaSet

Delete the ReplicaSet, and then the released Pod, which no longer belongs to anything:

```bash
kubectl delete -f manifests/replicasets-deployments/nginx-replicaset.yaml
kubectl delete pod $POD
kubectl get pods
```

```text
NAME    READY   STATUS        RESTARTS   AGE
stray   1/1     Terminating   0          45s
```

The ReplicaSet takes **every** Pod it owns with it, including `stray`, which it never created. The `delete` command returns right away (the ReplicaSet's Pods are cleaned up in the background), but `stray` stays `Terminating` for about 30 seconds. `sleep` ignores the stop signal, so Kubernetes waits out the 30-second grace period before killing it (the problem color-api's [signal handlers](../pods/from-dockerfile-to-pod.md#1-the-app) solve). Wait for it to disappear before the next step.

## 5. Orphaned Pods get adopted again

In [Creating and Managing ReplicaSets](creating-replicasets.md#4-delete-it) you saw `--cascade=orphan`: delete a ReplicaSet but keep its Pods. Now you know what happens next. Create the ReplicaSet, orphan its Pods, and apply it again:

```bash
kubectl apply -f manifests/replicasets-deployments/nginx-replicaset.yaml
kubectl wait --for=condition=Ready pod -l app=nginx --timeout=60s
kubectl delete -f manifests/replicasets-deployments/nginx-replicaset.yaml --cascade=orphan
kubectl get pods -l app=nginx -o custom-columns=NAME:.metadata.name,OWNER:.metadata.ownerReferences[0].name
```

```text
NAME                     OWNER
nginx-replicaset-r52l7   <none>
nginx-replicaset-tn67j   <none>
nginx-replicaset-wntrd   <none>
```

Three bare Pods. Apply the ReplicaSet once more:

```bash
kubectl apply -f manifests/replicasets-deployments/nginx-replicaset.yaml
kubectl get pods -l app=nginx -o custom-columns=NAME:.metadata.name,OWNER:.metadata.ownerReferences[0].name
```

```text
NAME                     OWNER
nginx-replicaset-r52l7   nginx-replicaset
nginx-replicaset-tn67j   nginx-replicaset
nginx-replicaset-wntrd   nginx-replicaset
```

The new ReplicaSet adopted all three and created **none**: `kubectl describe rs nginx-replicaset` shows `Events: <none>`. The same Pods, the same names, now owned again.

## The rules

| The Pod… | The ReplicaSet… |
|---|---|
| matches the selector and has **no** owner | **adopts** it, and counts it |
| matches the selector, but already belongs to **another** controller | **ignores** it. It never takes Pods from another owner |
| belongs to it, but **stops** matching (a label changed) | **releases** it, and creates a replacement |
| belongs to it when the ReplicaSet is deleted | deletes it too, unless you use `--cascade=orphan` |

The second rule means two ReplicaSets with the same selector don't fight: each keeps its own three Pods, and you end up with six. That's quietly wrong in its own way, since a Service selecting `app=nginx` would spread traffic over all six.

## Clean up

```bash
kubectl delete -f manifests/replicasets-deployments/nginx-replicaset.yaml
```

## Best practices

- **Make selector labels specific to one app.** `app: nginx` is fine in a tutorial; in a shared cluster, a label anyone might reuse invites accidental adoption.
- **Don't create bare Pods with labels a controller selects on.** They'll be adopted, deleted, or counted as replicas they aren't.
- **Check `ownerReferences`** when Pods appear or disappear unexpectedly. `kubectl describe rs` Events (`SuccessfulCreate`, `SuccessfulDelete`) show what the controller did.
- **To debug one Pod without losing capacity, remove its selector label.** The controller replaces it, and you can inspect the released Pod. Delete it by name when you're done.

---

[← ReplicaSets Can't Update Pods](replicaset-updates.md) · [↑ Contents](../../README.md) · [Introduction to Deployments →](introduction-to-deployments.md)
