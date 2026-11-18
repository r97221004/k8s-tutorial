# Inspect with k9s

> A terminal UI that turns `kubectl get/describe/logs` into a live, navigable dashboard.

---

Once you have more than a couple of objects, jumping between `kubectl get`, `describe`, and `logs` over and over gets tedious. **[k9s](https://k9scli.io)** is a terminal dashboard that shows your cluster live and lets you describe, log, shell into, and delete things with a keypress. We use it throughout the guide to *watch* Kubernetes reconcile — seeing self-healing happen beats reading about it.

> **k9s complements kubectl — it doesn't replace it.** Your core skill is still reading/writing YAML and running `kubectl`. Reach for k9s mainly to *observe* the cluster. It can change things too, though; see the warning below.

### Launch it

k9s was installed on the node in [Before You Start](before-you-start.md#1-build-the-cluster), by the `install_kube_tools.yml` playbook. (Skipped it? Go back and run that one command.) On the node, start it:

```bash
k9s        # uses your current kubeconfig/context automatically
```

### Getting around

k9s is keyboard-driven. The essentials:

| Key | Action |
|-----|--------|
| `:pods` ⏎ | jump to a resource (`:deploy`, `:svc`, `:ns`, …) |
| `0` | show **all namespaces** (or pick one with `:ns`) |
| `d` | **describe** the highlighted object |
| `y` | view the object's **YAML** |
| `l` | view **logs** (of a Pod) |
| `s` | open a **shell** in a container |
| `r` | **restart** a Deployment, StatefulSet, or DaemonSet (same as `kubectl rollout restart`) |
| `Ctrl-D` | **delete** the highlighted object |
| `/` | filter the current list |
| `?` | show **every key** available on the current screen |
| `Esc` | back out, `:q` to quit |

You don't need to memorize this table. Press `?` on any screen and k9s lists what you can do there.

> ⚠️ **k9s acts on the real cluster.** `Ctrl-D` really deletes and `r` really restarts. k9s asks you to confirm first, but it's still easy to hit the wrong row. When you only want to look around, start it with `k9s --readonly`, which turns off every action that changes the cluster.

### Try it

In k9s, press `:pods` ⏎ then `0`. You'll see every Pod in the cluster — including the [control plane running in `kube-system`](../getting-started/control-plane.md). Move the highlight with the arrow keys (or `j`/`k`), then press `d` on a Pod to describe it, or `l` for its logs. This is the same information as `kubectl describe`/`logs`, just faster to move around.

You'll come back to k9s in nearly every chapter — e.g. watching a [Deployment](../core-objects/deployment.md) heal a deleted Pod, or a [rolling update](../running-and-operating/rolling-updates.md) swap Pods one by one.

---

[← Before You Start](before-you-start.md) · [↑ Contents](../../README.md) · [Pod →](../core-objects/pod.md)
