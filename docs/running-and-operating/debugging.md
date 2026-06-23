# Debugging

> The handful of commands that explain almost any broken Pod.

---

Most Kubernetes troubleshooting is the same four commands. Learn to read what they tell you and the majority of problems explain themselves.

## The four commands

```bash
kubectl get pods                  # 1. STATUS + RESTARTS — the headline
kubectl describe pod <name>       # 2. events at the bottom — WHY it's stuck/crashing
kubectl logs <name>               # 3. the app's own output
kubectl logs <name> --previous    #    …the CRASHED container's logs (vital for restarts)
kubectl get events --sort-by=.lastTimestamp   # 4. cluster-wide recent events
```

`describe` is the workhorse: its **Events** section says "pulling image", "failed mount", "back-off restarting", "Insufficient cpu" — usually the answer in plain English. For a live crash loop, `logs --previous` shows what the *dying* container printed before it exited.

## Reproduce a crash loop

▶ **Runnable manifest:** [`manifests/running-and-operating/crashloop-pod.yaml`](../../manifests/running-and-operating/crashloop-pod.yaml)

```bash
kubectl apply -f manifests/running-and-operating/crashloop-pod.yaml
kubectl get pod crasher           # STATUS cycles to CrashLoopBackOff, RESTARTS climbs
kubectl logs crasher --previous   # shows "boom" — the reason it exited
kubectl describe pod crasher      # Events: "Back-off restarting failed container"
kubectl delete -f manifests/running-and-operating/crashloop-pod.yaml
```

In [k9s](../getting-started/k9s.md), a red `crasher` row jumps out; press `l` for logs, `d` for describe — same data, faster.

## Status cheat-sheet

| Status | Usually means | First check |
|--------|---------------|-------------|
| `Pending` | can't be scheduled / PVC unbound | `describe` → Events ("Insufficient cpu", "unbound PVC"); [resources](resources.md), [volumes](../config-and-data/volumes.md) |
| `ContainerCreating` (stuck) | image pull or volume mount in progress/failing | `describe` → Events |
| `ImagePullBackOff` | wrong image name/tag or no registry access | image string, pull secret |
| `CrashLoopBackOff` | container starts then exits repeatedly | `logs --previous` |
| `OOMKilled` (in describe) | hit the memory limit | raise/limit memory ([resources](resources.md)) |
| `Running` but `0/1` READY | readiness probe failing | [health checks](health-checks.md), `describe` |
| Service returns nothing | selector matches no Pods | `kubectl get endpoints <svc>` ([Service](../core-objects/service.md)) |

## Best practices

- **Start with `describe` → Events**, then `logs` (add `--previous` for restarts). Resist random `delete`/restart before you've read the cause.
- **`kubectl exec -it <pod> -- sh`** to inspect from inside (env vars, mounted files, reach a dependency).
- **`kubectl get events`** when something cluster-wide is off (scheduling, node pressure).
- See the [Troubleshooting appendix](../appendix/troubleshooting.md) for a fuller symptom→fix table.

---

[← Rolling Update & Rollback](rolling-updates.md) · [↑ Contents](../../README.md) · [Security Basics →](security-basics.md)
