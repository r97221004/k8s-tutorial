# Deploy a Two-Tier App

> Put it all together: a web front end + a database back end, configured, persisted, and exposed.

---

_TODO — the capstone that ties the guide together:_

- _Database: a StatefulSet (or Deployment) + PVC for persistence, credentials in a Secret._
- _Web: a Deployment reading config from a ConfigMap and the DB Secret, reaching the DB by Service DNS name._
- _Expose the web tier via Service + Ingress._
- _Add readiness/liveness probes and resource requests/limits._
- _Finish with a rolling update to a new image version, then a rollback._

---

[← Kustomize (intro)](../packaging/kustomize.md) · [↑ Contents](../../README.md) · [Cleanup →](cleanup.md)
