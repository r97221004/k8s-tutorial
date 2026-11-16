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

Each half gets its own chapter:

- **[The Control Plane](control-plane.md)** — `kube-apiserver`, `etcd`, `kube-scheduler`, `kube-controller-manager`.
- **[The Data Plane](data-plane.md)** — `kubelet`, `containerd`, `kube-proxy`, plus add-ons (CNI, CoreDNS).

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

[← What is Kubernetes?](what-is-kubernetes.md) · [↑ Contents](../../README.md) · [The Control Plane →](control-plane.md)
