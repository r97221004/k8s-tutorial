# Kustomize (intro)

> Layer environment-specific patches over a common base — no templating language required.

---

Kustomize solves the same "almost-identical manifests per environment" problem as [Helm](helm.md), but with a different philosophy: **no templating language**. You keep plain YAML as a **base**, then layer environment-specific **patches** (overlays) on top. It's built into `kubectl` (`-k`), so there's nothing extra to install.

## Base + overlays

```
manifests/packaging/kustomize/
├── base/
│   ├── deployment.yaml         # plain, valid YAML (1 replica)
│   └── kustomization.yaml      # lists the resources
└── overlays/
    └── prod/
        └── kustomization.yaml  # references ../../base, patches it (3 replicas, prod- prefix)
```

The prod overlay just records the *differences*:

▶ **Runnable example:** [`manifests/packaging/kustomize/`](../../manifests/packaging/kustomize/)

```yaml
# overlays/prod/kustomization.yaml
resources:
  - ../../base
namePrefix: prod-        # web → prod-web
patches:
  - target: { kind: Deployment, name: web }
    patch: |
      - op: replace
        path: /spec/replicas
        value: 3          # prod overrides the base's 1
```

## See it render

`kustomize build` (or `kubectl kustomize`) prints the final YAML — diff base vs overlay:

```bash
kubectl kustomize manifests/packaging/kustomize/base            # replicas: 1, name: web
kubectl kustomize manifests/packaging/kustomize/overlays/prod   # replicas: 3, name: prod-web

# apply an overlay directly with -k:
kubectl apply -k manifests/packaging/kustomize/overlays/prod
```

The base never changes; each environment is a thin overlay of differences. Common overlay moves: `namePrefix`/`nameSuffix`, `namespace`, `commonLabels`, `images:` (swap tags), `configMapGenerator`, and strategic/JSON patches.

Clean up the overlay when you're done:

```bash
kubectl delete -k manifests/packaging/kustomize/overlays/prod
```

## Kustomize vs Helm

| | Kustomize | Helm |
|---|---|---|
| Mechanism | overlay/patch plain YAML | template + values |
| Extra tooling | none (built into kubectl) | install Helm |
| Best for | *your* manifests, env variations | packaging/distributing, third-party apps |
| Learning curve | low | higher (templating, chart structure) |

They're not mutually exclusive — teams often template third-party apps with Helm and manage their own manifests with Kustomize.

## Best practices

- **Keep the base environment-agnostic**; put every environment difference in an overlay.
- **Review `kubectl kustomize` output** before applying — see exactly what will be created.
- **Prefer Kustomize for your own manifests** when differences are small; reach for [Helm](helm.md) when you need real packaging/distribution.

---

[← Helm (intro)](helm.md) · [↑ Contents](../../README.md) · [Deploy a Two-Tier App →](../capstone/two-tier-app.md)
