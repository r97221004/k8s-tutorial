# Volumes & PersistentVolumes

> Where data survives a container restart — and how Pods request durable storage.

[← Environment Variables & Mounts](env-and-mounts.md) · [↑ Contents](../../README.md) · [StatefulSet (intro) →](statefulset.md)

---

_TODO — emptyDir vs PV/PVC. Vanilla kubeadm has no default StorageClass; install local-path-provisioner (or define a hostPath PV) so PVCs can bind._

> 📝 **Multi-node note:** local-path / hostPath volumes live on one node's disk. On a single node that's invisible — but on a multi-node cluster a Pod rescheduled to another node can't reach that data, and `ReadWriteOnce` means only one node mounts it at a time. Networked storage exists to solve exactly this.

---

[← Environment Variables & Mounts](env-and-mounts.md) · [↑ Contents](../../README.md) · [StatefulSet (intro) →](statefulset.md)
