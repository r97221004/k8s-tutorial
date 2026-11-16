# The kubectl CLI

> Your one tool for talking to a cluster — and under the hood, it's just another client of the apiserver.

---

`kubectl` (say "kube-control" or "kube-cuttle") is the command-line tool you'll use for almost everything in this guide. This chapter is the mental model; you'll run the commands for real in [kubectl 101](../cluster-setup/kubectl-101.md), once your cluster is up.

### It's just an API client

`kubectl` has no special powers. Every command turns into an **HTTPS request to the `kube-apiserver`** — the same front door the scheduler and every kubelet use (see [Architecture Overview](architecture.md)):

```
kubectl get pods
   │  reads ~/.kube/config: which cluster, which credentials
   ▼
HTTPS  GET /api/v1/namespaces/default/pods
   ▼
kube-apiserver ──▶ etcd
```

The file it reads is the **kubeconfig** (`~/.kube/config` by default). It holds three things:

- **clusters** — the apiserver's address and the certificate to trust it
- **users** — your credentials
- **contexts** — named pairings of a cluster, a user, and a default namespace

Point `kubectl` at a different kubeconfig or context, and the same commands drive a different cluster.

### The shape of every command

Almost every `kubectl` command follows one pattern:

```
kubectl  [command]  [type]  [name]       [flags]
kubectl  get        pods    web-7d4b9    -o wide
```

| Part | Meaning | Examples |
|------|---------|----------|
| **command** | What to do | `get`, `describe`, `apply`, `delete`, `logs` |
| **type** | What kind of object | `pods`, `deployments`, `services` — or short names `po`, `deploy`, `svc` |
| **name** | Which one — leave it out to mean "all of them" | `web-7d4b9` |
| **flags** | Options | `-n kube-system` (namespace), `-o yaml` (output format), `-A` (all namespaces) |

So `kubectl get pods` lists every Pod, `kubectl get pod web-7d4b9` shows one, and `kubectl get pods -A` lists Pods in every namespace.

The one big exception is `-f file.yaml`: the file already says each object's type and name, so commands like `kubectl apply -f web.yaml`, `kubectl diff -f web.yaml`, and `kubectl delete -f web.yaml` skip those parts.

### Three kinds of commands

| Kind | Commands | What it does |
|------|----------|--------------|
| **Inspect** | `get`, `describe`, `logs` | Read the cluster's state. Changes nothing. |
| **Imperative** | `run`, `create`, `scale`, `delete` | Tell the cluster to do one specific thing, now. |
| **Declarative** | `apply -f`, `diff -f` (and `delete -f`) | Hand over a file describing the desired state; the cluster converges on it. |

The last two rows are the [imperative vs. declarative](what-is-kubernetes.md#imperative-vs-declarative) split from earlier, as commands. Both work, but they suit different jobs:

- **Imperative** is handy for quick experiments: `kubectl scale deployment web --replicas=5`. But nothing records what you did.
- **Declarative** is what this guide uses: edit the YAML, run `kubectl apply -f`, and keep the file in Git. Run `kubectl diff -f` first to see exactly what would change.

> 💡 If you ever want to change something imperatively, ask yourself whether it should be in a file instead. If anyone else — or future you — needs to reproduce it, the answer is yes.

Next, you'll build the cluster that all of this talks to.

---

[← The Data Plane](data-plane.md) · [↑ Contents](../../README.md) · [Set Up a Cluster (kubeadm) →](../cluster-setup/setup-kubeadm.md)
