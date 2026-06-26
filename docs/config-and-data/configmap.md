# ConfigMap

> Keep configuration out of your image — inject it at runtime instead.

---

Your container image should be **the same everywhere** — dev, staging, prod. What changes between them is *configuration*: a log level, a feature flag, a backend URL. Baking that into the image means rebuilding for every environment. A **ConfigMap** keeps non-secret configuration *outside* the image and injects it at runtime.

> **Rule of thumb:** build the image once; configure it per environment with ConfigMaps (and [Secrets](secret.md) for sensitive values).

## Create a ConfigMap

It's just key/value data — individual values *and* multi-line content:

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

You can also build a ConfigMap straight from the CLI without writing a YAML file first:

```bash
# Step 1: create a local file whose content will become one ConfigMap key
printf 'color=blue\nlog.level=info\n' > app.properties

# Step 2: generate the ConfigMap (--dry-run=client means "don't actually create it,
#          just print the YAML so I can review or save it")
kubectl create configmap app-config \
  --from-literal=APP_TIER=frontend \
  --from-file=app.properties \
  --dry-run=client -o yaml
```

- `--from-literal=APP_TIER=frontend` — adds a single key/value pair inline, no file needed
- `--from-file=app.properties` — reads the file and stores its entire content as one key; the key name is the filename (`app.properties`), the value is the file content
- `--dry-run=client -o yaml` — prints the resulting YAML to your terminal without creating anything in the cluster; copy it into a manifest file and commit it to Git

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

**env var injection** — Kubernetes does a three-step lookup at Pod startup:

1. Open the ConfigMap named **`app-config`** (matched by `configMapKeyRef.name`)
2. Read the value of the key **`APP_GREETING`** (matched by `configMapKeyRef.key`)
3. Hand it to the container as an env var called **`APP_GREETING`** (the name in `env[].name`)

End result inside the container: `APP_GREETING=Hello from a ConfigMap`

The env var name in step 3 does not have to match the ConfigMap key in step 2 — you can rename it. For example, `env[].name: WELCOME_MSG` with `key: APP_GREETING` would expose the same value as `WELCOME_MSG` instead.

This `env` + `configMapKeyRef` approach picks keys one at a time — no matter how many keys the ConfigMap has, the container only receives the ones you explicitly list. If you want every key in the ConfigMap to become an env var without listing them individually, use `envFrom` instead:

```yaml
envFrom:
  - configMapRef:
      name: app-config   # every key in app-config becomes an env var
```

| | `env` + `configMapKeyRef` | `envFrom` + `configMapRef` |
|---|---|---|
| Keys injected | only the ones you list | all keys at once |
| Can rename the env var | yes | no |
| Safe with keys like `app.properties` | yes (you skip them) | no (invalid names are silently dropped) |

**file mount** — some apps don't read env vars; they read a config file from disk (e.g. nginx reads `/etc/nginx/nginx.conf`, a Java app reads `app.properties`). A ConfigMap is a Kubernetes object stored in the cluster, not a file itself — but when you mount it, Kubernetes takes each key/value pair and generates real files inside the container at runtime. Your app then reads those files as if they were always there.

This takes two steps that work together:

Step 1 — `volumes` gives the ConfigMap a short nickname (`config-volume`) so the container can refer to it:
```yaml
volumes:
  - name: config-volume      # nickname, used only inside this Deployment
    configMap:
      name: app-config       # the actual ConfigMap to read from
```

Step 2 — `volumeMounts` tells the container "put that volume at this path":
```yaml
volumeMounts:
  - name: config-volume      # same nickname as above
    mountPath: /etc/app      # where it appears inside the container
    readOnly: true
```

End result: every key becomes a file at that path, and the file's content is the key's value.

| ConfigMap key | File path | File content |
|---|---|---|
| `APP_GREETING` | `/etc/app/APP_GREETING` | `Hello from a ConfigMap` |
| `APP_TIER` | `/etc/app/APP_TIER` | `frontend` |
| `app.properties` | `/etc/app/app.properties` | `color=blue`<br>`log.level=info` |

This is why the key is named `app.properties` — the file at `/etc/app/app.properties` contains exactly the lines you wrote under that key, and your app reads it like any other config file on disk.

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

Verify it in the capstone namespace (only if you have already deployed the capstone app):

```bash
kubectl exec deploy/todo-backend -n demo -- printenv APP_NAME APP_VERSION DATABASE_PATH
```

The full chapter on all injection options (including `envFrom` to pull in every key at once) is [Environment Variables & Mounts](env-and-mounts.md).

## Updates

How updates behave depends on how the Pod consumes the ConfigMap:

**Environment variables are frozen at container start.**
Kubernetes reads env vars once when the container starts and never checks again. If you update the ConfigMap, the running container still sees the old values. To pick up the new values, you need to recreate the container:

```bash
kubectl rollout restart deployment/web-config
```

**Mounted ConfigMap files refresh automatically.**
The kubelet periodically syncs mounted ConfigMap content (roughly every 1 minute by default). After you update the ConfigMap, the files inside the container update on their own — no restart needed. You can watch it happen:

```bash
# update the ConfigMap
kubectl patch configmap app-config --type merge \
  -p '{"data":{"app.properties":"color=green\nlog.level=debug\n"}}'

# wait ~60 seconds, then check the file inside the container
kubectl exec deploy/web-config -- cat /etc/app/app.properties
```

**`subPath` mounts are the exception — they do not refresh.**
Normally a volume mount exposes the entire ConfigMap as a directory. `subPath` lets you mount a single key to a specific file path (e.g. mount only `app.properties` directly to `/etc/app.properties` instead of `/etc/app/app.properties`). The trade-off is that `subPath` mounts bypass the auto-refresh mechanism, so you must restart the Pod after changes.

**`immutable: true` locks the ConfigMap permanently.**
Once set, the ConfigMap cannot be edited — any `kubectl apply` or `kubectl patch` on its `data` will be rejected. This protects against accidental changes and also improves cluster performance (the kubelet stops watching it for changes). To roll out new config, create a new ConfigMap with a different name and update the Deployment to reference it.

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
