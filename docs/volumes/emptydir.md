# Working with emptyDir

> Share scratch files between the containers of a Pod, and see what survives a restart and what doesn't.

---

[EmptyDir and Local Volumes](emptydir-and-local-volumes.md#1-emptydir-data-follows-the-pod) said an `emptyDir` is shared by all of a Pod's containers, survives a container restart, and is deleted with the Pod, and that going past its `sizeLimit` gets the Pod evicted. In this chapter you'll check each of those on a real Pod. It has two containers: a **writer**, which can change the files, and a **reader**, which can only read them.

## Before you start

You need a running cluster, and a shell on the node. The Pod runs in `default`, which has no quota, and uses the public `busybox` image, so there's nothing to fill in: apply the manifest straight from the repo.

## 1. One volume, two containers

[`empty-dir-example.yaml`](../../manifests/volumes/empty-dir-example.yaml) declares one `emptyDir`, and mounts it in both containers, each at its own path:

```yaml
  containers:
    - name: empty-dir-writer
      ...
      volumeMounts:
        - name: temporary-storage
          mountPath: /usr/share/temp
    - name: empty-dir-reader
      ...
      volumeMounts:
        - name: temporary-storage
          mountPath: /temp
          readOnly: true # this container can read the files, but not change them
  volumes:
    - name: temporary-storage
      emptyDir:
        sizeLimit: 100Mi
```

Both containers run `sleep 3600`, so they just stay up for an hour, and you do the writing and reading with `kubectl exec`.

`readOnly` is set on the **mount**, not on the volume. The volume is the same for both; each container decides how it sees it. The path is each container's choice too: the writer sees the files in `/usr/share/temp`, the reader in `/temp`. Here, only the writer may change the files. That's a good habit whenever one container produces data and another consumes it: a bug in the reader can't damage what the writer made.

Create the Pod:

```bash
kubectl apply -f manifests/volumes/empty-dir-example.yaml
kubectl get pod empty-dir-example
```

```text
NAME                READY   STATUS    RESTARTS   AGE
empty-dir-example   2/2     Running   0          8s
```

`2/2`: both containers are up. `kubectl describe` shows the volume, and how each container mounts it:

```bash
kubectl describe pod empty-dir-example | grep -A 1 'Mounts:'
kubectl describe pod empty-dir-example | grep -A 3 'temporary-storage:'
```

```text
    Mounts:
      /usr/share/temp from temporary-storage (rw)
--
    Mounts:
      /temp from temporary-storage (ro)
```

```text
  temporary-storage:
    Type:       EmptyDir (a temporary directory that shares a pod's lifetime)
    Medium:
    SizeLimit:  100Mi
```

The first `Mounts` is the writer's, `rw`; the second is the reader's, `ro`. `Medium` is empty, which means the node's disk; with `medium: Memory`, it would say `Memory`.

## 2. Write in one container, read in the other

Write a file from the writer. `-c` picks the container, as in [Working with Pods](../pods/working-with-pods.md#pods-with-more-than-one-container):

```bash
kubectl exec empty-dir-example -c empty-dir-writer -- \
  sh -c 'echo "hello from the writer" > /usr/share/temp/hello.txt'
```

Then read it from the reader:

```bash
kubectl exec empty-dir-example -c empty-dir-reader -- cat /temp/hello.txt
```

```text
hello from the writer
```

Two containers, two separate filesystems, two paths, and one shared directory. Now try to write from the reader:

```bash
kubectl exec empty-dir-example -c empty-dir-reader -- touch /temp/from-reader.txt
```

```text
touch: /temp/from-reader.txt: Read-only file system
command terminated with exit code 1
```

The reader sees every file the writer makes, and can't add or change any.

`kubectl logs` shows nothing for either container: the file was written to the volume, not to stdout. To see what's in a volume, `exec` into a container that mounts it.

## 3. Where it is on the node

An `emptyDir` on disk is just a directory the kubelet made on the node, under the Pod's UID. Get the UID:

```bash
POD_UID=$(kubectl get pod empty-dir-example -o jsonpath='{.metadata.uid}')
echo $POD_UID
```

```text
6f1c2d3e-8a4b-4c5d-9e0f-1a2b3c4d5e6f
```

Yours will differ. On the node, the volume is in the kubelet's directory for that Pod, under its name:

```bash
sudo ls -l /var/lib/kubelet/pods/$POD_UID/volumes/kubernetes.io~empty-dir/temporary-storage
```

```text
total 4
-rw-r--r-- 1 root root 22 Nov 28 10:12 hello.txt
```

That's the file the writer made. The writer's `/usr/share/temp` and the reader's `/temp` are both this one directory, mounted twice.

## 4. A container restart keeps the files

First, have the writer save a second file, this one outside the volume, in its own filesystem:

```bash
kubectl exec empty-dir-example -c empty-dir-writer -- \
  sh -c 'echo "not in the volume" > /tmp/notes.txt'
```

Now kill the writer container from the node, with `crictl`, from [The Data Plane](../getting-started/data-plane.md):

```bash
sudo crictl stop $(sudo crictl ps --name empty-dir-writer -q)
sleep 5      # give the kubelet a moment to notice, and start a new container
kubectl get pod empty-dir-example
```

```text
NAME                READY   STATUS    RESTARTS      AGE
empty-dir-example   2/2     Running   1 (4s ago)    4m
```

If `RESTARTS` is still `0`, or `READY` is `1/2`, wait a few more seconds and run `kubectl get` again.

`RESTARTS` is `1`: the kubelet started a new writer container, from its image, with a fresh filesystem of its own. Ask the new writer for both files:

```bash
kubectl exec empty-dir-example -c empty-dir-writer -- cat /usr/share/temp/hello.txt /tmp/notes.txt
```

```text
hello from the writer
cat: can't open '/tmp/notes.txt': No such file or directory
command terminated with exit code 1
```

`hello.txt` is in the volume, which isn't part of the container's filesystem, so it survived. `/tmp/notes.txt` was in the old container's own filesystem, and went with it. That's the problem from [Introduction to Volumes](introduction-to-volumes.md), and the volume is the fix.

## 5. A new Pod gets a new, empty one

Delete the Pod, and create it again from the same file:

```bash
kubectl delete pod empty-dir-example
kubectl apply -f manifests/volumes/empty-dir-example.yaml
```

The delete takes about 30 seconds. Each container's main process runs as PID 1, and has no handler for `SIGTERM`; PID 1 ignores signals it doesn't handle. So both containers, at the same time, sit out the 30-second grace period before they're killed, as in [Color API v1.3](../resources-probes/color-api-health-endpoints.md#2-three-switches).

Same name, same spec, but a new Pod, with a new `emptyDir`:

```bash
kubectl exec empty-dir-example -c empty-dir-reader -- cat /temp/hello.txt
```

```text
cat: can't open '/temp/hello.txt': No such file or directory
command terminated with exit code 1
```

The old directory on the node is gone too. `$POD_UID` still holds the old Pod's UID:

```bash
sudo ls /var/lib/kubelet/pods/$POD_UID
```

```text
ls: cannot access '/var/lib/kubelet/pods/6f1c2d3e-8a4b-4c5d-9e0f-1a2b3c4d5e6f': No such file or directory
```

When the Pod was deleted, the kubelet removed its directory, and the volume with it. A Deployment's rollout does the same to every Pod it replaces. Data that has to survive this belongs in a PersistentVolume, from [Introduction to Persistent Volume Claims](introduction-to-pvcs.md) on.

## 6. Going past `sizeLimit`

The volume has `sizeLimit: 100Mi`. [EmptyDir and Local Volumes](emptydir-and-local-volumes.md#1-emptydir-data-follows-the-pod) said that on disk, that isn't a hard limit: writes past it succeed, and the kubelet evicts the Pod. Write 150Mi into the new Pod's volume:

```bash
kubectl exec empty-dir-example -c empty-dir-writer -- \
  dd if=/dev/zero of=/usr/share/temp/big bs=1M count=150
```

```text
150+0 records in
150+0 records out
157286400 bytes (150.0MB) copied, 0.4 seconds, 375.0MB/s
```

No error: all 150Mi were written. The kubelet only notices when it next measures the volume, which can take up to about a minute. Wait that long, then check the Pod:

```bash
sleep 60
kubectl describe pod empty-dir-example | grep -E '^(Status|Reason|Message):'
```

```text
Status:           Failed
Reason:           Evicted
Message:          Usage of EmptyDir volume "temporary-storage" exceeds the limit "100Mi".
```

If it still says `Status: Running`, with no `Reason`, the kubelet hasn't measured it yet: wait a little longer, and run it again.

The whole Pod was evicted: both containers stopped, and the volume was deleted, `big` and all. `kubectl get pod` shows it as `Evicted`. Nothing brings it back, because it's a bare Pod. Under a Deployment, a new Pod would replace it, with a new, empty volume.

That's what `sizeLimit` protects: one Pod filling the volume can't fill the node's disk, and starve every other Pod on it. It costs this Pod its data, which is fine for an `emptyDir`, since nothing in it should be irreplaceable.

## Clean up

```bash
kubectl delete -f manifests/volumes/empty-dir-example.yaml
```

## Best practices

- **Mount read-only wherever a container only reads.** `readOnly: true` on the mount keeps a bug in one container from damaging another's data.
- **Set `sizeLimit` on every `emptyDir`.** Going past it costs one Pod its scratch data, instead of filling the node's disk.
- **Use `exec`, not `logs`, to look at a volume.** `kubectl logs` only shows stdout and stderr.
- **Don't keep anything in an `emptyDir` you can't rebuild.** It survives a container restart, but not the Pod.

---

[← EmptyDir and Local Volumes](emptydir-and-local-volumes.md) · [↑ Contents](../../README.md) · [Introduction to Persistent Volume Claims →](introduction-to-pvcs.md)
