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

`s3cr3t-change-me` is a lab placeholder so the manifest is runnable. Do not commit real passwords, tokens, or certificates to Git.

`type: Opaque` means "generic key/value Secret," which is what most app credentials use. Kubernetes also has special Secret types for common shapes:

| Type | Use case |
|---|---|
| `Opaque` | Generic key/value — most app credentials |
| `kubernetes.io/tls` | TLS certificate + private key pair |
| `kubernetes.io/dockerconfigjson` | Private container registry credentials |
| `kubernetes.io/service-account-token` | Legacy long-lived token for a ServiceAccount |

Each special type enforces that the expected keys are present. For example, a `kubernetes.io/tls` Secret must contain `tls.crt` and `tls.key`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-tls
type: kubernetes.io/tls
data:
  tls.crt: <base64-encoded cert>
  tls.key: <base64-encoded private key>
```

In practice you generate TLS Secrets with `kubectl create secret tls` rather than writing the YAML by hand, since base64-encoding a cert manually is error-prone.

`stringData` is a write-friendly convenience field: you send plain text, and Kubernetes stores it under `.data` as base64. If you read the Secret back, you will see `.data`, not `stringData`.

```bash
kubectl apply -f manifests/config-and-data/app-secret.yaml
kubectl describe secret app-secret          # shows keys and sizes, not values
kubectl get secret app-secret -o jsonpath='{.data.DB_PASSWORD}' | base64 -d   # reads back the value
```

`describe` output looks like this — values are never shown, only key names and byte counts:

```
Name:         app-secret
Namespace:    default
Labels:       <none>
Annotations:  <none>

Type:  Opaque

Data
====
DB_PASSWORD:  16 bytes
DB_USER:      7 bytes
```

The byte count lets you confirm a key exists and roughly validate its length without exposing the value.

The decode command is only for learning. Avoid printing real secret values in shared terminals, screenshots, CI logs, or shell history.

## ⚠️ base64 is encoding, not encryption

This is the single most misunderstood thing about Secrets:

```bash
printf 's3cr3t-change-me' | base64      # czNjcjN0LWNoYW5nZS1tZQ==
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

This checks whether *you* can read Secret objects through the Kubernetes API. A normal application Pod usually should **not** need permission to `get secrets` at all. Kubernetes resolves the referenced Secret and injects it into the Pod as an environment variable or mounted file; the app reads its local env/file, not the Secret API.

You can also check the default ServiceAccount identity that a Pod would use:

```bash
kubectl auth can-i get secrets \
  --as=system:serviceaccount:default:default
```

In a normal namespace this should be `no`. If it says `yes`, something granted that ServiceAccount broader permissions than most application Pods need.

All three tools below solve the same problem: real Secret values cannot be committed to Git, but deployments need them — so where do they live?

**External Secrets** — values never touch Git; they live in an external secret manager. You commit only a declaration of *where to fetch from*, and the External Secrets Operator in the cluster reads it, fetches the value from AWS / GCP Secret Manager / Vault, and creates a real Secret object automatically.

**Sealed Secrets** — values are encrypted before being committed to Git; only the cluster can decrypt them. You encrypt locally:

```bash
kubeseal < secret.yaml > sealed-secret.yaml
```

`sealed-secret.yaml` contains ciphertext — safe to commit. The Sealed Secrets controller in the cluster holds the private key, decrypts it, and creates a real Secret object automatically. Someone who steals the Git repo gets ciphertext that is useless without the cluster's private key.

**SOPS** — values are also encrypted in Git, but decryption happens on the **CI/CD side**, not inside a cluster controller. Your pipeline (ArgoCD, Helm, etc.) holds a key stored in AWS KMS or GCP KMS, decrypts the file at deploy time, and applies it to the cluster.

| | Values stored | Who decrypts | Best fit |
|---|---|---|---|
| External Secrets | External service (AWS / GCP / Vault) | Cluster operator | Already have a secret manager |
| Sealed Secrets | Git (ciphertext) | Cluster controller | Want Git as the single source of truth |
| SOPS | Git (ciphertext) | CI/CD tooling | Deploying with Helm or ArgoCD |

## Consuming it

Same as a ConfigMap — as env vars or mounted files. Here is where each piece fits inside a Deployment:

```yaml
spec:
  template:
    spec:
      containers:
        - name: app
          image: my-app:1.0
          env:
            - name: DB_PASSWORD        # env var name inside the container
              valueFrom:
                secretKeyRef:
                  name: app-secret     # Secret name
                  key: DB_PASSWORD     # key inside the Secret
          volumeMounts:
            - name: secret-volume
              mountPath: /etc/secrets  # directory inside the container
              readOnly: true
      volumes:
        - name: secret-volume
          secret:
            secretName: app-secret
```

`env` + `secretKeyRef` injects one key at a time as an environment variable. `volumes` + `volumeMounts` mounts every key as a file under `/etc/secrets/` — for example, `/etc/secrets/DB_PASSWORD` contains the raw value.

The full runnable example is in [Environment Variables & Mounts](env-and-mounts.md).

**Prefer file mounts over env vars for sensitive values.** Environment variables are accessible to every process in the container, are inherited by all child processes, and can appear in crash dumps, debug output, or process inspection (`/proc/<pid>/environ`). A mounted Secret file is only read by the code that explicitly opens it — nothing else sees it automatically.

Secret update behavior matches ConfigMaps: env vars are frozen until restart, mounted Secret files refresh after a short delay, and `subPath` mounts do not refresh automatically.

## Rotation

Credentials should be rotated periodically. How you rotate depends on whether the Secret is mutable or immutable.

**Mutable Secret (default)** — edit the value in place, then restart Pods to pick it up:

```bash
kubectl patch secret app-secret --type merge \
  -p '{"stringData":{"DB_PASSWORD":"new-password-here"}}'

kubectl rollout restart deployment/<your-deployment>
```

Mounted Secret files refresh automatically within ~60 seconds even without a restart. Env-var consumers need the restart.

**`immutable: true`** — once set, the Secret cannot be edited; any patch on `.data` is rejected. This does not make the credential harder to read; RBAC and encryption at rest still do that. What it gives you is operational safety: the value cannot drift unexpectedly, and rotation becomes an explicit "create a new version, then update consumers" workflow. To rotate, create a new Secret under a versioned name and point the Deployment at it:

Step 1 — create the new version:

```bash
kubectl create secret generic db-creds-v2 \
  --from-literal=DB_USER=appuser \
  --from-literal=DB_PASSWORD=new-password-here
```

Step 2 — update the Deployment manifest to reference `db-creds-v2`:

```yaml
env:
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: db-creds-v2   # ← changed from db-creds-v1
        key: DB_PASSWORD
volumes:
  - name: secret-volume
    secret:
      secretName: db-creds-v2   # ← changed from db-creds-v1
```

Step 3 — apply your updated Deployment manifest and verify:

```bash
kubectl apply -f manifests/<your-deployment>.yaml
kubectl rollout status deployment/<your-deployment>
```

The old `db-creds-v1` stays untouched — rolling back is just switching the Deployment back to it.

## Hands-on

Work through these steps to experience the full Secret lifecycle:

**1. Apply the Secret and inspect it:**

```bash
kubectl apply -f manifests/config-and-data/app-secret.yaml
kubectl describe secret app-secret       # keys and sizes — no values shown
kubectl get secret app-secret -o yaml    # base64-encoded values in .data
```

**2. Decode a value and confirm base64 is not encryption:**

```bash
kubectl get secret app-secret -o jsonpath='{.data.DB_PASSWORD}' | base64 -d
```

**3. Check your own permission to read Secrets:**

```bash
kubectl auth can-i get secret app-secret
```

**4. Simulate rotation — patch the password and observe:**

```bash
kubectl patch secret app-secret --type merge \
  -p '{"stringData":{"DB_PASSWORD":"rotated-password"}}'

kubectl get secret app-secret -o jsonpath='{.data.DB_PASSWORD}' | base64 -d
```

**5. Lock the Secret and confirm edits are rejected:**

```bash
kubectl patch secret app-secret --type merge -p '{"immutable": true}'

kubectl patch secret app-secret --type merge \
  -p '{"stringData":{"DB_PASSWORD":"another-change"}}'
# Error: the Secret "app-secret" is invalid:
#   data: Forbidden: field is immutable when `immutable` is set
```

After this step, `app-secret` cannot be patched anymore. Delete and re-apply it before continuing to later chapters that expect the original mutable lab Secret.

**6. Clean up:**

```bash
kubectl delete secret app-secret
```

## Best practices

- **RBAC-restrict Secret access** and **enable encryption at rest**.
- **Prefer file mounts over env vars** for the most sensitive values.
- **Use `describe` for routine checks** so you can confirm keys exist without printing values.
- **Never bake secrets into images or commit them to Git** — keep real values out of version control.
- **Rotate** secrets periodically; use versioned names (`db-creds-v2`) with `immutable: true` for auditability, or patch in place for simpler setups.

---

[← ConfigMap](configmap.md) · [↑ Contents](../../README.md) · [Environment Variables & Mounts →](env-and-mounts.md)
