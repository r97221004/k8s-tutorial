# Kubernetes in Practice

<p align="center">
  <img src="docs/images/kubernetes-logo.svg" width="120" alt="Kubernetes logo" />
</p>

> _Learn Kubernetes by building a real cluster with `kubeadm`, one component at a time._

![Kubernetes](https://img.shields.io/badge/Kubernetes-1.30%2B-326CE5?logo=kubernetes&logoColor=white)
![Cluster](https://img.shields.io/badge/Cluster-kubeadm-0F766E)
![Inspect](https://img.shields.io/badge/Inspect-k9s-5D3FD3)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> **Problem**: Running containers by hand — `docker run` on one machine, restarting them when they crash, wiring up networking, scaling by copy-paste — falls apart the moment you have more than one container or more than one machine.
>
> **Solution**: Kubernetes lets you *declare* the desired state of your apps in YAML and continuously reconciles reality to match it — self-healing, scaling, rolling out new versions, and routing traffic, all repeatably.

Many tutorials start you off on minikube or kind — quick to set up, but the components are mostly hidden. Here you stand up a real, upstream Kubernetes cluster with **[kubeadm](https://kubernetes.io/docs/reference/setup-tools/kubeadm/)** instead, learn it by taking every component apart — `kube-apiserver`, `etcd`, `kubelet`, the CNI — and then put it to work, watching the cluster live in **[k9s](https://k9scli.io)**.

Every concept is paired with a runnable `kubectl apply` example — configure apps with ConfigMaps/Secrets, persist data on a PVC, expose them through a Service + Ingress, then roll out an update and tear it back down.

> **No prior Kubernetes experience assumed.** New to k8s? Read top to bottom. Already know the basics? Jump straight to the [Table of Contents](#table-of-contents).

> **"kubeadm" is not a different kind of Kubernetes.** It's the official *installer* that assembles upstream components the standard way — so a kubeadm cluster **is** plain, vanilla Kubernetes (the same thing the official docs and the CKA exam describe). k3s, by contrast, is a *repackaged lightweight distro* with batteries-included defaults baked in. Analogy: Kubernetes is the Linux kernel, kubeadm is a clean standard install, k3s is a pre-loaded distro like Ubuntu. More in [Set Up a Cluster (kubeadm)](docs/cluster-setup/setup-kubeadm.md).

## What You'll Learn

By the end you'll be able to:

- **Read the architecture** and say what each component does — control plane vs. data plane (see [Architecture Overview](docs/getting-started/architecture.md)).
- **Deploy and expose apps** with the core objects: Pods, Deployments, Services.
- **Separate config from images** with ConfigMaps and Secrets, and **persist data** with PersistentVolumeClaims.
- **Keep apps healthy and current** — health probes, resource limits, scaling, and rolling updates with rollback.
- **Control where Pods run and who can touch them** — taints/tolerations for placement, RBAC and NetworkPolicy for access control.
- **Route traffic in** with an Ingress, and **debug** confidently when things break.

Every section is hands-on: a manifest you `kubectl apply`, then watch take effect.

## Prerequisites

A Linux host (or WSL2 / a VM), `kubectl` installed, and basic shell + container familiarity.

For the kubeadm path, use a fresh Linux machine where you can run `sudo` (Ubuntu is the assumed happy path in the companion Ansible role). A single-node lab is comfortable with **2 vCPU, 4 GB RAM, and 20 GB disk**. Start from a clean host if you can; old container runtimes, stale kubeconfigs, or half-removed clusters make first-time Kubernetes debugging unnecessarily noisy.

**You'll need a cluster to follow along. Two ways to get one:**

1. **The real lesson — build it with kubeadm.** Provision the single-node cluster with the companion **[Ansible tutorial → kubeadm Role](https://github.com/r97221004/ansible-tutorial/blob/master/docs/roles/kubeadm.md)**, then read [Set Up a Cluster (kubeadm)](docs/cluster-setup/setup-kubeadm.md) to understand every component you just stood up. This is the path the guide is built around.
2. **Fast lane — just want to run the examples?** Spin up a real single-node cluster with k3s in one line and circle back to kubeadm later:

   ```bash
   curl -sfL https://get.k3s.io | sh -s - --write-kubeconfig-mode 644
   export KUBECONFIG=/etc/rancher/k3s/k3s.yaml   # so plain kubectl just works
   ```

   This is convenient for a throwaway lab, but it still runs a remote install script as root. For anything beyond a local practice VM, inspect the script first or use your platform's normal package/install process.

   k3s is great for running the manifests quickly, but its defaults are not identical to bare kubeadm: it may include built-in storage, ingress, and load-balancer helpers that vanilla kubeadm does not. When this guide calls that out, trust the kubeadm behavior as the main lesson.

Before starting Part 3, verify your cluster is reachable and healthy:

```bash
kubectl get nodes                 # one node, STATUS Ready
kubectl get pods -n kube-system   # CoreDNS, kube-proxy, flannel, and control-plane Pods Running
```

If those commands fail, finish [Set Up a Cluster (kubeadm)](docs/cluster-setup/setup-kubeadm.md) or fix your kubeconfig before continuing.

## Table of Contents

**Part 1 — Getting Started**

- [**Why Use Kubernetes?**](docs/getting-started/why-kubernetes.md) — the problems of running containers by hand, and when you don't need k8s.
- [**What is Kubernetes?**](docs/getting-started/what-is-kubernetes.md) — declarative vs. imperative; the one idea behind everything.
- [**Architecture Overview**](docs/getting-started/architecture.md) — the big picture, and why a kubeadm cluster is vanilla k8s.
- [**The Control Plane**](docs/getting-started/control-plane.md) — apiserver, etcd, scheduler, controller-manager: the brain.
- [**The Data Plane**](docs/getting-started/data-plane.md) — kubelet, containerd, kube-proxy, and add-ons: the muscle.

**Part 2 — Cluster Setup**

- [**Set Up a Cluster (kubeadm)**](docs/cluster-setup/setup-kubeadm.md) — build the cluster, then understand each piece the installer wires up.
- [**kubectl 101**](docs/cluster-setup/kubectl-101.md) — the everyday commands you'll live in.
- [**Anatomy of a Manifest**](docs/cluster-setup/manifest-anatomy.md) — `apiVersion`/`kind`/`metadata`/`spec`, once and for all.
- [**Inspect with k9s**](docs/cluster-setup/k9s.md) — a live terminal dashboard for your cluster.

**Part 3 — Core Objects**

- [**Pod**](docs/core-objects/pod.md) — the smallest thing Kubernetes runs.
- [**Labels & Selectors**](docs/core-objects/labels-selectors.md) — the glue wiring objects together.
- [**Deployment**](docs/core-objects/deployment.md) — keep N replicas alive and roll out updates.
- [**ReplicaSet**](docs/core-objects/replicaset.md) — what actually maintains the replica count.
- [**Scheduling, Taints & Tolerations**](docs/core-objects/scheduling.md) — control where Pods can land.
- [**DaemonSet (intro)**](docs/core-objects/daemonset.md) — one Pod per node.
- [**Job & CronJob**](docs/core-objects/job-cronjob.md) — batch and scheduled work.
- [**Service**](docs/core-objects/service.md) — a stable address + load balancer for Pods.
- [**Namespace**](docs/core-objects/namespace.md) — partition the cluster.

**Part 4 — Configuration & Data**

- [**ConfigMap**](docs/config-and-data/configmap.md) — keep config out of the image.
- [**Secret**](docs/config-and-data/secret.md) — sensitive values.
- [**Environment Variables & Mounts**](docs/config-and-data/env-and-mounts.md) — how config reaches the container.
- [**Volumes & PersistentVolumes**](docs/config-and-data/volumes.md) — storage that survives restarts.
- [**StatefulSet (intro)**](docs/config-and-data/statefulset.md) — stable identity + storage for stateful apps.

**Part 5 — Running & Operating**

- [**Health Checks**](docs/running-and-operating/health-checks.md) — liveness / readiness / startup probes.
- [**Resource Requests & Limits**](docs/running-and-operating/resources.md) — CPU/memory scheduling and caps.
- [**Scaling**](docs/running-and-operating/scaling.md) — manual and autoscaling.
- [**Rolling Update & Rollback**](docs/running-and-operating/rolling-updates.md) — zero-downtime releases, instant undo.
- [**Graceful Shutdown & Disruptions**](docs/running-and-operating/graceful-shutdown.md) — SIGTERM, preStop, drains, and PDBs.
- [**Debugging**](docs/running-and-operating/debugging.md) — the commands that explain a broken Pod.
- [**Security Basics**](docs/running-and-operating/security-basics.md) — ServiceAccounts, RBAC, Secrets, and NetworkPolicy.

**Part 6 — Networking & Access**

- [**Service Discovery & DNS**](docs/networking/dns.md) — find Pods by name.
- [**Ingress**](docs/networking/ingress.md) — route external traffic by host/path.
