# Service Discovery & DNS

> How Pods find each other by name instead of chasing IP addresses.

---

[Service](../core-objects/service.md) IPs are stable, but you still don't want to hard-code them. **CoreDNS** (running in `kube-system`) gives every Service a DNS name, so Pods talk to each other by *name* — `http://web`, not `http://10.96.x.x`.

## The naming scheme

Every Service gets a record:

```
<service>.<namespace>.svc.cluster.local
```

From a Pod, the shorter forms also work thanks to DNS search domains:

| From a Pod, you can use | Resolves to |
|--------------------------|-------------|
| `web` | a Service named `web` **in the same namespace** |
| `web.dev` | Service `web` in namespace `dev` |
| `web.dev.svc.cluster.local` | the fully-qualified name (always works) |

So a frontend in namespace `dev` reaches its backend with just `http://api`, and a database in another namespace with `postgres.data`.

## Try it

Spin up a throwaway Pod and resolve a Service by name (assumes the `web` Service from the [Service chapter](../core-objects/service.md) exists):

```bash
kubectl run tmp --rm -it --image=busybox:1.36 -- sh
# inside the Pod:
nslookup web                 # shows web.<ns>.svc.cluster.local + its ClusterIP
wget -qO- http://web         # reaches the Service by name
```

> **Headless Services** (`clusterIP: None`, used by [StatefulSets](../config-and-data/statefulset.md)) resolve differently: instead of one Service IP, DNS returns each Pod's IP, and each Pod gets its own name like `postgres-0.postgres.<ns>.svc.cluster.local`. That's how you address a *specific* replica.

## Best practices

- **Address Services by name, never by IP** — names are stable across restarts and environments; IPs aren't.
- **Use the short name within a namespace**, the `svc.namespace` form across namespaces — clearer and portable.
- **If name resolution fails**, check CoreDNS is healthy (`kubectl get pods -n kube-system -l k8s-app=kube-dns`) and that the target Service has [endpoints](../core-objects/service.md).

---

[← Debugging](../running-and-operating/debugging.md) · [↑ Contents](../../README.md) · [Ingress →](ingress.md)
