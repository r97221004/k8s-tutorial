# Labels & Selectors

> Key/value tags on objects, and the queries that wire objects together — the glue of Kubernetes.

---

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

…it continuously matches **any** Pod labelled `app: web` — no list, no IDs. Create a new such Pod and it's instantly part of the Service; delete one and it drops out. The same mechanism is how a Deployment knows which Pods it owns (and why its `selector` must equal the Pod template's labels — the [gotcha from the Deployment chapter](deployment.md)).

```
Service (selector app=web)  ──matches──▶  every Pod labelled app=web
```

> **Why this matters:** scaling, rolling updates, and self-healing all work *because* relationships are recomputed from labels every moment — not frozen at creation.

## Labels vs annotations

Both are key/value metadata, but:

- **Labels** are for **identifying and selecting** — small, queryable, used by selectors.
- **Annotations** are for **non-identifying info** — arbitrary, often larger (build SHAs, tooling config, descriptions). You **can't** select on annotations.

Rule of thumb: if something needs to *find* the object, it's a label; if it's just attached data, it's an annotation.

## Best practices

- **Adopt a consistent label scheme.** Kubernetes recommends `app.kubernetes.io/name`, `app.kubernetes.io/instance`, `app.kubernetes.io/component`, etc. — predictable labels make selectors and tooling sane.
- **Keep selector labels stable** — a Service/Deployment `selector` is hard or impossible to change later.
- **Don't put volatile data in labels** (timestamps, hashes that change) — use annotations.

---

[← Namespace](namespace.md) · [↑ Contents](../../README.md) · [ConfigMap →](../config-and-data/configmap.md)
