# Health Checks

> Tell Kubernetes when your container is alive, ready for traffic, and done starting up.

---

"The Pod is `Running`" doesn't mean "the app inside is working". A process can be up but deadlocked, or still loading a 30-second cache. **Probes** let Kubernetes check the *app*, not just the process, and act on the answer.

## Three probes, three questions

| Probe | Question | If it fails |
|-------|----------|-------------|
| **startupProbe** | "Has it finished starting?" | keep waiting (holds off the other probes) |
| **readinessProbe** | "Can it serve traffic *right now*?" | remove the Pod from its [Service](../core-objects/service.md)'s endpoints (no traffic) — but don't restart |
| **livenessProbe** | "Is it still healthy?" | **restart** the container |

The crucial distinction: **readiness controls traffic; liveness controls restarts.** Getting them backwards is a classic mistake — a too-aggressive liveness probe restart-loops a Pod that was merely busy.

## A production-ready Deployment

▶ **Runnable manifest:** [`manifests/running-and-operating/web-healthy.yaml`](../../manifests/running-and-operating/web-healthy.yaml) (the `web` Deployment, now with probes + resources)

```yaml
startupProbe:        # slow starters get up to 30×2s before liveness applies
  httpGet: { path: /, port: 80 }
  failureThreshold: 30
  periodSeconds: 2
readinessProbe:      # gate traffic until the app answers
  httpGet: { path: /, port: 80 }
  periodSeconds: 5
livenessProbe:       # restart if it stops answering
  httpGet: { path: /, port: 80 }
  periodSeconds: 10
```

Probes come in three flavours: **`httpGet`** (2xx/3xx = pass — most web apps), **`tcpSocket`** (port open = pass — for non-HTTP), and **`exec`** (a command exits 0 = pass — anything else).

```bash
kubectl apply -f manifests/running-and-operating/web-healthy.yaml
kubectl get pods -l app=web      # READY 1/1 only appears once readiness passes
kubectl describe pod -l app=web  # see Liveness/Readiness lines and probe events
```

## See readiness gate traffic (with k9s)

Open [k9s](../getting-started/k9s.md), `:pods`. The **READY** column (`0/1` → `1/1`) flips only when readiness passes — that's the moment the Pod is added to its Service's endpoints. Break the probe (e.g. point `readinessProbe.httpGet.path` to `/nope` and re-apply) and watch the Pod stay `Running` but `0/1` — up, but receiving no traffic.

## Best practices

- **Always set readiness** on anything behind a Service — it's what makes rolling updates and scaling zero-downtime.
- **Be conservative with liveness** — only restart on true deadlock, not slowness. Many apps need *only* readiness + startup.
- **Use startupProbe for slow boots** instead of a big `initialDelaySeconds`, so liveness can still react quickly once started.
- **Probe a cheap, dependency-free endpoint** (e.g. `/healthz`) — don't let a probe hammer your database.

---

[← StatefulSet (intro)](../config-and-data/statefulset.md) · [↑ Contents](../../README.md) · [Resource Requests & Limits →](resources.md)
