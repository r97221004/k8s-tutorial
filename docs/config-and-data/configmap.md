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
  APP_GREETING: "Hello from a ConfigMap"
  APP_TIER: "frontend"
  app.properties: |
    color=blue
    log.level=info
```

**`metadata.name`** — the identifier Pods use when they reference this ConfigMap.

**`data`** — ConfigMap uses `data` instead of `spec` because it holds pure data, not a description of workload behavior. Every entry is a key/value pair you define yourself. There are two kinds:

- **Short string keys** (`APP_GREETING`, `APP_TIER`) — a one-liner value. These are designed to be injected as environment variables. The key name becomes the env var name, which is why `UPPER_SNAKE_CASE` is the convention.
- **File-content keys** (`app.properties`) — the `|` after the colon is YAML's block-scalar syntax, meaning "treat everything indented below as a single multi-line string and preserve the newlines exactly." The key name becomes the filename when the entry is mounted into a container as a file.

```bash
kubectl apply -f manifests/config-and-data/app-config.yaml
kubectl get configmap app-config -o yaml    # inspect it
kubectl get configmap app-config -o jsonpath='{.data.APP_GREETING}'
```

You can also make one straight from the CLI. The `--dry-run=client -o yaml` flag prints the YAML without actually creating anything — useful for previewing or pasting into a manifest file:

```bash
printf 'color=blue\nlog.level=info\n' > app.properties
kubectl create configmap app-config \
  --from-literal=APP_TIER=frontend \
  --from-file=app.properties \
  --dry-run=client -o yaml
```

## Consuming it

A ConfigMap does nothing until a Pod uses it. Here is a complete Deployment that reads `app-config` both ways — as env vars and as a file on disk:

▶ **Runnable manifest:** [`manifests/config-and-data/web-configmap.yaml`](../../manifests/config-and-data/web-configmap.yaml)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-config
  labels:
    app: web-config
spec:
  replicas: 1
  selector:
    matchLabels:
      app: web-config
  template:
    metadata:
      labels:
        app: web-config
    spec:
      containers:
        - name: web
          image: nginx:1.27
          env:
            - name: APP_GREETING
              valueFrom:
                configMapKeyRef:
                  name: app-config
                  key: APP_GREETING
          volumeMounts:
            - name: config-volume
              mountPath: /etc/app
              readOnly: true
      volumes:
        - name: config-volume
          configMap:
            name: app-config
```

There are three connection points to notice:

**env var injection** — `configMapKeyRef.name` points at the ConfigMap (`app-config`), and `configMapKeyRef.key` picks the exact key (`APP_GREETING`). The container sees it as the env var named in `env[].name`.

**volume declaration** — `volumes` is a sibling of `containers` under `spec` (not nested inside it). You give the volume a local name (`config-volume`) and tell it to source its content from the `app-config` ConfigMap.

**volume mount** — `volumeMounts` is inside the container and references the volume by that same local name. Every key in the ConfigMap becomes a file at `mountPath`, so `app.properties` appears at `/etc/app/app.properties`.

Keys used as environment variables must be valid env var names (`APP_GREETING` works; `app.properties` does not — the dot is illegal). Keys mounted as files become filenames, which is why `app.properties` is better suited for file mounts.

If you later use `envFrom` to pull every key into environment variables, invalid env var names are skipped. In this example, `app.properties` mounts cleanly as a file but cannot become an environment variable.

> **Watch out:** if the ConfigMap does not exist when the Pod starts, the container will not start successfully. Check `kubectl describe pod` Events for the missing ConfigMap message, then apply the ConfigMap before recreating or restarting the Pod.

Apply and verify both injection methods work:

```bash
kubectl apply -f manifests/config-and-data/app-config.yaml
kubectl apply -f manifests/config-and-data/web-configmap.yaml

kubectl rollout status deployment/web-config
kubectl exec deploy/web-config -- printenv APP_GREETING
kubectl exec deploy/web-config -- cat /etc/app/app.properties
```

## Real backend example

A backend service usually consumes several scalar settings at once: app name, version, database path, feature flags, upstream URLs. In the capstone app, the backend ConfigMap looks like this:

▶ **Runnable manifest:** [`manifests/capstone/backend-config.yaml`](../../manifests/capstone/backend-config.yaml)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: todo-backend-config
data:
  APP_NAME: "Todo Board API"
  APP_VERSION: "0.1.0"
  DATABASE_PATH: "/data/todo.db"
```

The backend Deployment injects the whole ConfigMap with `envFrom`:

```yaml
containers:
  - name: backend
    image: todo-backend:0.1.0
    envFrom:
      - configMapRef:
          name: todo-backend-config
```

That gives the container `APP_NAME`, `APP_VERSION`, and `DATABASE_PATH` environment variables. The app code reads those variables at startup, so the same backend image can run with different config in dev, staging, and prod.

Verify it in the capstone namespace:

```bash
kubectl exec deploy/todo-backend -n demo -- printenv APP_NAME APP_VERSION DATABASE_PATH
```

The full chapter on all injection options (including `envFrom` to pull in every key at once) is [Environment Variables & Mounts](env-and-mounts.md).

## Updates

How updates behave depends on how the Pod consumes the ConfigMap:

- **Environment variables are fixed at container start.** Update the ConfigMap, then restart the Pod or roll out the Deployment to pick up new env values.
- **Mounted ConfigMap files refresh automatically** after a short delay.
- **`subPath` mounts do not refresh automatically.** If you mount one ConfigMap key into one exact file path with `subPath`, restart the Pod after changes.
- **`immutable: true` locks a ConfigMap after creation.** Use it for config you never want changed in place; create a new ConfigMap name when you need a new version.

Try changing both values:

```bash
kubectl patch configmap app-config --type merge \
  -p '{"data":{"APP_GREETING":"Hello after an update","app.properties":"color=green\nlog.level=debug\n"}}'

# Mounted files refresh on their own after a short delay.
sleep 30
kubectl exec deploy/web-config -- cat /etc/app/app.properties

# Env vars are still frozen in the running container.
kubectl exec deploy/web-config -- printenv APP_GREETING

# Restart the Deployment to pick up the new env var value.
kubectl rollout restart deployment/web-config
kubectl rollout status deployment/web-config

kubectl exec deploy/web-config -- printenv APP_GREETING
```

## Best practices

- **Only non-sensitive data** — ConfigMaps are stored and shown in plain text. Passwords/keys go in a [Secret](secret.md).
- **One ConfigMap per app/concern**, named clearly.
- **Choose env vars or files based on update behavior** — env vars are simple but need restarts; mounted files can refresh.
- **Use `immutable: true` for fixed config** so accidental edits fail fast.
- **Keep ConfigMaps in Git** alongside the Deployment that uses them.

---

[← Namespace](../core-objects/namespace.md) · [↑ Contents](../../README.md) · [Secret →](secret.md)
