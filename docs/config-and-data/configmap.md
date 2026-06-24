# ConfigMap

> Keep configuration out of your image — inject it at runtime instead.

---

Your container image should be **the same everywhere** — dev, staging, prod. What changes between them is *configuration*: a log level, a feature flag, a backend URL. Baking that into the image means rebuilding for every environment. A **ConfigMap** keeps non-secret configuration *outside* the image and injects it at runtime.

> **Rule of thumb:** build the image once; configure it per environment with ConfigMaps (and [Secrets](secret.md) for sensitive values).

## Create a ConfigMap

It's just key/value data — individual values *and* whole files:

▶ **Runnable manifest:** [`manifests/config-and-data/app-config.yaml`](../../manifests/config-and-data/app-config.yaml)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_GREETING: "Hello from a ConfigMap"   # a single value
  APP_TIER: "frontend"
  app.properties: |                         # a whole file, keyed by filename
    color=blue
    log.level=info
```

```bash
kubectl apply -f manifests/config-and-data/app-config.yaml
kubectl get configmap app-config -o yaml    # inspect it
```

You can also make one straight from the CLI — handy and great with `--dry-run`:

```bash
kubectl create configmap app-config \
  --from-literal=APP_TIER=frontend \
  --from-file=app.properties \
  --dry-run=client -o yaml
```

## Consuming it

A ConfigMap does nothing until a Pod uses it — as **env vars** or **mounted files**. That's the next chapter: [Environment Variables & Mounts](env-and-mounts.md).

## Updates

How updates behave depends on how the Pod consumes the ConfigMap:

- **Environment variables are fixed at container start.** Update the ConfigMap, then restart the Pod or roll out the Deployment to pick up new env values.
- **Mounted ConfigMap files refresh automatically** after a short delay.
- **`subPath` mounts do not refresh automatically.** If you mount one ConfigMap key into one exact file path with `subPath`, restart the Pod after changes.

## Best practices

- **Only non-sensitive data** — ConfigMaps are stored and shown in plain text. Passwords/keys go in a [Secret](secret.md).
- **One ConfigMap per app/concern**, named clearly.
- **Choose env vars or files based on update behavior** — env vars are simple but need restarts; mounted files can refresh.
- **Keep ConfigMaps in Git** alongside the Deployment that uses them.

---

[← Namespace](../core-objects/namespace.md) · [↑ Contents](../../README.md) · [Secret →](secret.md)
