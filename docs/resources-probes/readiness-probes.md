# Readiness Probes

> Give color-api a readiness probe, let about half the Pods fail it, and watch the Service send traffic only to the ones that pass.

---

[Health Probes](health-probes.md#1-three-probes-three-questions) said the readiness probe asks "can the app take traffic right now?", and that a Pod that answers no is taken out of its Services, but not restarted. In this chapter you'll see both halves of that. color-api's `FAIL_READINESS` switch from [Color API v1.3](color-api-health-endpoints.md#2-three-switches) flips a coin in each container: on heads, `/ready` answers `503` for as long as the container runs. With four replicas, some Pods are ready and some never are, side by side, behind one Service.

## Before you start

You need color-api `1.3.0` and the traffic generator `1.0.0` on Docker Hub, from [Color API v1.3](color-api-health-endpoints.md) and [Traffic Generator](../services/traffic-generator.md). Everything runs in `default`, which has no quota.

This chapter has three manifests, in [`manifests/resources-probes/readiness/`](../../manifests/resources-probes/readiness/). Copy the directory, and fill in your Docker Hub username:

```bash
DOCKERHUB_USER=your-dockerhub-user      # ← change this to your username
mkdir -p /tmp/probes
cp -r manifests/resources-probes/readiness /tmp/probes/
sed -i "s/<YOUR_DOCKERHUB_USER>/$DOCKERHUB_USER/" /tmp/probes/readiness/*.yaml
grep image: /tmp/probes/readiness/*.yaml      # check: your username, twice
```

## 1. A Deployment with all three probes

[`color-api.yaml`](../../manifests/resources-probes/readiness/color-api.yaml) is a Deployment of four color-api Pods, with `FAIL_READINESS` on and all three probes:

```yaml
          env:
            - name: FAIL_READINESS
              value: "true"
          startupProbe:
            httpGet:
              path: /health
              port: 8080
            periodSeconds: 3
            failureThreshold: 2
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            periodSeconds: 10
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            periodSeconds: 5
            failureThreshold: 3
```

The startup and liveness probes are the ones from the last two chapters, both on `/health`, which works here. They're there because a real app has all three, and they stay out of the way.

The new one is the **readiness probe**, on `/ready`, every 5 seconds. It's checked more often than liveness, because whether a Pod should get traffic needs to be known quickly. A new container starts out **not ready**, and stays that way until its first readiness check passes. So `failureThreshold` only matters for a Pod that was ready and then starts failing; a Pod whose `/ready` never passes is never ready at all.

The other two manifests are a ClusterIP Service, [`color-api-svc.yaml`](../../manifests/resources-probes/readiness/color-api-svc.yaml), named `color-api`, selecting `app: color-api`, and the traffic generator, [`traffic-generator.yaml`](../../manifests/resources-probes/readiness/traffic-generator.yaml), calling `http://color-api/api?format=text` twice a second. Both are as in [ClusterIP Services](../services/clusterip-services.md).

## 2. Some ready, some not

Apply all three:

```bash
kubectl apply -f /tmp/probes/readiness/
```

```text
service/color-api created
deployment.apps/color-api created
pod/traffic-generator created
```

Wait half a minute, and look at the Pods and the Deployment:

```bash
kubectl get pods -l app=color-api
kubectl get deployment color-api
```

```text
NAME                         READY   STATUS    RESTARTS   AGE
color-api-6d9f7b8c5d-2xkqp   1/1     Running   0          32s
color-api-6d9f7b8c5d-7hn4w   0/1     Running   0          32s
color-api-6d9f7b8c5d-c9mzt   1/1     Running   0          32s
color-api-6d9f7b8c5d-wq5rl   0/1     Running   0          32s
NAME        READY   UP-TO-DATE   AVAILABLE   AGE
color-api   2/4     4            2           32s
```

Your Pod names will differ, and so will how many are ready: each Pod flipped its own coin. If all four came out the same, delete one Pod with `kubectl delete pod`: its replacement flips again. Repeat until you have both kinds.

Two things to notice:

- **The unready Pods are `Running`, with `0` restarts.** A failing readiness probe doesn't restart anything, unlike the liveness probe in the [previous chapter](liveness-probes.md). The container is fine; it's just not getting traffic. `kubectl describe pod` on one of them shows `Readiness probe failed: HTTP probe failed with statuscode: 503` every 5 seconds, and never `Killing`.
- **The Deployment counts only ready Pods as available.** `AVAILABLE` is `2`, not `4`. That's the same count a rollout waits on, as in [Health Probes](health-probes.md#1-three-probes-three-questions).

## 3. Only ready Pods get traffic

The traffic generator has been calling the Service all along. Count who answered:

```bash
kubectl logs traffic-generator | grep -o 'HOSTNAME: .*' | sort | uniq -c
```

```text
     31 HOSTNAME: color-api-6d9f7b8c5d-2xkqp
     29 HOSTNAME: color-api-6d9f7b8c5d-c9mzt
```

Only the two ready Pods. The Service's selector matches all four, but it sends traffic only to the ready ones; the unready two never get a single request. If the traffic generator started before any Pod was ready, its first few lines are `(no response …)`: for those seconds, the Service had no ready Pod to send them to.

The Service finds out through its EndpointSlice, which lists every Pod the selector matches, each with a `ready` condition:

```bash
kubectl get endpointslice -l kubernetes.io/service-name=color-api \
  -o jsonpath='{range .items[*].endpoints[*]}{.targetRef.name}{"  ready="}{.conditions.ready}{"\n"}{end}'
```

```text
color-api-6d9f7b8c5d-2xkqp  ready=true
color-api-6d9f7b8c5d-7hn4w  ready=false
color-api-6d9f7b8c5d-c9mzt  ready=true
color-api-6d9f7b8c5d-wq5rl  ready=false
```

The readiness probe sets that condition, and the Service skips every `ready=false`. The moment a Pod's probe passes, its condition flips to `true`, and it starts getting traffic, with nothing restarted.

## 4. Make them all ready

color-api's switch never changes inside a running container, so the way out here is new Pods. In a real app, a Pod whose database came back would simply pass `/ready` again, and rejoin the Service on its own.

Turn the switch off, and apply. It's a change to the Pod template, so the Deployment rolls out new Pods:

```bash
sed -i 's/value: "true"/value: "false"/' /tmp/probes/readiness/color-api.yaml
kubectl apply -f /tmp/probes/readiness/color-api.yaml
kubectl rollout status deployment/color-api
```

```text
deployment.apps/color-api configured
Waiting for deployment "color-api" rollout to finish: 2 out of 4 new replicas have been updated...
...
deployment "color-api" successfully rolled out
```

Each new Pod counts as available only once its readiness probe passes, so the rollout moves at the pace of `/ready`, not of `Running`. Once it's done, `kubectl get pods -l app=color-api` shows four new Pods, all `1/1`.

Count the traffic generator's answers again, from the last 15 seconds only:

```bash
kubectl logs traffic-generator --since=15s | grep -o 'HOSTNAME: .*' | sort | uniq -c
```

All four hostnames show up now, sharing the traffic.

## Clean up

```bash
kubectl delete -f /tmp/probes/readiness/
rm -rf /tmp/probes
```

This is the last probes chapter, so `/tmp/probes` can go too.

## Best practices

- **Put dependency checks in readiness, not liveness.** If the database is down, `/ready` should fail, so the Pod stops getting traffic it can't serve. Restarting it wouldn't bring the database back.
- **Check readiness more often than liveness.** Taking a Pod out of traffic is cheap and quickly undone; a restart isn't.
- **When a Service reaches only some of its Pods, look at `READY`.** A `0/1` Pod that's `Running` with no restarts is failing its readiness probe; `kubectl describe pod` shows why.
- **Remember that readiness paces rollouts.** A new Pod that never becomes ready stops the rollout, and the old Pods keep serving. Without a readiness probe, a rollout can't tell.

---

[← Liveness Probes](liveness-probes.md) · [↑ Contents](../../README.md) · [Scheduling, Taints & Tolerations →](../core-objects/scheduling.md)
