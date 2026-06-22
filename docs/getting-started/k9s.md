# Inspect with k9s

> A terminal UI that turns `kubectl get/describe/logs` into a live, navigable dashboard.

---

Once you have more than a couple of objects, running `kubectl get … -w` over and over gets tedious. **[k9s](https://k9scli.io)** is a terminal dashboard that shows your cluster live and lets you describe, log, shell into, and delete things with a keypress. We use it throughout the guide to *watch* Kubernetes reconcile — seeing self-healing happen beats reading about it.

> **k9s complements kubectl — it doesn't replace it.** Your core skill is still reading/writing YAML and running `kubectl`. Treat k9s as the X-ray you reach for to *observe* the cluster.

### Install

```bash
# Linux (or use your package manager: brew install k9s, etc.)
curl -sS https://webi.sh/k9s | sh

k9s        # launch — it uses your current kubeconfig/context automatically
```

> ⚠️ **Piping a remote script into `sh` is convenient but skips inspection.** Prefer your package manager (`brew install k9s`, `apt`/`dnf` if packaged) where available, or grab a binary directly from k9s' [GitHub releases](https://github.com/derailed/k9s/releases) if you'd rather not run an installer script unread.

### Getting around

k9s is keyboard-driven. The essentials:

| Key | Action |
|-----|--------|
| `:pods` ⏎ | jump to a resource (`:deploy`, `:svc`, `:ns`, …) |
| `0` | show **all namespaces** (or pick one with `:ns`) |
| `d` | **describe** the highlighted object |
| `l` | view **logs** (of a Pod) |
| `s` | open a **shell** in a container |
| `Ctrl-D` | **delete** the highlighted object |
| `/` | filter the current list |
| `Esc` | back out, `:q` to quit |

### Try it

Launch `k9s`, press `:pods` ⏎ then `0`. You'll see every Pod in the cluster — including the [control plane running in `kube-system`](setup-kubeadm.md). Highlight one and press `d` to describe it, `l` for its logs. This is the same information as `kubectl describe`/`logs`, just faster to move around.

You'll come back to k9s in nearly every chapter — e.g. watching a [Deployment](../core-objects/deployment.md) heal a deleted Pod, or a [rolling update](../running-and-operating/rolling-updates.md) swap Pods one by one.

---

[← Anatomy of a Manifest](manifest-anatomy.md) · [↑ Contents](../../README.md) · [Pod →](../core-objects/pod.md)
