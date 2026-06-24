# Secret

> Like a ConfigMap, but for sensitive values — handled more carefully by the cluster.

---

A **Secret** is structurally almost identical to a [ConfigMap](configmap.md) — key/value data injected into Pods — but it's meant for **sensitive** values: passwords, API keys, TLS certs. Kubernetes treats Secrets a little more carefully (kept out of some logs, mountable as in-memory `tmpfs`), and you should treat them *much* more carefully.

## Create a Secret

Use `stringData` so you can write plain text; Kubernetes base64-encodes it for storage:

▶ **Runnable manifest:** [`manifests/config-and-data/app-secret.yaml`](../../manifests/config-and-data/app-secret.yaml)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secret
type: Opaque
stringData:
  DB_USER: appuser
  DB_PASSWORD: s3cr3t-change-me
```

`type: Opaque` means "generic key/value Secret," which is what most app credentials use. Kubernetes also has special Secret types for common shapes, such as `kubernetes.io/tls` for TLS certificates and `kubernetes.io/dockerconfigjson` for private registry credentials.

`stringData` is a write-friendly convenience field: you send plain text, and Kubernetes stores it under `.data` as base64. If you read the Secret back, you will see `.data`, not `stringData`.

```bash
kubectl apply -f manifests/config-and-data/app-secret.yaml
kubectl describe secret app-secret          # shows keys and sizes, not values
kubectl get secret app-secret -o jsonpath='{.data.DB_PASSWORD}' | base64 -d   # reads back the value
```

The decode command is only for learning. Avoid printing real secret values in shared terminals, screenshots, CI logs, or shell history.

## ⚠️ base64 is encoding, not encryption

This is the single most misunderstood thing about Secrets:

```bash
echo 's3cr3t-change-me' | base64        # czNjcjN0LWNoYW5nZS1tZQ==
echo 'czNjcjN0LWNoYW5nZS1tZQ==' | base64 -d   # s3cr3t-change-me  ← trivially reversed
```

Base64 is just an encoding so binary data fits in YAML — **anyone who can read the Secret object can read the value**. A Secret is "secret" only because of *who is allowed to read it*, not because it's scrambled.

To make Secrets genuinely safe:

- **RBAC** — restrict who/what can `get` Secrets (most important).
- **Encryption at rest** — enable etcd encryption so the value isn't plaintext on disk.
- **Don't commit real secrets to Git.** Commit the *Deployment* that references a Secret, but inject the actual values via a sealed-secrets / external-secrets tool or your CI — never the raw `Secret` YAML with live credentials.

Quick permission check:

```bash
kubectl auth can-i get secrets
kubectl auth can-i get secret app-secret
```

Common Git-safe flows: **External Secrets** syncs from a secret manager, **Sealed Secrets** stores encrypted Secret YAML that only the cluster can decrypt, and **SOPS** encrypts values in Git for your deployment tooling to decrypt.

## Consuming it

Same as a ConfigMap — as env vars or mounted files:

```yaml
env:
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: app-secret
        key: DB_PASSWORD
volumes:
  - name: secret-volume
    secret:
      secretName: app-secret
```

The full runnable example is in [Environment Variables & Mounts](env-and-mounts.md). Mounting as files is slightly safer than env vars (env can leak via crash dumps / child processes).

Secret update behavior matches ConfigMaps: env vars are frozen until restart, mounted Secret files refresh after a short delay, and `subPath` mounts do not refresh automatically.

`immutable: true` also works on Secrets. Use it for credentials that should never be changed in place; create a new Secret name when rotating.

## Best practices

- **RBAC-restrict Secret access** and **enable encryption at rest**.
- **Prefer file mounts over env vars** for the most sensitive values.
- **Use `describe` for routine checks** so you can confirm keys exist without printing values.
- **Never bake secrets into images or commit them to Git** — keep real values out of version control.
- **Rotate** secrets periodically; with Secrets mounted as files, updates propagate without rebuilding the Pod.

---

[← ConfigMap](configmap.md) · [↑ Contents](../../README.md) · [Environment Variables & Mounts →](env-and-mounts.md)
