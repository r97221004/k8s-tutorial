# The Control Plane

> The brain of the cluster: it decides what should run and records the desired state — but never runs your containers itself.

---

The control plane is made of four components. Each one has a single, narrow job:

- **`kube-apiserver`** — the front door. *Every* request (yours via `kubectl`, and every component's) goes through its REST API. Nothing talks to anything else directly.
- **`etcd`** — the cluster's memory: a key-value store holding the desired and current state of every object. It is the cluster state store, not a database for your application data. If `etcd` is the source of truth, the apiserver is the only one allowed to read/write it.
- **`kube-scheduler`** — watches for Pods with no node assigned and picks a node for each (based on resources, constraints, etc.). It chooses *where* a Pod should run; it does not start containers.
- **`kube-controller-manager`** — runs many **control loops** that reconcile reality toward desired state (e.g. "Deployment wants 3 Pods, only 2 exist → make one more"). Deployment, ReplicaSet, Job, Node, and EndpointSlice controllers all live under this umbrella.

### Static Pods

On a kubeadm control plane, these components run as **static Pods**: manifest files on disk under `/etc/kubernetes/manifests/` that the local kubelet starts directly. They are still Pods you can inspect, but they are not managed by Deployments. The kubelet's static Pod mechanism keeps them running.

### See it live

Once the cluster is running:

```bash
kubectl get pods -n kube-system                  # apiserver, etcd, scheduler, controller-manager
kubectl get pods -n kube-system -o wide          # which node each Pod runs on
sudo ls /etc/kubernetes/manifests                # static Pod manifests from kubeadm
```

| Component | Where you usually see it in this lab |
|-----------|--------------------------------------|
| apiserver / scheduler / controller-manager / etcd | static Pods in `kube-system`, backed by files in `/etc/kubernetes/manifests/` |

---

[← Architecture Overview](architecture.md) · [↑ Contents](../../README.md) · [The Data Plane →](data-plane.md)
