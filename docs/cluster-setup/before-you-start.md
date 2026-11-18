# Before You Start

> Everything you need in place before Part 3: a kubeadm cluster, a shell on its node, and this repository.

---

This guide doesn't walk through installing Kubernetes. That's covered step by step in the companion Ansible tutorial. Instead, this page is a short checklist. Work through it once, and every hands-on example from [Pod](../core-objects/pod.md) onward will run as written.

### 1. A kubeadm cluster

Provision the single-node cluster with **[r97221004/ansible-tutorial → kubeadm Role](https://github.com/r97221004/ansible-tutorial/blob/master/docs/roles/kubeadm.md)**. It prepares the OS, installs containerd and `kubelet`/`kubeadm`/`kubectl`, runs `kubeadm init`, and installs flannel. Every component it sets up is explained in [The Control Plane](../getting-started/control-plane.md) and [The Data Plane](../getting-started/data-plane.md).

> 📌 **This guide targets Kubernetes 1.30+.** If you run a different minor version, some output (flag names, default behavior) may differ slightly from what's shown here.

### 2. Work on the node

Ansible runs on your own machine and configures the node over SSH, so when the playbook finishes, the cluster lives **on the node, not on your machine**. Typing `kubectl get nodes` locally will fail with `connection refused`, because your machine has no kubeconfig for this cluster.

SSH into the node, as the same user Ansible connected with (the `ansible_user` in your inventory), and run every command in this guide from there:

```bash
ssh <ansible_user>@<node-ip>
kubectl get nodes      # works right away: no sudo, no extra setup
```

That works because the role copied the cluster's admin credentials, `/etc/kubernetes/admin.conf`, to `~/.kube/config` for that user, which is where `kubectl` looks by default (see [The kubectl CLI](../getting-started/kubectl-cli.md)). Working on the node also matters later: a few chapters inspect the node directly, with commands like `sudo ls /etc/kubernetes/manifests` or `sudo systemctl stop kubelet`.

If `kubectl` still reports `connection refused` or `the server doesn't have a resource type`, check two things: that you're on the node, and that you're the user who owns `~/.kube/config`.

### 3. Let the one node run your Pods

kubeadm taints the control-plane node with `node-role.kubernetes.io/control-plane:NoSchedule`, so that ordinary workloads stay off it. That makes sense when worker nodes exist. On a single-node lab, though, it means none of your Pods could ever be scheduled: they would all sit at `Pending`. The Ansible role leaves the taint in place, so remove it yourself, once:

```bash
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

The trailing `-` means "remove". [Scheduling, Taints & Tolerations](../core-objects/scheduling.md) explains the mechanism.

### 4. Verify

```bash
kubectl get nodes                      # one node, STATUS Ready
kubectl get pods -A                    # apiserver, etcd, scheduler, controller-manager, coredns, flannel, kube-proxy: all Running
kubectl describe nodes | grep Taints   # Taints: <none>
```

If the node is `NotReady`, the CNI usually isn't up yet. Give flannel a minute, then look for its Pod with `kubectl get pods -A | grep flannel`.

### 5. This repository

Every `▶ Runnable manifest` path in this guide is relative to the repo root. Clone the repo on the node and run commands from there:

```bash
git clone https://github.com/r97221004/k8s-tutorial.git
cd k8s-tutorial
```

### 6. What a bare kubeadm cluster does *not* have

kubeadm installs only the core components. A few things later chapters rely on are deliberately left out:

- **No default StorageClass.** PVCs stay `Pending` until you install one. local-path-provisioner is installed in [Volumes](../config-and-data/volumes.md).
- **No LoadBalancer provider.** `type: LoadBalancer` Services sit at `<pending>`. Use NodePort or MetalLB; see [Service](../core-objects/service.md).
- **No Ingress controller.** ingress-nginx is installed in [Ingress](../networking/ingress.md).

Don't install these now. Each chapter adds what it needs, when it needs it.

### 7. Optional: k9s

Not required, but recommended. Most chapters include a k9s watch point so you can *see* the cluster react. The Ansible tutorial's **[kube_tools role](https://github.com/r97221004/ansible-tutorial/blob/master/docs/roles/kube-tools.md)** installs it on the node for you, or you can install it by hand from the [next page](k9s.md).

---

[← The kubectl CLI](../getting-started/kubectl-cli.md) · [↑ Contents](../../README.md) · [Inspect with k9s →](k9s.md)
