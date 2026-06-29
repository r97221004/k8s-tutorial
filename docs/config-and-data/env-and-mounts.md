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
  - configMapRef:
      name: other-config
      prefix: OTHER_          # avoids name collisions across maps
```

Both `configMapKeyRef` and `secretKeyRef` accept `optional: true` — Kubernetes can still start the container even if the referenced ConfigMap, Secret, or key is missing. Without it, the Pod object can be created, but the container will not start successfully until the reference exists. Useful for optional feature flags or config that may not be present in all environments:

```yaml
env:
  - name: FEATURE_FLAG
    valueFrom:
      configMapKeyRef:
        name: optional-config
        key: FEATURE_FLAG
        optional: true      # container starts even if optional-config doesn't exist
```

`web-with-config.yaml` actually uses both at once: an explicit `env` entry for `APP_GREETING`, *and* `envFrom` pulling in the whole `app-config` (which also contains an `APP_GREETING` key). When the same name comes from both, the explicit `env` entry wins — `envFrom` never overwrites a name already set in `env`.

`envFrom` also skips any key that isn't a valid environment variable name. `app-config` has a key `app.properties` (the dot isn't legal in an env var name), so it's silently dropped from the env vars — you'll see an `InvalidVariableNames` warning in `kubectl describe pod` Events. The Pod still starts; Kubernetes is only warning that this one key could not become an env var.

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

When the ConfigMap or Secret changes, the kubelet refreshes the mounted files automatically — no Pod restart needed. The update is not instant; it can take roughly the kubelet sync period plus cache delay. **Exception: `subPath` mounts** are frozen at Pod start and never live-update. `subPath` lets you drop a single key into an existing directory without replacing the whole directory:

```yaml
volumeMounts:
  - name: config-volume
    mountPath: /etc/nginx/nginx.conf
    subPath: nginx.conf    # mounts only this key; live-update does NOT apply
```

**Mounting only specific keys** — use `items` to select which keys appear as files and rename them:

```yaml
volumes:
  - name: config-volume
    configMap:
      name: app-config
      items:
        - key: app.properties
          path: config.properties   # filename inside the mounted directory
```

`path` is relative to the volume's `mountPath`. With `mountPath: /etc/app`, the key `app.properties` appears at `/etc/app/config.properties` — both selecting the key and renaming it. Any key not listed in `items` is excluded from the mount entirely.

**File permissions** — use `defaultMode` (octal) to restrict access. Useful for TLS private keys or SSH keys that must not be world-readable:

```yaml
volumes:
  - name: secret-volume
    secret:
      secretName: app-secret
      defaultMode: 0400   # owner read-only
```

If your container runs as a non-root user, test this carefully: a strict mode like `0400` can make the file unreadable unless the file ownership/group settings match your `securityContext`.

**Merging multiple sources into one directory** — two separate `volumeMounts` targeting the same `mountPath` conflict: the second mount replaces the first entirely. Use a `projected` volume to combine ConfigMaps and Secrets into a single directory:

```yaml
volumes:
  - name: combined
    projected:
      sources:
        - configMap:
            name: app-config
        - secret:
            name: app-secret
            items:
              - key: DB_PASSWORD
                path: db-password
                mode: 0400
volumeMounts:
  - name: combined
    mountPath: /etc/app
    readOnly: true
```

Every key from `app-config` and the selected key from `app-secret` all land in `/etc/app` as siblings. `projected` volumes also support `serviceAccountToken` and `downwardAPI` sources, making them the standard way to assemble mixed-source config directories.

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

In [k9s](../getting-started/k9s.md), inspect the same Deployment from a few angles:

1. Type `:pods`, press `/`, and filter for `web-config`.
2. Highlight the Pod and press `d` to describe it. The Events section shows warnings like `InvalidVariableNames` from `envFrom`, plus missing ConfigMap/Secret errors if a reference is wrong.
3. Press `s` to open a shell, then run:

   ```bash
   printenv APP_GREETING DB_PASSWORD
   cat /etc/app/app.properties
   cat /etc/app-secret/DB_PASSWORD   # lab only: avoid printing real secrets
   ```

4. Type `:configmaps`, highlight `app-config`, and press `d` to confirm the keys exist. Press `y` if you want to inspect the YAML.
5. Type `:secrets`, highlight `app-secret`, and press `d` to confirm the Secret keys exist. k9s shows key names and sizes, not the raw values.

To watch ConfigMap file updates in k9s:

1. Keep `:pods` filtered to `web-config`.
2. Patch the ConfigMap from another terminal:

   ```bash
   kubectl patch configmap app-config --type merge \
     -p '{"data":{"APP_GREETING":"Hello after update","app.properties":"color=green\nlog.level=debug\n"}}'
   ```

3. Press `s` on the existing Pod and run `cat /etc/app/app.properties` again. The mounted file refreshes inside the same Pod after the kubelet syncs the volume.
4. Check `printenv APP_GREETING` in that same shell: the env var is still the old value.

To watch Secret/env-var restart behavior in k9s:

1. Patch the Secret from another terminal:

   ```bash
   kubectl patch secret app-secret --type merge \
     -p '{"stringData":{"DB_PASSWORD":"changed-for-restart-demo"}}'
   ```

2. Type `:secrets`, describe `app-secret`, and notice `DB_PASSWORD` has a new byte count.
3. Go back to `:pods` and press `s` on the existing Pod. The mounted Secret file refreshes after the kubelet syncs the volume; checking `/etc/app-secret/DB_PASSWORD` is a lab-only verification step.
4. Check `printenv DB_PASSWORD` in that same shell: the env var is still the old value.
5. Restart the Deployment so env vars are re-read. In k9s, type `:deployments`, highlight `web-config`, and press `Ctrl-R`. For a quick lab-only replacement, go back to `:pods`, highlight the `web-config-...` Pod, and press `Ctrl-D`.

## env vars vs files — which to use

| | Environment variables | Mounted files |
|---|---|---|
| Updates without restart | ❌ frozen at start | ✅ files refresh automatically (except `subPath` mounts — see above) |
| Good for | small scalar config | whole config files, certs, large values |
| Typical consumer | apps that read settings at startup | apps that read files, cert libraries, reloadable config |
| Sensitive data | riskier (leaks via dumps/child procs) | safer (esp. Secrets as `tmpfs`) |

## Best practices

- **Reference keys explicitly** for the values your app needs; `envFrom` is convenient but imports everything, making dependencies invisible and causing surprises when keys are added or removed.
- **Mount sensitive data as files, not env vars** — environment variables are inherited by child processes and can leak through crash dumps, debug output, or `/proc/<pid>/environ`; mounted Secret files (backed by `tmpfs`) are only read by code that opens the file.
- **Mount config files when you need live updates** — env vars are frozen at Pod start; mounted files refresh automatically when the ConfigMap or Secret changes (no restart needed).
- **Mark all config mounts `readOnly: true`** — a container that can write to its own config volume is a misconfiguration waiting to cause confusion.
- **Set restrictive file modes** on Secret volumes that hold private keys or certs — `defaultMode: 0400` is a good target when the container user can read it; otherwise adjust ownership/group access with your `securityContext`.

---

[← Secret](secret.md) · [↑ Contents](../../README.md) · [Volumes & PersistentVolumes →](volumes.md)
