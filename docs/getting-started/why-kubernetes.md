# Why Use Kubernetes?

> Containers solved "it works on my machine." Kubernetes solves "now run it on many machines, all the time, without babysitting it."

---

Containers package an app with everything it needs, so it runs the same everywhere. For one container on one machine, `docker run` is all you need:

```bash
docker run -d -p 80:80 nginx:1.27
```

The trouble starts when that app becomes **real**: more traffic, more services, more machines, and users who expect it to stay up.

### The problems that show up

Picture running a web app and its database by hand across three servers:

- **A container crashes at 3 a.m.** Someone has to notice and restart it. `--restart=always` helps, but only on that one machine.
- **A whole server dies.** Its containers are gone. You need to decide where they go now, start them there, and update anything that pointed at the old IP.
- **Traffic doubles.** You SSH into machines and start more copies, then check that none of them are already full.
- **You ship a new version.** Stop old, start new — and hope nothing breaks in between. If it does, rolling back is manual too.
- **Containers need to find each other.** IPs change every time a container restarts, so hard-coding them doesn't work.
- **Config and passwords** end up copy-pasted into scripts and `docker run` flags on every host.

Each problem is solvable with enough scripts. But the scripts grow, drift between servers, and only one person understands them.

> **The real problem isn't running containers — it's keeping them running correctly, across machines, as things change.**

### What Kubernetes gives you

Kubernetes turns each of those chores into something you **declare once** and the cluster maintains for you:

| Problem | What Kubernetes does | Where you'll learn it |
|---------|----------------------|-----------------------|
| Crashed container | **Self-healing** — restarts it, or replaces the Pod | [Deployment](../core-objects/deployment.md), [Health Checks](../running-and-operating/health-checks.md) |
| Dead server | **Reschedules** the work onto healthy nodes | [Scheduling](../core-objects/scheduling.md) |
| More traffic | **Scaling** — change `replicas: 3` to `replicas: 10` | [Deployment](../core-objects/deployment.md) |
| New version | **Rolling updates** with one-command rollback | [Rolling Updates](../running-and-operating/rolling-updates.md) |
| Finding other services | **Stable names and IPs** via Services and DNS | [Service](../core-objects/service.md), [DNS](../networking/dns.md) |
| Config and secrets | **ConfigMaps and Secrets**, kept out of the image | [ConfigMap](../config-and-data/configmap.md), [Secret](../config-and-data/secret.md) |
| Data that must survive | **Persistent volumes** that outlive the Pod | [Volumes](../config-and-data/volumes.md) |

And because it's all YAML, your whole setup can live in **Git** — reviewed, versioned, and reproducible on any cluster.

### When you *don't* need Kubernetes

Kubernetes is powerful, but it isn't free. It adds moving parts to learn, run, and upgrade. Be honest about whether you need it:

- **One small app on one server?** Docker Compose or a plain systemd service is simpler and perfectly fine.
- **No one to run the cluster?** A managed platform (a PaaS, serverless, or a managed Kubernetes service) may fit better than running your own.
- **A short-lived prototype?** Ship it first; reach for Kubernetes when the problems above actually show up.

> 💡 A good rule of thumb: adopt Kubernetes when you feel the pain of **many containers, many machines, or frequent releases** — not before.

For learning, though, a real cluster is the best way to understand what all those managed platforms are doing for you. That's what this guide builds.

---

[↑ Contents](../../README.md) · [What is Kubernetes? →](what-is-kubernetes.md)
