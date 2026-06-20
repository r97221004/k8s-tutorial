# StatefulSet (intro)

> For workloads that need stable identity and their own persistent storage — like databases.

---

A [Deployment](../core-objects/deployment.md) treats its Pods as **interchangeable** — random names, shared storage, any order. Perfect for stateless web apps. But a database replica is *not* interchangeable: it has its own data and its own identity. A **StatefulSet** is the controller for workloads where each Pod must be distinct and durable.

## What a StatefulSet adds

- **Stable network identity** — Pods are named by ordinal (`postgres-0`, `postgres-1`), not random suffixes, and keep that name across restarts. Paired with a *headless* Service, each gets a stable DNS name.
- **Stable per-Pod storage** — a `volumeClaimTemplate` gives **each replica its own [PVC](volumes.md)** (`pgdata-postgres-0`, …). When `postgres-0` restarts, it reattaches to *its* volume, not a sibling's.
- **Ordered, predictable lifecycle** — Pods are created/updated/deleted in order (`-0`, then `-1`, …), which matters for clustered databases.

▶ **Runnable manifest:** [`manifests/config-and-data/postgres-statefulset.yaml`](../../manifests/config-and-data/postgres-statefulset.yaml) (a headless Service + StatefulSet; needs `app-secret` and a default StorageClass — see [Volumes](volumes.md))

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres        # the headless Service for stable DNS
  replicas: 1
  selector:
    matchLabels: { app: postgres }
  template:
    metadata:
      labels: { app: postgres }
    spec:
      containers:
        - name: postgres
          image: postgres:16
          # ...env from app-secret...
          volumeMounts:
            - name: pgdata
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:        # ← the key difference: a PVC PER replica
    - metadata: { name: pgdata }
      spec:
        accessModes: ["ReadWriteOnce"]
        resources: { requests: { storage: 1Gi } }
```

```bash
kubectl apply -f manifests/config-and-data/postgres-statefulset.yaml
kubectl get statefulset,pods,pvc -l app=postgres
```

```
pod/postgres-0   1/1   Running          ← ordinal name, not a random suffix
persistentvolumeclaim/pgdata-postgres-0  Bound   ← its own dedicated volume
```

Delete `postgres-0` and watch (in [k9s](../getting-started/k9s.md), `:sts` / `:pods`): it comes back with the **same name** and **reattaches the same PVC** — its data is intact.

## When (not) to use one

- ✅ Databases, message queues, anything where each replica owns data or needs a stable identity.
- ❌ Stateless apps — use a [Deployment](../core-objects/deployment.md). StatefulSets are heavier and slower to roll out; don't reach for one just because your app *uses* a database. (Often the right answer is: **stateless app as a Deployment** talking to a **managed database** outside the cluster.)

## Best practices

- **Don't run production databases in-cluster casually** — managed DBs remove a lot of operational pain. Use a StatefulSet when you have a real reason to self-host.
- **Always pair with a headless Service** (`clusterIP: None`) for stable per-Pod DNS.
- **Size `volumeClaimTemplates` carefully** — they're created per replica and usually persist even after the StatefulSet is deleted (so data isn't lost by accident).

---

[← Volumes & PersistentVolumes](volumes.md) · [↑ Contents](../../README.md) · [Health Checks →](../running-and-operating/health-checks.md)
