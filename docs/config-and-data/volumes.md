# Volumes & PersistentVolumes

> Where data survives a container restart — and how Pods request durable storage.

---

A container's filesystem is **ephemeral**: when a Pod restarts, anything written inside is gone. That's fine for a stateless web server, fatal for a database. **Volumes** give a Pod storage that outlives the container; **PersistentVolumes** give it storage that outlives the Pod entirely.

## Ephemeral: `emptyDir`

The simplest volume — scratch space that lives as long as the Pod (survives container restarts, but dies with the Pod):

```yaml
volumes:
  - name: scratch
    emptyDir: {}
```

Good for caches and scratch files shared between containers in a Pod. **Not** for data you can't lose.

## Durable: PersistentVolume & PersistentVolumeClaim

Two roles, deliberately separated:

- A **PersistentVolume (PV)** is a piece of real storage in the cluster (a disk, an NFS share, a cloud volume).
- A **PersistentVolumeClaim (PVC)** is a Pod's *request* for storage ("I need 1Gi, read-write"). Kubernetes binds the claim to a matching PV — usually created on demand by a **StorageClass**.

> **Analogy:** a PVC is a *ticket* ("I want 1Gi"); the PV is the *seat* you're given. Your Pod holds the ticket and doesn't care which physical disk backs it.

▶ **Runnable manifest:** [`manifests/config-and-data/data-pvc.yaml`](../../manifests/config-and-data/data-pvc.yaml) (a PVC + a Pod that writes to it)

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data
spec:
  accessModes: ["ReadWriteOnce"]   # mounted read-write by a single node
  resources:
    requests:
      storage: 1Gi
```

```bash
kubectl apply -f manifests/config-and-data/data-pvc.yaml
kubectl get pvc data               # STATUS should become Bound
kubectl exec writer -- cat /data/log.txt   # the data is there

# Prove it persists: delete the Pod, recreate, data survives
kubectl delete pod writer
kubectl apply -f manifests/config-and-data/data-pvc.yaml
kubectl exec writer -- cat /data/log.txt   # still 'persisted!'
```

## ⚠️ Vanilla kubeadm has no default StorageClass

If your PVC is stuck `Pending`, this is why: unlike k3s (which bundles `local-path`), bare kubeadm ships **no** storage provisioner, so there's nothing to create a PV for your claim. Fix it once:

```bash
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/master/deploy/local-path-storage.yaml
kubectl patch storageclass local-path -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

Now PVCs bind automatically. (`kubectl get storageclass` should show `local-path (default)`.)

> 📝 **Multi-node note:** local-path / hostPath volumes live on one node's disk. On a single node that's invisible — but on a multi-node cluster a Pod rescheduled to another node can't reach that data, and `ReadWriteOnce` means only one node mounts it at a time. Networked storage (NFS, cloud disks, Ceph) exists to solve exactly this.

## Best practices

- **Use PVCs, never `hostPath`,** for app data — `hostPath` ties a Pod to one node and is a security risk.
- **Right-size `requests.storage`** and pick the `accessModes` your app truly needs (`ReadWriteOnce` is the common, widely-supported case).
- **For databases, prefer a [StatefulSet](statefulset.md)** with a `volumeClaimTemplate` so each replica gets its own stable volume.
- **Mind the reclaim policy** — know whether deleting a PVC deletes the data.

---

[← Environment Variables & Mounts](env-and-mounts.md) · [↑ Contents](../../README.md) · [StatefulSet (intro) →](statefulset.md)
