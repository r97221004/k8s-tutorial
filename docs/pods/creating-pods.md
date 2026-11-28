# Creating Pods

> Check that the cluster is ready, create a Pod with a single command, and confirm it's really running.

---

You've already run `kubectl run` a few times in this part. This chapter slows down and walks through the everyday routine properly: check the cluster, create the Pod, confirm it came up, and recognize what it looks like when it doesn't.

If you have [k9s](../cluster-setup/k9s.md), keep it open on `:pods` in a second terminal. Every Pod in this chapter shows up there as you create it.

## 1. Check the cluster is ready

Before creating anything, make sure the cluster is there and healthy. Three commands cover it:

```bash
kubectl cluster-info              # where the control plane is: "Kubernetes control plane is running at https://…:6443"
kubectl get nodes                 # your node, STATUS Ready
kubectl get pods -n kube-system   # the cluster's own Pods: every one Running
```

Then check **where** your Pods will land. `kubectl` creates them in your current namespace:

```bash
kubectl config get-contexts       # the * row is your current context; its NAMESPACE column is where Pods go (blank means default)
```

If any of these fails, go back to [Before You Start](../cluster-setup/before-you-start.md#4-verify) before going further. A Pod can't come up on a cluster that isn't healthy.

## 2. Create a Pod

One command creates a Pod:

```bash
kubectl run web --image=nginx:1.27
```

```
pod/web created
```

`pod/web created` only means the API server **accepted** the request and stored it. It doesn't mean the Pod is running yet. From here, the scheduler picks a node, and that node's kubelet pulls the image and starts the container: the Pending phase from [The Pod Lifecycle](pod-lifecycle.md).

### The flags you'll use

| Flag | What it does | Example |
|---|---|---|
| `--image` | The container image to run. Required. | `--image=nginx:1.27` |
| `--port` | Records which port the container listens on. | `--port=80` |
| `--env` | Sets an environment variable in the container. Repeat it for more. | `--env=GREETING=hello` |
| `--labels` | Attaches labels to the Pod, so you can find it later. | `--labels=app=hello,tier=demo` |
| `--restart` | The restart policy: `Always` (default), `OnFailure`, or `Never`. | `--restart=Never` |
| `-- <args>` | Everything after `--` replaces the image's default arguments (its `CMD`). Add `--command` to replace its entrypoint too. | `-- sh -c 'sleep 3600'` |

Put a few of them together:

```bash
kubectl run hello --image=busybox:1.36 \
  --labels=app=hello,tier=demo \
  --env=GREETING=hello \
  -- sh -c 'echo "$GREETING from $HOSTNAME"; sleep 3600'
```

The single quotes matter: they stop *your* shell from expanding `$GREETING`, so it's expanded inside the container instead, where the variable actually exists.

**Naming rules:** a Pod name must be unique in its namespace, and may only contain lowercase letters, digits, `-`, and `.`, starting and ending with a letter or digit. `web`, `hello`, and `api-v2` are fine. `Web` and `my_pod` are rejected.

## 3. Confirm it's running

Wait until the Pod is ready instead of guessing:

```bash
kubectl wait --for=condition=Ready pod/web pod/hello --timeout=60s
```

Then look at it from a few angles:

```bash
kubectl get pods                  # the quick view
kubectl get pods -o wide          # + the Pod's IP and the node it runs on
kubectl get pods --show-labels    # + its labels
kubectl get pods -l app=hello     # only Pods carrying a given label
```

In the quick view, read the columns like this:

| Column | Meaning |
|---|---|
| `READY` | Containers ready / containers in the Pod. `1/1` is what you want. |
| `STATUS` | A summary of its state. Not quite the phase; see [STATUS is not the phase](pod-lifecycle.md#status-is-not-the-phase). |
| `RESTARTS` | How many times a container has been restarted. It should stay `0`. |
| `AGE` | How long ago the Pod was created. |

To confirm the `hello` Pod picked up its environment variable, read what it printed:

```bash
kubectl logs hello                # hello from hello
```

### Read the Events

For the full picture, use `describe`:

```bash
kubectl describe pod web
```

It's long, but three parts matter most:

- **Node** and **IP** near the top: where the Pod runs, and its address.
- **Containers → State**: `Running`, with a `Started` time.
- **Events** at the bottom: the story of how the Pod came up, step by step.

For a healthy Pod, the Events read like this, in order:

| Reason | From | What happened |
|---|---|---|
| `Scheduled` | default-scheduler | The scheduler assigned the Pod to your node. |
| `Pulling` | kubelet | The kubelet started downloading the image. |
| `Pulled` | kubelet | The image is on the node. |
| `Created` | kubelet | The container was created. |
| `Started` | kubelet | The container is running. |

If the image was already on the node, `Pulling` is skipped and `Pulled` says the image is already present. When a Pod doesn't come up, the Events are where you'll find out which step it got stuck on.

## 4. When creation goes wrong

Three mistakes you'll make sooner or later, and how each one shows up.

**A typo in the image.** There's no `nginx:1.277`:

```bash
kubectl run oops --image=nginx:1.277
kubectl get pod oops              # STATUS: ErrImagePull, then ImagePullBackOff
kubectl describe pod oops         # Events: a Failed event saying the image can't be pulled
```

The Pod stays in Pending, and the kubelet keeps retrying with growing delays. Check the image name and tag, then delete the Pod and create it again.

**A name that's already taken.**

```bash
kubectl run web --image=nginx:1.27
```

```
Error from server (AlreadyExists): pods "web" already exists
```

Nothing changes: the existing `web` Pod is left as it was. Pick another name, or delete the old Pod first.

**A Pod stuck in Pending with no image errors.** `describe` shows a `FailedScheduling` event: the scheduler found no node that can take the Pod. On this single-node lab, the usual cause is the control-plane taint; see [Let the one node run your Pods](../cluster-setup/before-you-start.md#3-let-the-one-node-run-your-pods).

## Clean up

```bash
kubectl delete pod web hello oops
```

---

[← The Pod Lifecycle](pod-lifecycle.md) · [↑ Contents](../../README.md) · [Working with Pods →](working-with-pods.md)
