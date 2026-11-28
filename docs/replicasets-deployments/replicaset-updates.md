# ReplicaSets Can't Update Pods

> Change a ReplicaSet's Pod template, and find out why the running Pods stay the same.

---

A ReplicaSet keeps the right **number** of Pods running. But apps change: sooner or later you'll ship a new version. In this chapter you'll try to upgrade the nginx ReplicaSet from `1.27` to `1.28` by changing its image, and see why a ReplicaSet alone can't do it.

Start from a fresh copy of the ReplicaSet and create it:

```bash
mkdir /tmp/rs
cp manifests/replicasets-deployments/nginx-replicaset.yaml /tmp/rs/
kubectl apply -f /tmp/rs/nginx-replicaset.yaml
kubectl wait --for=condition=Ready pod -l app=nginx --timeout=60s
```

To see which image each Pod runs, ask `kubectl get` for exactly those columns:

```bash
kubectl get pods -l app=nginx -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[0].image
```

```text
NAME                     IMAGE
nginx-replicaset-2wdjf   nginx:1.27
nginx-replicaset-5swml   nginx:1.27
nginx-replicaset-t8jmc   nginx:1.27
```

(`custom-columns` takes `HEADER:field-path` pairs, using the same paths as [`kubectl explain`](../object-management/manifest-files.md#look-up-any-field-with-kubectl-explain). You'll use this command several times below.)

## 1. Change the image

Upgrade the template to `1.28`, preview, and apply:

```bash
sed -i 's/image: nginx:1.27$/image: nginx:1.28/' /tmp/rs/nginx-replicaset.yaml
kubectl diff -f /tmp/rs/nginx-replicaset.yaml
```

```diff
-      - image: nginx:1.27
+      - image: nginx:1.28
```

```bash
kubectl apply -f /tmp/rs/nginx-replicaset.yaml
```

```
replicaset.apps/nginx-replicaset configured
```

`configured`: the change was accepted. The ReplicaSet itself now says `1.28`:

```bash
kubectl get rs nginx-replicaset -o wide
```

```text
NAME               DESIRED   CURRENT   READY   AGE   CONTAINERS   IMAGES       SELECTOR
nginx-replicaset   3         3         3       7s    nginx        nginx:1.28   app=nginx
```

## 2. Look at the Pods

Wait as long as you like, then check the Pods again:

```bash
kubectl get pods -l app=nginx -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[0].image
```

```text
NAME                     IMAGE
nginx-replicaset-2wdjf   nginx:1.27
nginx-replicaset-5swml   nginx:1.27
nginx-replicaset-t8jmc   nginx:1.27
```

Same three Pods, same names, still `1.27`. Nothing happened, and nothing will.

That isn't a bug. Go back to the [loop](what-are-replicasets.md#desired-count-actual-count-and-a-loop): the ReplicaSet counts the Pods that match its selector. All three still carry `app: nginx`, so the count is three, which is what it wants, so it does nothing. The **template** is only a recipe for making *new* Pods. The ReplicaSet never compares running Pods against it.

## 3. Delete one Pod

A ReplicaSet only uses the template when it creates a Pod. So give it a reason to create one:

```bash
POD=$(kubectl get pods -l app=nginx -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod $POD
kubectl get pods -l app=nginx -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[0].image
```

```text
NAME                     IMAGE
nginx-replicaset-5swml   nginx:1.27
nginx-replicaset-t8jmc   nginx:1.27
nginx-replicaset-vjxqd   nginx:1.28
```

The replacement Pod runs `1.28`. Now your app runs **two versions at once**, and nothing in the ReplicaSet tells you so: `kubectl get rs` still shows `IMAGES nginx:1.28`, but two of its three Pods aren't. Whether a request gets the old version or the new one depends on which Pod it lands on.

## 4. Delete them all

To get every Pod onto `1.28`, every old Pod has to go. Start `kubectl get pods -l app=nginx -w` in a second terminal to watch, then delete them all at once:

```bash
kubectl delete pod -l app=nginx --wait=false
kubectl get rs nginx-replicaset
```

(`--wait=false` makes `delete` return right away. Without it, `delete` waits until the old Pods are completely gone, and by then the new ones are often ready, so the next command would already show the outage over.)

```text
NAME               DESIRED   CURRENT   READY   AGE
nginx-replicaset   3         3         0       14s
```

`READY 0`. For a few seconds, while the old Pods shut down and the new ones pull the image and start, **no Pod can serve anything**. Your app is down. In the watch terminal you'll see all three old Pods `Terminating` while three new ones are still `ContainerCreating`.

When the new Pods are running, check again:

```bash
kubectl get pods -l app=nginx -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[0].image
```

```text
NAME                     IMAGE
nginx-replicaset-778n6   nginx:1.28
nginx-replicaset-fdbmt   nginx:1.28
nginx-replicaset-kqnwb   nginx:1.28
```

All on `1.28`, at the price of an outage.

> Don't use `kubectl wait -l app=nginx` right after this delete. The selector still matches the old Pods while they're `Terminating`, so `wait` waits on them too, and times out. Watching with `-w` is more reliable here.

## What you'd need instead

You can avoid the outage by hand: delete **one** old Pod, wait until its replacement is ready, delete the next, and so on. That keeps most Pods serving the whole time. But now *you* are the controller: you have to watch readiness, remember which Pods are still old, decide how many to replace at a time, and know what to do if the new version crashes halfway through.

| What an upgrade needs | ReplicaSet |
|---|---|
| Notice that running Pods don't match the template | ✗ Never compares them |
| Replace old Pods gradually, keeping some serving | ✗ Only if you delete them yourself, one at a time |
| Stop if the new version doesn't come up | ✗ Keeps creating whatever the template says |
| Go back to the previous version | ✗ Only by editing the template back and deleting Pods again |

Every row is something a **Deployment** does for you. It doesn't change a ReplicaSet's template at all: it creates a **new** ReplicaSet for the new version, and shifts Pods from the old one to the new one step by step. That's [Introduction to Deployments](introduction-to-deployments.md).

## Clean up

```bash
kubectl delete -f /tmp/rs/nginx-replicaset.yaml
rm -rf /tmp/rs
```

## Best practices

- **Don't upgrade apps with a bare ReplicaSet.** Changing the template changes nothing that's running, and deleting Pods to force it causes either an outage or a lot of manual work. Use a [Deployment](introduction-to-deployments.md).
- **Check what Pods actually run**, not just what their controller says: `-o custom-columns=...IMAGE:.spec.containers[0].image` shows the real image of every Pod.
- **Never `kubectl delete pod -l …` on Pods that serve traffic** unless you accept that they all go down together.

---

[← Creating and Managing ReplicaSets](creating-replicasets.md) · [↑ Contents](../../README.md) · [ReplicaSets and Existing Pods →](replicaset-existing-pods.md)
