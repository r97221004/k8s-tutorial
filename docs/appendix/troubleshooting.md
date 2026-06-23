# Troubleshooting

> Common failure modes and the first thing to check for each.

---

When something's wrong, start with the same two commands every time:

```bash
kubectl describe <kind> <name>   # the Events section usually names the cause
kubectl logs <pod> [--previous]  # what the app (or the crashed container) said
```

Then match the symptom below.

| Symptom | Likely cause | First moves |
|---------|--------------|-------------|
| Pod **`Pending`** | no node has room, PVC unbound, or untolerated taint | `describe pod` → Events; check [resources](../running-and-operating/resources.md), [PVC/StorageClass](../config-and-data/volumes.md), and [taints/tolerations](../core-objects/scheduling.md) |
| Pod stuck **`ContainerCreating`** | image pull or volume mount failing | `describe pod` → Events |
| **`ImagePullBackOff`** | wrong image name/tag, or private registry without a pull secret | fix the image string; add an imagePullSecret |
| **`CrashLoopBackOff`** | container starts then exits repeatedly | `logs --previous` for the real error; check command/config/env |
| **`OOMKilled`** (in describe) | exceeded the memory limit | raise the memory [limit](../running-and-operating/resources.md) or fix the leak |
| Pod **`Running` but `0/1`** | readiness probe failing | `describe` → probe events; fix the [health check](../running-and-operating/health-checks.md) or app |
| Node **`NotReady`** | no/broken CNI, or kubelet down | `kubectl get pods -n kube-system` (flannel/CNI Running?); see [Set Up](../getting-started/setup-kubeadm.md) |
| **Service returns nothing** | selector matches no Pods (empty endpoints) | `kubectl get endpoints <svc>`; align Service `selector` with Pod [labels](../core-objects/labels-selectors.md) |
| **Service name won't resolve** | wrong name/namespace, or CoreDNS down | use `svc.namespace`; check CoreDNS ([DNS](../networking/dns.md)) |
| **Ingress 404 / not reachable** | no ingress controller, wrong host/path or `ingressClassName` | controller Running? host header matches a rule? ([Ingress](../networking/ingress.md)) |
| **PVC `Pending`** | no (default) StorageClass | install/default a provisioner — [Volumes](../config-and-data/volumes.md) |
| Rollout **hangs** | new Pods never become ready (bad image/probe) | `rollout status`; `rollout undo`; then [debug](../running-and-operating/debugging.md) |
| API says **`Forbidden`** | RBAC denies this user or ServiceAccount | `kubectl auth can-i ...`; check [Security Basics](../running-and-operating/security-basics.md) |

> **Golden rule:** read `describe` Events and `logs --previous` *before* deleting or restarting anything — the cause is almost always written there. Full debugging workflow in [Debugging](../running-and-operating/debugging.md).

---

[← kubectl Cheat Sheet](cheatsheet.md) · [↑ Contents](../../README.md) · [Further Reading →](further-reading.md)
