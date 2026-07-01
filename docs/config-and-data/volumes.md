# Volumes & PersistentVolumes

> Where data survives a container restart — and how Pods request durable storage.

---

Storage in Kubernetes survives in layers — and knowing which layer you're on tells you exactly when data disappears:

| What got deleted | Container filesystem | Volume (e.g. `emptyDir`) | PersistentVolume |
|---|---|---|---|
| Container crashed & restarted | ❌ wiped | ✅ survives | ✅ survives |
| Pod deleted | ❌ wiped | ❌ wiped | ✅ survives |

Think of it this way: a **Volume** is the Pod's local scratch drive — it outlives individual container restarts but is gone the moment the Pod is deleted. A **PersistentVolume** is an external drive plugged into the Pod — no matter how many times the Pod comes and goes, plugging it back in gives you the same data. That's fine for a stateless web server, fatal for a database without one.

This chapter focuses on the two volume paths you'll use most while learning:

- `emptyDir` for throwaway scratch space inside one Pod.
- PersistentVolumeClaims (PVCs) for app data that should survive Pod deletion.

Kubernetes has other volume types, including `hostPath`, but avoid `hostPath` for app data in normal workloads: it mounts a directory from one specific node, which makes the Pod harder to reschedule and weakens the isolation Kubernetes usually gives you.

## Ephemeral: `emptyDir`

The simplest volume — scratch space that lives as long as the Pod (survives container restarts, but dies with the Pod):

```yaml
volumes:
  - name: scratch
    emptyDir: {}
```

Good for caches, scratch files, and handoff files shared between containers in one Pod — not for anything you can't afford to lose when the Pod goes away.

▶ **Runnable manifest:** [`manifests/config-and-data/emptydir-sidecar.yaml`](../../manifests/config-and-data/emptydir-sidecar.yaml)

The manifest runs two containers in one Pod sharing a single `emptyDir`:

```yaml
containers:
  - name: writer
    image: busybox:1.36
    command: ["sh", "-c", "i=1; while true; do echo \"line $i\" >> /shared/log.txt; i=$((i+1)); sleep 3; done"]
    volumeMounts:
      - name: shared
        mountPath: /shared
  - name: reader
    image: busybox:1.36
    command: ["sh", "-c", "sleep 3600"]
    volumeMounts:
      - name: shared
        mountPath: /shared
volumes:
  - name: shared
    emptyDir: {}
```

Both containers mount the same `shared` volume at `/shared`. `writer` appends a new line every 3 seconds; `reader` just idles so you can exec into it and observe the file growing.

```bash
kubectl apply -f manifests/config-and-data/emptydir-sidecar.yaml
kubectl wait --for=condition=Ready pod/sidecar-demo --timeout=60s

# Read the file from the reader container — written by a different container
kubectl exec sidecar-demo -c reader -- cat /shared/log.txt

# Kill the writer container to trigger a restart, then check the file is still there
kubectl exec sidecar-demo -c writer -- kill 1
kubectl wait --for=condition=Ready pod/sidecar-demo --timeout=30s
kubectl exec sidecar-demo -c reader -- cat /shared/log.txt   # lines still present

# Delete the Pod — data is gone
kubectl delete pod sidecar-demo
kubectl apply -f manifests/config-and-data/emptydir-sidecar.yaml
kubectl wait --for=condition=Ready pod/sidecar-demo --timeout=60s
kubectl exec sidecar-demo -c reader -- cat /shared/log.txt   # file is empty, starts from line 1
```

The kill step is the key proof: a container restart does **not** wipe the volume — only Pod deletion does. Seeing the line count reset to 1 after you recreate the Pod confirms the volume has the same lifetime as the Pod, not the container.

Clean up when done:

```bash
kubectl delete -f manifests/config-and-data/emptydir-sidecar.yaml --ignore-not-found
```

Pass `medium: Memory` to back the volume with `tmpfs` instead of disk — faster, never written to disk, but still counted as memory usage:

```yaml
volumes:
  - name: fast-scratch
    emptyDir:
      medium: Memory
      sizeLimit: 128Mi   # prevents unbounded memory growth
```

## Config volumes: ConfigMap & Secret

**ConfigMap and Secret volumes** follow the same `volumes:` / `volumeMounts:` pattern as `emptyDir` — they mount cluster objects as read-only files inside the Pod. Their lifecycle is independent of the Pod: the data comes from the cluster object, not from Pod-local storage.

The key mechanic: **each key in the ConfigMap or Secret becomes a file** at the `mountPath`, with the key as the filename and the value as the file content.

▶ The existing [`manifests/config-and-data/web-with-config.yaml`](../../manifests/config-and-data/web-with-config.yaml) uses both. The relevant volume section:

```yaml
volumeMounts:
  - name: config-volume
    mountPath: /etc/app          # ConfigMap keys appear as files here
    readOnly: true
  - name: secret-volume
    mountPath: /etc/app-secret   # Secret keys appear as files here
    readOnly: true
volumes:
  - name: config-volume
    configMap:
      name: app-config
  - name: secret-volume
    secret:
      secretName: app-secret
```

Apply the ConfigMap and Secret first, then the Deployment:

```bash
kubectl apply -f manifests/config-and-data/app-config.yaml
kubectl apply -f manifests/config-and-data/app-secret.yaml
kubectl apply -f manifests/config-and-data/web-with-config.yaml
kubectl wait --for=condition=Available deployment/web-config --timeout=60s
```

Exec into the Pod and inspect what Kubernetes created on disk:

```bash
POD=$(kubectl get pod -l app=web-config -o jsonpath='{.items[0].metadata.name}')

kubectl exec $POD -- ls /etc/app
# APP_GREETING  APP_TIER  app.properties

kubectl exec $POD -- cat /etc/app/app.properties
# color=blue
# log.level=info

kubectl exec $POD -- ls /etc/app-secret
# DB_PASSWORD  DB_USER
```

Every key in `app-config` landed as a file under `/etc/app`; every key in `app-secret` landed under `/etc/app-secret`. The app reads them like normal files — no code change needed when the value changes, just a ConfigMap update.

Secret volumes are backed by `tmpfs` (the same in-memory filesystem as `emptyDir { medium: Memory }`), which is why Secret files don't appear in `df` output and are gone when the Pod exits — but the Secret object itself stays in the cluster.

See the [ConfigMap](configmap.md) and [Secret](secret.md) chapters for details on file layout and live-update behavior.

One common trap: `subPath` mounts a single file or subdirectory from a volume, but it does **not** receive live updates from ConfigMaps or Secrets. Use a normal directory mount when you want Kubernetes to refresh projected config files; use `subPath` only when you deliberately want a fixed file path inside an existing directory.

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

Keep the mental model small:

- **Pod mounts PVC.**
- **PVC binds PV.**
- **StorageClass creates PV** when dynamic provisioning is available.

There are two ways a PVC gets a PV:

| Provisioning style | How it works | Common in |
|---|---|---|
| Dynamic provisioning | A StorageClass creates the PV after the PVC is requested | Labs, cloud clusters, most day-to-day app work |
| Static provisioning | An admin creates a PV first; the PVC binds to a matching one | Pre-existing NFS shares, manually managed disks, special storage policies |

Most tutorials use dynamic provisioning because it keeps the app manifest focused on the claim, not the storage backend. Static PVs are useful when the storage already exists or needs hand-tuned settings.

> **⚠️ Vanilla kubeadm has no default StorageClass.** Unlike k3s (which bundles `local-path`), bare kubeadm ships no storage provisioner — PVCs stay `Pending` indefinitely without one. Fix it once before running the exercise below:
>
> ```bash
> kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.36/deploy/local-path-storage.yaml
> kubectl patch storageclass local-path -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
> ```
>
> `kubectl get storageclass` should show `local-path (default)`. The version is pinned so the lab stays reproducible; if the tag is ever removed, check the [local-path-provisioner releases page](https://github.com/rancher/local-path-provisioner/releases) for a current tag.
>
> In k9s, type `:sc` or `:storageclasses` and confirm `local-path` is marked as the default before proceeding.
>
> **Multi-node note:** local-path volumes live on one node's disk. On a multi-node cluster a Pod rescheduled to another node can't reach that data, and `ReadWriteOnce` means only one node mounts it at a time. Networked storage (NFS, cloud disks, Ceph) exists to solve exactly this.

▶ **Runnable manifest:** [`manifests/config-and-data/data-pvc.yaml`](../../manifests/config-and-data/data-pvc.yaml) (a PVC + a Pod that writes to it)

The lab uses a bare Pod so the storage behavior is easy to see. In real apps, the same `volumes:` and `volumeMounts:` shape appears inside a Deployment's Pod template; for databases, a [StatefulSet](statefulset.md) usually creates one PVC per replica with `volumeClaimTemplates`.

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

The main access modes cover different multi-node patterns:

| Mode | Short | Meaning |
|---|---|---|
| `ReadWriteOnce` | RWO | Read-write by one node at a time — supported by most block storage |
| `ReadOnlyMany` | ROX | Read-only by many nodes simultaneously |
| `ReadWriteMany` | RWX | Read-write by many nodes simultaneously — requires networked storage (NFS, EFS, Ceph) |
| `ReadWriteOncePod` | RWOP | Read-write by one Pod in the whole cluster — useful when you want Kubernetes to enforce a single writer |

Most cloud block disks and local-path only support RWO. If your app needs RWX (e.g. multiple Pods writing to a shared directory), you need a networked storage backend. RWOP is stricter than RWO and fits leader/single-writer workloads, but support depends on the storage driver.

```bash
kubectl apply -f manifests/config-and-data/data-pvc.yaml
kubectl wait --for=condition=Ready pod/writer --timeout=60s
kubectl get pvc data               # STATUS should become Bound
kubectl get pv                     # the cluster-side volume backing the claim
kubectl exec writer -- cat /data/log.txt   # the data is there

# Prove it persists: delete the Pod, recreate, data survives
kubectl delete pod writer
kubectl apply -f manifests/config-and-data/data-pvc.yaml
kubectl wait --for=condition=Ready pod/writer --timeout=60s
kubectl exec writer -- cat /data/log.txt   # 'persisted!' appears again, appended below the first line
```

The writer's command appends (`>>`) rather than overwrites, so the new Pod adds a *second* `persisted!` line instead of replacing the file. Seeing two lines (not one) is the actual proof: if the volume had been wiped along with the old Pod, you'd only see one.

In [k9s](../getting-started/k9s.md):

1. Type `:pvc`, press `/`, and filter for `data`. Confirm it shows `Bound`, note the `STORAGECLASS`, and press `d` to describe it if it is stuck `Pending`.
2. Type `:pv` — see the backing PersistentVolume, its `CLAIM`, and its `RECLAIM POLICY`.
3. Type `:sc` or `:storageclasses` — inspect the StorageClass used by the PVC. Check the provisioner, reclaim policy, and volume binding mode.
4. Type `:pods`, highlight `writer`, press `d`, and read Events if the Pod is waiting for the PVC. Press `s` for a shell, then run `cat /data/log.txt`.
5. Press `Ctrl-D` to delete the Pod. Unlike a Deployment, this is a bare Pod — it won't restart on its own. Run `kubectl apply -f manifests/config-and-data/data-pvc.yaml` from another terminal to recreate it.
6. Once the new Pod appears and becomes Running, press `s` and run `cat /data/log.txt` again — two lines confirm data persisted across the Pod deletion.

If the Pod stays `Pending` on a multi-node cluster with `local-path`, check where the PV was created:

```bash
kubectl get pod writer -o wide
kubectl describe pod writer
kubectl describe pvc data
kubectl describe pv <pv-name>
```

Look for Events like volume node affinity conflicts or attach/mount failures. They usually mean the data lives on one node's disk but the scheduler is trying to run the Pod somewhere else.

## Reclaim policy

The reclaim policy controls what happens to the PV — and the data — when its PVC is deleted. Deleting only the Pod does not trigger reclaim behavior; the PVC is the object that owns the claim on durable storage.

| Policy | Behavior |
|---|---|
| `Delete` | PV and backing storage are deleted automatically — the default for most dynamic provisioners |
| `Retain` | PV is kept and data preserved, but the PV enters `Released` state and cannot be rebound until manually reclaimed |

Check what your StorageClass uses:

```bash
kubectl get storageclass
kubectl describe storageclass <name>
```

In k9s, type `:sc` or `:storageclasses`, highlight the class, and press `d`. `Delete` is convenient in a lab; `Retain` gives you a safety net in production against accidental data loss from a stray `kubectl delete pvc`.

Also check `VOLUMEBINDINGMODE`:

- `Immediate` provisions or binds the PV as soon as the PVC is created.
- `WaitForFirstConsumer` waits until a Pod uses the PVC, so Kubernetes can pick storage in the same zone/node topology as the Pod.

If a PVC looks `Pending`, describe both the PVC and the Pod Events before assuming storage is broken. With `WaitForFirstConsumer`, a PVC may wait until a consumer Pod exists; with no default StorageClass, it may wait forever.

## Advanced: Volume expansion

You do not need this for the first PVC exercise, but it matters once an app keeps real data. If a PVC runs out of space, you can resize it — but only if the StorageClass has `allowVolumeExpansion: true`. Check first:

```bash
kubectl get storageclass -o custom-columns="NAME:.metadata.name,EXPANSION:.allowVolumeExpansion"
```

If expansion is allowed, patch the PVC with a larger size:

```bash
kubectl patch pvc data -p '{"spec":{"resources":{"requests":{"storage":"5Gi"}}}}'
```

Kubernetes resizes the underlying volume automatically. Whether the filesystem inside expands immediately depends on the driver:

- **Online expansion supported** (most CSI drivers): the filesystem grows without restarting the Pod.
- **Online expansion not supported**: the filesystem expands the next time the Pod restarts and remounts the volume.

Check `kubectl describe pvc data` — if you see a `FileSystemResizePending` condition, a Pod restart is needed. The PVC's `STATUS` stays `Bound` throughout; watch `kubectl get pvc data` until `CAPACITY` reflects the new size.

Shrinking a PVC is not supported — you can only increase `requests.storage`.

## Best practices

- **Keep app data behind PVCs** so Pods can move without depending on a hand-picked node path.
- **Right-size `requests.storage`** and pick the `accessModes` your app truly needs (`ReadWriteOnce` is the common, widely-supported case).
- **Use `ReadWriteOncePod` for leader or single-writer workloads** when you need Kubernetes to enforce exactly one writer Pod and your storage driver supports it.
- **Avoid `subPath` for live config files** from ConfigMaps or Secrets; it pins the mounted file and skips live refresh behavior.
- **For databases, prefer a [StatefulSet](statefulset.md)** with a `volumeClaimTemplate` — unlike a Deployment where all replicas share one PVC, a `volumeClaimTemplate` creates one PVC per replica automatically, giving each its own stable, named volume that survives rescheduling and scales correctly when you add replicas.
- **Mind the reclaim policy** — know whether deleting a PVC deletes the data.

## Clean up

If you're done with the PVC exercise, delete the writer Pod and its claim. Treat this as the data deletion boundary: deleting the PVC may delete the backing storage too, depending on the reclaim policy.

```bash
kubectl delete -f manifests/config-and-data/data-pvc.yaml --ignore-not-found
```

Most dynamic lab StorageClasses delete the backing PV when the PVC is deleted, but a StorageClass with reclaim policy `Retain` can leave the PV and underlying data behind. Check with `kubectl get pv` if you need to verify nothing remains.

In k9s, type `:pods` to confirm `writer` is gone, then `:pvc` to confirm `data` is gone. Finally check `:pv`; with a `Delete` reclaim policy the PV should disappear, while with `Retain` it may remain in `Released` state for manual cleanup.

---

[← Environment Variables & Mounts](env-and-mounts.md) · [↑ Contents](../../README.md) · [StatefulSet (intro) →](statefulset.md)
