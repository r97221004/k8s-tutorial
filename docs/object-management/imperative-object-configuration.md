# Imperative Commands with Files

> create -f, replace -f, and delete -f: files driven by imperative commands, and why they fall short.

---

This is the second approach from [Object Management](object-management.md): the objects live in files, but **you** still pick the operation each time. Three verbs cover it:

| Command | Does |
|---|---|
| `kubectl create -f <file>` | Create what the file describes |
| `kubectl replace -f <file>` | Overwrite the live object with the file |
| `kubectl delete -f <file>` | Delete what the file describes |

Each one does exactly that, and nothing else. The rest of the chapter is about what happens when the cluster isn't in the state the verb expects.

Like [Generating Manifests](generating-manifests.md), this chapter uses plain `nginx`, so every command works as-is.

## The files

Two manifests, a Pod and a NodePort Service in front of it:

▶ **Runnable manifests:** [`nginx-pod.yaml`](../../manifests/object-management/nginx-pod.yaml) and [`nginx-svc.yaml`](../../manifests/object-management/nginx-svc.yaml) in `manifests/object-management/`

```yaml
# nginx-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
  labels:
    app: nginx
spec:
  containers:
    - name: nginx
      image: nginx:1.27
      ports:
        - containerPort: 80
```

```yaml
# nginx-svc.yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx
  labels:
    app: nginx
spec:
  type: NodePort
  selector:
    app: nginx
  ports:
    - port: 80
      targetPort: 80
```

You'll edit them along the way, so copy both into a directory of their own:

```bash
mkdir /tmp/nginx
cp manifests/object-management/nginx-pod.yaml manifests/object-management/nginx-svc.yaml /tmp/nginx/
```

## 1. `create -f`

Create the Pod from its file:

```bash
kubectl create -f /tmp/nginx/nginx-pod.yaml
```

```
pod/nginx created
```

`-f` also takes a directory, and acts on every manifest in it. Point it at `/tmp/nginx/` to create the Service too:

```bash
kubectl create -f /tmp/nginx/
```

```
service/nginx created
Error from server (AlreadyExists): error when creating "/tmp/nginx/nginx-pod.yaml": pods "nginx" already exists
```

The Service was created, but the command still **failed**, because the Pod already existed. `create` only knows one thing: create. It can't tell "already there and fine" from "already there and different", so it refuses both. Run it once more and both files fail.

The more files you manage, the more this hurts: to use `create -f` on a directory, you have to know which objects in it don't exist yet.

## 2. `replace -f`

`replace` is the "update" verb. It sends your file as the **complete new version** of the object.

### It throws away changes made elsewhere

A teammate adds a label to the live Service:

```bash
kubectl label svc nginx team=web
```

Meanwhile, you change the Service's port to `8080` in your file, and replace:

```bash
sed -i 's/- port: 80$/- port: 8080/' /tmp/nginx/nginx-svc.yaml
kubectl replace -f /tmp/nginx/nginx-svc.yaml
kubectl get svc nginx --show-labels
```

```text
NAME    TYPE       CLUSTER-IP       EXTERNAL-IP   PORT(S)          AGE   LABELS
nginx   NodePort   10.100.122.164   <none>        8080:31429/TCP   1s    app=nginx
```

Your port change is in. The teammate's `team=web` label is **gone**: it wasn't in your file, so it isn't in the object anymore. Nothing warned either of you.

(The `CLUSTER-IP` and the node port `31429` did survive. The cluster assigned those, and keeps them when your file leaves them out. Fields *you* could have set, like labels, get no such protection.)

### It doesn't work on Pods, with your own file

Now try replacing the Pod with its file, **unchanged**:

```bash
kubectl replace -f /tmp/nginx/nginx-pod.yaml
```

```
The Pod "nginx" is invalid: spec: Forbidden: pod updates may not change fields other than `spec.containers[*].image`, ...
```

You changed nothing, and it still fails. The diff printed under the error shows why: it marks `NodeName`, `ServiceAccountName`, and the token `Volumes` as removed. As [Manifest Files](manifest-files.md#what-the-cluster-added) showed, the cluster filled in fields your file doesn't have, like `nodeName` and the service account volume. Replacing the live Pod with your file would remove them, which counts as changing the Pod's immutable spec.

(It does work if you start from the full live object instead: save `kubectl get pod nginx -o yaml`, change only the `image`, and `replace` accepts it. But that file is a snapshot of one live Pod, not a manifest you'd keep.)

The escape hatch is `--force`, which **deletes** the object and creates it again from the file:

```bash
kubectl replace --force -f /tmp/nginx/nginx-pod.yaml
```

```
pod "nginx" deleted
pod/nginx replaced
```

That works, but it's a brand-new Pod: new `uid`, new IP, and nothing serving while the old one is gone.

### It fails when there's nothing to replace

Try to replace a Pod that was never created. Rename it to `nginx-2` on the fly, and pipe the result to `replace` (`-f -` reads the manifest from stdin):

```bash
sed 's/^  name: nginx$/  name: nginx-2/' /tmp/nginx/nginx-pod.yaml | kubectl replace -f -
```

```
Error from server (NotFound): error when replacing "STDIN": pods "nginx-2" not found
```

`replace` only updates. So `create` needs the object to be missing, `replace` needs it to be present, and you have to know which is true before you run either.

> **The Service exception.** A Service is one of the few kinds where `replace` on a missing object quietly **creates** it (`service/nginx replaced`). Pods, ConfigMaps, Deployments, Secrets, and Namespaces all fail with `NotFound` as above. One more thing to remember about a command whose whole appeal is being simple.

## 3. `delete -f`

`delete -f` finds each object by the `kind`, `namespace`, and `name` in the file, and deletes it. Delete everything in the directory:

```bash
kubectl delete -f /tmp/nginx/
```

```
pod "nginx" deleted
service "nginx" deleted
```

Run it again, now that nothing is left:

```
Error from server (NotFound): error when deleting "/tmp/nginx/nginx-pod.yaml": pods "nginx" not found
Error from server (NotFound): error when deleting "/tmp/nginx/nginx-svc.yaml": services "nginx" not found
```

Same pattern: it does exactly one thing, and errors if the cluster isn't in the state it expects. (`--ignore-not-found` turns these errors off.)

## Where it falls short

Compared with [imperative commands](imperative-commands.md), the files are a real step up: they can go in Git, be reviewed, and be reused as templates. But you've now hit every shortcoming from [Object Management](object-management.md) for yourself:

| Shortcoming | What you saw |
|---|---|
| **You must pick the operation** | `create -f /tmp/nginx/` failed on the Pod that existed; `replace` failed on the Pod that didn't. A directory where some objects exist and some don't fits neither. |
| **Changes made elsewhere are lost** | `replace` silently dropped the teammate's `team=web` label. |
| **You must know each kind's quirks** | `replace` can't update a Pod from your own file, and on a missing Service it creates one instead of failing. |

What you want is a command that looks at the file and the live object, and works out the right operation on its own, while leaving alone the fields your file doesn't manage. That's `kubectl apply`, in [Declarative Object Management](declarative-management.md).

## Clean up

Everything in the cluster is already deleted. Remove the copies:

```bash
rm -rf /tmp/nginx
```

## Best practices

- **Prefer `kubectl apply -f`** for anything you keep in files. This chapter is mostly about why.
- **Don't `replace` objects that other people or tools also change.** It overwrites their changes without a word.
- **Never `replace --force` something serving traffic** unless you accept the downtime: it's a delete followed by a create.
- **`create -f` is fine for one-shot objects**, like a Job you run once and then delete.

---

[← Generating Manifests](generating-manifests.md) · [↑ Contents](../../README.md) · [Declarative Object Management →](declarative-management.md)
