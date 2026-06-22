# Labels & Selectors

> Key/value tags on objects, and the queries that wire objects together — the glue of Kubernetes.

---

You can read this chapter before creating any new objects. The next chapters use labels constantly, so this is the small idea that makes Deployments and Services feel much less mysterious.

Kubernetes has no foreign keys. A [Service](service.md) doesn't store a list of "its" Pods; a [Deployment](deployment.md) doesn't hold pointers to Pods. Instead, objects carry **labels** (key/value tags), and other objects use a **selector** to *query* for them at runtime. That loose coupling is how almost everything connects.

## Labels

Labels are arbitrary key/value tags in `metadata.labels`:

```yaml
metadata:
  labels:
    app: web
    tier: frontend
    env: prod
```

Filter by them with `-l`:

```bash
kubectl get pods -l app=web                 # equality
kubectl get pods -l 'env in (prod,staging)' # set-based
kubectl get pods -l app=web,tier=frontend   # AND (both must match)
kubectl get pods --show-labels              # see every Pod's labels
```

## Selectors wire objects together

This is the part to internalize. When a Service has:

```yaml
spec:
  selector:
    app: web
```

…it continuously matches **any** Pod labelled `app: web` — no list, no IDs. Create a new such Pod and it's instantly part of the Service; delete one and it drops out. The same mechanism is how a Deployment knows which Pods it owns: its `selector` must equal the Pod template's labels.

```
Service (selector app=web)  ──matches──▶  every Pod labelled app=web
```

> **Why this matters:** scaling, rolling updates, and self-healing all work *because* relationships are recomputed from labels every moment — not frozen at creation.

## Labels vs annotations

Both are key/value metadata, but:

- **Labels** are for **identifying and selecting** — small, queryable, used by selectors.
- **Annotations** are for **non-identifying info** — arbitrary, often larger (build SHAs, tooling config, descriptions). You **can't** select on annotations.

Rule of thumb: if something needs to *find* the object, it's a label; if it's just attached data, it's an annotation.

## The standard label scheme

This guide's examples use plain `app: web` to keep YAML short, but Kubernetes defines a [recommended set](https://kubernetes.io/docs/concepts/overview/working-with-objects/common-labels/) of `app.kubernetes.io/*` labels for anything beyond a toy example — tools like Helm rely on them:

```yaml
metadata:
  labels:
    app.kubernetes.io/name: web          # the app itself, e.g. "nginx"
    app.kubernetes.io/instance: web-prod  # this specific deployment of it
    app.kubernetes.io/component: frontend # its role within the larger app
    app.kubernetes.io/part-of: two-tier-app # the larger app it belongs to
```

A Service or Deployment `selector` can match on just one or two of these (e.g. `app.kubernetes.io/name` + `app.kubernetes.io/instance`) — it doesn't need to repeat every label.

## Best practices

- **Adopt a consistent label scheme.** Kubernetes recommends `app.kubernetes.io/name`, `app.kubernetes.io/instance`, `app.kubernetes.io/component`, etc. — predictable labels make selectors and tooling sane.
- **Keep selector labels stable** — a Service/Deployment `selector` is hard or impossible to change later.
- **Don't put volatile data in labels** (timestamps, hashes that change) — use annotations.

---

[← Pod](pod.md) · [↑ Contents](../../README.md) · [Deployment →](deployment.md)
