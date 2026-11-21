# Working with Pods

> Inspect a running Pod, find out why you can't reach it yet, run commands inside it, and read its logs.

---

[Creating Pods](creating-pods.md) got a Pod to `Running`. This chapter is what comes next: look inside it, try to reach it, and read what it prints. It's also where you put [The kubectl CLI](../getting-started/kubectl-cli.md) to work for real.

> Getting `connection refused` or `the server doesn't have a resource type`? Your kubeconfig probably isn't in place yet. See [Work on the node](../cluster-setup/before-you-start.md#2-work-on-the-node).

## Before you start

Creating Pods cleaned up after itself, so start a fresh Pod to work with:

```bash
kubectl run web --image=nginx:1.27 --port=80
kubectl wait --for=condition=Ready pod/web --timeout=60s
```

## 1. See the API calls

Start by proving that `kubectl` really is just an API client. Raise the verbosity and it prints every HTTP request it makes:

```bash
kubectl get pods -v=6
```

```
... GET https://<apiserver>:6443/api/v1/namespaces/default/pods?limit=500 200 OK in 12 milliseconds
```

That's the whole trick: a `GET` to the apiserver's REST API, authenticated with your kubeconfig. Every command in this chapter is a request like this one.

## 2. Find and filter Pods

```bash
kubectl get pods -o wide         # extra columns: node, Pod IP
kubectl get pod web -o yaml      # the object's full manifest (incl. status)
kubectl get pods -A              # across ALL namespaces (-A = --all-namespaces)
kubectl get pods -n kube-system  # a specific namespace
kubectl get pods -l run=web      # filter by label (kubectl run added run=web; see Labels & Selectors)
kubectl get pods -w              # watch: stream changes live (Ctrl+C to stop)
```

Commands run in your current namespace (`default` unless you changed it). To stop typing `-n`, change the default:

```bash
kubectl config set-context --current --namespace=my-namespace
```

> 💡 **Discover any field** with `kubectl explain`, e.g. `kubectl explain pod.spec.containers`. No need to memorize the API.

## 3. Read `describe` closely

[Creating Pods](creating-pods.md#read-the-events) pointed out the three parts of `describe` that matter most: Node and IP, the container's State, and the Events. Here are the fields worth reading, with the output trimmed (your names, IPs, and times will differ):

```bash
kubectl describe pod web
```

```text
Name:         web
Namespace:    default
Node:         node-1/192.168.56.10        ← which node it runs on (and that node's IP)
Labels:       run=web                     ← kubectl run adds this label for you
Status:       Running                     ← the Pod's phase
IP:           10.244.0.5                  ← the Pod's own IP
Containers:
  web:
    Image:          nginx:1.27            ← the image you asked for
    Image ID:       docker.io/library/nginx@sha256:…   ← the exact image that's running
    Port:           80/TCP
    State:          Running               ← Waiting / Running / Terminated
      Started:      ...
    Ready:          True                  ← is it accepting traffic?
    Restart Count:  0                     ← > 0 means it exited and was restarted
Events:
  Type    Reason     Age   From               Message
  Normal  Scheduled  30s   default-scheduler  Successfully assigned default/web to node-1
  Normal  Pulled     29s   kubelet            Container image "nginx:1.27" already present on machine
  Normal  Created    29s   kubelet            Created container web
  Normal  Started    29s   kubelet            Started container web
```

- **Events** (at the bottom) is the most useful part. It's the step-by-step story of how the Pod came up, and when something fails, the reason shows up here.
- **State** and **Restart Count** tell you whether the container is healthy *right now*, and whether it has died before. A climbing Restart Count is how [CrashLoopBackOff](pod-lifecycle.md#crashloopbackoff) starts.
- **Image** vs **Image ID**: `Image` is the tag you asked for, and a tag can be moved to point at a different build. `Image ID` is the content digest of what actually runs. If you pushed a new build under the same tag and the app still behaves the old way, compare the digest.

> **Events don't last.** The cluster keeps them for about an hour by default. On an older Pod, the Events section may say `<none>`. That doesn't mean nothing happened, only that the record expired.

## 4. Pod IP & name: why you can't connect (yet)

Every Pod gets a name (`web`) and its own IP:

```bash
kubectl get pods -o wide
```

```text
NAME   READY   STATUS    RESTARTS   AGE   IP           NODE     ...
web    1/1     Running   0          2m    10.244.0.5   node-1   ...
```

So the obvious next step is to `curl` it. Try four ways, replacing `10.244.0.5` with your Pod's IP:

```bash
# 1. On the node, by IP → works, prints the nginx welcome page
curl http://10.244.0.5

# 2. On the node, by name → fails: "Could not resolve host: web"
curl http://web

# 3. From another Pod, by name → fails: "bad address 'web'"
kubectl run tmp --rm -it --image=busybox:1.36 --restart=Never -- wget -qO- http://web

# 4. On your own laptop (not the node), by IP → hangs, then times out
curl --max-time 5 http://10.244.0.5
```

Only the first one works. Here's why:

| Attempt | Result | Why |
|---|---|---|
| **By IP, on the node** | ✓ works | The Pod IP comes from the Pod network that flannel builds. The node is part of that network: flannel set up routes on it, so the node (and every other Pod) can reach any Pod IP. |
| **By name, anywhere** | ✗ can't resolve | A Pod's name is a name in the API, **not a DNS name**. Cluster DNS ([CoreDNS](../networking/dns.md)) creates names for **Services**. It doesn't create one from a Pod's name, so `web` resolves to nothing inside the cluster. On the node, `curl` doesn't even ask CoreDNS: the node uses its own DNS, which knows nothing about the cluster. |
| **By IP, from your laptop** | ✗ times out | The Pod network is private to the cluster. Your laptop isn't part of it and has no route to `10.244.x.x`. |

Even the one that works has a catch: **the IP isn't stable.** Delete the Pod and create it again, and it comes back with a **different** IP. Anything that hard-coded `10.244.0.5` breaks.

> **This is exactly the problem [Services](../core-objects/service.md) solve.** A Service gives a group of Pods a **stable name** (resolvable by DNS), a **stable IP**, and, with `type: NodePort`, a way in **from outside** the cluster. Until then, `kubectl port-forward` is the quick workaround.

## 5. `port-forward`: reach the Pod without its IP

```bash
kubectl port-forward pod/web 8080:80   # localhost:8080 on the node → port 80 in the Pod
```

It keeps running in the foreground. In a second terminal on the node:

```bash
curl http://localhost:8080
```

You didn't need the Pod's IP: `port-forward` finds the Pod by name and tunnels to it through the API server.

To open it in your **laptop's** browser, add an SSH tunnel from your laptop to that port on the node, then visit `http://localhost:8080`:

```bash
ssh -L 8080:localhost:8080 <YOUR_USER>@<YOUR_VM_IP>
```

Press Ctrl+C to stop `port-forward` when you're done. It's a debugging shortcut, not a way to expose an app. That's a Service's job.

## 6. `exec`: run commands inside the container

```bash
kubectl exec web -- nginx -v            # run a single command and get its output
kubectl exec web -- cat /etc/nginx/conf.d/default.conf
kubectl exec -it web -- bash            # open an interactive shell (type `exit` to leave)
```

- Everything after `--` is the command to run inside the container. `-it` gives you an interactive terminal, which you need for a shell.
- **No `bash`?** Many small images (alpine, busybox) only have `sh`, so use `-- sh` instead. Distroless images have no shell at all.
- Changes you make inside the container are lost when it restarts. Use `exec` to look around, not to fix things.

## 7. `logs`: what the container printed

```bash
kubectl logs web                   # everything written to stdout/stderr so far
kubectl logs web -f                # follow new lines as they arrive (Ctrl+C to stop)
kubectl logs web --tail=20         # only the last 20 lines
kubectl logs web --previous        # logs from the previous (crashed) run of the container
```

Leave `logs -f` running, and in a second terminal on the node, `curl` the Pod IP from [section 4](#4-pod-ip--name-why-you-cant-connect-yet). Each request shows up as an nginx access-log line.

- `logs` only shows what the app writes to **stdout/stderr**. If the app writes to a file inside the container, read that file with `exec` instead.
- `--previous` matters when **Restart Count** is above 0. After a restart, the current container's logs start fresh, so the error that caused the crash is in the previous run's logs.

### Pods with more than one container

`kubectl logs` and `kubectl exec` work on **one container at a time**. If a Pod has several containers (an app plus a [sidecar](what-is-a-pod.md)) and you don't say which one, kubectl picks a default and prints a note telling you which one it picked. Be explicit instead:

```bash
kubectl get pod <pod> -o jsonpath='{.spec.containers[*].name}'   # list the container names
kubectl logs <pod> -c <container-name>          # one specific container (long form: --container)
kubectl logs <pod> --all-containers             # every container in the Pod, one after another
kubectl logs <pod> --all-containers --prefix    # same, each line tagged with [pod/<pod>/<container>]
kubectl exec -it <pod> -c <container-name> -- sh
```

You'll use both in the [sidecar example in Volumes](../config-and-data/volumes.md). There, the `writer` container writes to a file instead of stdout, so `kubectl logs` shows nothing, and you read the file with `exec -c reader` instead.

## 8. Changing a Pod

A Pod's **spec** is mostly **immutable**. After a Pod is created, you can change only a few spec fields, such as a container's `image`. (Metadata like labels is different: you can change that any time, as the next chapter shows.)

Try adding an environment variable to the running Pod:

```bash
kubectl set env pod/web MODE=demo
```

```
... The Pod "web" is invalid: spec: Forbidden: pod updates may not change fields other than `spec.containers[*].image`, ...
```

The API server refuses: environment variables, ports, and commands are all fixed once the Pod exists. To change a bare Pod, delete it and create it again:

```bash
kubectl delete pod web
kubectl run web --image=nginx:1.27 --port=80 --env=MODE=demo
```

Doing that by hand gets old fast. A [Deployment](../core-objects/deployment.md) does the delete-and-replace for you, which is one reason you'll rarely create bare Pods once you get there.

## Clean up

```bash
kubectl delete pod web
kubectl get pods       # gone, and nothing brings it back
```

A bare Pod has no safety net: once it's deleted, nothing recreates it.

## Best practices

- **Read before you act.** When something's wrong, start with `describe` → Events, then `logs` (add `--previous` for restarts). Resist deleting the Pod before you've read the cause. See [Debugging](../running-and-operating/debugging.md).
- **Don't hard-code Pod IPs.** They change every time a Pod is recreated. Put a [Service](../core-objects/service.md) in front instead.
- **Use `exec` to inspect, not to fix.** Changes made inside a container disappear when it restarts.
- For fast, visual browsing of all this, use [k9s](../cluster-setup/k9s.md): `l` for logs, `d` for describe, `s` for a shell.

---

[← Creating Pods](creating-pods.md) · [↑ Contents](../../README.md) · [From Dockerfile to Pod →](from-dockerfile-to-pod.md)
