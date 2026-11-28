# Declarative Object Management

> kubectl apply and diff: describe the desired state and let the cluster converge on it.

---

This is the third approach from [Object Management](object-management.md), and the one this guide uses from here on. You still keep your objects in files, but you stop choosing between `create` and `replace`. One command looks at your file and the live object, and works out what to do:

| Command | Does |
|---|---|
| `kubectl apply -f <file or dir>` | Create what's missing, update what differs, leave the rest alone |
| `kubectl diff -f <file or dir>` | Show what `apply` *would* change, without changing anything |
| `kubectl delete -f <file or dir>` | Delete what the files describe |

This chapter repeats the [previous one](imperative-object-configuration.md) step for step, with the same nginx Pod and Service, so you can compare each result with what `create` and `replace` did.

## The files

The same two manifests as last time, [`nginx-pod.yaml`](../../manifests/object-management/nginx-pod.yaml) and [`nginx-svc.yaml`](../../manifests/object-management/nginx-svc.yaml): a Pod running `nginx:1.27`, and a NodePort Service on port 80. Copy them into a fresh directory:

```bash
mkdir /tmp/nginx
cp manifests/object-management/nginx-pod.yaml manifests/object-management/nginx-svc.yaml /tmp/nginx/
```

## 1. Apply creates

```bash
kubectl apply -f /tmp/nginx/
```

```
pod/nginx created
service/nginx created
```

Now run the exact same command again:

```bash
kubectl apply -f /tmp/nginx/
```

```
pod/nginx unchanged
service/nginx unchanged
```

No `AlreadyExists` error. The objects already match the files, so there's nothing to do, and `apply` says so. You can run `apply` as often as you like: it only acts on differences. That's what makes it safe to point at a whole directory, where some objects exist and some don't.

## 2. Preview with `diff`, then apply

Upgrade nginx from `1.27` to `1.28`, the task that took `replace --force` and a brand-new Pod last time. Change the image in your file:

```bash
sed -i 's/image: nginx:1.27$/image: nginx:1.28/' /tmp/nginx/nginx-pod.yaml
```

Before touching the cluster, ask what would change:

```bash
kubectl diff -f /tmp/nginx/
```

```diff
--- /tmp/LIVE-1956395162/v1.Pod.default.nginx
+++ /tmp/MERGED-1959076615/v1.Pod.default.nginx
@@ -13,7 +13,7 @@
   uid: fb1de54a-11ee-4b04-96c7-c0e4a7ccd12c
 spec:
   containers:
-  - image: nginx:1.27
+  - image: nginx:1.28
     imagePullPolicy: IfNotPresent
     name: nginx
     ports:
```

`LIVE` is the object in the cluster now, `MERGED` is what it would become. One line changes, in the Pod, and nothing in the Service. (`diff` exits with status `1` when there are differences and `0` when there are none, which is handy in scripts.)

Happy with that? Apply it:

```bash
kubectl apply -f /tmp/nginx/
```

```
pod/nginx configured
service/nginx unchanged
```

`configured` means the update was accepted, not that it's done. The kubelet still has to pull `1.28` and restart the container, which takes a few seconds; until then, the old container keeps running. Watch the Pod: `-w` prints a new line every time its status changes. Once you see a line with `RESTARTS` at `1`, press Ctrl+C:

```bash
kubectl get pod nginx -o wide -w
```

```text
NAME    READY   STATUS    RESTARTS      AGE   IP            NODE     ...
nginx   1/1     Running   1 (15s ago)   18s   10.244.0.43   node-1   ...
```

Now check the version:

```bash
kubectl exec nginx -- nginx -v     # nginx version: nginx/1.28.x
```

Compare that with `replace --force`:

| | `replace --force` | `apply` |
|---|---|---|
| The Pod | Deleted, and a new one created | **The same Pod**, updated in place |
| IP | New | **Unchanged** |
| `RESTARTS` | `0` (it's a new Pod) | `1` (the container restarted with the new image) |

Why does `apply` succeed where `replace` was rejected? `replace` sent your whole file as the new object, which would have wiped the fields the cluster filled in. `apply` sends only the **difference**: "change the image". The image is one of the few Pod fields that may change, so the update is allowed.

## 3. Changes made elsewhere survive

Same scenario as last chapter. A teammate labels the live Service:

```bash
kubectl label svc nginx team=web
```

Meanwhile, you change the Service's port to `8080` in your file, and apply:

```bash
sed -i 's/- port: 80$/- port: 8080/' /tmp/nginx/nginx-svc.yaml
kubectl apply -f /tmp/nginx/nginx-svc.yaml
kubectl get svc nginx --show-labels
```

```text
service/nginx configured

NAME    TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)          AGE   LABELS
nginx   NodePort   10.101.65.163   <none>        8080:32482/TCP   19s   app=nginx,team=web
```

Your port change is in, **and** the teammate's `team=web` label is still there. With `replace`, it was silently deleted. `apply` changed only what your file is responsible for, and `team=web` never was.

## 4. How `apply` remembers what it manages

How does `apply` know that `team=web` isn't its business? Every time you apply, kubectl stores a copy of your file **on the object itself**, in an annotation named `kubectl.kubernetes.io/last-applied-configuration`. You can read it back:

```bash
kubectl apply view-last-applied svc nginx
```

```yaml
apiVersion: v1
kind: Service
metadata:
  annotations: {}
  labels:
    app: nginx
  name: nginx
  namespace: default
spec:
  ports:
  - port: 8080
    targetPort: 80
  selector:
    app: nginx
  type: NodePort
```

That's your file, as of your last `apply`. No `team=web` in it. On the next `apply`, kubectl compares three versions of the object:

| Version | Where it comes from |
|---|---|
| **Your file** | The manifest you're applying now |
| **Last applied** | The annotation: your file as of the previous `apply` |
| **Live** | The object in the cluster, including everyone else's changes |

and follows three rules for each field:

| The field is… | `apply`… |
|---|---|
| In your file | Sets it to your value |
| In the last-applied copy, but **no longer** in your file | **Deletes** it: you removed it, so you want it gone |
| In neither (only in the live object) | **Leaves it alone**: someone else owns it |

`team=web` falls under the last rule. The second rule is the one that surprises people.

## 5. Deleting a line deletes the field

Add a `tier: web` label to the Service in your file, and apply. (The `sed` below uses a GNU-only form, which is fine on the node. On a Mac, add the line in your editor instead.)

```bash
sed -i '0,/^    app: nginx$/s//    app: nginx\n    tier: web/' /tmp/nginx/nginx-svc.yaml   # first match only: the labels, not the selector
kubectl apply -f /tmp/nginx/nginx-svc.yaml
kubectl get svc nginx -o jsonpath='{.metadata.labels}'     # {"app":"nginx","team":"web","tier":"web"}
```

Now `tier: web` is in the last-applied copy. Delete the line from your file again, and check with `diff` first:

```bash
sed -i '/^    tier: web$/d' /tmp/nginx/nginx-svc.yaml
kubectl diff -f /tmp/nginx/nginx-svc.yaml
```

```diff
@@ -8,7 +8,6 @@
   labels:
     app: nginx
     team: web
-    tier: web
   name: nginx
```

```bash
kubectl apply -f /tmp/nginx/nginx-svc.yaml
kubectl get svc nginx -o jsonpath='{.metadata.labels}'     # {"app":"nginx","team":"web"}
```

`tier` is gone, because you used to manage it and stopped. `team` stays, because you never managed it. This is useful (deleting a line really removes it), but it's also the trap from [Object Management](object-management.md): delete `replicas: 3` from a Deployment's file "so an autoscaler can own it", and `apply` *removes* the field, which resets it to the default of 1. **Removing a line means "delete this field", not "stop managing it".** Run `kubectl diff` first, and it shows you which one you're about to do.

## 6. Delete

`delete -f` works the same as before:

```bash
kubectl delete -f /tmp/nginx/
```

```
pod "nginx" deleted
service "nginx" deleted
```

Note that `apply` never deletes whole objects on its own. If you delete `nginx-svc.yaml` from the directory and apply again, the Service stays in the cluster; `apply` simply doesn't look at it anymore. Delete the object with `kubectl delete -f` **before** you remove its file.

## Don't mix approaches on one object

Everything above depends on the last-applied annotation, and objects made with `kubectl run`, `kubectl create`, or `create -f` don't have one. Imperative changes to fields that *are* in your file also get overwritten on the next `apply`. Once an object is managed with `apply`, change it through its file. [From Imperative to Declarative](imperative-to-declarative.md) shows how to hand an existing object over to `apply`.

> There's also **server-side apply** (`kubectl apply --server-side`), where the API server tracks which tool owns each field instead of kubectl keeping an annotation. It follows the same idea. The client-side `apply` in this chapter is the default, and what you'll see in most guides.

## Clean up

The objects are already deleted. Remove the copies:

```bash
rm -rf /tmp/nginx
```

## Best practices

- **Use `kubectl apply -f` for everything you keep in files**, and keep those files in Git. The file is the source of truth: change it, then apply.
- **Run `kubectl diff -f` before `apply`**, especially after deleting lines.
- **Apply whole directories.** `apply` is safe to repeat, so `kubectl apply -f manifests/` is a fine way to sync everything.
- **Don't change applied objects with imperative commands**, except for fields your file doesn't set. Otherwise the next `apply` undoes your change, or you end up with a file that no longer describes what's running.
- **Delete objects before deleting their files.** `apply` won't remove an object just because its file is gone.

---

[← Imperative Commands with Files](imperative-object-configuration.md) · [↑ Contents](../../README.md) · [From Imperative to Declarative →](imperative-to-declarative.md)
