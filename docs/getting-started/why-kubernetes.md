# Why Use Kubernetes?

> Containers solved "it works on my machine." Kubernetes solves "now run it on many machines, all the time, without babysitting it."

---

Containers package an app with everything it needs, so it runs the same everywhere. For one container on one machine, `docker run` is all you need:

```bash
docker run -d -p 80:80 nginx:1.27
```

The trouble starts when that app becomes **real**: more traffic, more services, more machines, and users who expect it to stay up. A container crashes at 3 a.m. A whole server dies and takes its containers with it. Traffic doubles and someone has to SSH in and start more copies.

Each of those is solvable with enough scripts. But the scripts grow, drift between servers, and only one person understands them.

> **The real problem isn't running containers — it's keeping them running correctly, across machines, as things change.**

### Can't we just use Docker?

**Docker and Docker Compose are great for single containers and development environments.** Many of the features below exist in Docker too — but only **within one host**. Production workloads span many hosts, and that's where Kubernetes comes in:

| Challenge | With Docker alone | With Kubernetes |
|-----------|-------------------|-----------------|
| **Scheduling** | You pick a server for each container | Declare [CPU/memory requests](../running-and-operating/resources.md); the [scheduler](../core-objects/scheduling.md) places Pods |
| **Self-healing** | Restarts on one host; unhealthy containers aren't replaced | [Probes](../running-and-operating/health-checks.md) catch failures; Pods are replaced on any node |
| **Load balancing** | Bring your own nginx/HAProxy | A [Service](../core-objects/service.md) spreads traffic across Pods |
| **Scaling** | Start containers by hand | Change `replicas`, or [autoscale](../running-and-operating/scaling.md) on metrics |
| **Service discovery** | Names resolve within one host | [Cluster DNS](../networking/dns.md) works from any node |
| **Config & secrets** | Copied onto every host | [ConfigMaps](../config-and-data/configmap.md) and [Secrets](../config-and-data/secret.md), injected at deploy |
| **Releases** | Stop old, start new, roll back by hand | [Rolling updates](../replicasets-deployments/understanding-rollouts.md) with one-command rollback |
| **Data** | Volumes tied to one host | [PersistentVolumeClaims](../config-and-data/volumes.md) outlive the Pod |

**What about Docker Swarm?** Swarm (and HashiCorp Nomad) can also run containers across many hosts. Kubernetes isn't the only orchestrator — but it has become the industry standard, with the largest ecosystem of tools, managed offerings, and jobs.

How does Kubernetes keep all of this true without you watching it? That's the one idea behind everything, and it's the [next chapter](what-is-kubernetes.md).

### When you *don't* need Kubernetes

Kubernetes is powerful, but it isn't free. It adds moving parts to learn, run, and upgrade. Be honest about whether you need it:

- **One small app on one server?** Docker Compose or a plain systemd service is simpler and perfectly fine.
- **No one to run the cluster?** A managed platform (a PaaS, serverless, or a managed Kubernetes service) may fit better than running your own.
- **A short-lived prototype?** Ship it first; reach for Kubernetes when the problems above actually show up.

> 💡 A good rule of thumb: adopt Kubernetes when you feel the pain of **many containers, many machines, or frequent releases** — not before.

For learning, though, a real cluster is the best way to understand what all those managed platforms are doing for you. That's what this guide builds.

---

[↑ Contents](../../README.md) · [What is Kubernetes? →](what-is-kubernetes.md)
