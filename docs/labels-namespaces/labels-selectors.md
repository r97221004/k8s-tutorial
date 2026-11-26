# Labels and Selectors in Depth

> Add and change labels, select with `matchLabels` and `matchExpressions`, and use the recommended labels.

---

You've used labels since Part 3, and [What Are ReplicaSets](../replicasets-deployments/what-are-replicasets.md#labels-and-selectors) showed the basics: a **label** is a key-value tag on an object, and a **selector** is a query that matches objects by their labels. That's how a ReplicaSet finds its Pods, and how a Service finds where to send traffic.

So far, though, each object had one or two labels, and every selector looked for `app: something`. Real clusters label along several dimensions at once: which app, which environment, which tier, which release. In this chapter you'll label a small set of Pods that way, change their labels from the command line, and write the two kinds of selector that manifests use.

## Before you start

You need a running cluster with nothing left over from the Services part. The Pods in this chapter use `app: color-api`, the same label as color-api's Deployment and Services, so anything still running from there would get mixed in. The Services would send real traffic to these nginx Pods, and every `-l app=color-api` below would match color-api's own Pods too.

If you haven't run the [clean-up at the end of ExternalName Services](../services/externalname-services.md#clean-up), do it now. If its files in `/tmp/services` are gone, for example after a reboot, delete by label instead. Every object from that part carries an `app` label:

```bash
kubectl delete deployment,svc -l app=color-api
kubectl delete pod -l app=traffic-generator
```

Then check that the `default` namespace is empty:

```bash
kubectl get pods,svc
```

```text
NAME                 TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)   AGE
service/kubernetes   ClusterIP   10.96.0.1    <none>        443/TCP   4d
```

No Pods, and only the `kubernetes` Service, which the cluster creates for its own API server.

## 1. Five Pods, four labels

[`manifests/labels-namespaces/labeled-pods.yaml`](../../manifests/labels-namespaces/labeled-pods.yaml) holds five Pods. They all run plain nginx; only their labels differ:

| Pod | `app` | `environment` | `tier` | `release` |
|---|---|---|---|---|
| `color-api-frontend` | `color-api` | `dev` | `frontend` | `stable` |
| `color-api-backend` | `color-api` | `dev` | `backend` | `stable` |
| `color-api-canary` | `color-api` | `dev` | `backend` | `canary` |
| `ecomm-dev` | `ecomm` | `dev` | `backend` | `stable` |
| `ecomm-prod` | `ecomm` | `prod` | `backend` | `stable` |

Each one looks like this:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: color-api-canary
  labels:
    app: color-api
    environment: dev
    tier: backend
    release: canary
spec:
  containers:
    - name: nginx
      image: nginx:1.27
```

Notice that **labels aren't unique**. Four Pods share `tier: backend`, and four share `release: stable`. A name identifies one object; a label describes a group, so many objects carrying the same one is the whole idea.

Bare Pods keep the focus on labels here. In a real cluster, these would be the templates of five Deployments.

Apply the file. Nothing in it needs filling in, so apply it straight from the repo:

```bash
kubectl apply -f manifests/labels-namespaces/labeled-pods.yaml
```

`--show-labels` crams every label into one column. With four of them, `-L` reads better: it gives each label key you name its own column:

```bash
kubectl get pods -L app,environment,tier,release
```

```text
NAME                 READY   STATUS    RESTARTS   AGE   APP         ENVIRONMENT   TIER       RELEASE
color-api-backend    1/1     Running   0          10s   color-api   dev           backend    stable
color-api-canary     1/1     Running   0          10s   color-api   dev           backend    canary
color-api-frontend   1/1     Running   0          10s   color-api   dev           frontend   stable
ecomm-dev            1/1     Running   0          10s   ecomm       dev           backend    stable
ecomm-prod           1/1     Running   0          10s   ecomm       prod          backend    stable
```

## 2. Change labels from the command line

`kubectl label` adds, changes, and removes labels on objects that already exist.

### Add a label

Name the object, then `key=value`. To label several objects at once, select them with `-l` instead of naming them. Give both ecomm Pods an owner:

```bash
kubectl label pods -l app=ecomm owner=shop
```

```text
pod/ecomm-dev labeled
pod/ecomm-prod labeled
```

### Change a label

Say the canary has proved itself, and you want to promote it to `stable`. Setting a label that already has a value fails:

```bash
kubectl label pod color-api-canary release=stable
```

```text
error: 'release' already has a value (canary), and --overwrite is false
```

That's a safety catch, so a typo doesn't silently replace a label something depends on. Say you mean it with `--overwrite`:

```bash
kubectl label pod color-api-canary release=stable --overwrite
```

```text
pod/color-api-canary labeled
```

### Remove a label

Put a `-` after the key, with no value:

```bash
kubectl label pod ecomm-prod owner-
```

```text
pod/ecomm-prod unlabeled
```

Now only `ecomm-dev` has an owner, and the canary is `stable`:

```bash
kubectl get pods -L app,release,owner
```

```text
NAME                 READY   STATUS    RESTARTS   AGE   APP         RELEASE   OWNER
color-api-backend    1/1     Running   0          1m    color-api   stable
color-api-canary     1/1     Running   0          1m    color-api   stable
color-api-frontend   1/1     Running   0          1m    color-api   stable
ecomm-dev            1/1     Running   0          1m    ecomm       stable    shop
ecomm-prod           1/1     Running   0          1m    ecomm       stable
```

### The file still wins

These are imperative changes, and the file knows nothing about them. Apply it again:

```bash
kubectl apply -f manifests/labels-namespaces/labeled-pods.yaml
```

```text
pod/color-api-frontend unchanged
pod/color-api-backend unchanged
pod/color-api-canary configured
pod/ecomm-dev unchanged
pod/ecomm-prod unchanged
```

```bash
kubectl get pods -L release,owner
```

```text
NAME                 READY   STATUS    RESTARTS   AGE   RELEASE   OWNER
color-api-backend    1/1     Running   0          2m    stable
color-api-canary     1/1     Running   0          2m    canary
color-api-frontend   1/1     Running   0          2m    stable
ecomm-dev            1/1     Running   0          2m    stable    shop
ecomm-prod           1/1     Running   0          2m    stable
```

The two changes came out differently, for the reason from [Declarative Object Management](../object-management/declarative-management.md):

- **`release` went back to `canary`.** The file sets `release`, so `apply` puts back what the file says, just as it did with `kubectl scale` in [Scaling Deployments](../replicasets-deployments/scaling-deployments.md).
- **`owner: shop` stayed on `ecomm-dev`.** The file never mentioned `owner`, so `apply` leaves it alone.

So `kubectl label` is fine for experiments, and for labels nothing manages. For a label that's in a manifest, change the manifest. Otherwise the next `apply` undoes your change.

## 3. Selectors on the command line

There are two kinds of selector, and `-l` takes both.

**Equality-based** selectors compare a label with one value: `=` (or `==`, which means the same) and `!=`. **Set-based** selectors check a label against a set of values, or just check whether the key is there: `in`, `notin`, the bare key, and `!key`.

Against the five Pods, with `release` back to `canary` and `owner` only on `ecomm-dev`:

| Selector | Matches | Means |
|---|---|---|
| `-l environment=dev` | all but `ecomm-prod` | the label equals this value |
| `-l 'owner!=shop'` | all but `ecomm-dev` | the label doesn't equal this value |
| `-l 'tier in (frontend,backend)'` | all five | the label is one of these values |
| `-l 'release notin (canary)'` | all but `color-api-canary` | the label isn't any of these values |
| `-l owner` | `ecomm-dev` | the key exists, with any value |
| `-l '!owner'` | all but `ecomm-dev` | the key doesn't exist |

Quote anything with `!`, spaces, or parentheses, so the shell leaves it alone.

A comma means **and**, and you can mix the two kinds. Find the color-api Pods that aren't the canary:

```bash
kubectl get pods -l 'app=color-api,release notin (canary)' -L tier,release
```

```text
NAME                 READY   STATUS    RESTARTS   AGE   TIER       RELEASE
color-api-backend    1/1     Running   0          3m    backend    stable
color-api-frontend   1/1     Running   0          3m    frontend   stable
```

There's no **or**. To get "color-api or ecomm", use one key with `in`: `-l 'app in (color-api,ecomm)'`. Across two different keys, you run two queries.

### `notin` and `!=` match missing labels too

Ask for the Pods whose owner isn't `shop`:

```bash
kubectl get pods -l 'owner notin (shop)'
```

```text
NAME                 READY   STATUS    RESTARTS   AGE
color-api-backend    1/1     Running   0          3m
color-api-canary     1/1     Running   0          3m
color-api-frontend   1/1     Running   0          3m
ecomm-prod           1/1     Running   0          3m
```

Four Pods, none of which has an `owner` at all. A Pod without the key isn't "owned by shop", so it matches. `!=` works the same way: `-l 'owner!=shop'` in the table above matched these same four Pods. That's often what you want, but if you meant "has an owner, and it isn't shop", require the key too: `-l 'owner,owner notin (shop)'`.

## 4. Selectors in manifests

On the command line, both kinds share one string. In a manifest they're separate fields: `matchLabels` for equality, and `matchExpressions` for sets.

### `matchLabels`

You've written this in every Deployment:

```yaml
selector:
  matchLabels:
    app: color-api
    tier: backend
```

Each key must equal its value, and all of them must hold. It's `-l app=color-api,tier=backend`. There's no way to say `!=` here; for that, use `matchExpressions`.

### `matchExpressions`

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

The same rule as on the command line applies: `NotIn` and `DoesNotExist` also match objects that don't have the key at all.

### Putting them together

Every condition must hold: each entry in `matchLabels`, and each expression in `matchExpressions`. The non-canary color-api Pods from step 3 look like this:

```yaml
selector:
  matchLabels:
    app: color-api
  matchExpressions:
    - key: release
      operator: NotIn
      values: [canary]
```

### Try it on a Deployment

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

It uses its own `app` label, so it doesn't pick up the five Pods from step 1. You'll edit it below, so work on a copy:

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

The `SELECTOR` column shows the YAML turned into the `-l` form from step 3: `matchLabels` became `app=selector-demo`, and the expression became `release in (canary,stable)`. They're two ways to write the same query, so you can paste it straight into `kubectl get pods -l`.

Two rules apply to a workload's selector, and the API server enforces both.

**The selector must match the template's labels.** A Deployment counts its Pods with its selector, so Pods that don't match would never be counted, and it would create new ones forever. Change the template's `release` to a value the selector doesn't allow, and try it with `--dry-run=server`, which has the API server check the change without saving it:

```bash
sed -i 's/release: stable/release: beta/' /tmp/labels/selector-demo.yaml
kubectl apply -f /tmp/labels/selector-demo.yaml --dry-run=server
```

```text
The Deployment "selector-demo" is invalid: spec.template.metadata.labels: Invalid value: map[string]string{"app":"selector-demo", "release":"beta"}: `selector` does not match template `labels`
```

**The selector can't change after creation.** In `apps/v1`, `spec.selector` is immutable. Start from a fresh copy, and narrow the selector to `stable` only. The template still matches it, so this time the only problem is the change itself:

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

### Services take less

Not every selector is the same field. A Service's selector is just `key: value` pairs, as in [`color-api-clusterip.yaml`](../../manifests/services/color-api-clusterip.yaml):

| Object | The selector is written as | It can express |
|---|---|---|
| Deployment, ReplicaSet, StatefulSet, DaemonSet | `matchLabels`, `matchExpressions`, or both | Everything from step 3 |
| Service | Plain `key: value` pairs, no `matchLabels` | Equality only: no `!=`, `notin`, or `!key` |

So a Service can't say "everything except the canary". It can only send traffic to Pods that **have** certain labels. To keep the canary out, select a label that only the stable Pods carry, like `release: stable`.

## 5. Choosing label keys

Labels are free-form, but a few conventions keep them useful.

### Recommended labels

Kubernetes documents a set of [recommended labels](https://kubernetes.io/docs/concepts/overview/working-with-objects/common-labels/), all under the `app.kubernetes.io/` prefix. Tools like Helm, and dashboards, know how to read them:

| Key | Example | Describes |
|---|---|---|
| `app.kubernetes.io/name` | `color-api` | The app |
| `app.kubernetes.io/instance` | `color-api-dev` | This particular installation of it |
| `app.kubernetes.io/version` | `1.0.0` | The app's version |
| `app.kubernetes.io/component` | `backend` | Its role in the architecture |
| `app.kubernetes.io/part-of` | `ecomm` | The larger system it belongs to |
| `app.kubernetes.io/managed-by` | `helm` | The tool that manages it |

This tutorial keeps using a short `app:` for readability. In a shared cluster, the recommended keys are a better default, because everyone, and every tool, reads them the same way.

### Prefixes and syntax

A key can have a **prefix**, a DNS name followed by `/`, like `app.kubernetes.io/name`. Keys without one, like `app`, are for you. Prefixes keep labels from different teams and tools from colliding.

The `kubernetes.io/` and `k8s.io/` prefixes, and their subdomains, belong to Kubernetes. You've already got some: every node carries `kubernetes.io/hostname` and `kubernetes.io/os`, which `kubectl get nodes --show-labels` shows, and which [Scheduling](../core-objects/scheduling.md) uses to place Pods. Don't invent keys under them. `app.kubernetes.io/` is under `kubernetes.io/` too, but it's the exception: Kubernetes defines its keys for you to use, so use them as documented, and put your own keys under your own prefix.

Both the name part of a key and a value can be up to 63 characters: letters, digits, `-`, `_`, and `.`, starting and ending with a letter or digit. A value can also be empty. Anything longer, or with spaces, isn't a label. That's what [Annotations](annotations.md) are for.

## Clean up

```bash
kubectl delete \
  -f manifests/labels-namespaces/labeled-pods.yaml \
  -f manifests/labels-namespaces/selector-demo.yaml
rm -rf /tmp/labels
```

The `owner` label you added by hand goes with its Pod, so there's nothing else to remove.

## Best practices

- **Label along several dimensions**, like app, environment, tier, and release, so you can slice the same objects in different ways.
- **Keep labels in the manifest.** Use `kubectl label` for experiments; the next `apply` undoes changes to labels the file sets.
- **Keep workload selectors small and stable.** They can't change later, so select on the app's name, not its version or release.
- **Watch for missing keys with `notin` and `!=`.** They match objects without the key; add the bare key when you need it to exist.
- **Prefer the `app.kubernetes.io/` labels in shared clusters**, and prefix your own keys when they could collide with someone else's.

---

[← ExternalName Services](../services/externalname-services.md) · [↑ Contents](../../README.md) · [Annotations →](annotations.md)
