# Generating Manifests

> Let kubectl write the YAML for you with --dry-run=client -o yaml.

---

Writing a manifest from memory means remembering every field name, every level of indentation, and which `apiVersion` goes with which `kind`. You don't have to. The imperative commands from the [previous chapter](imperative-commands.md) already know how to build an object from a few flags. You can ask them to **print** the object instead of creating it.

This chapter uses plain `nginx`, so every command works as-is, with no image of your own.

## The trick: `--dry-run=client -o yaml`

Take a `kubectl run` command, and add two flags:

```bash
kubectl run nginx --image=nginx:1.27 --port=80 --labels=app=nginx \
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
    app: nginx
  name: nginx
spec:
  containers:
  - image: nginx:1.27
    name: nginx
    ports:
    - containerPort: 80
    resources: {}
  dnsPolicy: ClusterFirst
  restartPolicy: Always
status: {}
```

`apiVersion`, `kind`, the nesting, the list syntax: all correct, and you didn't type any of it. Redirect it into a file to keep it:

```bash
kubectl run nginx --image=nginx:1.27 --port=80 --labels=app=nginx \
  --dry-run=client -o yaml > /tmp/nginx-pod.yaml
```

(It goes to `/tmp` so it doesn't clutter the repo.)

> List items aren't indented under their parent here (`containers:` then `- image:` at the same column). That's valid YAML, just a different style from the manifests in this guide. Both mean exactly the same thing.

## Tidy up the output

The generated file works as-is, but a few lines are noise. Delete them before you commit the file:

| Line | Why it's there | Keep it? |
|---|---|---|
| `creationTimestamp: null` | An empty field kubectl always prints. The cluster sets the real value. | Delete |
| `resources: {}` | An empty placeholder. | Delete, or fill it in later (see [Resources](../resources-probes/requests-limits.md)) |
| `status: {}` | `status` is written by the cluster, [never by you](manifest-files.md#spec-vs-status). | Delete |
| `dnsPolicy: ClusterFirst`, `restartPolicy: Always` | These are the defaults, spelled out. | Either. Deleting them keeps the file short. |

Delete them in your editor, or in one go:

```bash
sed -i '/creationTimestamp: null/d; /resources: {}/d; /status: {}/d' /tmp/nginx-pod.yaml
```

Then check the result the way [Manifest Files](manifest-files.md#catch-mistakes-before-they-reach-the-cluster) showed. The API server validates it without creating anything:

```bash
kubectl create --dry-run=server -f /tmp/nginx-pod.yaml
```

```
pod/nginx created (server dry run)
```

Generate, tidy, check: that's the whole loop.

## Other kinds of objects

Most `kubectl create <kind>` commands support the same two flags. For a Service, though, the `kubectl expose` from the previous chapter has a catch:

```bash
kubectl expose pod nginx --type=NodePort --port=80 --dry-run=client -o yaml
```

```
Error from server (NotFound): pods "nginx" not found
```

`expose` reads the **live** Pod to copy its labels and ports, so the Pod has to exist first, even for a dry run. To generate a Service before anything is running, use `kubectl create service` instead:

```bash
kubectl create service nodeport nginx --tcp=80:80 --dry-run=client -o yaml
```

```yaml
apiVersion: v1
kind: Service
metadata:
  creationTimestamp: null
  labels:
    app: nginx
  name: nginx
spec:
  ports:
  - name: 80-80
    port: 80
    protocol: TCP
    targetPort: 80
  selector:
    app: nginx
  type: NodePort
status:
  loadBalancer: {}
```

`--tcp=80:80` is `port:targetPort`: the Service's port first, then the container's. Both are 80 here because nginx listens on 80; for an app listening on 8080, you'd write `--tcp=80:8080`. The selector is always `app: <the name you gave>`, so it only finds your Pods if they carry that label. Here they do: the Pod above is labeled `app=nginx`.

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

| Command | Lines for the nginx Pod | What's extra |
|---|---|---|
| `--dry-run=client -o yaml` | 17 | Just a few empty fields |
| `--dry-run=server -o yaml` | 65 | A `uid`, and every default the API server filled in |
| `kubectl get pod nginx -o yaml` | 100+ | All of that, plus the scheduler's `nodeName` and the whole `status` ([Manifest Files](manifest-files.md#what-the-cluster-added)) |

`--dry-run=server` is for **checking** a file, as you did above. `--dry-run=client` is for **generating** one.

## When there's no generator

Generators only cover the flags their command offers. Anything beyond that, such as a probe, a volume, or a second container, you add by hand. Generate the skeleton first, then fill in the rest with [`kubectl explain`](manifest-files.md#look-up-any-field-with-kubectl-explain) to look up each field.

## Clean up

Nothing was created in the cluster. Just remove the file:

```bash
rm /tmp/nginx-pod.yaml
```

## Best practices

- **Generate, then edit.** Let kubectl write the skeleton, so `apiVersion`, `kind`, and indentation are right from the start.
- **Delete the noise** (`creationTimestamp: null`, `status: {}`, empty `{}`) before committing.
- **Don't start from `kubectl get -o yaml`.** It describes one live object, with fields that don't belong in a manifest.
- **Check what you edited** with `--dry-run=server` before you create it.

---

[← Imperative Commands](imperative-commands.md) · [↑ Contents](../../README.md) · [Imperative Commands with Files →](imperative-object-configuration.md)
