# DaemonSet (intro)

> Runs exactly one Pod per node — the pattern for node-level agents.

---

_TODO — runs exactly one Pod per node (log shippers, monitoring agents, CNI). Contrast with a Deployment's "N replicas placed anywhere."_

> 📝 **Multi-node note:** a DaemonSet places one Pod on _every_ node. On this single-node cluster you'll see exactly one — picture it fanning out to every machine in a real cluster.

---

[← ReplicaSet](replicaset.md) · [↑ Contents](../../README.md) · [Job & CronJob →](job-cronjob.md)
