# Rolling Update & Rollback

> Ship a new version with zero downtime — and undo it instantly when it goes wrong.

---

Change a [Deployment](../core-objects/deployment.md)'s Pod template — usually a new image — and Kubernetes rolls it out **gradually**: spin up new Pods, wait for them to be [ready](health-checks.md), then retire old ones, a few at a time. Done right, users never see downtime. And if the new version is bad, you roll back in one command.

## Before you start

Start from the known-good `nginx:1.27` Deployment:

```bash
kubectl apply -f manifests/running-and-operating/web-healthy.yaml
kubectl rollout status deployment/web
```

## Trigger a rollout

```bash
# Change the image. This creates a new rollout revision.
kubectl set image deployment/web web=nginx:1.28
# …or edit the image in the manifest and: kubectl apply -f manifests/running-and-operating/web-healthy.yaml

kubectl rollout status deployment/web      # follow it to completion
```

`kubectl rollout history` lists revision numbers. If you want human-readable notes there, annotate the Deployment with `kubernetes.io/change-cause` as part of your release process.

Watch it in [k9s](../getting-started/k9s.md) (`:pods`): new `web-…` Pods appear and go `Ready` while old ones terminate — never all at once. Under the hood the Deployment is shifting Pods from the old [ReplicaSet](../core-objects/replicaset.md) to a new one.

## Break one on purpose

A broken image creates a new ReplicaSet, but those Pods never become ready. This is the failure mode `rollout status` is meant to catch:

```bash
kubectl set image deployment/web web=nginx:does-not-exist
kubectl rollout status deployment/web --timeout=60s   # expected to time out
kubectl get pods -l app=web
kubectl describe pods -l app=web                      # Events show the image pull failure
```

The old ready Pods stay serving while the bad rollout stalls. Roll back, then wait for the Deployment to return to health:

```bash
kubectl rollout undo deployment/web
kubectl rollout status deployment/web
kubectl get deploy,rs,pods -l app=web
```

## The two knobs

`spec.strategy.rollingUpdate` controls the pace:

- **`maxUnavailable`** — how many Pods may be down during the rollout (availability floor).
- **`maxSurge`** — how many *extra* Pods may be created above the desired count (speed vs. resource headroom).

**Readiness probes gate the whole thing:** a new Pod only counts as "available" once its readiness probe passes, so a broken new version stalls the rollout instead of taking down the service.

## Roll back

```bash
kubectl rollout history deployment/web        # list revisions
kubectl rollout undo deployment/web           # back to the previous revision
kubectl rollout undo deployment/web --to-revision=2
```

Because each revision is its own ReplicaSet, rollback is instant — Kubernetes just scales the old one back up.

> 💡 **Stuck rollout?** `kubectl rollout status` hangs when new Pods never become ready (bad image, failing probe). `kubectl rollout undo` gets you back to safety; then debug with [describe/logs](debugging.md).

## Best practices

- **Always set readiness probes** — without them a rollout "succeeds" the instant Pods start, shipping a broken version with confidence.
- **Pin image tags** (`nginx:1.28`, never `latest`) so a rollout is a deliberate, reversible change.
- **Tune `maxUnavailable: 0`** for zero-downtime-critical services (surge first, then retire).
- **Watch `rollout status` in CI/CD** and fail the pipeline if it doesn't complete.

---

[← Scaling](scaling.md) · [↑ Contents](../../README.md) · [Debugging →](debugging.md)
