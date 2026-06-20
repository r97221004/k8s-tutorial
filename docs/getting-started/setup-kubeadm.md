# Set Up a Cluster (kubeadm)

> Installation lives in the companion Ansible tutorial — here we explain what each piece it installs actually is.

[← Architecture Overview](architecture.md) · [↑ Contents](../../README.md) · [kubectl 101 →](kubectl-101.md)

---

> ⚠️ **Build the cluster before starting this chapter.** The install steps aren't repeated here — they're fully covered in the companion Ansible tutorial, which provisions this exact single-node kubeadm cluster over SSH: **[r97221004/ansible-tutorial → kubeadm Role](https://github.com/r97221004/ansible-tutorial#kubeadm-role)**. Run that first. Once the cluster is up, this section explains **what each piece it installed actually is**, so the cluster isn't a black box.

_TODO — walk through each component the installer wires up, in pipeline order, explaining the "why":_

1. **Kernel prerequisites** — `overlay` + `br_netfilter` modules and the `net.bridge.*` / `ip_forward` sysctls: why pod traffic needs them; why swap must be off.
2. **containerd (the CRI runtime)** — what the Container Runtime Interface is; why the **systemd cgroup driver** must match kubelet.
3. **kubelet / kubeadm / kubectl** — the node agent vs. the bootstrapper vs. the client; why versions are held/pinned.
4. **`kubeadm init`** — what it actually creates: control-plane static Pods (apiserver, etcd, scheduler, controller-manager), the `--pod-network-cidr`, and the kubeconfig at `/etc/kubernetes/admin.conf`.
5. **CNI (flannel)** — why nodes stay `NotReady` until a CNI is applied; what the pod network CIDR binds to. _(Multi-node note: the CNI's real job is routing Pod traffic **across** nodes via an overlay — on one node that cross-node magic stays hidden, but it's why a CNI is mandatory.)_
6. **Single-node scheduling** — the `node-role.kubernetes.io/control-plane` taint and why you remove it to run workloads on one node.

> **Heads-up — vanilla k8s ships fewer batteries than k3s.** There is no default StorageClass, LoadBalancer provider, or Ingress controller. Those are installed in their own chapters: local-path-provisioner ([Volumes](../config-and-data/volumes.md)), MetalLB or NodePort ([Service](../core-objects/service.md)), ingress-nginx ([Ingress](../networking/ingress.md)).

---

[← Architecture Overview](architecture.md) · [↑ Contents](../../README.md) · [kubectl 101 →](kubectl-101.md)
