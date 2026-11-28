# Multiple Objects in One File

> Separate manifests with --- and apply a whole app at once.

---

So far every object has had its own file: `nginx-pod.yaml` and `nginx-svc.yaml`. But those two belong together. The Service is useless without the Pod, and you always create, change, and delete them as a pair. YAML lets you put both in **one file**, and kubectl treats that file as one unit.

## The separator: `---`

A line containing only `---` separates one YAML document from the next. Each document is a complete object, with its own `apiVersion`, `kind`, `metadata`, and `spec`:

▶ **Runnable manifest:** [`manifests/object-management/nginx.yaml`](../../manifests/object-management/nginx.yaml)

```yaml
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
---
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

It's simply the two files from the previous chapters, one after the other, with `---` in between. A few details:

- `---` must start at the beginning of the line, with nothing else on it.
- A `---` at the very top of the file is allowed too. Some people always start with one.
- Comments (`# …`) can go anywhere, including right above an object to say what it's for.

## Apply, inspect, and delete as one

Every `-f` command you've used works on the whole file:

```bash
kubectl apply -f manifests/object-management/nginx.yaml
```

```
pod/nginx created
service/nginx created
```

`kubectl get -f` shows exactly the objects the file describes, whatever their kinds:

```bash
kubectl get -f manifests/object-management/nginx.yaml
```

```text
NAME        READY   STATUS    RESTARTS   AGE
pod/nginx   1/1     Running   0          5s

NAME            TYPE       CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE
service/nginx   NodePort   10.109.112.175   <none>        80:30196/TCP   5s
```

Apply it again, and both objects report `unchanged`, as in [Declarative Object Management](declarative-management.md). `kubectl diff -f` works the same way. When you're done, one command removes the whole app:

```bash
kubectl delete -f manifests/object-management/nginx.yaml
```

```
pod "nginx" deleted
service "nginx" deleted
```

## Order matters

kubectl sends the objects to the API server **in the order they appear in the file**, top to bottom. Usually that doesn't matter: the Service can be created before or after its Pod, and the selector connects them whenever both exist. But some objects need another one to exist **first**. The common case is a Namespace and the objects inside it.

Try it. Write a file with the Namespace at the **bottom**:

```bash
cat > /tmp/ns-last.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: nginx
  namespace: web          # lives in the "web" namespace…
spec:
  containers:
    - name: nginx
      image: nginx:1.27
---
apiVersion: v1
kind: Namespace
metadata:
  name: web               # …which is only created afterwards
EOF
kubectl apply -f /tmp/ns-last.yaml
```

```text
namespace/web created
Error from server (NotFound): error when creating "/tmp/ns-last.yaml": namespaces "web" not found
```

The Namespace was created, but the Pod was sent before it existed, and failed. Running `apply` a second time would succeed, because by then the Namespace is there, which makes this kind of bug easy to miss.

To see the right order work on the first try, delete the Namespace again, then apply a file with it at the **top**:

```bash
kubectl delete ns web
cat > /tmp/ns-first.yaml <<'EOF'
apiVersion: v1
kind: Namespace
metadata:
  name: web
---
apiVersion: v1
kind: Pod
metadata:
  name: nginx
  namespace: web
spec:
  containers:
    - name: nginx
      image: nginx:1.27
EOF
kubectl apply -f /tmp/ns-first.yaml
```

```text
namespace/web created
pod/nginx created
```

**Put the objects others depend on first:** Namespaces before anything inside them, and, later in this guide, things like ConfigMaps and Secrets before the Pods that use them.

## One file, or many?

Both work. The question is what you want to manage as a unit.

| Layout | Good for |
|---|---|
| **One file per app** (`nginx.yaml`: Pod + Service) | Objects that are always created, changed, and deleted together. One `apply`, one `delete`, and one place to look. |
| **One file per object** (`nginx-pod.yaml`, `nginx-svc.yaml`) | Large objects, or objects that change on their own schedule or are owned by different people. Smaller files, smaller diffs. |
| **A directory per app** | Many objects. `kubectl apply -f <dir>/` applies every file in it (in alphabetical order), and `-R` also descends into subdirectories. |

A good default: one file per app while it's small, and a directory per app once the file gets long. Whatever you choose, keep each object in **exactly one** file. If the same object is described in two files, sooner or later someone edits only one of them, and from then on applying them in turn makes the object flip between the two versions.

> That's why you shouldn't run `kubectl apply -f manifests/object-management/` on this repo's folder: it holds `nginx.yaml` *and* `nginx-pod.yaml`/`nginx-svc.yaml`, which describe the same objects, plus the color-api files with a `<YOUR_DOCKERHUB_USER>` placeholder. Those files are teaching examples, one per chapter, not a single app.

## Clean up

The nginx Pod and Service in `default` are already gone. Delete the `web` namespace example, which takes the Pod inside it along, and the two files:

```bash
kubectl delete -f /tmp/ns-first.yaml
rm /tmp/ns-last.yaml /tmp/ns-first.yaml
```

## Best practices

- **Group objects that live and die together** in one file, and separate them with `---`.
- **Order objects by dependency**: Namespaces first, then whatever others need, then the rest.
- **Describe every object in exactly one file.** Two copies drift apart, and then fight each other on every `apply`.
- **Use `kubectl get -f` and `kubectl diff -f`** on the file to see the whole app's state and pending changes at once.

## Part 4 in one page

You now have all three approaches, and the tools around them:

| You want to… | Use |
|---|---|
| Try something quickly | [Imperative commands](imperative-commands.md): `run`, `create`, `expose`, `set`, `label` |
| Get a manifest without writing it from scratch | [`--dry-run=client -o yaml`](generating-manifests.md) |
| Check a file before using it | [`--dry-run=server`](manifest-files.md#catch-mistakes-before-they-reach-the-cluster) and [`kubectl diff`](declarative-management.md#2-preview-with-diff-then-apply) |
| Manage anything you keep | [`kubectl apply -f`](declarative-management.md), with the files in Git |
| Take over objects made by hand | [From Imperative to Declarative](imperative-to-declarative.md) |

From here on, this guide writes every object as a manifest and applies it.

---

[← From Imperative to Declarative](imperative-to-declarative.md) · [↑ Contents](../../README.md) · [What Are ReplicaSets →](../replicasets-deployments/what-are-replicasets.md)
