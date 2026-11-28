# Startup Probes

> Give color-api a startup probe, watch a slow start get the container restarted over and over, and fix it by giving the app enough time.

---

[Health Probes](health-probes.md#1-three-probes-three-questions) said the startup probe asks one question, "has the app finished starting?", and restarts the container if the answer stays no for too long. In this chapter you'll see both sides of that. First a quick start, which the probe lets through. Then a slow one, using color-api's `DELAY_STARTUP` switch from [Color API v1.3](color-api-health-endpoints.md#2-three-switches), which the probe keeps killing before it can finish. Then you'll fix it, with one number.

## Before you start

You need color-api `1.3.0` on Docker Hub, from [Color API v1.3: Health Endpoints](color-api-health-endpoints.md). This chapter's Pod runs in `default`, which has no quota.

Copy the manifest, and fill in your Docker Hub username:

```bash
DOCKERHUB_USER=your-dockerhub-user      # ← change this to your username
mkdir -p /tmp/probes
cp manifests/resources-probes/color-api-startup.yaml /tmp/probes/
sed -i "s/<YOUR_DOCKERHUB_USER>/$DOCKERHUB_USER/" /tmp/probes/color-api-startup.yaml
grep image: /tmp/probes/color-api-startup.yaml      # check: your username
```

You'll edit this copy twice in this chapter, with `sed`.

## 1. A startup probe that passes

[`color-api-startup.yaml`](../../manifests/resources-probes/color-api-startup.yaml) is one color-api Pod, with the `DELAY_STARTUP` switch off and a startup probe:

```yaml
      env:
        - name: DELAY_STARTUP
          value: "false"
      startupProbe:
        httpGet:
          path: /health
          port: 8080
        # periodSeconds × failureThreshold is how long the app gets to start
        periodSeconds: 3
        failureThreshold: 2
```

The probe calls `/health` on port 8080 every 3 seconds. Two failures in a row, and the container is restarted. So the app has at most about 6 seconds to start. That's an upper bound: the first check comes almost as soon as the container starts, so the second failure lands nearer 3 seconds in. That's short on purpose; you'll see why in a moment.

The startup probe calls `/health`, the same endpoint the liveness probe will. That's the usual choice: "has it started?" and "is it still working?" are both answered by the app being up and healthy. It stops working when `/health` can fail for other reasons, as you'll make it in [Liveness Probes](liveness-probes.md).

Create the Pod, and watch it:

```bash
kubectl apply -f /tmp/probes/color-api-startup.yaml
kubectl get pod color-api-startup -w
```

```text
NAME                READY   STATUS              RESTARTS   AGE
color-api-startup   0/1     ContainerCreating   0          1s
color-api-startup   0/1     Running             0          2s
color-api-startup   1/1     Running             0          5s
```

Press Ctrl+C to stop watching. Note the middle line: the container is `Running`, but `0/1` ready. Until the startup probe passes, Kubernetes doesn't count the container as ready, even though this Pod has no readiness probe. A few seconds later, the first check passed, and it's `1/1`.

`kubectl describe` shows the probe with all its settings, including the defaults you didn't write:

```bash
kubectl describe pod color-api-startup | grep Startup
```

```text
    Startup:        http-get http://:8080/health delay=0s timeout=1s period=3s #success=1 #failure=2
```

`delay=0s` and `timeout=1s` are the defaults from [Health Probes](health-probes.md#3-when-it-counts-as-failing). `http://:8080` has no host because the kubelet fills in the Pod's IP when it calls.

## 2. A start too slow for the probe

Now turn on the switch. color-api waits 60 seconds before it listens, and the probe allows at most about 6:

```bash
sed -i 's/value: "false"/value: "true"/' /tmp/probes/color-api-startup.yaml
grep -A 1 DELAY_STARTUP /tmp/probes/color-api-startup.yaml
```

```text
        - name: DELAY_STARTUP
          value: "true"
```

Most of a running Pod's spec can't be changed, and its environment variables are part of that, so `kubectl apply` would be refused. `kubectl replace --force` deletes the Pod and creates it again from the file:

```bash
kubectl replace --force -f /tmp/probes/color-api-startup.yaml
kubectl get pod color-api-startup -w
```

```text
pod "color-api-startup" deleted
pod/color-api-startup replaced
NAME                READY   STATUS             RESTARTS     AGE
color-api-startup   0/1     Running            0            2s
color-api-startup   0/1     Running            1 (1s ago)   9s
color-api-startup   0/1     Running            2 (1s ago)   18s
color-api-startup   0/1     CrashLoopBackOff   2 (1s ago)   25s
color-api-startup   0/1     Running            3 (22s ago)  45s
...
```

Your timings will differ a little. The pattern won't: `RESTARTS` goes up every few seconds, and the Pod never gets to `1/1`. The app needs 60 seconds, and it's killed within about 6, every time. Soon the restarts are spaced out by `CrashLoopBackOff`, the same back-off as for a container that [crashes on its own](../pods/pod-lifecycle.md#crashloopbackoff). Press Ctrl+C, and ask why:

```bash
kubectl describe pod color-api-startup | grep -A 10 Events
```

```text
Events:
  Type     Reason     Age                From               Message
  ----     ------     ----               ----               -------
  Normal   Scheduled  50s                default-scheduler  Successfully assigned default/color-api-startup to node-1
  Normal   Pulled     20s (x4 over 50s)  kubelet            Container image "<you>/color-api:1.3.0" already present on machine
  Normal   Created    20s (x4 over 50s)  kubelet            Created container color-api
  Normal   Started    20s (x4 over 50s)  kubelet            Started container color-api
  Warning  Unhealthy  14s (x8 over 47s)  kubelet            Startup probe failed: Get "http://10.244.0.31:8080/health": dial tcp 10.244.0.31:8080: connect: connection refused
  Normal   Killing    14s (x4 over 44s)  kubelet            Container color-api failed startup probe, will be restarted
```

Two lines tell the story:

- **`Unhealthy`**: `connection refused`. Nothing is listening on 8080 yet, because the app is still in its 60-second delay. Eight failures so far, two per start.
- **`Killing`**: `failed startup probe, will be restarted`. After the second failure in a row, the kubelet stops the container, and starts a new one, which begins its 60 seconds all over again.

The app isn't broken. It just needs more time than the probe gives it, so it never gets to finish. The logs agree: every container is stopped during its delay.

```bash
kubectl logs color-api-startup --previous
```

```text
Delay startup: true, fail liveness: false, fail readiness: false
Starting in 60 seconds
SIGTERM received, shutting down
```

`--previous` shows the container before the current one. It was told to stop, with `SIGTERM`, before it ever reached `color-api listening`.

## 3. Give it enough time

The fix is to make `periodSeconds × failureThreshold` longer than the slowest start. 60 seconds, with some room to spare: `failureThreshold: 30` gives `3 × 30 = 90` seconds.

```bash
sed -i 's/failureThreshold: 2/failureThreshold: 30/' /tmp/probes/color-api-startup.yaml
kubectl replace --force -f /tmp/probes/color-api-startup.yaml
kubectl get pod color-api-startup -w
```

```text
pod "color-api-startup" deleted
pod/color-api-startup replaced
NAME                READY   STATUS    RESTARTS   AGE
color-api-startup   0/1     Running   0          2s
color-api-startup   1/1     Running   0          63s
```

No restarts. For a minute, the container is `Running` and `0/1`, while the probe keeps failing. Then the app starts listening, the next check passes, and it's `1/1`. Press Ctrl+C. The events show the failures, but no `Killing`:

```bash
kubectl describe pod color-api-startup | grep -E 'Unhealthy|Killing'
```

```text
  Warning  Unhealthy  10s (x20 over 67s)  kubelet  Startup probe failed: Get "http://10.244.0.32:8080/health": dial tcp 10.244.0.32:8080: connect: connection refused
```

About 20 failures, all within the 30 allowed. The startup probe has now done its job, and won't run again for this container. That's the part that matters for the next two chapters: once it passes, the liveness and readiness probes take over, and while it's still waiting, they don't run at all.

Why not just make `failureThreshold` huge, to be safe? Because it's also how long Kubernetes waits before deciding a start has really failed. An app that hangs while starting would sit there, unready, for that whole time before it's restarted. Size it from how long your app really takes, plus a margin.

## Clean up

```bash
kubectl delete pod color-api-startup
```

Keep `/tmp/probes`: the next chapters put their manifests there too.

## Best practices

- **Size `periodSeconds × failureThreshold` from the slowest real start**, plus a margin. Too short, and the app is killed before it's ready. Too long, and a start that's really stuck takes that long to be noticed.
- **When `RESTARTS` climbs but the app never logs an error**, look for `failed startup probe` in `kubectl describe pod`.

---

[← Color API v1.3: Health Endpoints](color-api-health-endpoints.md) · [↑ Contents](../../README.md) · [Liveness Probes →](liveness-probes.md)
