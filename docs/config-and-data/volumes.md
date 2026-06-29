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

Pass `medium: Memory` to back the volume with `tmpfs` instead of disk — faster, never written to disk, but counts against the container's memory limit:

```yaml
volumes:
  - name: fast-scratch
    emptyDir:
      medium: Memory
      sizeLimit: 128Mi   # prevents unbounded memory growth
```

This is the same backing store Kubernetes uses for Secret volumes, which is why Secret files don't appear in `df` output and are gone the moment the Pod exits.

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

The three access modes cover different multi-node patterns:

| Mode | Short | Meaning |
|---|---|---|
| `ReadWriteOnce` | RWO | Read-write by one node at a time — supported by most block storage |
| `ReadOnlyMany` | ROX | Read-only by many nodes simultaneously |
| `ReadWriteMany` | RWX | Read-write by many nodes simultaneously — requires networked storage (NFS, EFS, Ceph) |

Most cloud block disks and local-path only support RWO. If your app needs RWX (e.g. multiple Pods writing to a shared directory), you need a networked storage backend.

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

In [k9s](../getting-started/k9s.md):

1. Type `:pvc` — confirm `data` shows `Bound` and note the `STORAGECLASS`.
2. Type `:pv` — see the backing PersistentVolume and its `RECLAIM POLICY`.
3. Type `:pods`, highlight `writer`, press `s` for a shell, and run `cat /data/log.txt`.
4. Press `Ctrl-D` to delete the Pod. Unlike a Deployment, this is a bare Pod — it won't restart on its own. Run `kubectl apply -f manifests/config-and-data/data-pvc.yaml` from another terminal to recreate it.
5. Once the new Pod appears, press `s` and run `cat /data/log.txt` again — two lines confirm data persisted across the Pod deletion.

## Reclaim policy

The reclaim policy controls what happens to the PV — and the data — when its PVC is deleted:

| Policy | Behavior |
|---|---|
| `Delete` | PV and backing storage are deleted automatically — the default for most dynamic provisioners |
| `Retain` | PV is kept and data preserved, but the PV enters `Released` state and cannot be rebound until manually reclaimed |

Check what your StorageClass uses: `kubectl get storageclass -o yaml | grep reclaimPolicy`. `Delete` is convenient in a lab; `Retain` gives you a safety net in production against accidental data loss from a stray `kubectl delete pvc`.

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
- **For databases, prefer a [StatefulSet](statefulset.md)** with a `volumeClaimTemplate` — unlike a Deployment where all replicas share one PVC, a `volumeClaimTemplate` creates one PVC per replica automatically, giving each its own stable, named volume that survives rescheduling and scales correctly when you add replicas.
- **Mind the reclaim policy** — know whether deleting a PVC deletes the data.

## Clean up

If you're done with the PVC exercise, delete the writer Pod and its claim:

```bash
kubectl delete -f manifests/config-and-data/data-pvc.yaml --ignore-not-found
```

Most dynamic lab StorageClasses delete the backing PV when the PVC is deleted, but a StorageClass with reclaim policy `Retain` can leave the PV and underlying data behind. Check with `kubectl get pv` if you need to verify nothing remains.

---

[← Environment Variables & Mounts](env-and-mounts.md) · [↑ Contents](../../README.md) · [StatefulSet (intro) →](statefulset.md)
