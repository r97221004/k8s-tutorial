# Anatomy of a Manifest

> Every Kubernetes object is the same four fields — learn them once and all YAML looks familiar.

---

Here's the good news that makes Kubernetes YAML far less scary: **every object has the same four top-level fields.** Pod, Deployment, Service, ConfigMap — all of them. Learn the shape once and every manifest in this guide reads the same way.

### The four fields

Take the [Pod](../core-objects/pod.md) manifest you already met:

▶ **Runnable manifest:** [`manifests/core-objects/nginx-pod.yaml`](../../manifests/core-objects/nginx-pod.yaml)

```yaml
apiVersion: v1          # 1. which API group/version defines this object
kind: Pod               # 2. what kind of object this is
metadata:               # 3. identity: name, namespace, labels, annotations
  name: nginx
  labels:
    app: nginx
spec:                   # 4. the desired state — what YOU want
  containers:
    - name: nginx
      image: nginx:1.27
      ports:
        - containerPort: 80
```

- **`apiVersion`** — which part of the Kubernetes API owns this kind. Core objects (Pod, Service, ConfigMap) use `v1`; workload controllers use `apps/v1`; others have their own groups (`batch/v1` for Jobs, `networking.k8s.io/v1` for Ingress). If you ever get the version wrong, `kubectl explain <kind>` tells you the right one.
- **`kind`** — the type of object (`Pod`, `Deployment`, `Service`, …).
- **`metadata`** — *who* this object is: its `name`, optional `namespace`, and the `labels`/`annotations` used to find and group it (see [Labels & Selectors](../core-objects/labels-selectors.md)).
- **`spec`** — the **desired state**: what you want to exist. This is the part that differs per kind, and the part you spend your time on.

### spec vs status

You write `spec` (what you *want*). Kubernetes adds a **`status`** (what *is*) and keeps updating it. You won't write `status` — but you'll read it constantly:

```bash
kubectl get pod nginx -o yaml    # scroll down to see the status: block the cluster filled in
```

That split — *you declare `spec`, the cluster reports `status`, controllers close the gap* — is the [declarative model](what-is-kubernetes.md) made concrete.

### Best practices

- **Keep one object per file** (or separate them with `---`) and store them in Git.
- **Always name things clearly** and label them consistently — labels are how everything else finds your objects.
- **Don't hand-write from memory** — generate a skeleton with `kubectl create … --dry-run=client -o yaml` (or copy from these manifests) and edit.
- **Look up fields** with `kubectl explain <kind>.<field>` instead of guessing.

---

[← kubectl 101](kubectl-101.md) · [↑ Contents](../../README.md) · [Inspect with k9s →](k9s.md)
