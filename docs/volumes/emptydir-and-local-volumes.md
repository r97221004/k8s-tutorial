# EmptyDir and Local Volumes

> The volumes that live on the node: `emptyDir`, scratch space that lasts as long as its Pod, and `hostPath` and `local`, a node directory that outlives it.

---

[Introduction to Volumes](introduction-to-volumes.md) listed the volume types, and where each one's data lives. Three of them keep their data on the node itself, with no storage outside the cluster:

- **`emptyDir`** is defined in the **Pod**, and is **ephemeral**: its data follows the Pod's lifecycle.
- **`hostPath`** is also defined in the Pod, but names a directory on the node, so its data follows the **node's** lifecycle.
- **`local`** is a cluster-wide object of its own, whose data is pinned to **one node**: it's **persistent**, and follows that node's lifecycle.

This chapter compares them, and explains why `local` is the one to use instead of `hostPath`. The next chapter, [Working with emptyDir](emptydir.md), tries `emptyDir` hands-on.

## Before you start

Nothing to set up: this chapter has no commands.

## 1. `emptyDir`: data follows the Pod

An `emptyDir` belongs to one Pod, from start to end:

- **It's created when the Pod is assigned to a node**, as a directory on that node.
- **It starts empty.** Nothing is copied into it, which gives it its name.
- **All the Pod's containers can read and write the same files in it**, and each container can mount it at a different path.
- **It survives a container restart.** A container that crashes and restarts finds its files still there.
- **When the Pod is removed from the node, its data is deleted permanently.** A Pod that's recreated, as a Deployment does in every rollout, gets a new, empty one.

By default, the directory is on the node's disk, and counts toward the Pod's `ephemeral-storage`, as in [Introduction to Resources](../resources-probes/introduction-to-resources.md#1-the-units). With `medium: Memory`, it's a `tmpfs` in RAM instead: faster, but what's written there counts against the container's memory limit. Either way, `sizeLimit` sets its maximum size:

```yaml
volumes:
  - name: cache
    emptyDir:
      sizeLimit: 500Mi        # on the node's disk
  - name: fast-scratch
    emptyDir:
      medium: Memory          # in RAM
      sizeLimit: 64Mi
```

The two enforce it differently:

- **On disk, it isn't a hard limit.** Writes past it still succeed. The kubelet checks the usage from time to time, and when it's over, it evicts the whole Pod, `emptyDir` and all.
- **In memory, it's the size of the `tmpfs`.** A write that doesn't fit fails with `No space left on device`, and the Pod keeps running. That's if the container is still under its memory limit: the `tmpfs` counts toward it, so with a limit lower than `sizeLimit`, the container is OOMKilled first.

So `emptyDir` is for data you can afford to lose: caches, temporary files, and files passed from one of the Pod's containers to another.

## 2. `local`: data follows the node

A `local` volume is a disk, or a directory, on one particular node. It isn't declared in the Pod. It's a **PersistentVolume**, a cluster-wide object of its own, created before any Pod uses it. It belongs to no node; only its data is on one, which its `nodeAffinity` names:

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: local-pv
spec:
  capacity:
    storage: 1Gi
  accessModes:
    - ReadWriteOnce
  storageClassName: local-storage  # the StorageClass below
  local:
    path: /mnt/disks/vol1          # must already exist on the node
  nodeAffinity:                    # mandatory: which node that path is on
    required:
      nodeSelectorTerms:
        - matchExpressions:
            - key: kubernetes.io/hostname
              operator: In
              values:
                - node-1
```

It comes with a StorageClass, which creates nothing, but sets when a claim is bound:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-storage
provisioner: kubernetes.io/no-provisioner   # nothing creates volumes for this class
volumeBindingMode: WaitForFirstConsumer     # bind a claim only once a Pod that uses it is scheduled
```

What makes it work:

- **`nodeAffinity` is mandatory.** The data is on one node's disk, so the PersistentVolume has to say which node.
- **The scheduler reads that `nodeAffinity`.** Any Pod that uses the volume is placed on that node, so it always finds its data. Even after the Pod is deleted and recreated, the new one lands back there.
- **A Pod uses it through a PersistentVolumeClaim**, like any other PersistentVolume. The Pod names the claim, and the claim is bound to the volume. [Introduction to Persistent Volume Claims](introduction-to-pvcs.md) explains how.
- **`WaitForFirstConsumer` delays the binding.** Without it, a claim is bound to a volume as soon as it's created, which picks the node before the scheduler has looked at the Pod. If that node can't take the Pod, because it's out of CPU or the Pod must run elsewhere, the Pod stays `Pending` for good. With it, the scheduler picks a node that fits the Pod, then binds the claim to a volume on that node.
- **It only supports static provisioning.** Someone has to create each `local` PersistentVolume, and the directory behind it, by hand; a claim can't make a new one appear. [Dynamic Provisioning](dynamic-provisioning.md) shows how a provisioner creates volumes for claims instead.

The data outlives any Pod, but not the node. If the node fails, or its disk does, the data is gone. And until the node is back, it can't move: the old Pod is stuck `Terminating` or `Unknown`, and a new one created to replace it stays `Pending`, because the scheduler won't put it anywhere else.

## 3. Why `local`, and not `hostPath`

`hostPath` also puts data on the node, and looks simpler: the Pod names a node path, and it's mounted. But it's discouraged, for two reasons:

- **Security.** The Pod can name any path: `/etc`, the container runtime's socket, the kubelet's files. A container with write access to the wrong path can take over the node. That's why Kubernetes' baseline Pod Security Standard forbids `hostPath`, and many clusters enforce it.
- **The Pod doesn't know which node its data is on.** If it's recreated on another node, it mounts the same path there, and finds an empty directory, or someone else's files.

A `local` volume fixes both. Its path is chosen by whoever creates the PersistentVolume, not by the Pod, and its `nodeAffinity` keeps every Pod that uses it on the right node. Leave `hostPath` to node-level components that genuinely need the node's files, like the API server reading its certificates, as [Introduction to Volumes](introduction-to-volumes.md#4-volumes-you-already-have) showed.

## 4. Three lifecycles, side by side

| | `emptyDir` | `hostPath` | `local` |
|---|---|---|---|
| Defined in | The Pod's `volumes` | The Pod's `volumes`, with a node path | A PersistentVolume, claimed by a PersistentVolumeClaim |
| Created | By Kubernetes, when the Pod is assigned to a node | Usually created empty if it's missing, unless its `type` says it must already exist, so a mistyped path gives no error | By an admin, before any Pod uses it |
| A container restarts | Kept | Kept | Kept |
| The Pod is deleted and recreated | **Lost**: the new Pod gets a new, empty one | **Kept only if** the new Pod happens to land on the same node | **Kept**: the new Pod is placed on the same node |
| The node fails | Lost: the replacement Pod starts on another node, empty | Lost: the replacement Pod starts on another node, empty | Lost, and the replacement Pod stays `Pending` until the node is back |
| Follows the lifecycle of | The **Pod** | The **node**, but the Pod doesn't know which | The **node** it names |

This cluster has a single node, so every Pod lands on the same one, and `hostPath` and `local` look the same: `local`'s `nodeAffinity` has nothing to choose between. On a cluster with several nodes, `nodeAffinity` is what decides whether a recreated Pod finds its data.

## Best practices

- **Use `emptyDir` only for data you can lose.** Anything that must outlive the Pod belongs in a PersistentVolume.
- **Set `sizeLimit` on an `emptyDir`.** On disk, a Pod that goes past it is evicted before it can fill the node's disk; with `medium: Memory`, it keeps the `tmpfs` from eating the container's memory.
- **Use `local`, not `hostPath`, for durable data on a node's disk**, with a StorageClass that has `volumeBindingMode: WaitForFirstConsumer`.
- **Plan for the node failing.** A `local` volume is only as safe as its node: keep a copy of the data elsewhere, or use network storage for anything you can't lose.

---

[← Introduction to Volumes](introduction-to-volumes.md) · [↑ Contents](../../README.md) · [Working with emptyDir →](emptydir.md)
