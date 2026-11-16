# The Control Plane

> The brain of the cluster: it decides what should run and records the desired state — but never runs your containers itself.

---

The control plane is made of **four core components**, each with a single, narrow job — plus one optional component for clusters that run on a cloud provider:

| Component | Its job | If it stops… |
|-----------|---------|--------------|
| **`kube-apiserver`** | The front door — every request goes through it | `kubectl` fails and nothing can change — **but running Pods keep running.** |
| **`etcd`** | The cluster's memory; only the apiserver touches it | The apiserver can't read or write state. Lose `etcd` without a backup, and the cluster forgets everything. |
| **`kube-scheduler`** | Picks a node for each new Pod — it doesn't start containers | New Pods stay `Pending`. Existing Pods are fine. |
| **`kube-controller-manager`** | Runs the **control loops** (Deployment, ReplicaSet, Job, …) | Nothing self-heals or scales: a deleted Pod isn't replaced, and changing `replicas` does nothing. |
| `cloud-controller-manager` *(optional)* | Creates cloud load balancers, disks, routes — [not in this lab](architecture.md#two-names-worth-knowing) | `LoadBalancer` Services stay `<pending>`. |

The last column holds the key idea: **the control plane going down doesn't take your apps down.** The kubelet on each node keeps its containers running (and restarts them if they crash). What you lose is the ability to *change* anything — and the loops that fix things for you.

`etcd` is not a database for your application data — it only holds Kubernetes objects. Your app's data belongs in [volumes](../config-and-data/volumes.md).

### Static Pods

On a kubeadm control plane, these components run as **static Pods**: manifest files on disk under `/etc/kubernetes/manifests/` that the local kubelet starts directly. They are still Pods you can inspect, but they aren't managed by a Deployment — the file is the source of truth.

Try deleting one:

```bash
kubectl delete pod -n kube-system -l component=kube-scheduler
kubectl get pods -n kube-system -l component=kube-scheduler   # it's back within seconds
```

What you deleted was only the **mirror Pod** — a read-only copy the kubelet publishes to the apiserver so you can see it. The real scheduler kept running the whole time, because the kubelet manages it straight from the file. To actually change or remove a static Pod, you edit or remove its file.

### See it live

Once the cluster is running:

```bash
kubectl get pods -n kube-system -l tier=control-plane   # the four core components
sudo ls /etc/kubernetes/manifests                       # their static Pod files
kubectl get --raw='/readyz?verbose'                     # the apiserver's own health checks

# only the apiserver is configured to reach etcd:
sudo grep etcd-servers /etc/kubernetes/manifests/kube-apiserver.yaml
```

Notice the Pod names end with your node's name (e.g. `kube-apiserver-<node>`). That suffix is the tell-tale sign of a static Pod.

In [k9s](../cluster-setup/k9s.md), type `:pods` ⏎, press `0` to show all namespaces, then `/kube-` to filter. Highlight `kube-apiserver-…` and press `d`: under **Controlled By** you'll see `Node/<node>` — not a ReplicaSet — because the kubelet on that node owns it.

### Best practices

- **Run a highly available control plane in production** — at least three control-plane nodes, so losing one machine doesn't freeze the cluster.
- **Run `etcd` with an odd number of members** (3 or 5). `etcd` is *distributed*: it only accepts writes while a majority (quorum) agrees, so 3 members survive 1 failure and 5 survive 2. A 4th member adds no extra tolerance.
- **Back up `etcd` regularly** — it *is* the cluster. Everything else can be rebuilt from it.
- **Keep app workloads off control-plane nodes.** kubeadm taints them for this reason. Our single-node lab removes that taint on purpose, since there's nowhere else to run — see [Set Up a Cluster](../cluster-setup/setup-kubeadm.md).

---

[← Architecture Overview](architecture.md) · [↑ Contents](../../README.md) · [The Data Plane →](data-plane.md)
