# Architecture Overview

> The component map to carry through the whole tutorial — and why "kubeadm" is not a different kind of Kubernetes.

---

> **Clear up a common beginner confusion first: "kubeadm" is not a different kind of Kubernetes.**
>
> - **Kubernetes** is the system itself (the components below).
> - **kubeadm** is just the official *installer* that assembles those components the standard way — so a "kubeadm cluster" **is** plain, upstream Kubernetes, exactly as the official docs (and the CKA exam) describe it.
> - **k3s** is also Kubernetes, but a *repackaged lightweight distribution* with batteries-included defaults (Traefik, ServiceLB, local-path) baked in.
>
> Analogy: Kubernetes is the Linux kernel, **kubeadm** is a clean standard install, **k3s** is a pre-loaded distro like Ubuntu. We use kubeadm here precisely so nothing is hidden — you see every component for what it is.

See the [single-node diagram on the home page](../../README.md) for the big picture. A cluster has two halves: a **control plane** (the brain that decides what should run) and one or more **nodes** (the muscle that actually runs it). On our single node, both live on the same machine. In a multi-node cluster, control-plane nodes and worker nodes are usually separated.

The control plane makes decisions and records desired state; the kubelet and container runtime on a node are what actually run your app containers.

### The control plane — decides

- **`kube-apiserver`** — the front door. *Every* request (yours via `kubectl`, and every component's) goes through its REST API. Nothing talks to anything else directly.
- **`etcd`** — the cluster's memory: a key-value store holding the desired and current state of every object. It is the cluster state store, not a database for your application data. If `etcd` is the source of truth, the apiserver is the only one allowed to read/write it.
- **`kube-scheduler`** — watches for Pods with no node assigned and picks a node for each (based on resources, constraints, etc.). It chooses *where* a Pod should run; it does not start containers.
- **`kube-controller-manager`** — runs many **control loops** that reconcile reality toward desired state (e.g. "Deployment wants 3 Pods, only 2 exist → make one more"). Deployment, ReplicaSet, Job, Node, and EndpointSlice controllers all live under this umbrella.

On a kubeadm control plane, these components run as **static Pods**: manifest files on disk under `/etc/kubernetes/manifests/` that the local kubelet starts directly. They are still Pods you can inspect, but they are not managed by Deployments. The kubelet's static Pod mechanism keeps them running.

### The node — runs

- **`kubelet`** — the agent on each node. It watches the apiserver for Pods assigned to its node and tells the container runtime to start/stop them, then reports status back.
- **`containerd`** — the **container runtime** that actually pulls images and runs containers (via the CRI, the Container Runtime Interface).
- **`kube-proxy`** — programs node networking rules (iptables/IPVS/nftables, depending on mode) so [Service](../core-objects/service.md) traffic forwards to the right Pods.

### Add-ons (themselves Pods)

- **CNI (flannel)** — gives every Pod an IP and routes Pod-to-Pod traffic (across nodes, on a real cluster). CNIs usually run as DaemonSets. NetworkPolicy enforcement also depends on the CNI; flannel handles connectivity, but does not enforce NetworkPolicies by itself.
- **CoreDNS** — in-cluster DNS, so Pods can find Services by name (see [Service Discovery & DNS](../networking/dns.md)).

### See it live

Once the cluster is running, these commands map the architecture to real processes and Pods:

```bash
kubectl get pods -n kube-system                  # control plane + add-ons
kubectl get pods -n kube-system -o wide          # which node each Pod runs on
sudo ls /etc/kubernetes/manifests                # static Pod manifests from kubeadm
systemctl status kubelet                         # node agent
sudo crictl ps                                   # containers running under containerd
```

If `crictl` is not installed or configured on your host yet, skip that line for now; the Kubernetes-level commands above are enough for this chapter.

| Component | Where you usually see it in this lab |
|-----------|--------------------------------------|
| apiserver / scheduler / controller-manager / etcd | static Pods in `kube-system`, backed by files in `/etc/kubernetes/manifests/` |
| kubelet | systemd service on the node |
| containerd | systemd service plus containers visible through `crictl` |
| kube-proxy / flannel | DaemonSet Pods in `kube-system` |
| CoreDNS | Deployment Pods in `kube-system` |

### What happens on `kubectl apply`

Tracing one command ties it all together:

```
1. kubectl ───▶ kube-apiserver      "create this Deployment" (validated, written to etcd)
2. controller-manager (Deployment + ReplicaSet controllers) ──▶ asks the apiserver to create ReplicaSet/Pod objects
3. kube-scheduler                   sees the unassigned Pods, assigns each to a node
4. kubelet (on that node)           sees its assigned Pods, tells containerd to run them
5. containerd                       pulls the image, starts the containers
6. kubelet                          reports "Running" back to the apiserver → you see it in kubectl/k9s
```

Notice the pattern: **you never command components directly.** You write your desired state to the apiserver, and independent controllers watch and converge toward it. That single idea is the whole of Kubernetes.

The same split shows up in every object: you write `spec` (what you want), while controllers and kubelets report `status` (what is true now).

---

[← What is Kubernetes?](what-is-kubernetes.md) · [↑ Contents](../../README.md) · [Set Up a Cluster (kubeadm) →](setup-kubeadm.md)
