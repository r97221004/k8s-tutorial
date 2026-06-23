# ReplicaSet

> The thing that actually keeps the replica count — usually managed for you by a Deployment.

---

## Before you start

This chapter expects the `web` Deployment from [Deployment](deployment.md) to be running:

```bash
kubectl get deployment web
```

A **ReplicaSet** has one job: keep exactly *N* Pods matching its `selector` running. If there are too few, it creates more; too many, it deletes some. That's the self-healing you saw with a [Deployment](deployment.md) — and it's no coincidence.

## You already used one

When you applied the Deployment, a ReplicaSet appeared:

```bash
kubectl get rs -l app=web
```

```
NAME              DESIRED   CURRENT   READY   AGE
web-6f8c9d4b7d    3         3         3       2m
```

The Deployment created it. So why have both?

- A **ReplicaSet** keeps *one* version of your Pods at the right count.
- A **Deployment** manages **multiple ReplicaSets over time** to give you rolling updates and rollbacks: on a new image it spins up a new ReplicaSet and scales the old one down, gradually (see [Rolling Update & Rollback](../running-and-operating/rolling-updates.md)). The random suffix (`web-6f8c9d4b7d`) is tied to that Pod-template version.

```
Deployment ──▶ ReplicaSet (v1)  ──▶ Pods   ◀─ old version, scaled to 0 after update
           └─▶ ReplicaSet (v2)  ──▶ Pods   ◀─ new version
```

## So should you ever write one?

**Almost never.** A bare ReplicaSet keeps Pods running but has *no* rollout machinery — change the image and nothing happens to existing Pods. Use a [Deployment](deployment.md) instead; it gives you the ReplicaSet plus version management for free.

Knowing the ReplicaSet exists matters for **debugging**: when you `kubectl get rs` or look in [k9s](../getting-started/k9s.md) (`:rs`), an extra ReplicaSet stuck with non-zero Pods is a strong hint that a rollout is mid-flight or wedged.

## Best practices

- **Don't create ReplicaSets directly** — use a Deployment.
- When debugging a Deployment, **check its ReplicaSets** (`kubectl get rs`) to see which template version owns the current Pods.

---

[← Deployment](deployment.md) · [↑ Contents](../../README.md) · [Scheduling, Taints & Tolerations →](scheduling.md)
