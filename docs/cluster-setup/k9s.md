# Inspect with k9s

> A terminal UI that turns `kubectl get/describe/logs` into a live, navigable dashboard.

---

Once you have more than a couple of objects, running `kubectl get … -w` over and over gets tedious. **[k9s](https://k9scli.io)** is a terminal dashboard that shows your cluster live and lets you describe, log, shell into, and delete things with a keypress. We use it throughout the guide to *watch* Kubernetes reconcile — seeing self-healing happen beats reading about it.

> **k9s complements kubectl — it doesn't replace it.** Your core skill is still reading/writing YAML and running `kubectl`. Treat k9s as the X-ray you reach for to *observe* the cluster.

### Install

Install k9s **on the node**, next to `kubectl`, since that's where you work (see [Before You Start](before-you-start.md#2-work-on-the-node)).

The easiest way is the Ansible tutorial's **[kube_tools role](https://github.com/r97221004/ansible-tutorial/blob/master/docs/roles/kube-tools.md)**. Run its `install_kube_tools.yml` playbook from your laptop, the same way you ran the kubeadm one, and it drops the k9s binary into `/usr/local/bin` on the node.

To install it by hand instead, SSH into the node and grab the binary from k9s' [GitHub releases](https://github.com/derailed/k9s/releases):

```bash
curl -fsSLO https://github.com/derailed/k9s/releases/latest/download/k9s_Linux_amd64.tar.gz
sudo tar -xzf k9s_Linux_amd64.tar.gz -C /usr/local/bin k9s
k9s version
```

(On an ARM VM, use `k9s_Linux_arm64.tar.gz` instead.)

Then launch it:

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
| `l` | view **logs** (of a Pod) |
| `s` | open a **shell** in a container |
| `Ctrl-D` | **delete** the highlighted object |
| `/` | filter the current list |
| `Esc` | back out, `:q` to quit |

### Try it

Launch `k9s`, press `:pods` ⏎ then `0`. You'll see every Pod in the cluster — including the [control plane running in `kube-system`](../getting-started/control-plane.md). Highlight one and press `d` to describe it, `l` for its logs. This is the same information as `kubectl describe`/`logs`, just faster to move around.

You'll come back to k9s in nearly every chapter — e.g. watching a [Deployment](../core-objects/deployment.md) heal a deleted Pod, or a [rolling update](../running-and-operating/rolling-updates.md) swap Pods one by one.

---

[← Before You Start](before-you-start.md) · [↑ Contents](../../README.md) · [Pod →](../core-objects/pod.md)
