# The Data Plane

> The muscle of the cluster: the node components that actually pull images, run containers, and move traffic.

---

The data plane is everything that runs on each **worker node**. The control plane decides; these components carry it out. Three run on every node, plus two cluster add-ons that every real cluster needs:

| Component | Its job | If it stops… |
|-----------|---------|--------------|
| **`kubelet`** | Runs this node's Pods and reports their status | Containers **keep running**, but nothing restarts them or reports on them. The node turns `NotReady`; after about 5 minutes, Pods managed by a controller are recreated elsewhere. |
| **`containerd`** | Pulls images and runs containers | Running containers survive, but no new ones can start. |
| **`kube-proxy`** | Programs the rules that route [Service](../core-objects/service.md) traffic to Pods | Existing rules keep working, but Service changes aren't applied. |
| CNI (**flannel**) *(add-on)* | Gives every Pod an IP and routes Pod-to-Pod traffic | Pod networking can't be set up or updated — new Pods may get stuck in `ContainerCreating`. |
| **CoreDNS** *(add-on)* | In-cluster DNS, so Pods find Services by [name](../networking/dns.md) | Lookups by name fail; connections by IP still work. |

Same lesson as the [control plane](control-plane.md): **when a component stops, what's already running mostly keeps running.** What breaks is the ability to start, fix, or change things.

### Why aren't kubelet and containerd Pods?

`kube-proxy`, flannel, and CoreDNS all run as Pods. `kubelet` and `containerd` don't — they're ordinary **systemd services** on the host. They can't be Pods, because **they're what runs Pods**: something has to be there first to start everything else.

### The container runtime, and what happened to Docker

Kubernetes doesn't run containers itself. The kubelet talks to a runtime through the **CRI** (Container Runtime Interface); the common choices are **containerd** (what we use) and **CRI-O**.

You may read that Kubernetes "supports Docker" — that's out of date. Built-in Docker Engine support (dockershim) was removed in Kubernetes 1.24. This **doesn't** affect your images: images built with `docker build` are standard OCI images, and containerd runs them just fine.

### Try it: stop the kubelet

On your lab node (restart it within a couple of minutes — see the warning below):

```bash
sudo systemctl stop kubelet
sudo crictl ps                    # containers are still running
kubectl get nodes -w              # within about a minute: NotReady (Ctrl-C to stop watching)
sudo systemctl start kubelet      # back to Ready
```

If `crictl` isn't set up on your host yet, `sudo ctr -n k8s.io tasks ls` shows the same running containers.

`kubectl` keeps working the whole time: the apiserver is a container too, and containerd keeps it alive without the kubelet.

> ⚠️ Don't leave the kubelet stopped. After about 5 minutes, Kubernetes starts evicting the node's Pods — and on a single-node cluster, there's nowhere else for them to go.

### See it live

```bash
systemctl status kubelet containerd                 # the two host services
kubectl get ds -A                                    # kube-proxy and flannel run as DaemonSets
kubectl get pods -n kube-system -l k8s-app=kube-dns  # CoreDNS
kubectl describe node                                # Conditions, Capacity, Allocatable
```

In `kubectl describe node`, look at two sections:

- **Conditions** — `Ready`, plus pressure signals like `MemoryPressure` and `DiskPressure`. This is how the kubelet tells the control plane how the node is doing.
- **Allocatable** — what's actually left for Pods after the system's own reservation. It's smaller than **Capacity**, and it's what the scheduler counts against.

In [k9s](../cluster-setup/k9s.md), type `:nodes` ⏎ and press `d` on your node to see the same Conditions and Allocatable. Then `:ds` ⏎ and `0` for all namespaces to see the DaemonSets that put `kube-proxy` and flannel on every node.

### Best practices

- **Drain before maintenance.** `kubectl drain <node>` moves Pods off gracefully before you reboot or upgrade a node — don't just power it off.
- **Never let the kubelet be newer than the apiserver.** When upgrading, do the control plane first, then the nodes.
- **Pick a CNI that fits your needs.** flannel handles connectivity but doesn't enforce NetworkPolicy; if you need it, choose a CNI that does, such as Calico or Cilium.
- **Reserve resources for the system.** Set the kubelet's `system-reserved` / `kube-reserved` so Pods can't starve the host's own processes. That reservation is the gap between Capacity and Allocatable.

---

[← The Control Plane](control-plane.md) · [↑ Contents](../../README.md) · [The kubectl CLI →](kubectl-cli.md)
