# Liveness Probes

> Give color-api a liveness probe, break its `/health` on purpose, and watch the kubelet restart a container that looks fine from the outside.

---

[Health Probes](health-probes.md#1-three-probes-three-questions) said the liveness probe asks "is the app still working?", and restarts the container when the answer stays no. It's for the case a crash doesn't cover: the process is up, but it's stuck. In this chapter you'll make that happen with color-api's `FAIL_LIVENESS` switch from [Color API v1.3](color-api-health-endpoints.md#2-three-switches): `/health` answers `503`, while everything else works.

## Before you start

You need color-api `1.3.0` on Docker Hub, and the `/tmp/probes` directory from [Startup Probes](startup-probes.md). Copy this chapter's manifest there, and fill in your Docker Hub username:

```bash
DOCKERHUB_USER=your-dockerhub-user      # ← change this to your username
mkdir -p /tmp/probes
cp manifests/resources-probes/color-api-liveness.yaml /tmp/probes/
sed -i "s/<YOUR_DOCKERHUB_USER>/$DOCKERHUB_USER/" /tmp/probes/color-api-liveness.yaml
grep image: /tmp/probes/color-api-liveness.yaml      # check: your username
```

## 1. Two probes, and a broken `/health`

[`color-api-liveness.yaml`](../../manifests/resources-probes/color-api-liveness.yaml) is one color-api Pod with `FAIL_LIVENESS` on, a startup probe, and a liveness probe:

```yaml
      env:
        - name: FAIL_LIVENESS
          value: "true"
      # /health fails on purpose here, so startup only checks that the app is listening
      startupProbe:
        tcpSocket:
          port: 8080
        periodSeconds: 3
        failureThreshold: 2
      livenessProbe:
        httpGet:
          path: /health
          port: 8080
        periodSeconds: 10
        failureThreshold: 3
```

The liveness probe calls `/health` every 10 seconds, and three failures in a row restart the container. Those are the defaults, written out so you can see them.

The startup probe is different from the previous chapter's. There, it called `/health`. Here, `/health` fails from the very first second, so a startup probe on it would never pass. The container would be restarted for a slow start that's really a broken health check, and the liveness probe would never get to run. So this startup probe uses `tcpSocket`, one of the other kinds from [Health Probes](health-probes.md#2-how-a-probe-checks): it passes as soon as something accepts a connection on port 8080. "Has it started?" becomes "is it listening?".

## 2. Watch it restart

```bash
kubectl apply -f /tmp/probes/color-api-liveness.yaml
kubectl get pod color-api-liveness -w
```

```text
NAME                 READY   STATUS    RESTARTS      AGE
color-api-liveness   0/1     Running   0             3s
color-api-liveness   0/1     Running   0             4s
color-api-liveness   1/1     Running   0             5s
color-api-liveness   0/1     Running   1 (1s ago)    32s
color-api-liveness   0/1     Running   1 (3s ago)    34s
color-api-liveness   1/1     Running   1 (4s ago)    35s
color-api-liveness   0/1     Running   2 (1s ago)    62s
color-api-liveness   0/1     Running   2 (3s ago)    64s
color-api-liveness   1/1     Running   2 (3s ago)    64s
...
```

Your timings will differ a little. `-w` prints a line whenever the Pod's status changes, including changes these columns don't show, so some lines look repeated. Read it in steps:

1. **About 5 seconds in, `1/1`.** The app is listening, so the startup probe passed, and with no readiness probe, the container counts as ready. `/health` is already failing, but nothing about `READY` says so.
2. **About 30 seconds in, `RESTARTS` goes to 1.** The liveness probe started once startup passed, failed three times, 10 seconds apart, and the kubelet restarted the container.
3. **Then it starts over.** The new container passes its startup probe again (it runs after every restart), is ready for half a minute, and is restarted.

Look at step 1 again: for those 30 seconds, the Pod was `1/1`, and a Service in front of it would have sent it traffic. A liveness probe doesn't affect whether a Pod is ready; only a readiness probe does, and that's the [next chapter](readiness-probes.md).

Leave it running. After a few restarts, the gaps between them grow, and the Pod shows `CrashLoopBackOff` in between: the same back-off as for a container that [crashes on its own](../pods/pod-lifecycle.md#crashloopbackoff). Press Ctrl+C.

## 3. Why it was restarted

The Pod's events say what the probe saw:

```bash
kubectl describe pod color-api-liveness | grep -E 'Unhealthy|Killing'
```

```text
  Warning  Unhealthy  8s (x9 over 98s)   kubelet  Liveness probe failed: HTTP probe failed with statuscode: 503
  Normal   Killing    8s (x3 over 78s)   kubelet  Container color-api failed liveness probe, will be restarted
```

Compare with the startup probe's failure in the previous chapter, `connection refused`: nothing was listening. This time the app answered, with `503`. The probe reached it, and it said it wasn't healthy. Three `Unhealthy` per `Killing`: that's `failureThreshold: 3`.

How did the old container end?

```bash
kubectl describe pod color-api-liveness | grep -A 2 'Last State'
```

```text
    Last State:     Terminated
      Reason:       Completed
      Exit Code:    0
```

`Completed`, exit code `0`. The app didn't crash: the kubelet sent it `SIGTERM`, as it does to stop any container, and color-api's handler shut it down cleanly. The previous container's logs show it:

```bash
kubectl logs color-api-liveness --previous
```

```text
Delay startup: false, fail liveness: true, fail readiness: false
color-api listening on port 8080 (color: blue)
SIGTERM received, shutting down
```

So `RESTARTS` going up doesn't always mean a crash. When the exit code is `0` and the events say `failed liveness probe`, Kubernetes stopped a container that was still running.

The restart is of the **container**, not the Pod. The Pod keeps its name, its IP, and its node; only the container inside it is replaced. Run `kubectl get pod color-api-liveness -o wide` after a couple of restarts, and the `IP` hasn't changed.

## 4. A restart only helps if it fixes something

These restarts will never end. `FAIL_LIVENESS` is set in the Pod's spec, so every new container fails `/health` exactly like the last. That's the limit of a liveness probe: it can only help when a fresh start fixes the problem, like a deadlock or a leak. It's also why, as [Health Probes](health-probes.md#5-common-mistakes) warned, `/health` shouldn't check a database. A restart doesn't fix a database either.

In a real app, the fix would be in the code. Here, it's turning off the switch. Do that, and replace the Pod:

```bash
sed -i 's/value: "true"/value: "false"/' /tmp/probes/color-api-liveness.yaml
kubectl replace --force -f /tmp/probes/color-api-liveness.yaml
```

Wait a minute, long enough for several liveness checks, and run `kubectl get pod color-api-liveness`: `RESTARTS` is still `0`, and `kubectl describe` shows no `Unhealthy` events. The liveness probe is still calling `/health` every 10 seconds; it just gets `200` every time.

## Clean up

```bash
kubectl delete pod color-api-liveness
```

Keep `/tmp/probes` for the next chapter.

## Best practices

- **Use a liveness probe only for problems a restart fixes**, like a deadlock or a leak. If the cause is outside the container, or in its spec, a restart just repeats it.
- **Give startup and liveness different checks when `/health` can fail for reasons other than starting.** A `tcpSocket` startup probe asks only whether the app is listening.
- **Don't read `RESTARTS` as "crashing".** Check `Last State` and the events: exit code `0` with `failed liveness probe` means Kubernetes stopped it.
- **Remember a liveness probe doesn't make a Pod unready.** Until it's restarted, a failing container still gets traffic, unless it also has a readiness probe.

---

[← Startup Probes](startup-probes.md) · [↑ Contents](../../README.md) · [Readiness Probes →](readiness-probes.md)
