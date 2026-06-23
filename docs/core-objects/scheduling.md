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

> **Important:** a toleration does not force a Pod onto a node. It only removes the repelling effect. To strongly target special nodes, combine a taint with labels plus `nodeSelector` or node affinity.

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

Apply a Pod that tolerates the taint:

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
- **Pair taints with labels** when you want placement, not just permission.
- **Check `describe pod` Events** when a Pod is `Pending`; untolerated taints are reported there.
- **Be careful in single-node labs**: one `NoSchedule` taint can block every new app Pod.

---

[← ReplicaSet](replicaset.md) · [↑ Contents](../../README.md) · [DaemonSet (intro) →](daemonset.md)
