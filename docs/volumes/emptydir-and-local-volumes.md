# EmptyDir and Local Volumes

> The volumes that live on the node: `emptyDir`, scratch space that lasts as long as its Pod, and `hostPath` and `local`, a node directory that outlives it.

---

[Introduction to Volumes](introduction-to-volumes.md) listed the volume types, and where each one's data lives. Two of them keep their data on the node itself, with no storage outside the cluster:

- **`emptyDir`** is defined at the **Pod** level, and is **ephemeral**: its data follows the Pod's lifecycle.
- **`local`** is defined at the **node** level, and is **persistent**: its data follows the node's lifecycle.

This chapter compares the two, and explains why `local` is the one to use instead of `hostPath`. The next chapter, [Working with emptyDir](emptydir.md), tries `emptyDir` hands-on.

## Before you start

Nothing to set up: this chapter has no commands.

## 1. `emptyDir`: data follows the Pod

An `emptyDir` belongs to one Pod, from start to end:

- **It's created when the Pod is assigned to a node**, as a directory on that node.
- **It starts empty.** Nothing is copied into it, which gives it its name.
- **All the Pod's containers can read and write the same files in it**, and each container can mount it at a different path.
- **It survives a container restart.** A container that crashes and restarts finds its files still there.
- **When the Pod is removed from the node, its data is deleted permanently.** A Pod that's recreated, as a Deployment does in every rollout, gets a new, empty one.

By default, the directory is on the node's disk, and counts toward the Pod's `ephemeral-storage`, as in [Introduction to Resources](../resources-probes/introduction-to-resources.md#1-the-units). With `medium: Memory`, it's a `tmpfs` in RAM instead: faster, but what's written there counts against the container's memory limit. Either way, `sizeLimit` caps its size:

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

So `emptyDir` is for data you can afford to lose: caches, temporary files, and files passed from one of the Pod's containers to another.

## 2. `local`: data follows the node

A `local` volume is a disk, or a directory, on one particular node. It isn't declared in the Pod. It's a **PersistentVolume**, an object of its own, created before any Pod uses it:

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
  storageClassName: local-storage  # a name that matches claims to this volume; nothing provisions it
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

What makes it work:

- **`nodeAffinity` is mandatory.** The data is on one node's disk, so the PersistentVolume has to say which node.
- **The scheduler reads that `nodeAffinity`.** Any Pod that uses the volume is placed on that node, so it always finds its data. Even after the Pod is deleted and recreated, the new one lands back there.
- **A Pod uses it through a PersistentVolumeClaim**, like any other PersistentVolume. The Pod names the claim, and the claim is bound to the volume. [Introduction to Persistent Volume Claims](introduction-to-pvcs.md) explains how.
- **It only supports static provisioning.** Someone has to create each `local` PersistentVolume, and the directory behind it, by hand; a claim can't make a new one appear. [Dynamic Provisioning](dynamic-provisioning.md) installs a provisioner that creates node-local volumes for you.

The data outlives any Pod, but not the node. If the node fails, or its disk does, the data is gone. And until the node is back, every Pod that uses the volume stays `Pending`: the scheduler won't put it anywhere else.

## 3. Why `local`, and not `hostPath`

`hostPath` also puts data on the node, and looks simpler: the Pod names a node path, and it's mounted. But it's discouraged, for two reasons:

- **Security.** The Pod can name any path: `/etc`, the container runtime's socket, the kubelet's files. A container with write access to the wrong path can take over the node. That's why Kubernetes' baseline Pod Security Standard forbids `hostPath`, and many clusters enforce it.
- **The Pod doesn't know which node its data is on.** If it's recreated on another node, it mounts the same path there, and finds an empty directory, or someone else's files.

A `local` volume fixes both. Its path is chosen by whoever creates the PersistentVolume, not by the Pod, and its `nodeAffinity` keeps every Pod that uses it on the right node. Leave `hostPath` to node-level components that genuinely need the node's files, like the API server reading its certificates, as [Introduction to Volumes](introduction-to-volumes.md#4-volumes-you-already-have) showed.

## 4. Two lifecycles, side by side

| | `emptyDir` | `local` |
|---|---|---|
| Defined in | The Pod's `volumes` | A PersistentVolume, claimed by a PersistentVolumeClaim |
| Created | By Kubernetes, when the Pod is assigned to a node | By an admin, before any Pod uses it |
| A container restarts | Kept | Kept |
| The Pod is deleted and recreated | **Lost**: the new Pod gets a new, empty one | **Kept**: the new Pod is placed on the same node |
| The node fails | Lost | Lost, and its Pods stay `Pending` |
| Follows the lifecycle of | The **Pod** | The **node** |

This cluster has a single node, so every Pod lands on the same one, and `local`'s `nodeAffinity` has nothing to choose between. On a cluster with several nodes, it's what decides whether a recreated Pod finds its data.

## Best practices

- **Use `emptyDir` only for data you can lose.** Anything that must outlive the Pod belongs in a PersistentVolume.
- **Set `sizeLimit` on an `emptyDir`**, so one Pod can't fill the node's disk, or its own memory with `medium: Memory`.
- **Use `local`, not `hostPath`, for durable data on a node's disk.**
- **Plan for the node failing.** A `local` volume is only as safe as its node: keep a copy of the data elsewhere, or use network storage for anything you can't lose.

---

[← Introduction to Volumes](introduction-to-volumes.md) · [↑ Contents](../../README.md) · [Working with emptyDir →](emptydir.md)
