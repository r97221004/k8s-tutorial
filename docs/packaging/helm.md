# Helm (intro)

> The package manager for Kubernetes — template your manifests and install them as one versioned unit.

---

By now you have a pile of manifests — Deployment, Service, ConfigMap, Ingress — and for dev/staging/prod they're *almost* identical, differing by a replica count or an image tag. Copy-pasting and hand-editing that per environment is how mistakes happen. **Helm** is the package manager for Kubernetes: it **templates** your manifests and installs them as one versioned, upgradeable unit.

> This is an intro — enough to recognize Helm and use existing charts. Authoring production charts is a topic of its own.

## The vocabulary

- **Chart** — a package of templated manifests + default values (a folder, or a `.tgz`).
- **Values** — the knobs (`values.yaml`, or `--set`/`-f` overrides) injected into the templates.
- **Template** — a manifest with placeholders, e.g. `replicas: {{ .Values.replicaCount }}`.
- **Release** — one *installation* of a chart into a cluster, with a name and a revision history.

One chart, many releases with different values = the same app across every environment, without copy-paste.

## Using a chart

The most common day-one use is installing someone else's chart:

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install my-nginx bitnami/nginx --version 25.0.10 --set replicaCount=3
helm list                              # your releases
helm upgrade my-nginx bitnami/nginx --version 25.0.10 --set replicaCount=5   # change values, new revision
helm rollback my-nginx 1               # back to revision 1 — instantly
helm uninstall my-nginx
```

`helm upgrade`/`rollback` track **revisions**, so changing config or recovering from a bad release is one command — Helm diffs and applies only what changed.

## What a tiny chart looks like

A chart is just a folder. This guide includes a runnable tiny chart at [`manifests/packaging/helm/my-app/`](../../manifests/packaging/helm/my-app/):

```
manifests/packaging/helm/my-app/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── deployment.yaml
    └── service.yaml
```

```yaml
# Chart.yaml
apiVersion: v2
name: my-app
description: A tiny Helm chart for the Kubernetes tutorial
type: application
version: 0.1.0
appVersion: "1.27"
```

```yaml
# values.yaml
replicaCount: 2
image:
  repository: nginx
  tag: "1.27"
service:
  port: 80
```

```yaml
# templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}
  labels:
    app.kubernetes.io/name: {{ .Chart.Name }}
    app.kubernetes.io/instance: {{ .Release.Name }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ .Chart.Name }}
      app.kubernetes.io/instance: {{ .Release.Name }}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {{ .Chart.Name }}
        app.kubernetes.io/instance: {{ .Release.Name }}
    spec:
      containers:
        - name: web
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
```

```yaml
# templates/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ .Release.Name }}
  labels:
    app.kubernetes.io/name: {{ .Chart.Name }}
    app.kubernetes.io/instance: {{ .Release.Name }}
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: {{ .Chart.Name }}
    app.kubernetes.io/instance: {{ .Release.Name }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.port }}
```

Render before applying so you can see the final YAML:

```bash
helm template demo manifests/packaging/helm/my-app
```

Install it as a release, change a value, then remove it:

```bash
helm install demo manifests/packaging/helm/my-app
kubectl get deploy,svc -l app.kubernetes.io/instance=demo

helm upgrade demo manifests/packaging/helm/my-app --set replicaCount=3
helm history demo

helm uninstall demo
```

## When Helm earns its keep

- ✅ **Reusable, distributable** apps (you publish a chart, others install it).
- ✅ Many **values-driven** variations of the same app.
- ✅ Installing **third-party** software (databases, ingress controllers, monitoring).
- ⚠️ For *your own* small set of manifests that differ only slightly per environment, [Kustomize](kustomize.md) is often simpler — no templating language.

## Best practices

- **Pin chart versions** (`--version`) so installs are reproducible.
- **Keep `values.yaml` per environment in Git**; inject secrets separately, never commit real ones.
- **`helm diff`** (plugin) or `--dry-run` before upgrading production.
- **Prefer well-maintained upstream charts** over rolling your own for common software.

---

[← Ingress](../networking/ingress.md) · [↑ Contents](../../README.md) · [Kustomize (intro) →](kustomize.md)
