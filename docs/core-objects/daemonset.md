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
NAME              DESIRED   CURRENT   READY   NODE SELECTOR            AGE
kube-flannel-ds   1         1         1       <none>                  1h
kube-proxy        1         1         1       kubernetes.io/os=linux  1h
```

`DESIRED 1` here is simply "1 node in the cluster". Add nodes and these counts rise to match — no config change needed. Open [k9s](../getting-started/k9s.md) and type `:ds` to watch them.

> **Why is `kube-proxy` a DaemonSet?** Every node needs [Service](service.md) routing, so it's the textbook DaemonSet use case — one copy per node, always. The short version: a Service is how traffic finds a moving target of Pods, and `kube-proxy` is the piece on each node that makes that routing work.

## When (not) to use one

- ✅ A per-node agent (logs, metrics, networking, storage).
- ❌ A regular app — use a [Deployment](deployment.md). You want "N replicas for capacity/availability", not "one per machine".

## Best practices

- **Set `resources` requests/limits** — DaemonSet Pods run on *every* node, so a leak is multiplied across the fleet.
- **Scope with a `nodeSelector`/tolerations** if the agent should only run on some nodes (e.g. GPU nodes).

---

[← ReplicaSet](replicaset.md) · [↑ Contents](../../README.md) · [Job & CronJob →](job-cronjob.md)
