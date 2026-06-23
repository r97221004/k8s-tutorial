# Graceful Shutdown & Disruptions

> Let Pods leave service cleanly, and protect enough replicas during voluntary maintenance.

---

A rolling update is only as graceful as the app inside the Pod. Kubernetes can stop sending traffic to a Pod, send it `SIGTERM`, wait, and then force-kill it — but your app has to use that window well: stop accepting new work, finish in-flight requests, flush state, and exit.

## The shutdown sequence

When a Pod is deleted or replaced:

1. Kubernetes marks it `Terminating`.
2. Readiness starts failing or the Pod is removed from Service endpoints.
3. kubelet runs any `preStop` hook.
4. kubelet sends `SIGTERM` to the container's main process.
5. Kubernetes waits up to `terminationGracePeriodSeconds`.
6. If the process is still alive, kubelet sends `SIGKILL`.

The default grace period is 30 seconds. For web apps, this is the window to drain requests. For workers, it is the window to finish or checkpoint work.

## A graceful Deployment

▶ **Runnable manifest:** [`manifests/running-and-operating/graceful-web.yaml`](../../manifests/running-and-operating/graceful-web.yaml)

```yaml
terminationGracePeriodSeconds: 30
containers:
  - name: web
    lifecycle:
      preStop:
        exec:
          command: ["sh", "-c", "sleep 10"]
    readinessProbe:
      httpGet: { path: /, port: 80 }
```

The `preStop` sleep is a lab-friendly stand-in for real drain logic. In a real app, the handler might stop accepting new requests, close listeners, flush telemetry, or wait for workers to finish.

```bash
kubectl apply -f manifests/running-and-operating/graceful-web.yaml
kubectl rollout status deployment/graceful-web
kubectl delete pod "$(kubectl get pod -l app=graceful-web -o name | head -1)"
kubectl get pods -l app=graceful-web -w
```

You should see the old Pod linger in `Terminating` while a replacement comes up.

## PodDisruptionBudget

A **PodDisruptionBudget** protects availability during **voluntary disruptions**: node drains, cluster upgrades, or someone evicting Pods through the eviction API. It does not stop crashes, OOM kills, or node power loss.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: graceful-web
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: graceful-web
```

With 3 replicas and `minAvailable: 2`, Kubernetes should not voluntarily evict more than one matching Pod at a time.

Inspect it:

```bash
kubectl get pdb graceful-web
kubectl describe pdb graceful-web
```

## Draining a node

`kubectl drain` is how you prepare a node for maintenance. On a multi-node cluster, Pods move elsewhere if controllers can recreate them and PDBs allow it.

```bash
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
kubectl uncordon <node-name>
```

> **Single-node lab note:** draining the only node is intentionally awkward: there is nowhere for normal Pods to go. Treat the commands above as the real-cluster workflow, not something you need to run in this one-node lab.

## Clean up

```bash
kubectl delete -f manifests/running-and-operating/graceful-web.yaml --ignore-not-found
```

## Best practices

- **Handle `SIGTERM` in your app**; do not rely only on Kubernetes settings.
- **Use readiness probes** so terminating or unready Pods leave Service endpoints.
- **Set a realistic `terminationGracePeriodSeconds`** for your workload.
- **Use PDBs for replicated services** so voluntary maintenance preserves enough capacity.
- **Remember PDBs are not magic availability**; they cannot prevent involuntary failures.

---

[← Rolling Update & Rollback](rolling-updates.md) · [↑ Contents](../../README.md) · [Debugging →](debugging.md)
