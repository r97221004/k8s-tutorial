# Health Checks

> Tell Kubernetes when your container is alive, ready for traffic, and done starting up.

---

"The Pod is `Running`" doesn't mean "the app inside is working". A process can be up but deadlocked, or still loading a 30-second cache. **Probes** let Kubernetes check the *app*, not just the process, and act on the answer.

## Three probes, three questions

| Probe | Question | If it fails |
|-------|----------|-------------|
| **startupProbe** | "Has it finished starting?" | keep waiting until `failureThreshold` is exhausted, then restart the container |
| **readinessProbe** | "Can it serve traffic *right now*?" | remove the Pod from its [Service](../core-objects/service.md)'s endpoints (no traffic) — but don't restart |
| **livenessProbe** | "Is it still healthy?" | **restart** the container |

The crucial distinction: **readiness controls traffic; liveness controls restarts.** Getting them backwards is a classic mistake — a too-aggressive liveness probe restart-loops a Pod that was merely busy.

## Before you start

Use the known-good `web` Deployment for Part 3:

```bash
kubectl apply -f manifests/running-and-operating/web-healthy.yaml
kubectl apply -f manifests/core-objects/web-service.yaml
kubectl rollout status deployment/web
```

## A probe-ready Deployment

▶ **Runnable manifest:** [`manifests/running-and-operating/web-healthy.yaml`](../../manifests/running-and-operating/web-healthy.yaml) (the `web` Deployment, now with probes + resources)

```yaml
startupProbe:        # slow starters get up to 30×2s before liveness applies
  httpGet: { path: /, port: 80 }
  failureThreshold: 30
  periodSeconds: 2
readinessProbe:      # gate traffic until the app answers
  httpGet: { path: /, port: 80 }
  initialDelaySeconds: 2
  periodSeconds: 5
livenessProbe:       # restart if it stops answering
  httpGet: { path: /, port: 80 }
  initialDelaySeconds: 5
  periodSeconds: 10
```

While `startupProbe` is still failing, Kubernetes holds off readiness and liveness checks. Once startup succeeds, liveness takes over normal "should this container be restarted?" decisions, and readiness controls whether the Pod receives Service traffic.

Probes come in three flavours:

- **`httpGet`** — 2xx/3xx = pass (most web apps): `httpGet: { path: /healthz, port: 80 }`
- **`tcpSocket`** — port open = pass (non-HTTP services): `tcpSocket: { port: 5432 }`
- **`exec`** — a command exits `0` = pass (anything else): `exec: { command: ["cat", "/tmp/healthy"] }`

`failureThreshold` and `timeoutSeconds` tune readiness/liveness the same way they tune startupProbe: raise `failureThreshold` (or `timeoutSeconds`) for a flappy network or a slow dependency so a single blip doesn't pull a Pod out of service or restart it; keep both low when you actually want a fast reaction to real failures.

```bash
kubectl get pods -l app=web      # READY 1/1 only appears once readiness passes
kubectl describe pod -l app=web  # see Liveness/Readiness lines and probe events
kubectl get endpoints web        # only Ready Pods appear behind the Service
```

## See startup hold back the other probes

Startup probes protect slow-starting apps from being judged too early. Break startup on purpose:

```bash
kubectl patch deployment web --type json \
  -p='[{"op":"replace","path":"/spec/template/spec/containers/0/startupProbe/httpGet/path","value":"/nope"}]'
```

In k9s, type `:pods` and filter for `web`. The new Pods stay `0/1` while startup keeps failing. Press `d` on one of them and check Events; you should see startup probe failures, while readiness and liveness are still held back. If startup keeps failing until `failureThreshold` is exhausted, the container is restarted. Restore the good probe before moving on:

```bash
kubectl apply -f manifests/running-and-operating/web-healthy.yaml
kubectl rollout status deployment/web
```

## See readiness gate traffic (with k9s)

Open [k9s](../getting-started/k9s.md), type `:pods`, and filter for `web`. The **READY** column (`0/1` → `1/1`) flips only when readiness passes — that's the moment the Pod is added to its Service's endpoints. Press `d` on a Pod to see the configured Readiness/Liveness/Startup probes in its describe view.

Break readiness on purpose:

```bash
kubectl patch deployment web --type json \
  -p='[{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/httpGet/path","value":"/nope"}]'
```

In k9s, watch the new `web-...` Pods stay `Running` but `0/1` Ready. Press `d` on one of those Pods and check Events; you should see readiness probe failures. If your k9s version exposes Endpoints or EndpointSlices, you can inspect `web` there too. The portable check is:

```bash
kubectl get endpoints web
```

The Service keeps routing only to Ready Pods. During this broken rollout, the bad new Pods are not added as backends, so the old Ready Pods keep serving while the rollout stalls. Restore the good probe:

```bash
kubectl apply -f manifests/running-and-operating/web-healthy.yaml
kubectl rollout status deployment/web
```

## See liveness restart a stuck app

Readiness failure removes traffic; liveness failure restarts the container. Break liveness separately:

```bash
kubectl patch deployment web --type json \
  -p='[{"op":"replace","path":"/spec/template/spec/containers/0/livenessProbe/httpGet/path","value":"/nope"}]'
```

In k9s, stay on `:pods` and watch the **RESTARTS** column climb after the liveness probe fails enough times. Press `d` on a Pod to see liveness probe failure Events, or `l` to inspect the container logs after a restart. This intentionally breaks all replicas, so restore the Deployment as soon as you have seen the restart behavior:

```bash
kubectl apply -f manifests/running-and-operating/web-healthy.yaml
kubectl rollout status deployment/web
```

## Best practices

- **Always set readiness** on anything behind a Service — it's what makes rolling updates and scaling zero-downtime.
- **Be conservative with liveness** — only restart on true deadlock, not slowness. Many apps need *only* readiness + startup.
- **Use startupProbe for slow boots** instead of a big `initialDelaySeconds`, so liveness can still react quickly once started.
- **Probe a cheap, dependency-free endpoint** (e.g. `/healthz`) — don't let a probe hammer your database.

---

[← StatefulSet (intro)](../config-and-data/statefulset.md) · [↑ Contents](../../README.md) · [Resource Requests & Limits →](resources.md)
