# Selecting with matchLabels and matchExpressions

> Write selectors into manifests, see that they're the same queries as `-l`, and learn the rules a workload's selector has to follow.

---

[Labels and Selectors](labels-selectors.md#3-selectors-on-the-command-line) ran both kinds of selector from the command line, where they share one string: `-l 'app=color-api,release notin (canary)'`. A Deployment, a ReplicaSet, or a Service stores a query like that in its manifest, and runs it again and again. Not all of them can store all of it, though: a Service can only hold the simplest kind, as step 6 shows.

In a manifest, the two kinds are separate fields: **`matchLabels`** for equality, and **`matchExpressions`** for sets. In this chapter you'll read both, put them in a Deployment, and see what the API server does when the selector breaks its rules.

## Before you start

You only need a running cluster. This chapter's Deployment uses its own `app: selector-demo` label, so it doesn't pick up anything left over from the previous chapter.

## 1. `matchLabels`

You've written this in every Deployment:

```yaml
selector:
  matchLabels:
    app: color-api
    tier: backend
```

Each key must equal its value, and all of them must hold. It's `-l app=color-api,tier=backend`. There's no way to say `!=` here; for that, use `matchExpressions`.

## 2. `matchExpressions`

Each expression is a `key`, an `operator`, and, for some operators, a list of `values`:

```yaml
selector:
  matchExpressions:
    - key: tier
      operator: In
      values: [frontend, backend]
```

```yaml
selector:
  matchExpressions:
    - key: release
      operator: NotIn
      values: [canary]
```

There are four operators, one for each set-based form of `-l`:

| `operator` | `values` | Same as |
|---|---|---|
| `In` | one or more | `-l 'tier in (frontend,backend)'` |
| `NotIn` | one or more | `-l 'release notin (canary)'` |
| `Exists` | none: leave `values` out | `-l owner` |
| `DoesNotExist` | none: leave `values` out | `-l '!owner'` |

The same catch as on the command line applies: `NotIn` and `DoesNotExist` also match objects that don't have the key at all.

## 3. Combine them

A selector can have both fields. Every condition must hold: each entry in `matchLabels`, and each expression in `matchExpressions`. The non-canary color-api Pods from the previous chapter, `-l 'app=color-api,release notin (canary)'`, look like this:

```yaml
selector:
  matchLabels:
    app: color-api
  matchExpressions:
    - key: release
      operator: NotIn
      values: [canary]
```

## 4. Try it on a Deployment

[`manifests/labels-namespaces/selector-demo.yaml`](../../manifests/labels-namespaces/selector-demo.yaml) is a Deployment whose selector uses both fields:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: selector-demo
spec:
  replicas: 2
  selector:
    matchLabels:
      app: selector-demo
    matchExpressions:
      - key: release
        operator: In
        values: [stable, canary]
  template:
    metadata:
      labels:
        app: selector-demo    # must satisfy every condition in the selector
        release: stable
    spec:
      containers:
        - name: nginx
          image: nginx:1.27
```

You'll edit it in step 5, so work on a copy:

```bash
mkdir -p /tmp/labels
cp manifests/labels-namespaces/selector-demo.yaml /tmp/labels/
kubectl apply -f /tmp/labels/selector-demo.yaml
kubectl get deployment selector-demo -o wide
```

```text
NAME            READY   UP-TO-DATE   AVAILABLE   AGE   CONTAINERS   IMAGES       SELECTOR
selector-demo   2/2     2            2           10s   nginx        nginx:1.27   app=selector-demo,release in (canary,stable)
```

The `SELECTOR` column shows the YAML turned into the `-l` form: `matchLabels` became `app=selector-demo`, and the expression became `release in (canary,stable)`. They're two ways to write the same query, so you can paste it straight into `kubectl get pods -l`.

So far, every Pod with `app: selector-demo` is the Deployment's own, and all of them are `stable`, so the `In` has nothing to do. Give it something: add two Pods by hand, with the same `app` but a different `release`:

```bash
kubectl run stray-beta --image=nginx:1.27 \
  --labels=app=selector-demo,release=beta
kubectl run stray-canary --image=nginx:1.27 \
  --labels=app=selector-demo,release=canary
```

Now run the pasted selector:

```bash
kubectl get pods -l 'app=selector-demo,release in (canary,stable)' -L release
```

```text
NAME                             READY   STATUS    RESTARTS   AGE   RELEASE
selector-demo-6b8f9c7d5d-4kx2p   1/1     Running   0          1m    stable
selector-demo-6b8f9c7d5d-r7wqn   1/1     Running   0          1m    stable
stray-canary                     1/1     Running   0          5s    canary
```

`stray-beta` is left out, because `beta` isn't in the set. `stray-canary` is in: it matches the Deployment's selector just like the Deployment's own Pods.

But the Deployment didn't take it. It still runs its two Pods, and didn't delete one to get back to `replicas: 2`. That's because the Deployment doesn't count Pods itself. Its ReplicaSet does, with a selector of its own:

```bash
kubectl get rs -l app=selector-demo -o wide
```

```text
NAME                       DESIRED   CURRENT   READY   AGE   CONTAINERS   IMAGES       SELECTOR
selector-demo-6b8f9c7d5d   2         2         2       1m    nginx        nginx:1.27   app=selector-demo,pod-template-hash=6b8f9c7d5d,release in (canary,stable)
```

It's the Deployment's selector, plus the `pod-template-hash` label from [Introduction to Deployments](../replicasets-deployments/introduction-to-deployments.md). The Deployment adds that label to the ReplicaSet's selector, and to every Pod it creates from the template. A Pod you made by hand doesn't have it, so the ReplicaSet never counts it, and never deletes it. A bare ReplicaSet has no such protection, and adopts any Pod that matches, as [ReplicaSets and Existing Pods](../replicasets-deployments/replicaset-existing-pods.md) showed.

Delete the two stray Pods:

```bash
kubectl delete pod stray-beta stray-canary
```

## 5. The rules a workload's selector follows

Two rules apply to the selector of a Deployment, and of a ReplicaSet, StatefulSet, or DaemonSet. The API server enforces both.

### It must match the template's labels

The Deployment's ReplicaSet creates Pods from the template, and counts them with the selector. Pods that didn't match would never be counted, so it would create new ones forever. Change the template's `release` to a value the selector doesn't allow, and try it with `--dry-run=server`, which has the API server check the change without saving it:

```bash
sed -i 's/release: stable/release: beta/' /tmp/labels/selector-demo.yaml
kubectl apply -f /tmp/labels/selector-demo.yaml --dry-run=server
```

```text
The Deployment "selector-demo" is invalid: spec.template.metadata.labels: Invalid value: map[string]string{"app":"selector-demo", "release":"beta"}: `selector` does not match template `labels`
```

### It can't change after creation

In `apps/v1`, `spec.selector` is immutable. Start from a fresh copy, and narrow the selector to `stable` only. The template still matches it, so this time the only problem is the change itself:

```bash
cp manifests/labels-namespaces/selector-demo.yaml /tmp/labels/
sed -i 's/values: \[stable, canary\]/values: [stable]/' /tmp/labels/selector-demo.yaml
kubectl apply -f /tmp/labels/selector-demo.yaml --dry-run=server
```

The error is one long line; the end of it is what matters:

```text
The Deployment "selector-demo" is invalid: spec.selector: Invalid value: ...: field is immutable
```

To change a Deployment's selector, you delete it and create it again, which replaces all its Pods. So choose a selector that will stay true for the Deployment's whole life, like the app's name, and leave labels that change, such as `release` or a version, out of it.

## 6. Services take less

Not every selector is the same field. A Service's selector is just `key: value` pairs, as in [`color-api-clusterip.yaml`](../../manifests/services/color-api-clusterip.yaml):

| Object | The selector is written as | It can express |
|---|---|---|
| Deployment, ReplicaSet, StatefulSet, DaemonSet | `matchLabels`, `matchExpressions`, or both | Everything `-l` can |
| Service | Plain `key: value` pairs, no `matchLabels` | Equality only: no `!=`, `notin`, or `!key` |

So a Service can't say "everything except the canary". It can only send traffic to Pods that **have** certain labels. To keep the canary out, select a label that only the stable Pods carry, like `release: stable`.

## Clean up

```bash
kubectl delete -f manifests/labels-namespaces/selector-demo.yaml
rm -rf /tmp/labels
```

## Best practices

- **Use `matchLabels` when equality is enough.** It's shorter, and easier to read. Reach for `matchExpressions` when you need a set, an exclusion, or a key's presence.
- **Keep workload selectors small and stable.** They can't change later, so select on the app's name, not its version or release.
- **Check a selector with `-o wide`.** The `SELECTOR` column shows it in `-l` form, ready to paste into `kubectl get pods -l`.
- **Select Services on labels the right Pods have.** A Service can't exclude anything, so give the Pods you want a label of their own.

---

[← Labels and Selectors](labels-selectors.md) · [↑ Contents](../../README.md) · [Annotations →](annotations.md)
