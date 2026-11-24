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

> **"kubeadm" is not a different kind of Kubernetes.** It's the official *installer* that assembles upstream components the standard way — so a kubeadm cluster **is** plain, vanilla Kubernetes (the same thing the official docs and the CKA exam describe). Analogy: Kubernetes is the Linux kernel, and kubeadm is a clean, standard install of it.

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

Two machines, plus basic shell and container familiarity:

- **A control machine** (your laptop) with Ansible and SSH. It runs the playbook that builds the cluster; see the Ansible tutorial's [Install Ansible](https://github.com/r97221004/ansible-tutorial/blob/master/docs/getting-started/install-ansible.md).
- **A target Linux VM** that becomes the single cluster node. You need SSH access and `sudo` on it. The companion Ansible tutorial uses **Ubuntu 22.04** (an Azure VM works well). A single-node lab is comfortable with **2 vCPU, 4 GB RAM, and 20 GB disk**. Start from a clean host if you can; old container runtimes, stale kubeconfigs, or half-removed clusters make first-time Kubernetes debugging unnecessarily noisy.

**You'll need a cluster to follow along.** Provision the single-node cluster with the companion **[Ansible tutorial → kubeadm Role](https://github.com/r97221004/ansible-tutorial/blob/master/docs/roles/kubeadm.md)**. You don't install `kubectl` or anything else Kubernetes-related on your laptop: the role installs it all on the VM, and you work from there over SSH. Then work through [Before You Start](docs/cluster-setup/before-you-start.md) before Part 3 to make sure the cluster is ready for the examples.

## Table of Contents

**Part 1 — Getting Started**

- [**Why Use Kubernetes?**](docs/getting-started/why-kubernetes.md) — the problems of running containers by hand, and when you don't need k8s.
- [**What is Kubernetes?**](docs/getting-started/what-is-kubernetes.md) — declarative vs. imperative; the one idea behind everything.
- [**Architecture Overview**](docs/getting-started/architecture.md) — the big picture, and why a kubeadm cluster is vanilla k8s.
- [**The Control Plane**](docs/getting-started/control-plane.md) — apiserver, etcd, scheduler, controller-manager: the brain.
- [**The Data Plane**](docs/getting-started/data-plane.md) — kubelet, containerd, kube-proxy, and add-ons: the muscle.
- [**The kubectl CLI**](docs/getting-started/kubectl-cli.md) — how kubectl talks to the cluster, and the three kinds of commands.

**Part 2 — Cluster Setup**

- [**Before You Start**](docs/cluster-setup/before-you-start.md) — a checklist: a kubeadm cluster, a shell on its node, this repo, and what a bare kubeadm cluster lacks.
- [**Inspect with k9s**](docs/cluster-setup/k9s.md) — a live terminal dashboard for your cluster.

**Part 3 — Pods**

- [**What Is a Pod**](docs/pods/what-is-a-pod.md) — the smallest thing Kubernetes runs.
- [**The Pod Lifecycle**](docs/pods/pod-lifecycle.md) — the phases a Pod moves through, and what restarts its containers.
- [**Creating Pods**](docs/pods/creating-pods.md) — check the cluster, create a Pod with `kubectl run`, and confirm it's running.
- [**Working with Pods**](docs/pods/working-with-pods.md) — inspect, debug, and clean up Pods with kubectl.
- [**From Dockerfile to Pod**](docs/pods/from-dockerfile-to-pod.md) — build your own image, push it to Docker Hub, and run it as a Pod.

**Part 4 — Object Management**

- [**Object Management**](docs/object-management/object-management.md) — three ways to create and change objects, and when to use each.
- [**Manifest Files**](docs/object-management/manifest-files.md) — the four fields every object has, and what the cluster adds.
- [**Imperative Commands**](docs/object-management/imperative-commands.md) — build and expose an app with commands alone, and see what that leaves out.
- [**Generating Manifests**](docs/object-management/generating-manifests.md) — let kubectl write the YAML with `--dry-run=client -o yaml`, then tidy it up.
- [**Imperative Commands with Files**](docs/object-management/imperative-object-configuration.md) — `create -f`, `replace -f`, and `delete -f`, and where they fall short.
- [**Declarative Object Management**](docs/object-management/declarative-management.md) — `kubectl apply` and `diff`, and how apply decides what to change.
- [**From Imperative to Declarative**](docs/object-management/imperative-to-declarative.md) — hand objects made with commands over to `apply`, safely.
- [**Multiple Objects in One File**](docs/object-management/multiple-objects-per-file.md) — put an app's objects in one file with `---`, in the right order.

**Part 5 — ReplicaSets & Deployments**

- [**What Are ReplicaSets**](docs/replicasets-deployments/what-are-replicasets.md) — keep N identical Pods running, and find them with labels and selectors.
- [**Creating and Managing ReplicaSets**](docs/replicasets-deployments/creating-replicasets.md) — create one, watch it replace a deleted Pod, scale it, and delete it.
- [**ReplicaSets Can't Update Pods**](docs/replicasets-deployments/replicaset-updates.md) — change the image, and see why running Pods stay on the old version.
- [**ReplicaSets and Existing Pods**](docs/replicasets-deployments/replicaset-existing-pods.md) — how the selector adopts Pods the ReplicaSet didn't create. *(coming soon)*
- [**Introduction to Deployments**](docs/replicasets-deployments/introduction-to-deployments.md) — the object that manages ReplicaSets for you. *(coming soon)*
- [**Creating and Managing Deployments**](docs/replicasets-deployments/creating-deployments.md) — create one, and see the ReplicaSet and Pods it makes. *(coming soon)*
- [**Updating the Pod Template**](docs/replicasets-deployments/updating-pod-template.md) — change the template, and watch the Pods get replaced. *(coming soon)*
- [**Understanding Rollouts**](docs/replicasets-deployments/understanding-rollouts.md) — how old and new ReplicaSets hand over, and how to roll back. *(coming soon)*
- [**Scaling Deployments**](docs/replicasets-deployments/scaling-deployments.md) — change the replica count with kubectl or the manifest. *(coming soon)*
- [**Troubleshooting Failed Rollouts**](docs/replicasets-deployments/troubleshooting-rollouts.md) — spot a stuck rollout, find out why, and recover. *(coming soon)*

**Part 6 — Core Objects**

- [**Scheduling, Taints & Tolerations**](docs/core-objects/scheduling.md) — control where Pods can land.
- [**DaemonSet (intro)**](docs/core-objects/daemonset.md) — one Pod per node.
- [**Job & CronJob**](docs/core-objects/job-cronjob.md) — batch and scheduled work.
- [**Service**](docs/core-objects/service.md) — a stable address + load balancer for Pods.
- [**Namespace**](docs/core-objects/namespace.md) — partition the cluster.

**Part 7 — Configuration & Data**

- [**ConfigMap**](docs/config-and-data/configmap.md) — keep config out of the image.
- [**Secret**](docs/config-and-data/secret.md) — sensitive values.
- [**Environment Variables & Mounts**](docs/config-and-data/env-and-mounts.md) — how config reaches the container.
- [**Volumes & PersistentVolumes**](docs/config-and-data/volumes.md) — storage that survives restarts.
- [**StatefulSet (intro)**](docs/config-and-data/statefulset.md) — stable identity + storage for stateful apps.

**Part 8 — Running & Operating**

- [**Health Checks**](docs/running-and-operating/health-checks.md) — liveness / readiness / startup probes.
- [**Resource Requests & Limits**](docs/running-and-operating/resources.md) — CPU/memory scheduling and caps.
- [**Scaling**](docs/running-and-operating/scaling.md) — manual and autoscaling.
- [**Rolling Update & Rollback**](docs/running-and-operating/rolling-updates.md) — zero-downtime releases, instant undo.
- [**Graceful Shutdown & Disruptions**](docs/running-and-operating/graceful-shutdown.md) — SIGTERM, preStop, drains, and PDBs.
- [**Debugging**](docs/running-and-operating/debugging.md) — the commands that explain a broken Pod.
- [**Security Basics**](docs/running-and-operating/security-basics.md) — ServiceAccounts, RBAC, Secrets, and NetworkPolicy.

**Part 9 — Networking & Access**

- [**Service Discovery & DNS**](docs/networking/dns.md) — find Pods by name.
- [**Ingress**](docs/networking/ingress.md) — route external traffic by host/path.
