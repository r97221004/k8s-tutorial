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

The crucial distinction: **readiness controls traffic; liveness controls restarts.** Mixing them up is a classic mistake. Say your app is just slow under heavy load, still working, just taking longer to respond:

- **Readiness** failing here is fine — the Pod stops getting *new* traffic until it catches up, no harm done.
- **Liveness** failing here is bad — Kubernetes reads "slow" as "dead" and restarts the container. The new Pod immediately faces the same load, fails the same probe, and gets restarted again — a restart loop, triggered by a Pod that was never actually broken.

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

Each probe checks the app with one of three mechanisms — **`httpGet`** (2xx/3xx = pass, most web apps), **`tcpSocket`** (port open = pass, non-HTTP services), or **`exec`** (a command exits `0` = pass, anything else). The manifest above uses `httpGet` for all three; walking through them in order:

**`startupProbe`** holds off readiness and liveness until it passes once — after that it stops running for the rest of the Pod's life. `failureThreshold: 30` and `periodSeconds: 2` mean: retry every 2s, up to 30 times, before giving up — 60s to finish starting. Fail past that, and Kubernetes restarts the container.

**`readinessProbe`** then runs continuously to decide whether the Pod should receive traffic. Failing it removes the Pod from the Service's endpoints — no restart, just no traffic until it recovers.

- `initialDelaySeconds: 2` — wait 2s after the container starts before the *first* check. Since `startupProbe` already covers slow boots, this is just a small buffer, not the main defense against false failures.
- `periodSeconds: 5` — re-check every 5s from then on. Checked often because flipping traffic on/off is cheap.

**`livenessProbe`** also runs continuously, but failing it means Kubernetes decides the container is broken and restarts it.

- `initialDelaySeconds: 5`, `periodSeconds: 10` — checked less often than readiness, because restarting is expensive; it's worth waiting a bit longer to be sure before pulling that trigger.

`initialDelaySeconds` and `startupProbe` are two independent delays, not one feeding into the other — `initialDelaySeconds` always counts from when the *container* starts, `startupProbe` gating still applies on top. So the real first-check time is whichever comes later: `max(container start + initialDelaySeconds, startupProbe success time)`. With the values above, `startupProbe` can take up to 60s while readiness only waits 2s, so in practice `startupProbe` succeeding is what actually unblocks the first readiness check — but that's because of these specific numbers, not because `initialDelaySeconds` restarts its clock when `startupProbe` succeeds.

Two more fields tune how forgiving any of these probes are:

- **`failureThreshold`** — how many *consecutive* failures Kubernetes requires before it acts. It's a counter, not a timer. The default is `3`: fail, fail, fail, *then* act — one bad response alone does nothing. Combined with `periodSeconds`, it sets how long real trouble has to persist: `failureThreshold: 3` with `periodSeconds: 10` means ~30s of continuous failure before the Pod is marked not-ready or restarted.
- **`timeoutSeconds`** — how long Kubernetes waits for a single probe to respond before counting *that one* as failed (default `1s`). Too short, and a probe on a busy app times out and counts as a failure even though the app would've answered a moment later.

Raise `failureThreshold` (or `timeoutSeconds`) for a flappy network or a slow dependency, so a single blip doesn't pull a Pod out of service or restart it. Keep both low when you actually want a fast reaction to real failures.

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
