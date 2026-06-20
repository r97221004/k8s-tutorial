# Deploy a Two-Tier App

> Put it all together: a web front end + a database back end, configured, persisted, and exposed.

---

Time to assemble everything into one realistic app: a **web front end** talking to a **PostgreSQL database**, configured with a [ConfigMap](../config-and-data/configmap.md) and [Secret](../config-and-data/secret.md), persisted on a [PVC](../config-and-data/volumes.md), discovered by [DNS](../networking/dns.md), and exposed through an [Ingress](../networking/ingress.md). Then we'll do a [rolling update](../running-and-operating/rolling-updates.md) and roll it back.

▶ **Runnable manifests:** [`manifests/capstone/`](../../manifests/capstone/)

> **Prereqs:** a default StorageClass ([Volumes](../config-and-data/volumes.md)) and an ingress controller ([Ingress](../networking/ingress.md)). On k3s both exist already.

## The pieces and how they connect

```
Ingress (demo.localdev.me)
   └─▶ Service web (ClusterIP) ─▶ Deployment web (2 replicas)
                                     │ env from ConfigMap web-config (DB_HOST=db)
                                     │ env from Secret db-credentials (user/password)
                                     ▼  reaches the DB by DNS name "db"
                                  Service db (headless) ─▶ StatefulSet db ─▶ PVC (Postgres data)
```

Every relationship you learned shows up here: labels wire Services to Pods, the web tier finds the DB via the `db` DNS name, secrets/config are injected as env, and the database's data lives on a PVC that survives restarts.

## Deploy it

Use a dedicated [namespace](../core-objects/namespace.md):

```bash
kubectl create namespace demo
kubectl apply -f manifests/capstone/ -n demo
```

Watch it come up — the database becomes ready first (its readiness probe runs `pg_isready`), then the web Pods:

```bash
kubectl get all,pvc,ingress -n demo
kubectl rollout status deployment/web -n demo
```

Or open [k9s](../getting-started/k9s.md), press `:ns` → `demo`, and watch `db-0` and the two `web-…` Pods go green.

## Verify the wiring

```bash
# Config + secret reached the web Pods:
kubectl exec deploy/web -n demo -- printenv APP_TITLE DB_HOST DB_USER

# The web tier can resolve the database by DNS:
kubectl exec deploy/web -n demo -- getent hosts db        # resolves to the db Service

# The database is actually serving:
kubectl exec db-0 -n demo -- pg_isready -U appuser -d appdb

# Reach the front end through the Ingress:
curl http://demo.localdev.me
```

## Prove the database persists

```bash
kubectl exec -it db-0 -n demo -- psql -U appuser -d appdb -c "CREATE TABLE hello(id int); INSERT INTO hello VALUES (1);"
kubectl delete pod db-0 -n demo            # StatefulSet recreates db-0, reattaching its PVC
kubectl exec -it db-0 -n demo -- psql -U appuser -d appdb -c "SELECT * FROM hello;"   # row still there
```

## Rolling update + rollback

Ship a new front-end version, watch it roll, then undo it:

```bash
kubectl set image deployment/web web=nginx:1.28 -n demo
kubectl rollout status deployment/web -n demo      # Pods replaced gradually, zero downtime
kubectl rollout history deployment/web -n demo
kubectl rollout undo deployment/web -n demo        # back to nginx:1.27 instantly
```

In k9s you'll see new Pods appear and become ready before old ones leave — the readiness probes gating the rollout.

## What you just used

Pod · Deployment · ReplicaSet · StatefulSet · Service (ClusterIP + headless) · Ingress · ConfigMap · Secret · PVC · DNS · probes · resources · rolling update + rollback — the whole guide, in one app. 🎉

Next: [tear it down cleanly](cleanup.md).

---

[← Kustomize (intro)](../packaging/kustomize.md) · [↑ Contents](../../README.md) · [Cleanup →](cleanup.md)
