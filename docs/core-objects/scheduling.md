# Scheduling, Taints & Tolerations

> Why a Pod lands on one node, why it sometimes stays Pending, and how nodes can repel workloads.

---

So far the scheduler has felt invisible: you create a Pod, Kubernetes picks a node. In real clusters, placement is a core part of running safely. The scheduler considers node health, resource requests, labels, taints, and other constraints before binding a Pod to a node.

## The simplest constraint: nodeSelector

Label a node, then ask a Pod to run only on nodes with that label:

```bash
kubectl label node <node-name> disk=ssd
```

```yaml
spec:
  nodeSelector:
    disk: ssd
```

If no node has the label, the Pod stays `Pending`. This is the first rule of scheduling: constraints don't create capacity; they only narrow the choices.

## Taints repel, tolerations allow

A **taint** lives on a node and says "do not schedule normal Pods here." A **toleration** lives on a Pod and says "this Pod is allowed to tolerate that taint."

The common effect is `NoSchedule`:

```bash
kubectl taint node <node-name> dedicated=lab:NoSchedule
```

That does not evict Pods already running there, but new Pods without a matching toleration will not be scheduled onto that node.

> **Important:** a toleration does not force a Pod onto a node. It only removes the repelling effect. A GPU Pod with a toleration for `gpu=true:NoSchedule` can still be scheduled onto any ordinary, untainted node — the toleration just means the GPU node is no longer off-limits, not that the Pod prefers it.

To get true node dedication — only GPU Pods run on the GPU node, *and* GPU Pods always land there — combine the taint with a label and `nodeSelector`. Try it on the lab's single node:

```bash
NODE=$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')
kubectl taint node "$NODE" gpu=true:NoSchedule   # repel: keeps non-GPU Pods off
kubectl label node "$NODE" gpu=true              # tag: lets GPU Pods find this node
```

The taint string is `key=value:effect`:

```text
gpu=true:NoSchedule
^^^ ^^^^ ^^^^^^^^^^
key value  effect
```

That sets a taint with key `gpu`, value `true`, effect `NoSchedule` on the node — any Pod without a toleration matching all three is blocked from scheduling there, though Pods already running there are left alone.

▶ **Runnable manifest:** [`manifests/core-objects/gpu-dedicated-pod.yaml`](../../manifests/core-objects/gpu-dedicated-pod.yaml)

```yaml
spec:
  tolerations:        # cancels the repelling effect of the taint (permission)
    - key: gpu
      operator: Equal
      value: "true"
      effect: NoSchedule
  nodeSelector:        # pulls the Pod toward the labeled node (placement)
    gpu: "true"
```

```bash
kubectl apply -f manifests/core-objects/gpu-dedicated-pod.yaml
kubectl get pod gpu-dedicated-demo -o wide   # scheduled onto $NODE
```

Toleration without `nodeSelector` only grants permission; `nodeSelector` without the toleration is rejected outright by the taint. You need both for the node to be reserved exclusively for GPU workloads.

Clean up before moving on, so the `gpu` taint doesn't block later Pods:

```bash
kubectl delete -f manifests/core-objects/gpu-dedicated-pod.yaml --ignore-not-found
kubectl taint node "$NODE" gpu=true:NoSchedule-
kubectl label node "$NODE" gpu-
```

## Why kubeadm control planes are tainted

In a normal multi-node cluster, the control-plane node is reserved for the cluster's brain: apiserver, scheduler, controller-manager, and etcd. kubeadm protects it with a taint like:

```text
node-role.kubernetes.io/control-plane:NoSchedule
```

That is why the setup chapter removes the taint for this single-node lab: without worker nodes, normal app Pods would have nowhere to go.

## Hands-on: make a Pod Pending

Pick the single node and add a lab taint:

```bash
NODE=$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')
kubectl taint node "$NODE" dedicated=lab:NoSchedule
```

Now create a Pod without a toleration:

```bash
kubectl run no-toleration --image=busybox:1.36 --restart=Never -- sleep 3600
kubectl get pod no-toleration
kubectl describe pod no-toleration   # Events show an untolerated taint
```

It should stay `Pending` because the only node repels it.

## Add a toleration

A taint is a `key=value:effect` triple. The toleration matches it field by field:

```text
kubectl taint node "$NODE" dedicated=lab:NoSchedule
                            ^^^^^^^^^ ^^^   ^^^^^^^^^
                            key       value effect
```

```yaml
tolerations:
  - key: dedicated      # must equal the taint's key
    operator: Equal      # "Equal" means value must also match exactly
    value: lab           # must equal the taint's value
    effect: NoSchedule   # must equal the taint's effect
```

All four fields must line up for the toleration to cancel that specific taint — a toleration with the right `key` but wrong `value` (or a missing `effect`, which then matches *any* effect) behaves differently, so check each field individually when something doesn't schedule as expected:

- **`operator: Equal`** (the default) requires `key`, `value`, and `effect` to all match exactly, as above.
- **`operator: Exists`** ignores `value` entirely — it only checks that the node has a taint with that `key` (and `effect`, if set), no matter what the value is. Use this when you don't care about the taint's value, only that the key is present. With `Exists`, omit `value` in the YAML (setting one is a validation error).
- **`effect` omitted** means the toleration matches the key/value pair under *any* effect (`NoSchedule`, `PreferNoSchedule`, or `NoExecute`).
- **`key` omitted** (with `operator: Exists`) tolerates *every* taint on the node — this is how `kube-system` Pods like `kube-proxy` tolerate the control-plane taint without listing it explicitly.

The `effect` itself also changes what an untolerated taint does to a Pod:

| Effect | Untolerated Pod that's not yet scheduled | Untolerated Pod already running there |
| --- | --- | --- |
| `NoSchedule` | Stays `Pending`, like `no-toleration` above | Keeps running, unaffected |
| `PreferNoSchedule` | Scheduler tries to avoid the node, but will place it there if no other node fits | Keeps running, unaffected |
| `NoExecute` | Stays `Pending` | **Evicted** — removed from the node |

This lab only exercises `NoSchedule`, since `NoExecute` would evict the very Pods you're using to test, but it's worth knowing `NoExecute` is the effect used for things like `node.kubernetes.io/unreachable` — it actively kicks Pods off a node that's gone bad, not just blocking new ones.

Apply a Pod that tolerates the lab taint from above:

▶ **Runnable manifest:** [`manifests/core-objects/toleration-pod.yaml`](../../manifests/core-objects/toleration-pod.yaml)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: toleration-demo
spec:
  tolerations:
    - key: dedicated
      operator: Equal
      value: lab
      effect: NoSchedule
  containers:
    - name: sleeper
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
```

```bash
kubectl apply -f manifests/core-objects/toleration-pod.yaml
kubectl get pods -o wide
```

`toleration-demo` can schedule; `no-toleration` cannot.

## Clean up

Remove the Pods and the taint so later chapters don't get stuck in `Pending`:

```bash
kubectl delete pod no-toleration --ignore-not-found
kubectl delete -f manifests/core-objects/toleration-pod.yaml --ignore-not-found
kubectl taint node "$NODE" dedicated=lab:NoSchedule-
```

## Best practices

- **Use taints for special-purpose nodes**: infra, GPU, storage, or dedicated team nodes.
- **Pair taints with labels and `nodeSelector`** when you want placement, not just permission — see the GPU example above.
- **Check `describe pod` Events** when a Pod is `Pending`; untolerated taints are reported there.
- **Be careful in single-node labs**: one `NoSchedule` taint can block every new app Pod.

---

[← ReplicaSet](replicaset.md) · [↑ Contents](../../README.md) · [DaemonSet (intro) →](daemonset.md)
