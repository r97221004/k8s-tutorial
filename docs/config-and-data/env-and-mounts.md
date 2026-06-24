# Environment Variables & Mounts

> The two ways config reaches your container: as environment variables, or as files on disk.

---

A [ConfigMap](configmap.md) or [Secret](secret.md) just *holds* data — a Pod has to pull it in. There are two ways, and one manifest below shows all of them.

▶ **Runnable manifest:** [`manifests/config-and-data/web-with-config.yaml`](../../manifests/config-and-data/web-with-config.yaml) (needs `app-config` and `app-secret` applied first)

## 1. As environment variables

Pick **individual keys** with `valueFrom`:

```yaml
env:
  - name: APP_GREETING
    valueFrom:
      configMapKeyRef:        # one key from a ConfigMap
        name: app-config
        key: APP_GREETING
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:           # one key from a Secret
        name: app-secret
        key: DB_PASSWORD
```

…or pull in **every key at once** with `envFrom`:

```yaml
envFrom:
  - configMapRef:
      name: app-config        # each key becomes an env var
```

`web-with-config.yaml` actually uses both at once: an explicit `env` entry for `APP_GREETING`, *and* `envFrom` pulling in the whole `app-config` (which also contains an `APP_GREETING` key). When the same name comes from both, the explicit `env` entry wins — `envFrom` never overwrites a name already set in `env`.

`envFrom` also skips any key that isn't a valid environment variable name. `app-config` has a key `app.properties` (the dot isn't legal in an env var name), so it's silently dropped from the env vars — you'll see an `InvalidVariableNames` warning in `kubectl describe pod` Events, which is expected, not a misconfiguration.

## 2. As files on disk

Mount the whole ConfigMap/Secret as a directory — each key becomes a file:

```yaml
volumeMounts:
  - name: config-volume
    mountPath: /etc/app       # app.properties shows up at /etc/app/app.properties
    readOnly: true
  - name: secret-volume
    mountPath: /etc/app-secret # DB_PASSWORD shows up at /etc/app-secret/DB_PASSWORD
    readOnly: true
volumes:
  - name: config-volume
    configMap:
      name: app-config
  - name: secret-volume
    secret:
      secretName: app-secret
```

Apply and verify both paths land inside the container:

```bash
kubectl apply -f manifests/config-and-data/app-config.yaml
kubectl apply -f manifests/config-and-data/app-secret.yaml
kubectl apply -f manifests/config-and-data/web-with-config.yaml

kubectl exec deploy/web-config -- printenv APP_GREETING DB_PASSWORD
kubectl exec deploy/web-config -- cat /etc/app/app.properties
kubectl exec deploy/web-config -- cat /etc/app-secret/DB_PASSWORD
```

Printing `DB_PASSWORD` is only a lab verification step. In real clusters, avoid echoing secret values into terminals, screenshots, or logs.

(In [k9s](../getting-started/k9s.md), press `s` on the Pod for a shell and poke around `/etc/app`.)

## env vars vs files — which to use

| | Environment variables | Mounted files |
|---|---|---|
| Updates without restart | ❌ frozen at start | ✅ files refresh automatically (except `subPath` mounts — those don't refresh) |
| Good for | small scalar config | whole config files, certs, large values |
| Sensitive data | riskier (leaks via dumps/child procs) | safer (esp. Secrets as `tmpfs`) |

## Best practices

- **Reference keys explicitly** for the values your app needs; use `envFrom` only when you really want the whole map.
- **Mount sensitive data as files**, not env vars, where you can.
- **Mount config files** (rather than env) when you want live updates without recreating Pods.
- **Mark config mounts `readOnly: true`.**

---

[← Secret](secret.md) · [↑ Contents](../../README.md) · [Volumes & PersistentVolumes →](volumes.md)
