# From Imperative to Declarative

> Hand objects you created with commands over to kubectl apply.

---

Sooner or later you'll have objects that were made by hand, with `kubectl run`, `kubectl expose`, or `create -f`, and you'll want to manage them with files and [`kubectl apply`](declarative-management.md) from now on. You don't need to delete and recreate them. But you do need to take over carefully, because the live objects may have drifted from whatever files you have.

This chapter walks through one migration with nginx: write the files, compare them with what's running, apply, and tidy up what's left.

## The starting point: objects made by hand

Create a Pod and a Service the imperative way, then change them a little, the way real objects get changed over time:

```bash
kubectl run nginx --image=nginx:1.27 --port=80 --labels=app=nginx
kubectl expose pod nginx --type=NodePort --port=80
kubectl wait --for=condition=Ready pod/nginx --timeout=60s

kubectl set image pod/nginx nginx=nginx:1.28     # someone upgraded it
kubectl label pod nginx tier=frontend            # someone labeled it
```

Neither object has the annotation `apply` relies on:

```bash
kubectl get pod nginx -o jsonpath='{.metadata.annotations}'     # prints nothing
```

> Don't use `kubectl apply view-last-applied` to check this. On an object without the annotation, it prints nothing and still exits successfully, which looks the same as a mistake in your command.

## 1. Write the files

You need a manifest for each object. [Generating Manifests](generating-manifests.md) shows how to produce them from the commands you'd run. For this chapter, the repo's [`nginx-pod.yaml`](../../manifests/object-management/nginx-pod.yaml) and [`nginx-svc.yaml`](../../manifests/object-management/nginx-svc.yaml) describe exactly what the `run` and `expose` above created. Copy them:

```bash
mkdir /tmp/nginx
cp manifests/object-management/nginx-pod.yaml manifests/object-management/nginx-svc.yaml /tmp/nginx/
```

Note what they describe: the objects as they were **created**. Not the upgrade, and not the extra label.

## 2. Diff before you apply

This is the step that matters. Ask what `apply` would change:

```bash
kubectl diff -f /tmp/nginx/
```

```diff
--- /tmp/LIVE-…/v1.Pod.default.nginx
+++ /tmp/MERGED-…/v1.Pod.default.nginx
@@ -11,7 +11,7 @@
   uid: 4e4ca0f5-8cf8-4dbc-9aa3-178fbfca3989
 spec:
   containers:
-  - image: nginx:1.28
+  - image: nginx:1.27
     imagePullPolicy: IfNotPresent
     name: nginx
     ports:
```

Applying these files now would **downgrade** nginx to `1.27`, undoing the upgrade someone made by hand. Your file says `1.27`, so `apply` would make it `1.27`. Nothing warns you about this except `diff`.

Fix the file so it describes what should be running:

```bash
sed -i 's/image: nginx:1.27$/image: nginx:1.28/' /tmp/nginx/nginx-pod.yaml
kubectl diff -f /tmp/nginx/
```

No output, exit status `0`: applying the files changes nothing. That's the state you want before taking over.

Two things `diff` does **not** show:

- **The `tier=frontend` label.** It isn't in your file, so `apply` won't touch it. You'll deal with it in step 4.
- **The annotation `apply` is about to add.** `diff` reports "no changes", yet the first `apply` still writes the annotation and prints a warning. That's expected.

## 3. Apply

```bash
kubectl apply -f /tmp/nginx/
```

```text
Warning: resource pods/nginx is missing the kubectl.kubernetes.io/last-applied-configuration annotation which is required by kubectl apply. kubectl apply should only be used on resources created declaratively by either kubectl create --save-config or kubectl apply. The missing annotation will be patched automatically.
pod/nginx configured
Warning: resource services/nginx is missing the kubectl.kubernetes.io/last-applied-configuration annotation which is required by kubectl apply. ...
service/nginx configured
```

The last sentence of the warning is the important one: **the missing annotation will be patched automatically.** `configured` here means "annotation added"; nothing else changed. Apply once more to confirm the handover:

```bash
kubectl apply -f /tmp/nginx/
```

```
pod/nginx unchanged
service/nginx unchanged
```

No warnings, nothing to do. Both objects now carry the annotation, and `kubectl apply view-last-applied pod nginx` prints your file. From here on, they're managed declaratively.

## 4. Deal with the leftovers

Look at the Pod's labels:

```bash
kubectl get pod nginx --show-labels
```

```text
NAME    READY   STATUS    RESTARTS   AGE   LABELS
nginx   1/1     Running   1          4s    app=nginx,tier=frontend
```

`tier=frontend` is still there. It was never in your file, so it's not in the last-applied copy either, and by the [three rules](declarative-management.md#4-how-apply-remembers-what-it-manages) `apply` will **never** touch it: not now, and not if you later decide you don't want it. For each leftover like this, choose:

| You want it… | Do this |
|---|---|
| **Managed by the file** | Add it to the file and `apply`. From then on, removing it from the file removes it from the object. |
| **Gone** | Remove it by hand, once: `kubectl label pod nginx tier-` (the trailing `-` deletes a label). |
| **Left alone on purpose** | Do nothing. Something else owns it, and `apply` won't interfere. |

Say nobody needs it:

```bash
kubectl label pod nginx tier-
```

```
pod/nginx unlabeled
```

Now the live objects and your files agree, and every field that matters is either in a file or deliberately left to something else.

## 5. From now on

- **Change objects through their files**, then `kubectl apply`. An imperative change to a field in the file, like another `set image`, is undone by the next `apply`; the file wins.
- **Create new objects with `kubectl apply -f`** from the start, so they get the annotation immediately.
- If a tool or habit insists on `create`, add **`--save-config`**: `kubectl create --save-config -f nginx-pod.yaml` writes the annotation at creation time, and the first `apply` afterwards reports `unchanged` with no warning.

## Clean up

```bash
kubectl delete -f /tmp/nginx/
rm -rf /tmp/nginx
```

## Best practices

- **Always `kubectl diff` before the first `apply` on an existing object.** Your files describe what you *think* is running; the live object is what *is* running. The diff shows where they disagree.
- **Update the file to match reality first**, unless you really want `apply` to revert a manual change.
- **Sweep for leftovers** (labels, annotations, fields set by hand) and decide for each: manage it in the file, remove it, or leave it alone on purpose.
- **Migrate one object (or one app) at a time**, and apply twice to confirm the result is `unchanged`.

---

[← Declarative Object Management](declarative-management.md) · [↑ Contents](../../README.md) · [Multiple Objects in One File →](multiple-objects-per-file.md)
