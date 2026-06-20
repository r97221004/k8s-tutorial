# Resource Requests & Limits

> Tell the scheduler how much CPU/memory a Pod needs, and cap how much it may use.

---

Every container can declare two numbers for CPU and memory: a **request** (what it needs) and a **limit** (what it may not exceed). They do very different jobs, and getting them right is most of what "running well" on Kubernetes means.

## requests vs limits

- **`requests`** — what the **scheduler** reserves. It places a Pod only on a node with at least this much free, and uses requests to pack Pods onto nodes (*bin-packing*). Requests don't cap usage; they guarantee a floor.
- **`limits`** — the hard ceiling the **kubelet/runtime enforces** at runtime.

```yaml
resources:
  requests:        # scheduling: "I need at least this"
    cpu: 50m       # 50 millicores = 0.05 of a core
    memory: 64Mi
  limits:          # runtime ceiling
    cpu: 200m
    memory: 128Mi
```

(See it in context in [`web-healthy.yaml`](../../manifests/running-and-operating/web-healthy.yaml).)

## What happens at the limit — CPU and memory differ

This trips people up:

- **CPU is compressible** → over the limit, the container is **throttled** (slowed), not killed.
- **Memory is not** → over the limit, the container is **`OOMKilled`** (terminated, then restarted).

So an undersized memory limit shows up as mysterious restarts:

```bash
kubectl get pod <name>      # RESTARTS climbing
kubectl describe pod <name> # Last State: Terminated, Reason: OOMKilled
```

## QoS classes (a consequence, not a setting)

Kubernetes derives a **Quality of Service** class from what you set — it decides who gets evicted first under node pressure:

| QoS | When | Eviction risk |
|-----|------|---------------|
| **Guaranteed** | requests == limits for all resources | lowest |
| **Burstable** | requests < limits | medium |
| **BestEffort** | nothing set | **first to be killed** |

That's why "no resources set" is risky: those Pods are BestEffort and the first sacrificed when a node runs hot.

## Best practices

- **Always set both requests and limits** — never ship BestEffort Pods to production.
- **Set `memory` limit == request** (Guaranteed for memory) so a Pod can't be OOMKilled by its own burst; leave **CPU limit higher** than request (or unset the CPU limit) to allow bursting without throttling.
- **Right-size from real usage** — `kubectl top pod` (needs metrics-server) or k9s shows actual CPU/mem; tune from data, don't guess.
- **Requests drive cost and density** — too high wastes the node, too low risks noisy-neighbour problems. Revisit them.

---

[← Health Checks](health-checks.md) · [↑ Contents](../../README.md) · [Scaling →](scaling.md)
