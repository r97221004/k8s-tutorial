# Scaling

> Run more copies on demand — by hand, or automatically based on load.

---

More load? Run more copies. Because a [Deployment](../core-objects/deployment.md)'s Pods are interchangeable and a [Service](../core-objects/service.md) load-balances across them, scaling is mostly just changing a number.

## Before you start

Start from the Part 3 `web` Deployment:

```bash
kubectl apply -f manifests/running-and-operating/web-healthy.yaml
kubectl rollout status deployment/web
```

## Manual scaling

```bash
# Declarative: edit replicas: 3 -> replicas: 5 in the manifest, then re-apply
kubectl apply -f manifests/running-and-operating/web-healthy.yaml

# Imperative (quick, for experiments):
kubectl scale deployment/web --replicas=5
kubectl get pods -l app=web -w        # watch the new Pods appear (or use k9s :pods)
```

## Autoscaling (HPA)

A **HorizontalPodAutoscaler** adjusts `replicas` for you based on a metric (commonly CPU). It needs the **metrics-server** add-on installed (vanilla kubeadm doesn't ship it):

For this Kubernetes 1.30+ lab, install a pinned Metrics Server release that supports that version line:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.7.2/components.yaml
kubectl -n kube-system rollout status deployment/metrics-server
```

On some kubeadm labs, kubelet serving certificates are not signed in the way Metrics Server expects. If `kubectl top nodes` still fails after the Deployment is ready, check `kubectl logs -n kube-system deploy/metrics-server`; for throwaway labs only, you may need to add the Metrics Server flag `--kubelet-insecure-tls`. Do not use that shortcut for production clusters.

```bash
kubectl top nodes        # should show CPU/memory; if it errors, install metrics-server first
kubectl autoscale deployment web --cpu-percent=50 --min=2 --max=10
kubectl get hpa web      # TARGETS should show current% / target%
```

Now the HPA watches average CPU across the Pods: above 50% of their *request* it adds replicas (up to 10), below it removes them (down to 2). This is exactly why [resource **requests**](resources.md) matter — the HPA measures usage *relative to the request*, so a missing request means the HPA can't compute a percentage.

If `kubectl top nodes` fails or the HPA shows `<unknown>` targets, metrics-server is not installed or cannot scrape kubelets yet. Fix metrics first; the HPA object can exist, but it can't make useful scaling decisions without those measurements.

> **requests, not limits, drive the HPA.** If CPU sits at 50% target, set sensible requests first or autoscaling misbehaves.

There's also the **VerticalPodAutoscaler** (resize a Pod's requests) and **Cluster Autoscaler** (add nodes) — beyond this guide, see [Further Reading](../appendix/further-reading.md).

> 📝 **Multi-node note:** scaling a Deployment to 5 replicas here lands all 5 on the one node. On a multi-node cluster the scheduler spreads them across machines for real high availability — and a dead node's Pods get rescheduled elsewhere (something a single node can't demonstrate).

## Best practices

- **Scale declaratively** (replicas in Git) for steady state; let an **HPA** handle variable load.
- **Set resource requests** before using an HPA — it can't autoscale on CPU% without them.
- **Add readiness probes** (see [Health Checks](health-checks.md)) so new replicas only take traffic when ready.
- **Mind `min`/`max`** — a sane floor for availability, a ceiling to cap cost/blast radius.

## Clean up

If you created the HPA for practice, remove it before continuing so it doesn't keep changing your replica count:

```bash
kubectl delete hpa web --ignore-not-found
kubectl apply -f manifests/running-and-operating/web-healthy.yaml
```

Leave Metrics Server installed if you want `kubectl top` and future HPA examples to keep working.

---

[← Resource Requests & Limits](resources.md) · [↑ Contents](../../README.md) · [Rolling Update & Rollback →](rolling-updates.md)
