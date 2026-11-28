# Annotations

> Attach information you don't select by, see the annotations Kubernetes and kubectl already write, and configure tools with them.

---

An **annotation** is a key-value pair in an object's `metadata`, just like a label. The difference is what it's for. Labels are for **finding** objects: selectors, `-l`, a Service choosing its Pods. Annotations are for **information** about an object that nothing selects by: who owns it, which commit it was built from, a link to its runbook, or settings for a tool that reads them.

You've met a few already, without the name: the change cause in [Understanding Rollouts](../replicasets-deployments/understanding-rollouts.md#2-record-why-the-change-cause), and the copy of your file that `apply` keeps in [Declarative Object Management](../object-management/declarative-management.md#4-how-apply-remembers-what-it-manages). In this chapter you'll add your own, see those built-in ones side by side, and change annotations from the command line.

## Before you start

You only need a running cluster. This chapter creates its own Deployment.

## 1. Labels or annotations?

Both are key-value pairs under `metadata`, with the same kind of key. Everything else differs:

| | Labels | Annotations |
|---|---|---|
| **For** | Identifying and grouping objects | Information about an object |
| **Selectable** | Yes: `-l`, `selector`, `matchLabels` | No |
| **Keys** | An optional DNS-subdomain prefix, then a name of up to 63 characters | The same |
| **Values** | Up to 63 characters, from a small set of characters | Any string: spaces, URLs, JSON. Up to 256 KiB for all of an object's annotations together |
| **Read by** | Kubernetes itself, to connect objects | People, and tools that look for specific keys |

A quick test: if you'd ever want to **select** by it, it's a label. If you'd only ever **read** it, it's an annotation. `environment: prod` is a label; the owner's email address is an annotation.

## 2. Add annotations in a manifest

[`manifests/labels-namespaces/web-annotated.yaml`](../../manifests/labels-namespaces/web-annotated.yaml) is a small nginx Deployment with build and ownership information:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-annotated
  labels:
    app: web-annotated                 # labels: for selecting
  annotations:                         # annotations: for information
    example.com/git-commit: "3f9c2ab"
    example.com/build-number: "42"     # values are strings: quote numbers
    example.com/owner: "Team Web <web@example.com>"
    example.com/runbook: "https://wiki.example.com/runbooks/web"
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web-annotated
  template:
    metadata:
      labels:
        app: web-annotated
    spec:
      containers:
        - name: nginx
          image: nginx:1.27
```

The values have spaces, `<>`, `:`, and `/`, none of which a label value could hold. The keys use a prefix, `example.com/`, for the same reason as with labels: so they can't collide with someone else's. In a real setup, a CI pipeline would fill in the commit and build number.

You'll break the file on purpose in a moment, so work on a copy:

```bash
mkdir -p /tmp/annotations
cp manifests/labels-namespaces/web-annotated.yaml /tmp/annotations/
kubectl apply -f /tmp/annotations/web-annotated.yaml
```

`describe` lists the annotations near the top:

```bash
kubectl describe deployment web-annotated | head -n 10
```

```text
Name:                   web-annotated
Namespace:              default
CreationTimestamp:      Thu, 26 Nov 2026 10:00:00 +0800
Labels:                 app=web-annotated
Annotations:            deployment.kubernetes.io/revision: 1
                        example.com/build-number: 42
                        example.com/git-commit: 3f9c2ab
                        example.com/owner: Team Web <web@example.com>
                        example.com/runbook: https://wiki.example.com/runbooks/web
Selector:               app=web-annotated
```

Your four annotations, plus one you didn't write: `deployment.kubernetes.io/revision`. Step 3 comes back to it.

### You can't select by them

An annotation looks like a label, but selectors don't see it:

```bash
kubectl get deployments -l example.com/git-commit=3f9c2ab
```

```text
No resources found in default namespace.
```

`-l` only looks at labels. To find objects by an annotation, you'd have to list them all and filter the output yourself. If you find yourself doing that, the annotation should probably be a label.

### Values are strings

Every annotation value is a string. YAML, though, reads an unquoted `42` as a number, and `true` as a boolean. Remove the quotes around the build number, and try it. `--dry-run=server` makes sure nothing changes, even if it went through:

```bash
sed -i 's/build-number: "42"/build-number: 42/' /tmp/annotations/web-annotated.yaml
kubectl apply -f /tmp/annotations/web-annotated.yaml --dry-run=server
```

The error is long; the end of it is what matters:

```text
... json: cannot unmarshal number into Go struct field ObjectMeta.metadata.annotations of type string
```

Booleans fail the same way, and YAML has more of them than you'd expect: besides `true` and `false`, an unquoted `yes`, `no`, `on`, or `off` is a boolean too, so `example.com/monitored: yes` is rejected as well. So quote anything that YAML might read as something else: numbers, and any of those six words. The [Ingress example](#5-annotations-that-configure-tools) in step 5 does the same with `"true"`. Put the quotes back:

```bash
cp manifests/labels-namespaces/web-annotated.yaml /tmp/annotations/
```

## 3. Annotations Kubernetes and kubectl write

`describe` showed one annotation you didn't write, and it hides another. List every annotation key on the Deployment with a Go template, which ranges over the map and prints each key:

```bash
kubectl get deployment web-annotated \
  -o go-template='{{range $k, $v := .metadata.annotations}}{{$k}}{{"\n"}}{{end}}'
```

```text
deployment.kubernetes.io/revision
example.com/build-number
example.com/git-commit
example.com/owner
example.com/runbook
kubectl.kubernetes.io/last-applied-configuration
```

You wrote four of these. The other two were written for you: `revision` by the Deployment controller, and `last-applied-configuration` by `kubectl apply`. The table adds two more you've met in Part 5, which don't show up here because nothing has written them on this Deployment yet:

| Annotation | Written by | What it holds |
|---|---|---|
| `deployment.kubernetes.io/revision` | The Deployment controller | The current revision number, from [Understanding Rollouts](../replicasets-deployments/understanding-rollouts.md#1-revisions-and-history) |
| `kubectl.kubernetes.io/last-applied-configuration` | `kubectl apply` | Your whole file, as JSON, from [Declarative Object Management](../object-management/declarative-management.md#4-how-apply-remembers-what-it-manages). `describe` hides it because it's so long |
| `kubernetes.io/change-cause` | You | Why this revision exists, shown by `rollout history` |
| `kubectl.kubernetes.io/restartedAt` | `kubectl rollout restart` | A timestamp in the **Pod template**, from [Understanding Rollouts](../replicasets-deployments/understanding-rollouts.md#7-restart-without-changing-anything) |

`last-applied-configuration` shows how much an annotation can hold: a whole manifest, as one JSON string. No label could.

Notice the prefixes, too. Kubernetes and kubectl put their annotations under `kubernetes.io/`, and your own go under your own prefix, the same rule as for [label keys](labels-selectors.md#prefixes-and-syntax).

## 4. Change annotations from the command line

`kubectl annotate` works like `kubectl label`. Add an on-call contact:

```bash
kubectl annotate deployment web-annotated example.com/on-call=alice
```

```text
deployment.apps/web-annotated annotated
```

Changing an existing value needs `--overwrite`, just like a label:

```bash
kubectl annotate deployment web-annotated example.com/on-call=bob
```

```text
error: --overwrite is false but found the following declared annotation(s): 'example.com/on-call' already has a value (alice)
```

```bash
kubectl annotate deployment web-annotated example.com/on-call=bob --overwrite
```

```text
deployment.apps/web-annotated annotated
```

### Annotating a Deployment doesn't roll it out

You changed the Deployment twice. Did it replace its Pods?

```bash
kubectl get rs -l app=web-annotated
```

```text
NAME                       DESIRED   CURRENT   READY   AGE
web-annotated-7c9d8b6f5d   2         2         2       3m
```

Still one ReplicaSet. A rollout only happens when the **Pod template** changes, and `kubectl annotate deployment` changes the Deployment's own `metadata`, outside the template. The same goes for the annotations in your file: changing `example.com/git-commit` on the Deployment doesn't touch a single Pod.

The annotation didn't stay on the Deployment alone, though. List the ReplicaSet's annotation keys:

```bash
kubectl get rs -l app=web-annotated \
  -o go-template='{{range .items}}{{range $k, $v := .metadata.annotations}}{{$k}}{{"\n"}}{{end}}{{end}}'
```

```text
deployment.kubernetes.io/desired-replicas
deployment.kubernetes.io/max-replicas
deployment.kubernetes.io/revision
example.com/build-number
example.com/git-commit
example.com/on-call
example.com/owner
example.com/runbook
```

The Deployment copies its annotations to its current ReplicaSet, `on-call` included. It leaves out `last-applied-configuration`, and the ReplicaSet gets a few `deployment.kubernetes.io/` annotations of its own, for its revision and its replica count. It's the same copying that carried `kubernetes.io/change-cause` to each revision's ReplicaSet in [Understanding Rollouts](../replicasets-deployments/understanding-rollouts.md#2-record-why-the-change-cause). The Pods get none of it: they're made from the template, and the template didn't change.

Annotations **inside** the template are different. They're copied to every Pod, so changing one is a template change, and starts a rollout. That's exactly how `kubectl rollout restart` works: it writes `restartedAt` into the template's annotations, as [Understanding Rollouts](../replicasets-deployments/understanding-rollouts.md#7-restart-without-changing-anything) showed.

| An annotation in… | Ends up on | Changing it |
|---|---|---|
| The Deployment's `metadata` | The Deployment, and its current ReplicaSet | Adds or updates the ReplicaSet's copy, but removing it doesn't; the Pods aren't touched |
| The template's `metadata` | Every Pod | Starts a rollout |

### Remove an annotation

As with labels, a `-` after the key removes it:

```bash
kubectl annotate deployment web-annotated example.com/on-call-
```

```text
deployment.apps/web-annotated annotated
```

It's gone from the Deployment. Now look at the ReplicaSet again:

```bash
kubectl get rs -l app=web-annotated \
  -o go-template='{{range .items}}{{range $k, $v := .metadata.annotations}}{{$k}}={{$v}}{{"\n"}}{{end}}{{end}}'
```

```text
deployment.kubernetes.io/desired-replicas=2
deployment.kubernetes.io/max-replicas=3
deployment.kubernetes.io/revision=1
example.com/build-number=42
example.com/git-commit=3f9c2ab
example.com/on-call=bob
example.com/owner=Team Web <web@example.com>
example.com/runbook=https://wiki.example.com/runbooks/web
```

`on-call=bob` is still there. The Deployment controller copies annotations to the ReplicaSet, and overwrites them when they change, but it never removes one. The stale copy does no harm, since nothing reads it, but don't look at a ReplicaSet's annotations to see what the Deployment says now. Ask the Deployment.

The same rule as with `kubectl label` applies, too: the next `apply` puts back any annotation your file sets, and leaves alone the ones it doesn't. Keep annotations that belong to the app in its manifest.

## 5. Annotations that configure tools

So far, annotations have been notes for people. They're also how many tools take settings that the Kubernetes API has no field for. The tool watches for objects, and reads the annotation keys it knows.

The most common example is the [ingress-nginx](https://kubernetes.github.io/ingress-nginx/) controller, which you'll meet in [Ingress](../networking/ingress.md). An Ingress object has fields for hosts and paths, but nothing for "allow uploads up to 10 MB". ingress-nginx reads that from an annotation:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: 10m
spec:
  ...
```

Each key is a **prefix** that names the tool, `nginx.ingress.kubernetes.io`, and a **name** for the setting, `proxy-body-size`. Kubernetes itself ignores all three; it stores them, and ingress-nginx acts on them.

That has a catch. Kubernetes doesn't know which annotations a tool expects, so it can't check them. Misspell one, say `proxy-body-sise`, and the API server accepts it, the tool doesn't recognize it, and the setting silently doesn't apply. Nothing tells you. When a setting from an annotation seems to do nothing, check the key against the tool's documentation, letter by letter.

Other tools work the same way: monitoring agents that look for annotations saying which port to scrape, service meshes that read whether to add a sidecar to a Pod, and operators that take per-object settings.

## Clean up

```bash
kubectl delete -f manifests/labels-namespaces/web-annotated.yaml
rm -rf /tmp/annotations
```

## Best practices

- **Use labels to select, annotations to describe.** If you'd ever filter by it, make it a label.
- **Prefix your own keys**, like `example.com/owner`, and leave `kubernetes.io/` to Kubernetes.
- **Quote values that YAML could read as something else:** numbers, `true`/`false`, and `yes`/`no`/`on`/`off`.
- **Keep annotations that belong to the app in its manifest.** `kubectl annotate` is for quick notes; the next `apply` puts back what the file says.
- **Know where an annotation lands.** On the Deployment, it changes nothing else; in the Pod template, changing it starts a rollout.
- **Check tool annotations against the tool's documentation.** A misspelled key is accepted without a word, and does nothing.

---

[← Selecting with matchLabels and matchExpressions](selectors-in-manifests.md) · [↑ Contents](../../README.md) · [Namespaces →](namespaces.md)
