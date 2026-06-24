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
kubectl get configmap app-config -o jsonpath='{.data.APP_GREETING}'
```

You can also make one straight from the CLI — handy and great with `--dry-run`:

```bash
printf 'color=blue\nlog.level=info\n' > app.properties
kubectl create configmap app-config \
  --from-literal=APP_TIER=frontend \
  --from-file=app.properties \
  --dry-run=client -o yaml
```

## Consuming it

A ConfigMap does nothing until a Pod uses it — as **env vars** or **mounted files**:

```yaml
env:
  - name: APP_GREETING
    valueFrom:
      configMapKeyRef:
        name: app-config
        key: APP_GREETING
volumes:
  - name: config-volume
    configMap:
      name: app-config
```

The full runnable example is in the next chapter: [Environment Variables & Mounts](env-and-mounts.md).

Keys used as environment variables should look like valid env var names (`APP_GREETING`, not `app.properties`). Keys mounted as files become filenames, which is why `app.properties` works well as a mounted config file.

## Updates

How updates behave depends on how the Pod consumes the ConfigMap:

- **Environment variables are fixed at container start.** Update the ConfigMap, then restart the Pod or roll out the Deployment to pick up new env values.
- **Mounted ConfigMap files refresh automatically** after a short delay.
- **`subPath` mounts do not refresh automatically.** If you mount one ConfigMap key into one exact file path with `subPath`, restart the Pod after changes.
- **`immutable: true` locks a ConfigMap after creation.** Use it for config you never want changed in place; create a new ConfigMap name when you need a new version.

## Best practices

- **Only non-sensitive data** — ConfigMaps are stored and shown in plain text. Passwords/keys go in a [Secret](secret.md).
- **One ConfigMap per app/concern**, named clearly.
- **Choose env vars or files based on update behavior** — env vars are simple but need restarts; mounted files can refresh.
- **Use `immutable: true` for fixed config** so accidental edits fail fast.
- **Keep ConfigMaps in Git** alongside the Deployment that uses them.

---

[← Namespace](../core-objects/namespace.md) · [↑ Contents](../../README.md) · [Secret →](secret.md)
