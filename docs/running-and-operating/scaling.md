# Scaling

> Run more copies on demand — by hand, or automatically based on load.

[← Resource Requests & Limits](resources.md) · [🏠 Home](../../README.md) · [Rolling Update & Rollback →](rolling-updates.md)

---

_TODO — `kubectl scale`, replica count, and an HPA intro (autoscale on CPU)._

> 📝 **Multi-node note:** scaling a Deployment to 3 replicas here lands all 3 on the one node. On a multi-node cluster the scheduler spreads them across machines for real high availability — and a dead node's Pods get rescheduled elsewhere (something a single node can't demonstrate).

---

[← Resource Requests & Limits](resources.md) · [🏠 Home](../../README.md) · [Rolling Update & Rollback →](rolling-updates.md)
