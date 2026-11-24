# Manifest Files

> The YAML that describes an object: apiVersion, kind, metadata, spec, and the status the cluster fills in.

---

So far you've described every object with flags: `kubectl run color-api --image=… --port=8080`. A **manifest** writes the same description down in a YAML file, so you can keep it, review it, and apply it again later. Both file-based approaches from [Object Management](object-management.md) start here.

The good news: **almost every Kubernetes object has the same four top-level fields.** Three of them, `apiVersion`, `kind`, and `metadata`, appear in every object. The fourth is usually `spec`. A few objects that just hold data use a different field instead: a [ConfigMap](../config-and-data/configmap.md), like the `color-config` in [Object Management](object-management.md), has `data`. Learn the shape once, and every manifest in this guide reads the same way.

## The color-api Pod as a manifest

Here's the Pod from [From Dockerfile to Pod](../pods/from-dockerfile-to-pod.md), written as a file:

▶ **Runnable manifest:** [`manifests/object-management/color-api-pod.yaml`](../../manifests/object-management/color-api-pod.yaml)

```yaml
apiVersion: v1                # 1. which API defines this kind of object
kind: Pod                     # 2. what kind of object it is
metadata:                     # 3. who it is: name, labels, …
  name: color-api
  labels:
    app: color-api
spec:                         # 4. what you want it to be
  containers:
    - name: color-api
      image: <YOUR_DOCKERHUB_USER>/color-api:1.0.0
      ports:
        - containerPort: 8080
```

Every flag you used with `kubectl run` has a home in this file:

| `kubectl run` | Manifest field |
|---|---|
| `color-api` (the name) | `metadata.name`, and the container's `name` |
| `--image=…` | `spec.containers[].image` |
| `--port=8080` | `spec.containers[].ports[].containerPort` |
| `--labels=app=color-api` | `metadata.labels` |

> The `a.b[].c` notation is how Kubernetes docs name a field: follow the keys down from the top, and `[]` marks a list. `kubectl explain`, which you'll meet below, takes the same path without the brackets: `pod.spec.containers.ports`.

## The four fields

### `apiVersion`: which API defines the object

The Kubernetes API is split into **groups**, and each group is versioned. `apiVersion` names the group and version that define this kind of object, in the form `<group>/<version>`. The original core objects belong to the **core group**, which has no name, so their `apiVersion` is just the version:

| `apiVersion` | Group | Kinds you'll meet |
|---|---|---|
| `v1` | core | `Pod`, `Service`, `ConfigMap`, `Secret`, `Namespace` |
| `apps/v1` | `apps` | `Deployment`, `ReplicaSet`, `StatefulSet`, `DaemonSet` |
| `batch/v1` | `batch` | `Job`, `CronJob` |
| `networking.k8s.io/v1` | `networking.k8s.io` | `Ingress` |

You don't need to memorize these. Your cluster lists every kind it knows, with its `apiVersion`:

```bash
kubectl api-resources
```

```text
NAME          SHORTNAMES   APIVERSION             NAMESPACED   KIND
configmaps    cm           v1                     true         ConfigMap
pods          po           v1                     true         Pod
deployments   deploy       apps/v1                true         Deployment
jobs                       batch/v1               true         Job
ingresses     ing          networking.k8s.io/v1   true         Ingress
...
```

### `kind`: what the object is

`kind` is the type of object, written in CamelCase and singular: `Pod`, `Deployment`, `ConfigMap`. It must be a kind that the `apiVersion` actually defines. A `Pod` with `apiVersion: apps/v1` is rejected, because Pods live in the core group.

### `metadata`: who the object is

`metadata` identifies the object and helps you find it:

| Field | What it's for |
|---|---|
| `name` | Required. Unique among objects of the same kind in a namespace. |
| `namespace` | Which [namespace](../core-objects/namespace.md) it lives in. Leave it out to use your current one. |
| `labels` | Key-value pairs for finding and grouping objects. Selectors match on them (see [What Are ReplicaSets](../replicasets-deployments/what-are-replicasets.md)). |
| `annotations` | Key-value pairs for extra information, meant for tools and people, not for selecting. |

The cluster also **adds** fields to `metadata` when it stores the object, such as a unique `uid` and a `creationTimestamp`. You'll see them below.

### `spec`: what you want

`spec` is the **desired state**: the actual configuration of the object. It's the part whose shape changes from kind to kind. A Pod's `spec` lists containers, a Deployment's adds `replicas` and a Pod template, a Service's has ports and a selector. `apiVersion` and `kind` together decide which fields `spec` may contain.

`spec` is where you'll spend nearly all your time. When you're not sure what goes in it, ask the cluster (see [Look up any field](#look-up-any-field-with-kubectl-explain) below).

## YAML in one minute

Manifests are written in YAML. You only need a few rules:

```yaml
key: value              # a map entry
parent:                 # a nested map: indent its children
  child: value
items:                  # a list: one "- " per item
  - first
  - second
containers:             # a list of maps, as in every Pod
  - name: web           #   the "- " starts a new item…
    image: nginx:1.27   #   …and these keys belong to the same item
```

- **Indent with spaces, never tabs.** Two spaces per level is the convention. A tab gives you an error like `found character that cannot start any token`.
- **Indentation is structure.** Move a line two spaces left or right, and it belongs to a different parent.
- **Quote values that look like something else.** `"true"`, `"8080"`, or `"1.10"` stay strings only when quoted. This matters where a field expects a string, such as an environment variable's value.

## Try it: send the file to the cluster

Work on a copy, so the file in the repo stays untouched. Copy it, fill in your Docker Hub username, and create the Pod from it:

```bash
cp manifests/object-management/color-api-pod.yaml /tmp/pod.yaml
sed -i 's/<YOUR_DOCKERHUB_USER>/your-dockerhub-user/' /tmp/pod.yaml   # use your username
kubectl create -f /tmp/pod.yaml
kubectl wait --for=condition=Ready pod/color-api --timeout=60s
```

`kubectl create -f` creates whatever the file describes. [Imperative Commands with Files](imperative-object-configuration.md) covers it properly, and [Declarative Object Management](declarative-management.md) shows the `kubectl apply -f` you'll use most of the time.

### What the cluster added

Now ask for the object back:

```bash
kubectl get pod color-api -o yaml
```

Your file had 12 lines. What comes back is over 100. Here it is, trimmed:

```yaml
apiVersion: v1
kind: Pod
metadata:
  creationTimestamp: "2026-11-21T10:37:35Z"   # ← added: when it was created
  labels:
    app: color-api
  name: color-api
  namespace: default                          # ← added: your current namespace
  resourceVersion: "22391"                    # ← added: changes on every update
  uid: 7fae1280-3730-4a1b-b3c1-2129532f0623   # ← added: unique forever
spec:
  containers:
  - image: <YOUR_DOCKERHUB_USER>/color-api:1.0.0
    imagePullPolicy: IfNotPresent             # ← default
    name: color-api
    ports:
    - containerPort: 8080
      protocol: TCP                           # ← default
    volumeMounts: [...]                       # ← added: the service account token
  nodeName: node-1                            # ← added: the scheduler's decision
  restartPolicy: Always                       # ← default
  ...                                         #   (about 15 more defaults)
status:                                       # ← added: the whole section
  phase: Running
  podIP: 10.244.0.18
  ...
```

The cluster filled in three kinds of things:

- **Identity** in `metadata`: `uid`, `resourceVersion`, `creationTimestamp`, and the `namespace`.
- **Defaults** in `spec`: every field you didn't set gets its default value, like `restartPolicy: Always`. Some fields are filled in by the cluster's own components, like `nodeName` by the scheduler.
- **A `status`** section, which your file never had.

This is also why `kubectl get -o yaml` makes a poor starting point for a new manifest: it's full of fields that only make sense for this one live object. [Generating Manifests](generating-manifests.md) shows a cleaner way.

> 💡 It's also why `kubectl replace` on a Pod fails, as [Object Management](object-management.md) mentioned. Your file doesn't have `nodeName` or the token volume, so replacing the live Pod with it would *change* its immutable spec.

## `spec` vs. `status`

| | `spec` | `status` |
|---|---|---|
| **Means** | What you **want** | What **is** |
| **Written by** | You (in the manifest) | The cluster, continuously |
| **In your file?** | Yes | Never |

You write `spec`; Kubernetes reports `status`; controllers work to close the gap between them. That's the [declarative model](../getting-started/what-is-kubernetes.md#imperative-vs-declarative) made concrete. You'll never write `status`, but you'll read it all the time: `kubectl get` and `kubectl describe` are mostly a friendly view of it.

## Catch mistakes before they reach the cluster

Add `--dry-run=server` and the API server checks the file exactly as it would for real, then throws the result away instead of storing it. In real work, run it **before** you create or change anything. Here you'll try it on the Pod you already created, which shows one more thing it catches:

```bash
kubectl create --dry-run=server -f /tmp/pod.yaml    # check the file, create nothing
```

Run it now, while `color-api` is still running, and it already finds a problem, exactly as a real `create` would:

```text
Error from server (AlreadyExists): error when creating "/tmp/pod.yaml": pods "color-api" already exists
```

Now break your copy on purpose, two ways. Each error is caught before the existence check, so leave the Pod running.

**A misspelled field.** Misspell `containers`, check, then fix it again:

```bash
sed -i 's/containers:/contianers:/' /tmp/pod.yaml
kubectl create --dry-run=server -f /tmp/pod.yaml
sed -i 's/contianers:/containers:/' /tmp/pod.yaml
```

```text
Error from server (BadRequest): error when creating "/tmp/pod.yaml": Pod in version "v1" cannot be handled as a Pod: strict decoding error: unknown field "spec.contianers"
```

**A kind that doesn't belong to the `apiVersion`.** Claim a Pod is in `apps/v1`:

```bash
sed -i 's#^apiVersion: v1#apiVersion: apps/v1#' /tmp/pod.yaml
kubectl create --dry-run=server -f /tmp/pod.yaml
sed -i 's#^apiVersion: apps/v1#apiVersion: v1#' /tmp/pod.yaml
```

```text
error: resource mapping not found for name: "color-api" namespace: "" from "/tmp/pod.yaml": no matches for kind "Pod" in version "apps/v1"
ensure CRDs are installed first
```

(The hint about CRDs is for custom kinds, which you'll meet much later. Here the cause is simply the wrong `apiVersion`.)

The error names the exact field or kind that's wrong, so it's worth running before you change anything that matters.

## Look up any field with `kubectl explain`

You don't need to memorize `spec`. The cluster documents every field of every kind, for the exact version you're running:

```bash
kubectl explain pod                            # the top-level fields, and what a Pod is
kubectl explain pod.spec.containers.ports      # one field, with its type and description
kubectl explain pod.spec --recursive | less    # every field under spec, as a tree
```

```text
KIND:       Pod
VERSION:    v1

FIELD: ports <[]ContainerPort>

DESCRIPTION:
    List of ports to expose from the container. ...
```

The type in angle brackets tells you how to write it: `<string>` is a value, `<Object>` is a nested map, and `<[]ContainerPort>` is a list, so each item starts with `- `.

## Clean up

```bash
kubectl delete -f /tmp/pod.yaml
rm /tmp/pod.yaml
```

`delete -f` deletes whatever the file describes, found by its `kind`, `namespace`, and `name`.

## Best practices

- **Don't write manifests from memory.** Generate a starting point ([Generating Manifests](generating-manifests.md)), and look fields up with `kubectl explain`.
- **Check with `--dry-run=server`** before creating or changing anything important.
- **Keep manifests in Git**, one object per file to start. [Multiple Objects in One File](multiple-objects-per-file.md) shows when to group them.
- **Label everything consistently**, starting with an `app` label. Labels are how everything else finds your objects.
- **Never copy `status`, `uid`, or `resourceVersion` into a manifest.** They belong to one live object, not to the description of it.

---

[← Object Management](object-management.md) · [↑ Contents](../../README.md) · [Imperative Commands →](imperative-commands.md)
