# Introduction to Volumes

> Why a container's files vanish, and the kinds of volumes that keep them: `emptyDir`, `hostPath` and `local`, and persistent storage.

---

Every container gets its own filesystem, built from its image. Whatever the app writes there lives in the container's writable layer, and that layer goes when the container does. You saw containers restarted over and over in [Liveness Probes](../resources-probes/liveness-probes.md); each restart starts the container from its image again, so anything the last one wrote is gone. And two containers in one Pod can't see each other's files at all, even though [they share everything else](../pods/what-is-a-pod.md).

A **volume** fixes both. It's a directory that lives outside any one container, and that the Pod's containers can mount. How long it lasts, and where its data really is, depends on its **type**. This chapter explains how a Pod uses a volume, which types there are, and how to choose. The next chapter, [EmptyDir and Local Volumes](emptydir-and-local-volumes.md), looks closer at the volumes that live on the node, and [Working with emptyDir](emptydir.md) tries the simplest one hands-on.

## Before you start

You only need a running cluster. This chapter only looks; it doesn't create anything.

## 1. Two halves: `volumes` and `volumeMounts`

A volume is declared in two places in the Pod's spec:

- **`spec.volumes`** says **what** the volume is: its name, and its type with that type's settings. It's declared once, for the whole Pod.
- **`spec.containers[*].volumeMounts`** says **where** each container sees it: the volume's name, and a `mountPath` inside that container.

```yaml
spec:
  volumes:                        # what: once, for the Pod
    - name: scratch
      emptyDir: {}                # type: an empty directory, for this Pod only
    - name: config
      configMap:                  # type: the keys of a ConfigMap, as files
        name: app-config
  containers:
    - name: app
      volumeMounts:               # where: per container
        - name: scratch
          mountPath: /tmp/work
        - name: config
          mountPath: /etc/app
          readOnly: true
    - name: helper
      volumeMounts:
        - name: scratch
          mountPath: /data        # the same volume, at another path
```

The name ties the two halves together. Each container decides for itself whether to mount a volume, and where: here `app` and `helper` share `scratch`, at different paths, and a file `app` writes to `/tmp/work/out.txt` is the file `helper` reads at `/data/out.txt`. Only `app` mounts `config`, and read-only.

Whatever the type, the container just sees a directory. The app doesn't know, or care, whether the files are on the node's disk, in a ConfigMap, or on a network disk. That's the type's business, and it's what decides the volume's lifetime. Here's a Pod with four volumes, each of a different type, and where each one's data really is: inside the Pod, on the node, in the cluster, or outside it altogether:

```mermaid
---
config:
  look: handDrawn
  theme: default
  themeVariables:
    fontFamily: '"Comic Sans MS", "Comic Sans", "Segoe Print", "Bradley Hand", cursive'
    lineColor: '#94A3B8'
    edgeLabelBackground: '#475569'
  themeCSS: |
    .edgeLabel, .edgeLabel p, .edgeLabel span { color: #FFFFFF !important; }
  flowchart:
    wrappingWidth: 400
---
flowchart LR
    subgraph cluster["☸️ Cluster"]
        subgraph node["🖥️ Node 1"]
            subgraph pod["📦 Pod"]
                vols["volumes:<br/>- pod-temp-storage<br/>- local-dir-in-node<br/>- config-map<br/>- aws-ebs"]
                c1["container 1<br/>volumeMounts:<br/>local-dir-in-node → /usr/data"]
                c2["container 2<br/>volumeMounts:<br/>aws-ebs → /data/db"]
                tmp["🗂️ pod-temp-storage<br/>emptyDir"]
            end
            local["📁 local-dir-in-node<br/>a directory on the node"]
        end
        cm["📄 config-map<br/>a ConfigMap"]
    end
    ebs["💾 aws-ebs<br/>a cloud disk"]
    note["Kubernetes supports many<br/>other storage backends,<br/>and you can add your own<br/>through a CSI driver"]

    c1 -.->|mounts| vols
    c2 -.->|mounts| vols
    vols --> tmp
    vols --> local
    vols --> cm
    vols --> ebs
    ebs ~~~ note

    classDef ctrl fill:#0F172A,stroke:#2563EB,stroke-width:2px,color:#FFFFFF
    classDef eng fill:#D97706,stroke:#92400E,stroke-width:3px,color:#FFFFFF
    classDef tgt fill:#0F172A,stroke:#16A34A,stroke-width:2px,color:#FFFFFF
    classDef memo fill:#0F172A,stroke:#DC2626,stroke-width:3px,color:#FFFFFF
    class c1,c2 eng
    class vols ctrl
    class tmp,local,cm,ebs tgt
    class note memo

    style cluster fill:#0B1120,stroke:#2563EB,color:#F1F5F9,fillStyle:solid
    style node fill:#1E293B,stroke:#334155,stroke-dasharray:5 5,color:#F1F5F9,fillStyle:solid
    style pod fill:#000000,stroke:#16A34A,color:#FFFFFF,fillStyle:solid
    style note fillStyle:solid
```

## 2. The types you'll meet

Kubernetes has many volume types. These are the ones that matter for apps:

| Type | Data lives | Use it for |
|---|---|---|
| `emptyDir` | A directory on the node, made for the Pod (or in memory) | Scratch space, caches, and files shared between a Pod's containers |
| `hostPath` | Any directory on the node you name | Node-level agents that need the node's files. Not for apps: see [EmptyDir and Local Volumes](emptydir-and-local-volumes.md#3-why-local-and-not-hostpath) |
| `local` | A disk or directory on one specific node, as a PersistentVolume | Fast durable storage pinned to a node. Preferred over `hostPath` |
| PersistentVolume, through a PersistentVolumeClaim | Wherever the volume is: a cloud disk, NFS, a node's disk | App data that must outlive Pods: databases, uploads |
| `configMap`, `secret` | A ConfigMap or Secret object in the cluster | Configuration and credentials, as files. See [Environment Variables & Mounts](../config-and-data/env-and-mounts.md#2-as-files-on-disk) |

That's not the whole list. Cloud disks, network filesystems, and storage systems like Ceph all plug in as PersistentVolumes, through **CSI** (Container Storage Interface) drivers. Anyone can write a driver for their own storage, as long as it follows the CSI specification. Older Kubernetes had some of these built in, like `awsElasticBlockStore`; those have moved out into CSI drivers. Your app's manifest doesn't change either way: it asks for storage with a claim, and the driver provides it. The rest of this part covers claims, from [Introduction to Persistent Volume Claims](introduction-to-pvcs.md) on.

## 3. Volumes on the node

Three of those types keep their data on the node itself. An `emptyDir` lasts as long as its Pod; `hostPath` and `local` outlive the Pod, but not the node. `hostPath` is discouraged for apps, and `local` is the safer way to the same disk. The next chapter, [EmptyDir and Local Volumes](emptydir-and-local-volumes.md), compares them, and explains why.

## 4. Volumes you already have

The control plane uses `hostPath` itself. The API server, a [static Pod](../getting-started/control-plane.md#static-pods), reads its certificates from the node's disk:

```bash
kubectl get pod -n kube-system -l component=kube-apiserver \
  -o jsonpath='{range .items[0].spec.volumes[*]}{.name}{"  "}{.hostPath.path}{"\n"}{end}'
```

```text
ca-certs  /etc/ssl/certs
etc-ca-certificates  /etc/ca-certificates
k8s-certs  /etc/kubernetes/pki
usr-local-share-ca-certificates  /usr/local/share/ca-certificates
usr-share-ca-certificates  /usr/share/ca-certificates
```

That's `hostPath` used as intended: a node-level component that must run on that node, and needs that node's files. An app is the opposite case.

Your own Pods have a volume too, one you never declared. Run `kubectl describe pod` on any of them, and its `Volumes:` section lists one named `kube-api-access-…`: a `projected` volume, which gathers several sources into one directory. Kubernetes adds it to every Pod, with the token and certificate the Pod would use to call the API server.

## Best practices

- **Choose a type by how long the data must live.** Scratch data: `emptyDir`. Data that must outlive the Pod: a PersistentVolumeClaim. Configuration: `configMap` or `secret`.
- **Don't keep data in the container's own filesystem.** It's gone at the next restart. Anything worth keeping goes in a volume.
- **Mount read-only when the container only reads.** `readOnly: true` on the `volumeMount` turns a bug that writes there into an error, not lost data.

---

[← Readiness Probes](../resources-probes/readiness-probes.md) · [↑ Contents](../../README.md) · [EmptyDir and Local Volumes →](emptydir-and-local-volumes.md)
