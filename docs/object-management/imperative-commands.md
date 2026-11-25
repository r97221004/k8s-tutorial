# Imperative Commands

> Create and change objects with one-off kubectl commands, and where that stops scaling.

---

This is the first approach from [Object Management](object-management.md): name an operation on the command line, and the cluster does it, now. You've already used it: `kubectl run` and `kubectl set image` in Part 3 were imperative commands.

In this chapter you'll build the color-api Pod **and make it reachable from your laptop's browser**, using nothing but commands. Then you'll see what's missing when you try to do it all again.

## Before you start

You need the `color-api` image on Docker Hub from [From Dockerfile to Pod](../pods/from-dockerfile-to-pod.md), with both the `1.0.0` and `1.1.0` tags. Replace `<YOUR_DOCKERHUB_USER>` with your username throughout.

## 1. Create

`kubectl run` creates a Pod. This time, give it an `app` label up front. You'll see why in the next step:

```bash
kubectl run color-api --image=<YOUR_DOCKERHUB_USER>/color-api:1.0.0 --port=8080 --labels=app=color-api
kubectl wait --for=condition=Ready pod/color-api --timeout=60s
```

`run` only makes Pods. For other kinds, the imperative verb is `kubectl create <kind>`:

| Command | Creates |
|---|---|
| `kubectl create deployment web --image=nginx:1.27 --replicas=3` | a [Deployment](../replicasets-deployments/introduction-to-deployments.md) |
| `kubectl create configmap color-config --from-literal=COLOR=blue` | a [ConfigMap](../config-and-data/configmap.md) |
| `kubectl create secret generic db --from-literal=password=s3cret` | a [Secret](../config-and-data/secret.md) |
| `kubectl create namespace dev` | a [Namespace](../core-objects/namespace.md) |
| `kubectl create job hello --image=busybox:1.36 -- echo hi` | a [Job](../core-objects/job-cronjob.md) |

Most of these kinds come later in the guide. For now, just know the commands exist. `kubectl create --help` lists every kind it knows. Each one takes only the handful of flags its subcommand offers, which is enough for a quick start and too little for most real configurations.

## 2. Expose

In [Working with Pods](../pods/working-with-pods.md#4-pod-ip--name-why-you-cant-connect-yet), you couldn't reach the Pod from your laptop: the Pod network is private to the cluster. A [Service](../services/what-are-services.md) fixes that, and one command creates it:

```bash
kubectl expose pod color-api --type=NodePort --port=80 --target-port=8080
```

```
service/color-api exposed
```

| Flag | Meaning |
|---|---|
| `--type=NodePort` | Open a port on **every node**, so traffic from outside the cluster can get in. |
| `--port=80` | The port the Service itself listens on, inside the cluster. |
| `--target-port=8080` | The port on the Pod that traffic is forwarded to: where color-api listens. |

See what it was given:

```bash
kubectl get svc color-api
```

```text
NAME        TYPE       CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE
color-api   NodePort   10.102.148.199   <none>        80:31545/TCP   5s
```

`80:31545` means: port `80` on the Service's own IP, and port `31545` on every node (yours will differ, somewhere in 30000–32767). So a NodePort Service gives you **two ways in**:

| Access | IP | Port | Reachable from |
|---|---|---|---|
| **ClusterIP** | `10.102.148.199` (the `CLUSTER-IP` column) | `80` (`--port`) | Inside the cluster only: Pods, and the node itself |
| **NodePort** | `<Node-IP>` (any node's address) | `31545` | Anywhere that can reach a node, including your laptop |

Now open `http://<YOUR_VM_IP>:31545` in your **laptop's** browser. No `port-forward`, no SSH tunnel: the page loads straight from the node.

> **Page won't load?** `curl http://localhost:31545` on the node first. If that works, something between your laptop and the VM is blocking the port: a firewall on the VM (for example `ufw`), or, on a cloud VM, a security group that doesn't allow the 30000–32767 range.

How did the Service know which Pod to send traffic to? `expose` copied the Pod's labels into the Service's **selector**:

```bash
kubectl get svc color-api -o jsonpath='{.spec.selector}'    # {"app":"color-api"}
```

That's why the `--labels=app=color-api` mattered. Without it, `kubectl run` adds a `run=color-api` label instead, and the selector would use that. The [Service](../services/what-are-services.md) chapter covers Services properly; for now, one command made the app reachable.

## 3. Change

Each kind of change has its own verb:

```bash
kubectl label pod color-api tier=frontend           # add a label
kubectl annotate pod color-api owner=your-name      # add an annotation
kubectl set image pod/color-api color-api=<YOUR_DOCKERHUB_USER>/color-api:1.1.0
kubectl get pod color-api --show-labels             # RESTARTS 1, labels app=color-api,tier=frontend
```

Refresh the browser and you'll see the 1.1.0 page, served through the same Service. `kubectl edit pod color-api` is the catch-all: it opens the live object in your editor, and saving sends your changes. (That's what k9s does when you press `e`.)

Some changes have no command, because the object can't do them:

```bash
kubectl scale pod color-api --replicas=2
```

```
Error from server (NotFound): the server could not find the requested resource
```

The message is confusing, but the cause is simple: a Pod has no replica count. Only controllers like a [Deployment](../replicasets-deployments/introduction-to-deployments.md) can be scaled. And as you saw in [Working with Pods](../pods/working-with-pods.md#8-changing-a-pod), most of a Pod's spec, like its environment variables, can't be changed at all after it's created.

## 4. Where it falls short

Everything works. Now imagine a teammate asks for the same setup in their cluster, or yours is rebuilt tomorrow. What exactly do you run?

```bash
kubectl run color-api --image=<YOUR_DOCKERHUB_USER>/color-api:1.0.0 --port=8080 --labels=app=color-api
kubectl expose pod color-api --type=NodePort --port=80 --target-port=8080
kubectl label pod color-api tier=frontend
kubectl annotate pod color-api owner=your-name
kubectl set image pod/color-api color-api=<YOUR_DOCKERHUB_USER>/color-api:1.1.0
```

You have to reconstruct that from memory or shell history, in the right order, with every flag right. These are the shortcomings from [Object Management](object-management.md), now concrete:

- **No record.** The cluster stores the **result**, not the commands. `kubectl get` shows a Pod running 1.1.0 with two labels; it doesn't show that it started as 1.0.0, or who changed it.
- **Nothing to reuse.** To recreate it, or make a similar `color-api-red`, you retype everything.
- **No review.** Each command takes effect the moment you press Enter. Nobody gets to check it first.

One fix is to write down what each **create** command made, as manifests, noting which command each one stands for:

```yaml
# Equivalent to:
#   kubectl run color-api --image=<YOUR_DOCKERHUB_USER>/color-api:1.0.0 --port=8080 --labels=app=color-api
apiVersion: v1
kind: Pod
metadata:
  name: color-api
  labels:
    app: color-api
spec:
  containers:
    - name: color-api
      image: <YOUR_DOCKERHUB_USER>/color-api:1.0.0
      ports:
        - containerPort: 8080
```

```yaml
# Equivalent to:
#   kubectl expose pod color-api --type=NodePort --port=80 --target-port=8080
apiVersion: v1
kind: Service
metadata:
  name: color-api
  labels:
    app: color-api
spec:
  type: NodePort
  selector:
    app: color-api
  ports:
    - port: 80
      targetPort: 8080
      protocol: TCP
```

Notice what these files *don't* have: the `tier=frontend` label, the `owner` annotation, the `1.1.0` image. Those came from later commands. Keep changing the live objects with commands, and you also have to remember to make every change in the files, or the files quietly stop describing what's running. That gap is what the file-based approaches close: change the file first, then send it to the cluster.

These two files are in the repo, without the comments, as [`color-api-pod.yaml`](../../manifests/object-management/color-api-pod.yaml) and [`color-api-svc.yaml`](../../manifests/object-management/color-api-svc.yaml), and the next chapters use them. Writing them by hand is tedious and easy to get wrong, though. [Generating Manifests](generating-manifests.md) shows how to let kubectl write them for you.

## 5. Delete

Delete by name, or by label, which catches both objects at once:

```bash
kubectl delete pod color-api                     # one object, by name
kubectl delete pod,svc -l app=color-api          # every Pod and Service labeled app=color-api
```

```
pod "color-api" deleted
service "color-api" deleted
```

Use the label form now to clean up. Note how the shared `app=color-api` label pays off again: one command removes everything that belongs to the app.

## Best practices

- **Use imperative commands for exploring**: trying an image, debugging, a throwaway Pod. They're the fastest way to see something work.
- **Label everything you create**, even with commands. Labels are how a Service finds its Pods, and how you find and delete everything an app owns.
- **If you'll need it again, write it down as a manifest.** The cluster remembers what exists, not how it got there.
- **Don't mix approaches on an object you keep.** Once an object is managed from a file, change the file, not the live object. See [From Imperative to Declarative](imperative-to-declarative.md).

---

[← Manifest Files](manifest-files.md) · [↑ Contents](../../README.md) · [Generating Manifests →](generating-manifests.md)
