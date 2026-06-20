# kubectl 101

> The one CLI you'll live in — talk to the API server to create, inspect, and debug everything.

---

`kubectl` is your remote control for the cluster. Every command is really an HTTP call to the [`kube-apiserver`](architecture.md) using the credentials in your **kubeconfig** (`~/.kube/config`). Learn a handful of verbs and flags and you can drive everything.

### The verbs you'll use all day

```bash
kubectl get pods                 # list things (pods, deploy, svc, nodes, …)
kubectl describe pod <name>      # full detail + recent events — your #1 debugging tool
kubectl apply -f file.yaml       # create/update from a manifest (declarative)
kubectl delete -f file.yaml      # remove what a manifest created
kubectl logs <pod>               # a container's stdout/stderr  (add -f to follow)
kubectl exec -it <pod> -- sh     # run a command / get a shell inside a container
```

> **`apply` vs `create`:** prefer `apply -f` — it's *declarative* (run it again after editing the file and Kubernetes reconciles the difference). `create` is one-shot and errors if the object already exists.

### Flags that save you

```bash
kubectl get pods -o wide         # extra columns: node, Pod IP
kubectl get pod <name> -o yaml   # the object's full manifest (incl. status)
kubectl get pods -A              # across ALL namespaces (-A = --all-namespaces)
kubectl get pods -n kube-system  # a specific namespace
kubectl get pods -l app=web      # filter by label (see Labels & Selectors)
kubectl get pods -w              # watch — stream changes live
```

> 💡 **Discover any field** with `kubectl explain`, e.g. `kubectl explain deployment.spec.replicas`. No need to memorize the API.

### Namespaces & contexts

Resources live in [namespaces](../core-objects/namespace.md); commands default to `default`. Set a default so you stop typing `-n`:

```bash
kubectl config set-context --current --namespace=my-namespace
kubectl config get-contexts      # which cluster/user/namespace am I pointed at?
```

A **context** bundles *which cluster*, *which user*, and *which namespace*. On this single-node setup you have one context, but the same `kubectl` switches between many clusters later.

### Best practices

- **Drive the cluster with `apply -f` and manifests in Git**, not ad-hoc imperative commands — so state is reproducible.
- **Reach for `describe` and `get events` first** when something's wrong (see [Debugging](../running-and-operating/debugging.md)).
- Use **`--dry-run=client -o yaml`** to *generate* manifests instead of writing them from scratch.
- For fast, visual browsing of all this, use [k9s](k9s.md) — it's `kubectl get/describe/logs` as a live dashboard.

---

[← Set Up a Cluster (kubeadm)](setup-kubeadm.md) · [↑ Contents](../../README.md) · [Anatomy of a Manifest →](manifest-anatomy.md)
