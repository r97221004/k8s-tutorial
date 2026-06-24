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

The usual flow looks like this:

```text
Pod volume -> PVC request -> StorageClass provisions PV -> real storage
```

The Pod names a PVC, the PVC describes the storage it needs, and the StorageClass decides how to create or find a matching PV. Once the PVC is `Bound`, the Pod can mount it.

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

`ReadWriteOnce` means the volume can be mounted read-write by **one node at a time**. It does not strictly mean "one Pod only": multiple Pods on the same node may be able to use the same RWO volume, but for app design you should usually treat one writer as the safe default.

```bash
kubectl apply -f manifests/config-and-data/data-pvc.yaml
kubectl get pvc data               # STATUS should become Bound
kubectl get pv                     # the cluster-side volume backing the claim
kubectl exec writer -- cat /data/log.txt   # the data is there

# Prove it persists: delete the Pod, recreate, data survives
kubectl delete pod writer
kubectl apply -f manifests/config-and-data/data-pvc.yaml
kubectl exec writer -- cat /data/log.txt   # 'persisted!' appears again, appended below the first line
```

The writer's command appends (`>>`) rather than overwrites, so the new Pod adds a *second* `persisted!` line instead of replacing the file. Seeing two lines (not one) is the actual proof: if the volume had been wiped along with the old Pod, you'd only see one.

## ⚠️ Vanilla kubeadm has no default StorageClass

If your PVC is stuck `Pending`, this is why: unlike k3s (which bundles `local-path`), bare kubeadm ships **no** storage provisioner, so there's nothing to create a PV for your claim. Fix it once:

```bash
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.36/deploy/local-path-storage.yaml
kubectl patch storageclass local-path -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

Now PVCs bind automatically. (`kubectl get storageclass` should show `local-path (default)`.)

The version in the URL is pinned on purpose: it keeps this lab reproducible instead of following whatever happens to be on the upstream `master` branch that day. If that tag ever gets removed upstream and the `apply` 404s, check the [local-path-provisioner releases page](https://github.com/rancher/local-path-provisioner/releases) for a current tag and swap it into the URL.

> 📝 **Multi-node note:** local-path / hostPath volumes live on one node's disk. On a single node that's invisible — but on a multi-node cluster a Pod rescheduled to another node can't reach that data, and `ReadWriteOnce` means only one node mounts it at a time. Networked storage (NFS, cloud disks, Ceph) exists to solve exactly this.

## Best practices

- **Use PVCs, never `hostPath`,** for app data — `hostPath` ties a Pod to one node and is a security risk.
- **Right-size `requests.storage`** and pick the `accessModes` your app truly needs (`ReadWriteOnce` is the common, widely-supported case).
- **For databases, prefer a [StatefulSet](statefulset.md)** with a `volumeClaimTemplate` so each replica gets its own stable volume.
- **Mind the reclaim policy** — know whether deleting a PVC deletes the data.

## Clean up

If you're done with the PVC exercise, delete the writer Pod and its claim:

```bash
kubectl delete -f manifests/config-and-data/data-pvc.yaml --ignore-not-found
```

Most dynamic lab StorageClasses delete the backing PV when the PVC is deleted, but a StorageClass with reclaim policy `Retain` can leave the PV and underlying data behind. Check with `kubectl get pv` if you need to verify nothing remains.

---

[← Environment Variables & Mounts](env-and-mounts.md) · [↑ Contents](../../README.md) · [StatefulSet (intro) →](statefulset.md)
