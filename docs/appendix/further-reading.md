# Further Reading

> Topics beyond this beginner path — reach for these once the fundamentals click.

---

- **RBAC & ServiceAccounts** — who and what can do what in the cluster, beyond the [Security Basics](../running-and-operating/security-basics.md) intro. [Docs](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- **NetworkPolicy** — firewall rules between Pods, beyond the [Security Basics](../running-and-operating/security-basics.md) intro. [Docs](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- **Pod Security Standards / Admission** — cluster-enforced baselines (privileged, baseline, restricted) that cap what a Pod spec is allowed to do, complementing the RBAC/Secret access control covered in [Security Basics](../running-and-operating/security-basics.md). [Docs](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- **Advanced scheduling** — affinity / anti-affinity and topology spread, beyond the [Scheduling, Taints & Tolerations](../core-objects/scheduling.md) intro. [Docs](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
- **Init containers & sidecars** — setup steps and helper containers within a Pod. [Docs](https://kubernetes.io/docs/concepts/workloads/pods/init-containers/)
- **Observability** — metrics, logs, and traces beyond `kubectl top`: Prometheus + Grafana for metrics, a log-shipping stack (e.g. Fluent Bit/Loki) for logs. [Docs](https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/)
- **Official tutorials** — [kubernetes.io/docs/tutorials](https://kubernetes.io/docs/tutorials/)

---

[← Troubleshooting](troubleshooting.md) · [↑ Contents](../../README.md)
