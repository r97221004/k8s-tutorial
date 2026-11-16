# The Data Plane

> The muscle of the cluster: the node components that actually pull images, run containers, and move traffic.

---

The data plane is everything that runs on each **node**. The control plane decides; these components carry it out.

### Node components

- **`kubelet`** — the agent on each node. It watches the apiserver for Pods assigned to its node and tells the container runtime to start/stop them, then reports status back.
- **`containerd`** — the **container runtime** that actually pulls images and runs containers (via the CRI, the Container Runtime Interface).
- **`kube-proxy`** — programs node networking rules (iptables/IPVS/nftables, depending on mode) so [Service](../core-objects/service.md) traffic forwards to the right Pods.

### Add-ons (themselves Pods)

- **CNI (flannel)** — gives every Pod an IP and routes Pod-to-Pod traffic (across nodes, on a real cluster). CNIs usually run as DaemonSets. NetworkPolicy enforcement also depends on the CNI; flannel handles connectivity, but does not enforce NetworkPolicies by itself.
- **CoreDNS** — in-cluster DNS, so Pods can find Services by name (see [Service Discovery & DNS](../networking/dns.md)).

### See it live

Once the cluster is running:

```bash
systemctl status kubelet                         # node agent
sudo crictl ps                                   # containers running under containerd
kubectl get pods -n kube-system -o wide          # kube-proxy, flannel, CoreDNS
```

If `crictl` is not installed or configured on your host yet, skip that line for now; the Kubernetes-level commands above are enough for this chapter.

| Component | Where you usually see it in this lab |
|-----------|--------------------------------------|
| kubelet | systemd service on the node |
| containerd | systemd service plus containers visible through `crictl` |
| kube-proxy / flannel | DaemonSet Pods in `kube-system` |
| CoreDNS | Deployment Pods in `kube-system` |

---

[← The Control Plane](control-plane.md) · [↑ Contents](../../README.md) · [Set Up a Cluster (kubeadm) →](../cluster-setup/setup-kubeadm.md)
