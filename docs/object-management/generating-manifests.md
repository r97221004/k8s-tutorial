# Generating Manifests

> Let kubectl write the YAML for you with --dry-run=client -o yaml.

---

Writing a manifest from memory means remembering every field name, every level of indentation, and which `apiVersion` goes with which `kind`. You don't have to. The imperative commands from the [previous chapter](imperative-commands.md) already know how to build an object from a few flags. You can ask them to **print** the object instead of creating it.

## The trick: `--dry-run=client -o yaml`

Take the `kubectl run` you already know, and add two flags:

```bash
kubectl run color-api --image=<YOUR_DOCKERHUB_USER>/color-api:1.0.0 --port=8080 --labels=app=color-api \
  --dry-run=client -o yaml
```

| Flag | What it does |
|---|---|
| `--dry-run=client` | Build the object in kubectl, and **don't send it** to the cluster. Nothing is created. |
| `-o yaml` | Print the object as YAML. |

```yaml
apiVersion: v1
kind: Pod
metadata:
  creationTimestamp: null
  labels:
    app: color-api
  name: color-api
spec:
  containers:
  - image: <YOUR_DOCKERHUB_USER>/color-api:1.0.0
    name: color-api
    ports:
    - containerPort: 8080
    resources: {}
  dnsPolicy: ClusterFirst
  restartPolicy: Always
status: {}
```

`apiVersion`, `kind`, the nesting, the list syntax: all correct, and you didn't type any of it. Redirect it into a file to keep it:

```bash
kubectl run color-api --image=<YOUR_DOCKERHUB_USER>/color-api:1.0.0 --port=8080 --labels=app=color-api \
  --dry-run=client -o yaml > /tmp/color-api-pod.yaml
```

(It goes to `/tmp` so it doesn't land next to the repo's own copy in `manifests/object-management/`.)

> List items aren't indented under their parent here (`containers:` then `- image:` at the same column). That's valid YAML, just a different style from the manifests in this guide. Both mean exactly the same thing.

## Tidy up the output

The generated file works as-is, but a few lines are noise. Delete them before you commit the file:

| Line | Why it's there | Keep it? |
|---|---|---|
| `creationTimestamp: null` | An empty field kubectl always prints. The cluster sets the real value. | Delete |
| `resources: {}` | An empty placeholder. | Delete, or fill it in later (see [Resources](../running-and-operating/resources.md)) |
| `status: {}` | `status` is written by the cluster, [never by you](manifest-files.md#spec-vs-status). | Delete |
| `dnsPolicy: ClusterFirst`, `restartPolicy: Always` | These are the defaults, spelled out. | Either. Deleting them keeps the file short. |

Delete them in your editor, or in one go:

```bash
sed -i '/creationTimestamp: null/d; /resources: {}/d; /status: {}/d' /tmp/color-api-pod.yaml
```

Then check the result the way [Manifest Files](manifest-files.md#catch-mistakes-before-they-reach-the-cluster) showed. The API server validates it without creating anything:

```bash
kubectl create --dry-run=server -f /tmp/color-api-pod.yaml
```

```
pod/color-api created (server dry run)
```

What's left is the same Pod as [`color-api-pod.yaml`](../../manifests/object-management/color-api-pod.yaml) in the repo, plus the two default lines (`dnsPolicy`, `restartPolicy`) that the repo's copy leaves out. Generate, tidy, check: that's the whole loop.

## Other kinds of objects

Most `kubectl create <kind>` commands support the same two flags. For the Service from the previous chapter, though, `kubectl expose` has a catch:

```bash
kubectl expose pod color-api --type=NodePort --port=80 --target-port=8080 --dry-run=client -o yaml
```

```
Error from server (NotFound): pods "color-api" not found
```

`expose` reads the **live** Pod to copy its labels and ports, so the Pod has to exist first, even for a dry run. To generate a Service before anything is running, use `kubectl create service` instead:

```bash
kubectl create service nodeport color-api --tcp=80:8080 --dry-run=client -o yaml
```

```yaml
apiVersion: v1
kind: Service
metadata:
  creationTimestamp: null
  labels:
    app: color-api
  name: color-api
spec:
  ports:
  - name: 80-8080
    port: 80
    protocol: TCP
    targetPort: 8080
  selector:
    app: color-api
  type: NodePort
status:
  loadBalancer: {}
```

`--tcp=80:8080` is `port:targetPort`. The selector is always `app: <the name you gave>`, so it only finds your Pods if they carry that label. Here they do. Apart from the generated port `name` and the noise lines, this is [`color-api-svc.yaml`](../../manifests/object-management/color-api-svc.yaml).

Some generators you'll use in later chapters:

| To generate a | Run |
|---|---|
| Pod | `kubectl run <name> --image=… --dry-run=client -o yaml` |
| Service | `kubectl create service clusterip\|nodeport <name> --tcp=<port>:<targetPort> --dry-run=client -o yaml` |
| Deployment | `kubectl create deployment <name> --image=… --replicas=3 --dry-run=client -o yaml` |
| ConfigMap | `kubectl create configmap <name> --from-literal=KEY=value --dry-run=client -o yaml` |
| Job | `kubectl create job <name> --image=… --dry-run=client -o yaml -- <command>` |

## Why `client`, not `server` or `get`?

You've seen two other ways to get YAML out of kubectl. Both give you far more than you want:

| Command | Lines for the color-api Pod | What's extra |
|---|---|---|
| `--dry-run=client -o yaml` | 17 | Just a few empty fields |
| `--dry-run=server -o yaml` | 65 | A `uid`, and every default the API server filled in |
| `kubectl get pod color-api -o yaml` | 100+ | All of that, plus the scheduler's `nodeName` and the whole `status` ([Manifest Files](manifest-files.md#what-the-cluster-added)) |

`--dry-run=server` is for **checking** a file, as in [Manifest Files](manifest-files.md#catch-mistakes-before-they-reach-the-cluster). `--dry-run=client` is for **generating** one.

## When there's no generator

Generators only cover the flags their command offers. Anything beyond that, such as a probe, a volume, or a second container, you add by hand. Generate the skeleton first, then fill in the rest with [`kubectl explain`](manifest-files.md#look-up-any-field-with-kubectl-explain) to look up each field.

## Best practices

- **Generate, then edit.** Let kubectl write the skeleton, so `apiVersion`, `kind`, and indentation are right from the start.
- **Delete the noise** (`creationTimestamp: null`, `status: {}`, empty `{}`) before committing.
- **Don't start from `kubectl get -o yaml`.** It describes one live object, with fields that don't belong in a manifest.
- **Check what you edited** with `--dry-run=server` before you create it.

---

[← Imperative Commands](imperative-commands.md) · [↑ Contents](../../README.md) · [Imperative Commands with Files →](imperative-object-configuration.md)
