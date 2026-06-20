# Set Up a Cluster (kubeadm)

> Installation lives in the companion Ansible tutorial — here we explain what each piece it installs actually is.

---

> ⚠️ **Build the cluster before starting this chapter.** The install steps aren't repeated here — they're fully covered in the companion Ansible tutorial, which provisions this exact single-node kubeadm cluster over SSH: **[r97221004/ansible-tutorial → kubeadm Role](https://github.com/r97221004/ansible-tutorial#kubeadm-role)**. Run that first. Once the cluster is up, this section explains **what each piece it installed actually is**, so the cluster isn't a black box.

Unlike k3s (one install script), kubeadm wires the cluster up from parts. The Ansible role does it as a pipeline; this is what each step is **for**, so the cluster stops being a black box.

### 1. Kernel prerequisites

Before anything else, the OS must be ready to run containers networked together:

- **Modules `overlay` + `br_netfilter`** — `overlay` is the filesystem containers layer their images on; `br_netfilter` lets the Linux bridge hand Pod traffic to `iptables`.
- **Sysctls** `net.bridge.bridge-nf-call-iptables=1` and `net.ipv4.ip_forward=1` — so traffic between Pods (and out to other nodes) is actually filtered and forwarded. Without these, Pod networking silently breaks.
- **Swap off** — the scheduler reasons about real memory; swap makes its accounting lie, so kubelet refuses to start with swap on.

### 2. containerd — the container runtime

Kubernetes doesn't run containers itself; it delegates to a runtime through the **CRI** (Container Runtime Interface). We use **containerd**. The one setting that bites everyone: **the cgroup driver must match kubelet's** — both must use `systemd`. Mismatch it and Pods fail to start with cgroup errors.

### 3. kubelet, kubeadm, kubectl — three different tools

Easy to confuse because they share a prefix:

| Tool | Role |
|------|------|
| **kubelet** | the long-running **agent** on the node that actually runs Pods (a systemd service) |
| **kubeadm** | the one-shot **bootstrapper** that stands the cluster up |
| **kubectl** | the **client** *you* use to talk to the cluster |

Their versions are **held/pinned** (`apt-mark hold`) so an unattended `apt upgrade` can't skew versions and break the cluster — k8s only supports a narrow version skew.

### 4. `kubeadm init` — the cluster is born

This one command does the heavy lifting:

- Generates certificates and writes the **control-plane components as static Pods** (apiserver, etcd, scheduler, controller-manager) — kubelet starts them straight from manifest files in `/etc/kubernetes/manifests/`.
- `--pod-network-cidr` reserves the IP range Pods will draw from (must match the CNI's expectation).
- Writes the admin **kubeconfig** to `/etc/kubernetes/admin.conf` — the credentials `kubectl` uses to authenticate.

### 5. CNI (flannel) — give Pods a network

Right after init, `kubectl get nodes` shows the node as **`NotReady`**. That's expected: a fresh cluster has *no* Pod networking. Installing a **CNI** plugin (here **flannel**) assigns Pod IPs from the CIDR above and wires up routing — then the node flips to `Ready`.

> 📝 **Multi-node note:** a CNI's real job is routing Pod traffic **across** nodes via an overlay network. On one node that cross-node magic stays hidden — but a CNI is still mandatory for Pods to get IPs at all.

### 6. Let one node run everything

By default the control-plane node carries a **taint** (`node-role.kubernetes.io/control-plane:NoSchedule`) that repels normal workloads — on a multi-node cluster you want the brain kept clear. On a *single* node that would mean nothing can ever run, so you **remove the taint**:

```bash
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

### Verify your cluster

After the Ansible run, confirm it's healthy:

```bash
kubectl get nodes                 # the node should be Ready
kubectl get pods -n kube-system   # apiserver, etcd, scheduler, controller-manager, coredns, flannel all Running
```

Or open [k9s](k9s.md) and type `:pods` ⏎, then `0` to show all namespaces — you'll see the whole control plane running as Pods in `kube-system`. That's the payoff of kubeadm: the "magic" is just Pods you can inspect.

> **Heads-up — vanilla k8s ships fewer batteries than k3s.** There is no default StorageClass, LoadBalancer provider, or Ingress controller. Those are installed in their own chapters: local-path-provisioner ([Volumes](../config-and-data/volumes.md)), MetalLB or NodePort ([Service](../core-objects/service.md)), ingress-nginx ([Ingress](../networking/ingress.md)).

---

[← Architecture Overview](architecture.md) · [↑ Contents](../../README.md) · [kubectl 101 →](kubectl-101.md)
