# StatefulSet (intro)

> For workloads that need stable identity and their own persistent storage — like databases.

---

A [Deployment](../core-objects/deployment.md) treats its Pods as **interchangeable** — random names, shared storage, any order. Perfect for stateless web apps. But a database replica is *not* interchangeable: it has its own data and its own identity. A **StatefulSet** is the controller for workloads where each Pod must be distinct and durable.

The PostgreSQL example below is a lab for learning StatefulSet mechanics, not a production database recommendation. Real production databases need backup/restore, upgrade, failover, monitoring, and storage choices beyond this intro.

It is also a **single-replica lab**, not high availability PostgreSQL. Scaling this example teaches StatefulSet identity and PVC behavior; it does not create a safe replicated database.

## What a StatefulSet adds

- **Stable network identity** — Pods are named by ordinal (`postgres-0`, `postgres-1`), not random suffixes, and keep that name across restarts. Paired with a *headless* Service, each gets a stable DNS name.
- **Stable per-Pod storage** — a `volumeClaimTemplate` gives **each replica its own [PVC](volumes.md)** (`pgdata-postgres-0`, …). When `postgres-0` restarts, it reattaches to *its* volume, not a sibling's.
- **Ordered, predictable lifecycle** — Pods are created/updated/deleted in order (`-0`, then `-1`, …), which matters for clustered databases.

### What a headless Service is

A **headless Service** is a Service with `clusterIP: None` — it gets no virtual IP and does no load balancing. Instead of one DNS name that resolves to a single (load-balanced) IP, DNS resolves it to the IPs of **every matching Pod** individually.

| | Normal Service | Headless Service |
|---|---|---|
| ClusterIP | Virtual IP assigned | `None` |
| DNS lookup returns | One A record (the virtual IP) | One A record per matching Pod |
| Traffic routing | kube-proxy load-balances to any backing Pod | Client resolves a specific Pod's IP/DNS name itself |

Paired with a StatefulSet, this gives each Pod its own stable DNS name:

```
postgres-0.postgres.default.svc.cluster.local
postgres-1.postgres.default.svc.cluster.local
```

That matters because StatefulSet Pods are not interchangeable — you need to reach *a specific* replica (e.g. the primary at `postgres-0`), not "any Pod behind the Service," which is all a normal (non-headless) Service gives you.

### What a volumeClaimTemplate is

A regular Pod (or Deployment) references an *already-existing* PVC by name in `volumes:` — every replica that mounts it shares that one PVC. As [Volumes](volumes.md) explains, that's fine for read-only data but a footgun once multiple replicas write to it.

`volumeClaimTemplates` is different: instead of naming one PVC, it's a *template* the StatefulSet controller uses to create a **new PVC per replica**, automatically, the first time each ordinal comes up. Kubernetes names each one `<template-name>-<statefulset-name>-<ordinal>` — hence `pgdata-postgres-0`, `pgdata-postgres-1`, …

| | Pod/Deployment `volumes:` | StatefulSet `volumeClaimTemplates:` |
|---|---|---|
| PVC | You create it yourself, once | Controller creates one automatically per replica |
| Sharing | All replicas mount the **same** PVC | Each replica gets its **own** PVC |
| Naming | Whatever you called it | `<template-name>-<statefulset-name>-<ordinal>` |

This is what makes `postgres-1` safe to run alongside `postgres-0` without them corrupting each other's data — see the `pgdata-postgres-0` / `pgdata-postgres-1` PVCs in the scaling exercise below. It's also why the PVCs **outlive** the StatefulSet: they aren't owned by a single Pod, so scaling down or deleting the StatefulSet doesn't delete them (see [Best practices](#best-practices) and [Volumes](volumes.md) for the full reclaim-policy story).

▶ **Runnable manifest:** [`manifests/config-and-data/postgres-statefulset.yaml`](../../manifests/config-and-data/postgres-statefulset.yaml) (a headless Service + StatefulSet; needs `app-secret` and a default StorageClass — see [Volumes](volumes.md))

Here's the core shape — just enough to see the three things a StatefulSet adds. (The runnable file also adds production-style hardening — probes, a security context, resource limits — explained separately in [Hardening this lab](#hardening-this-lab) below, after the core mechanics make sense.)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
spec:
  clusterIP: None          # headless: no single virtual IP
  selector:
    app: postgres
  ports:
    - name: postgres
      port: 5432
      targetPort: postgres
---
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
          image: postgres:16        # lab image tag; pin a patch version/digest in production
          ports:
            - containerPort: 5432
              name: postgres
          env:
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: app-secret
                  key: DB_USER
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: app-secret
                  key: DB_PASSWORD
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
          volumeMounts:
            - name: pgdata
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:        # ← the key difference: a PVC PER replica
    - metadata: { name: pgdata }
      spec:
        accessModes: ["ReadWriteOnce"]
        # storageClassName omitted: use the cluster's default StorageClass for this lab.
        resources: { requests: { storage: 1Gi } }
```

```bash
kubectl apply -f manifests/config-and-data/app-secret.yaml
kubectl apply -f manifests/config-and-data/postgres-statefulset.yaml
kubectl wait --for=condition=Ready pod/postgres-0 --timeout=180s
kubectl exec postgres-0 -- sh -c 'until pg_isready -U appuser; do sleep 2; done'
kubectl get statefulset,pods -l app=postgres
kubectl get pvc pgdata-postgres-0
kubectl exec postgres-0 -- hostname
```

```
pod/postgres-0   1/1   Running          ← ordinal name, not a random suffix
persistentvolumeclaim/pgdata-postgres-0  Bound   ← its own dedicated volume
```

With the headless Service, that same Pod also gets a stable DNS name:

```text
postgres-0.postgres.default.svc.cluster.local
```

That name has the form `<pod>.<service>.<namespace>.svc.cluster.local`. `postgres` appears twice — once as the Pod's name, once as the Service's `metadata.name` — and `default` is the **namespace**, not part of the Service name. Neither manifest sets `metadata.namespace`, so `kubectl apply` used whatever namespace your current context defaults to; this tutorial has stayed on `default` throughout. Deploy into another namespace (e.g. `-n mydb`) and the DNS name changes to `postgres-0.postgres.mydb.svc.cluster.local` accordingly.

You can verify that DNS name from another Pod:

```bash
kubectl run dns-test --image=busybox:1.36 --restart=Never --command -- sleep 3600
kubectl wait --for=condition=Ready pod/dns-test --timeout=60s
kubectl exec dns-test -- nslookup postgres-0.postgres.default.svc.cluster.local
kubectl delete pod dns-test
```

Now write a row into PostgreSQL so the persistence test proves more than "the Pod came back":

```bash
kubectl exec postgres-0 -- psql -U appuser -d appuser -c \
  "CREATE TABLE IF NOT EXISTS statefulset_lab (id int primary key, note text);"
kubectl exec postgres-0 -- psql -U appuser -d appuser -c \
  "INSERT INTO statefulset_lab VALUES (1, 'survived a Pod delete') ON CONFLICT (id) DO UPDATE SET note = EXCLUDED.note;"
kubectl exec postgres-0 -- psql -U appuser -d appuser -c "SELECT * FROM statefulset_lab;"
```

Delete `postgres-0` and watch (in [k9s](../getting-started/k9s.md), `:sts` / `:pods`): it comes back with the **same name** and **reattaches the same PVC**.

```bash
kubectl delete pod postgres-0
kubectl wait --for=condition=Ready pod/postgres-0 --timeout=180s
kubectl exec postgres-0 -- sh -c 'until pg_isready -U appuser; do sleep 2; done'
kubectl get pods,pvc
kubectl exec postgres-0 -- psql -U appuser -d appuser -c "SELECT * FROM statefulset_lab;"
```

Scale to two replicas and you will see the ordinal pattern repeat: `postgres-1` appears with its own `pgdata-postgres-1` PVC.

```bash
kubectl scale statefulset/postgres --replicas=2
kubectl get pods,pvc
kubectl scale statefulset/postgres --replicas=1
kubectl get pvc   # pgdata-postgres-1 is still here
```

That second Pod is another independent PostgreSQL instance with its own volume. This lab does not configure PostgreSQL replication.

Scaling down only removes the Pod — `pgdata-postgres-1` is **not** deleted. If you scale back to 2, `postgres-1` reattaches to that same PVC instead of getting a fresh volume. This is the same "PVCs outlive the Pod" behavior as the delete/reattach test above, just triggered by scaling instead of a manual delete.

By default, StatefulSets use ordered lifecycle behavior: Kubernetes creates `postgres-0` before `postgres-1`, and deletes higher ordinals first when scaling down. The field behind that default is `podManagementPolicy: OrderedReady`.

This ordering isn't just cosmetic — it's what makes primary/replica database clustering possible. A classic pattern: `postgres-1`'s startup script runs `pg_basebackup` against the primary at `postgres-0.postgres.default.svc.cluster.local` to clone its data before joining as a replica. If `postgres-1` came up before `postgres-0` was Ready, the primary might not be discoverable or accepting connections yet, and the replica bootstrap could fail. `OrderedReady` makes Kubernetes wait for the lower ordinal Pod to become Ready before creating the next one.

Updates are ordered too. The default `updateStrategy: RollingUpdate` replaces Pods from the highest ordinal down, so `postgres-1` updates before `postgres-0`.

`PGDATA` points PostgreSQL at a subdirectory inside the mounted volume. That avoids a common lab failure where the image expects to initialize an empty data directory but the volume mount contains filesystem metadata.

## Hardening this lab

The core YAML above is enough to see stable identity, per-Pod storage, and ordering. The runnable manifest goes further and adds a few fields you'll see in most real StatefulSets. Here's what each one does, in plain terms:

| Field | What it does | Why it's here |
|---|---|---|
| `terminationGracePeriodSeconds: 30` | Gives PostgreSQL 30s to shut down cleanly before Kubernetes force-kills it | An abrupt `SIGKILL` mid-write risks a corrupted or unclean data directory |
| `securityContext` (`runAsUser/Group: 999`, `fsGroup`) | Runs the container as the image's built-in non-root `postgres` user instead of root, and makes the mounted volume writable by that user's group | Running databases as root is an unnecessary privilege; this is the standard hardening for the official postgres image |
| `startupProbe` | Gives the container up to `30 × 5s = 150s` to finish first-time initialization before liveness checks start judging it | Without this, a slow `initdb` on first boot could get killed by the liveness probe before it ever finishes starting |
| `readinessProbe` | Runs `pg_isready` every 5s; the Pod isn't marked `Ready` (and won't receive traffic) until it passes | Without it, `kubectl wait --for=condition=Ready` would report Ready as soon as the container process starts — before PostgreSQL can actually accept connections |
| `livenessProbe` | Runs `pg_isready` every 10s once the Pod is up; if it keeps failing, Kubernetes restarts the container | Recovers automatically if PostgreSQL wedges or stops responding without the process exiting |
| `resources` (requests/limits) | Reserves 100m CPU / 256Mi memory, caps at 500m CPU / 512Mi memory | Keeps the scheduler informed and stops one runaway Pod from starving others on the node |

Here's just the additional fields, layered onto the container spec and Pod spec from the core example above:

```yaml
      # Pod-level, alongside `containers:`
      terminationGracePeriodSeconds: 30
      securityContext:
        runAsNonRoot: true
        runAsUser: 999
        runAsGroup: 999
        fsGroup: 999
      containers:
        - name: postgres
          # ...same image/env/volumeMounts as above...
          startupProbe:
            exec:
              command: ["sh", "-c", "pg_isready -U \"$POSTGRES_USER\""]
            failureThreshold: 30
            periodSeconds: 5
          readinessProbe:
            exec:
              command: ["sh", "-c", "pg_isready -U \"$POSTGRES_USER\""]
            initialDelaySeconds: 5
            periodSeconds: 5
          livenessProbe:
            exec:
              command: ["sh", "-c", "pg_isready -U \"$POSTGRES_USER\""]
            initialDelaySeconds: 30
            periodSeconds: 10
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

This is still a tutorial-sized lab, not a hardened production posture — real production databases add network policy, pod security standards, backups, monitoring, and tested restore procedures on top of this.

## When (not) to use one

- ✅ Databases, message queues, anything where each replica owns data or needs a stable identity.
- ❌ Stateless apps — use a [Deployment](../core-objects/deployment.md). StatefulSets are heavier and slower to roll out; don't reach for one just because your app *uses* a database. (Often the right answer is: **stateless app as a Deployment** talking to a **managed database** outside the cluster.)

## Best practices

- **Don't run production databases in-cluster casually** — managed DBs remove a lot of operational pain. Use a StatefulSet when you have a real reason to self-host.
- **Always pair with a headless Service** (`clusterIP: None`) for stable per-Pod DNS.
- **Size `volumeClaimTemplates` carefully** — they're created per replica and usually persist even after the StatefulSet is deleted (so data isn't lost by accident).
- **Pin production images and storage deliberately** — this lab uses `postgres:16` and the default StorageClass for portability, but production manifests should pin image versions/digests and choose an explicit storage class.

## Reset after Part 2

If you're moving on to Part 3 and want a clean default namespace, remove the config examples and the StatefulSet:

```bash
kubectl delete -f manifests/config-and-data/web-with-config.yaml --ignore-not-found
kubectl delete -f manifests/config-and-data/postgres-statefulset.yaml --ignore-not-found
kubectl delete -f manifests/config-and-data/data-writer.yaml --ignore-not-found
kubectl delete -f manifests/config-and-data/data-pvc.yaml --ignore-not-found
kubectl delete -f manifests/config-and-data/app-config.yaml --ignore-not-found
kubectl delete -f manifests/config-and-data/app-secret.yaml --ignore-not-found
```

StatefulSet PVCs are deliberately kept when the StatefulSet is deleted. To remove the PostgreSQL lab data too:

```bash
kubectl delete pvc pgdata-postgres-0 pgdata-postgres-1 --ignore-not-found
```

`pgdata-postgres-1` exists only if you tried the scale-to-2 exercise above.

---

[← Volumes & PersistentVolumes](volumes.md) · [↑ Contents](../../README.md) · [Health Checks →](../running-and-operating/health-checks.md)
