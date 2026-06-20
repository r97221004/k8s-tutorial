# Architecture Overview

> The component map to carry through the whole tutorial — and why "kubeadm" is not a different kind of Kubernetes.

[← What is Kubernetes?](what-is-kubernetes.md) · [↑ Contents](../../README.md) · [Set Up a Cluster (kubeadm) →](setup-kubeadm.md)

---

> **Clear up a common beginner confusion first: "kubeadm" is not a different kind of Kubernetes.**
>
> - **Kubernetes** is the system itself (the components below).
> - **kubeadm** is just the official *installer* that assembles those components the standard way — so a "kubeadm cluster" **is** plain, upstream Kubernetes, exactly as the official docs (and the CKA exam) describe it.
> - **k3s** is also Kubernetes, but a *repackaged lightweight distribution* with batteries-included defaults (Traefik, ServiceLB, local-path) baked in.
>
> Analogy: Kubernetes is the Linux kernel, **kubeadm** is a clean standard install, **k3s** is a pre-loaded distro like Ubuntu. We use kubeadm here precisely so nothing is hidden — you see every component for what it is.

See the [single-node diagram on the home page](../../README.md) for the big picture. Here's what each piece does:

- **Control plane** — `kube-apiserver` (the front door / REST API), `etcd` (cluster state store), `kube-scheduler` (assigns Pods to nodes), `kube-controller-manager` (reconciliation loops).
- **Node** — `kubelet` (runs Pods, talks to the API server), `kube-proxy` (Service networking), the **container runtime** (`containerd`).
- **Add-ons** — **CNI** (pod networking, here flannel), **CoreDNS** (in-cluster DNS).

_TODO — trace what happens on a `kubectl apply`: kubectl → apiserver → etcd → scheduler → kubelet → containerd._

---

[← What is Kubernetes?](what-is-kubernetes.md) · [↑ Contents](../../README.md) · [Set Up a Cluster (kubeadm) →](setup-kubeadm.md)
