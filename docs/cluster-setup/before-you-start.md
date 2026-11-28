# Before You Start

> Everything you need in place before [Pods](../pods/what-is-a-pod.md): a kubeadm cluster, a shell on its node, and this repository.

---

You won't install Kubernetes by hand. The companion Ansible tutorial automates the install, and this page walks you through running it, then checks the cluster is ready. Work through it once, and every hands-on example from [Pod](../pods/what-is-a-pod.md) onward will run as written.

### 1. Build the cluster

You build the cluster with the companion **[Ansible tutorial](https://github.com/r97221004/ansible-tutorial)**. Its kubeadm role prepares the OS, installs containerd and `kubelet`/`kubeadm`/`kubectl`, runs `kubeadm init`, and installs flannel. Every Kubernetes component it sets up is explained in [The Control Plane](../getting-started/control-plane.md) and [The Data Plane](../getting-started/data-plane.md).

First, make sure your laptop and VM meet the Ansible tutorial's [prerequisites](https://github.com/r97221004/ansible-tutorial#prerequisites): Ansible 2.14+ on your laptop, your SSH public key copied to the VM, and `sudo` rights on the VM.

Then, on your laptop:

```bash
git clone https://github.com/r97221004/ansible-tutorial.git
cd ansible-tutorial
```

Point the inventory at your VM by editing `ansible/inventory/azure.ini`. Despite the file name, any Linux VM you can SSH into works, not just Azure:

```ini
[control]
azure-vm ansible_host=<YOUR_VM_IP> ansible_user=<YOUR_USER> ansible_connection=ssh
```

Check that Ansible can reach the VM, then run the kubeadm playbook:

```bash
ansible control -i ansible/inventory/azure.ini -m ping     # expect "ping": "pong"
ansible-playbook -i ansible/inventory/azure.ini ansible/playbooks/install_kubeadm.yml
```

The first run takes several minutes, because `kubeadm init` pulls the control-plane images. When it finishes, the play prints the node's status, followed by a `PLAY RECAP` line with `failed=0`. For what each task does, see the [kubeadm role walkthrough](https://github.com/r97221004/ansible-tutorial/blob/master/docs/roles/kubeadm.md).

> 📌 **The role installs Kubernetes 1.30** and holds the packages at that version, so an `apt upgrade` can't move them. All output in this guide assumes 1.30.

**Then install k9s (optional, but recommended).** k9s is the terminal dashboard most chapters use to *watch* the cluster react. While you're still in this directory, the [kube_tools role](https://github.com/r97221004/ansible-tutorial/blob/master/docs/roles/kube-tools.md) puts it on the node, along with Helm:

```bash
ansible-playbook -i ansible/inventory/azure.ini ansible/playbooks/install_kube_tools.yml
```

Both playbooks use `sudo` on the VM. Cloud VMs such as Azure usually allow it without a password; if yours asks for one, add `--ask-become-pass` to each `ansible-playbook` command. Both are also safe to re-run: the kubeadm playbook skips `kubeadm init` on a cluster that already exists.

### 2. Work on the node

Ansible runs on your own machine and configures the node over SSH, so when the playbook finishes, the cluster lives **on the node, not on your machine**. Typing `kubectl get nodes` on your laptop fails: with `command not found` if kubectl isn't installed there, or with `The connection to the server localhost:8080 was refused` if it is, since your laptop has no kubeconfig for this cluster.

SSH into the node, as the same user Ansible connected with (the `ansible_user` in your inventory), and run every command in this guide from there:

```bash
ssh <YOUR_USER>@<YOUR_VM_IP>
kubectl get nodes      # works right away: no sudo, no extra setup
```

That works because the role copied the cluster's admin credentials, `/etc/kubernetes/admin.conf`, to `~/.kube/config` for that user, which is where `kubectl` looks by default (see [The kubectl CLI](../getting-started/kubectl-cli.md)). Working on the node also matters later: a few chapters inspect the node directly, with commands like `sudo ls /etc/kubernetes/manifests` or `sudo systemctl stop kubelet`.

If `kubectl` still reports `connection refused` or `the server doesn't have a resource type`, check two things: that you're on the node, and that you're the user who owns `~/.kube/config`.

### 3. Let the one node run your Pods

kubeadm taints the control-plane node with `node-role.kubernetes.io/control-plane:NoSchedule`, so that ordinary workloads stay off it. That makes sense when worker nodes exist. On a single-node lab, though, it means none of your Pods could ever be scheduled: they would all sit at `Pending`. The Ansible role leaves the taint in place, so remove it yourself:

```bash
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

The trailing `-` means "remove". The taint comes back whenever the cluster is rebuilt, so run this again after any fresh `install_kubeadm.yml` run on a reset VM. [Scheduling, Taints & Tolerations](../core-objects/scheduling.md) explains the mechanism.

### 4. Verify

```bash
kubectl get nodes                      # one node, STATUS Ready
kubectl get pods -A                    # apiserver, etcd, scheduler, controller-manager, coredns, flannel, kube-proxy: all Running
kubectl describe nodes | grep Taints   # Taints: <none>
```

If the node is `NotReady`, the CNI usually isn't up yet. Give flannel a minute, then look for its Pod with `kubectl get pods -A | grep flannel`.

### 5. This repository

Every `▶ Runnable manifest` path in this guide is relative to the repo root. Clone the repo on the node and run commands from there:

```bash
git clone https://github.com/r97221004/k8s-tutorial.git
cd k8s-tutorial
```

### 6. What a bare kubeadm cluster does *not* have

kubeadm installs only the core components. A few things later chapters rely on are deliberately left out:

- **No default StorageClass.** PVCs stay `Pending` until you install one. local-path-provisioner is installed in [Dynamic Provisioning](../volumes/dynamic-provisioning.md).
- **No LoadBalancer provider.** `type: LoadBalancer` Services sit at `<pending>`. Use NodePort or MetalLB; see [Service](../services/what-are-services.md).
- **No Ingress controller.** ingress-nginx is installed in [Ingress](../networking/ingress.md).

Don't install these now. Each chapter adds what it needs, when it needs it.

---

[← The kubectl CLI](../getting-started/kubectl-cli.md) · [↑ Contents](../../README.md) · [Inspect with k9s →](k9s.md)
