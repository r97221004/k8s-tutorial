# DaemonSet (intro)

> Runs exactly one Pod per node — the pattern for node-level agents.

---

## Before you start

You only need the cluster components from setup. This chapter observes existing DaemonSets in `kube-system`; it does not create new app resources.

A [Deployment](deployment.md) says *"run N copies, anywhere there's room."* A **DaemonSet** says something different: *"run exactly one copy on every node."* As nodes join the cluster, they automatically get the Pod; as they leave, it goes with them.

That's the right model for **per-node agents** — things that must touch each machine:

- log shippers (Fluent Bit, Filebeat)
- monitoring agents (node-exporter)
- networking — the CNI (flannel) itself runs as a DaemonSet

> 📝 **Multi-node note:** a DaemonSet places one Pod on _every_ node. On this single-node cluster you'll see exactly one — picture it fanning out to every machine in a real cluster.

## See one you already have

You don't need to create a DaemonSet to study one — your cluster already runs a couple in `kube-system`:

```bash
kubectl get daemonset -n kube-system
```

```
NAME              DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR            AGE
kube-flannel-ds   1         1         1       1            1           <none>                   1h
kube-proxy        1         1         1       1            1           kubernetes.io/os=linux   1h
```

`DESIRED 1` here is simply "1 node in the cluster". Add nodes and these counts rise to match — no config change needed. Open [k9s](../getting-started/k9s.md) and type `:ds` to watch them.

> **Why is `kube-proxy` a DaemonSet?** Every node needs [Service](service.md) routing, so it's the textbook DaemonSet use case — one copy per node, always. The short version: a Service is how traffic finds a moving target of Pods, and `kube-proxy` is the piece on each node that makes that routing work.

## When (not) to use one

- ✅ A per-node agent (logs, metrics, networking, storage).
- ❌ A regular app — use a [Deployment](deployment.md). You want "N replicas for capacity/availability", not "one per machine".

## Scoping to specific nodes

A DaemonSet itself has no special power over taints — like any Pod, it's still blocked from a tainted node unless its template carries a matching toleration. `kube-flannel-ds` and `kube-proxy` show up even on this single control-plane node only because kubeadm's manifests for them explicitly include a toleration for the control-plane taint (and others) — it's not something the DaemonSet kind grants automatically. To restrict your own agent to a subset (say, only GPU nodes), add the same `nodeSelector` + `tolerations` pair from the [scheduling chapter](scheduling.md#taints-repel-tolerations-allow):

```yaml
spec:
  template:
    spec:
      nodeSelector:
        gpu: "true"
      tolerations:
        - key: gpu
          operator: Equal
          value: "true"
          effect: NoSchedule
```

Without the `nodeSelector`, the DaemonSet still spreads to every node that doesn't repel it; without the matching `tolerations`, it gets repelled by any node carrying that taint, GPU or not.

## Update strategy

What happens when you change a DaemonSet's Pod template (e.g. bumping the image) depends on `spec.updateStrategy.type`:

- **`RollingUpdate`** (the default) — old Pods are deleted and replaced node by node automatically, same idea as a Deployment rollout. This matches what you'd expect.
- **`OnDelete`** — the controller does nothing until you manually delete a Pod; the replacement then picks up the new template. Switching to this is how you get the "template changed but nothing happened" behavior, useful when you need to control exactly when each node's agent restarts.

## Best practices

- **Set `resources` requests/limits** — DaemonSet Pods run on *every* node, so a leak is multiplied across the fleet.
- **Scope with a `nodeSelector`/tolerations** if the agent should only run on some nodes (e.g. GPU nodes).

---

[← Scheduling, Taints & Tolerations](scheduling.md) · [↑ Contents](../../README.md) · [Job & CronJob →](job-cronjob.md)
