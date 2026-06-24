# Namespace

> A virtual partition of the cluster — scope names, quotas, and access by environment or team.

---

## Before you start

Use the `default` namespace as your starting point, then this chapter creates a separate `dev` namespace:

```bash
kubectl config set-context --current --namespace=default
kubectl delete namespace dev --ignore-not-found
```

A **Namespace** is a virtual partition of one cluster. It scopes object **names**, and gives you a unit to attach **quotas** and **access control** to. Think folders: two teams can each have a `web` Deployment without clashing, as long as they're in different namespaces.

## What you already have

Your cluster came with a few:

```bash
kubectl get namespaces
```

```
NAME              STATUS   AGE
default           Active   1h     ← where your objects go if you don't say otherwise
kube-system       Active   1h     ← the control plane + add-ons (don't touch)
kube-public       Active   1h
kube-node-lease   Active   1h
```

Everything you've created so far landed in `default`. The control plane you saw in [Set Up](../getting-started/setup-kubeadm.md) lives in `kube-system`.

## Using namespaces

```bash
kubectl create namespace dev
kubectl apply -f manifests/core-objects/web-deployment.yaml -n dev   # create in dev
kubectl apply -f manifests/core-objects/web-service.yaml -n dev       # create a same-named Service in dev
kubectl get pods -n dev                                              # view dev only
kubectl get svc -n dev                                               # view Services in dev
kubectl get deploy web -n default
kubectl get deploy web -n dev                                        # same name, different namespace
kubectl get pods -A                                                  # every namespace
```

Tired of typing `-n dev`? Pin it to your context:

```bash
kubectl config set-context --current --namespace=dev
```

That default sticks until you change it again. When a later command seems to "lose" an object, check your current namespace with `kubectl config get-contexts`.

For namespaced objects, `kubectl -n dev` decides where an object goes when the manifest does **not** set `metadata.namespace`. If the manifest already says `metadata.namespace: dev`, `kubectl apply -f file.yaml` uses that namespace. Cluster-scoped objects ignore `-n` entirely.

In [k9s](../getting-started/k9s.md), press `:ns` to switch, or `0` to see all namespaces at once.

## Capping usage with a ResourceQuota

A namespace by itself doesn't stop one team from eating all the cluster's CPU/memory. A **ResourceQuota** sets hard caps on a namespace — total Pod count, total requested/limited CPU and memory. A **LimitRange** can set default requests/limits for Pods that forget to declare them.

Short version: **ResourceQuota is the ceiling** for the namespace; **LimitRange is the default or per-object rule** inside that namespace.

▶ **Runnable manifest:** [`manifests/core-objects/dev-resourcequota.yaml`](../../manifests/core-objects/dev-resourcequota.yaml)

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: dev-quota
  namespace: dev
spec:
  hard:
    pods: "4"
    requests.cpu: "300m"
    requests.memory: 320Mi
    limits.cpu: "1"
    limits.memory: 640Mi
```

Every key under `hard` is a cap on the *sum across the whole namespace*, not per Pod:

| Key | Caps |
|-----|------|
| `pods` | Total number of Pods allowed in `dev`, regardless of their size. |
| `requests.cpu` | Sum of every container's `resources.requests.cpu` in the namespace. `300m` = 0.3 CPU core. |
| `requests.memory` | Sum of every container's `resources.requests.memory`. `320Mi` = 320 mebibytes. |
| `limits.cpu` | Sum of every container's `resources.limits.cpu`. `"1"` = 1 full CPU core. |
| `limits.memory` | Sum of every container's `resources.limits.memory`. `640Mi` = 640 mebibytes. |

Numeric values are quoted (`"4"`, `"300m"`, `"1"`) because Kubernetes' quantity format (`300m`, `1`, `640Mi`) isn't a plain YAML number — quoting keeps it from being misparsed. So with this quota: at most 4 Pods total in `dev`, and across all of them combined, requests can't exceed 0.3 CPU / 320Mi memory, nor limits exceed 1 CPU / 640Mi memory.

▶ **Runnable manifest:** [`manifests/core-objects/dev-limitrange.yaml`](../../manifests/core-objects/dev-limitrange.yaml)

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: dev-defaults
  namespace: dev
spec:
  limits:
    - type: Container
      defaultRequest:
        cpu: 50m
        memory: 64Mi
      default:
        cpu: 200m
        memory: 128Mi
```

Unlike `ResourceQuota`, this applies *per container*, not as a namespace-wide sum:

| Key | Meaning |
|-----|---------|
| `type: Container` | These defaults apply to each container individually (LimitRange can also target `Pod` or `PersistentVolumeClaim`). |
| `defaultRequest` | If a container omits `resources.requests`, it gets `cpu: 50m` (0.05 core) / `memory: 64Mi` here. |
| `default` | If a container omits `resources.limits`, it gets `cpu: 200m` (0.2 core) / `memory: 128Mi` here. |

So a Pod that declares no `resources` at all isn't actually "unbounded" — the apiserver silently fills in these values at creation time, and *those* filled-in values are what count against the `ResourceQuota` above. This is also why a quota-tracked namespace doesn't reject bare Pods outright: as long as a `LimitRange` default exists, there's something to count.

```bash
kubectl apply -f manifests/core-objects/dev-resourcequota.yaml
kubectl apply -f manifests/core-objects/dev-limitrange.yaml
kubectl describe resourcequota dev-quota -n dev   # USED vs HARD for each resource
kubectl describe limitrange dev-defaults -n dev    # default requests/limits
```

Once a quota tracks CPU/memory, every Pod in that namespace needs `resources.requests`/`limits`. The [Deployment](deployment.md) example declares them directly; the LimitRange provides defaults for simpler Pods that do not. Without either one, the apiserver rejects the Pod because it cannot count it against the quota.

Try pushing past the cap:

```bash
kubectl scale deployment/web -n dev --replicas=5
kubectl get pods -n dev                  # only 4 Running — quota caps at pods: "4"
kubectl get events -n dev --sort-by=.lastTimestamp   # look for "exceeded quota: dev-quota …"
kubectl describe deployment web -n dev   # also shows the failed scale-up event
```

The 5th Pod never gets created — the apiserver rejects it at admission time, before the scheduler even sees it. Scale back down to clean up:

```bash
kubectl scale deployment/web -n dev --replicas=3
```

To see namespaced vs cluster-scoped resources directly:

```bash
kubectl api-resources --namespaced=true
kubectl api-resources --namespaced=false
```

## What a namespace does and doesn't isolate

- ✅ **Names** — `web` in `dev` and `web` in `prod` are different objects.
- ✅ **A scope for `ResourceQuota`, `LimitRange`, and RBAC** — cap resources or restrict access per namespace.
- ✅ **DNS** — the `web` Service you created in `dev` is reachable cross-namespace as `web.dev.svc.cluster.local` (see [Service Discovery & DNS](../networking/dns.md)).
- ❌ **Not a security boundary by default** — without a [NetworkPolicy](../appendix/further-reading.md), Pods in one namespace can still reach Pods in another over the network. Namespaces organize; they don't firewall.
- ❌ **Not for every little thing** — cluster-wide objects (Nodes, PersistentVolumes, Namespaces themselves) aren't namespaced.

## Best practices

- **Separate environments/teams** with namespaces (`dev`, `staging`, `prod`), not separate clusters, when isolation needs are modest.
- **Never deploy your apps into `kube-system`** — it's reserved for cluster components.
- **Add `ResourceQuota`/`LimitRange`** per namespace in shared clusters so one team can't starve others.
- For real isolation between namespaces, add **NetworkPolicies** and **RBAC**.

## Clean up

If you set your default namespace to `dev`, switch back to `default` before continuing:

```bash
kubectl config set-context --current --namespace=default
```

Then delete the lab namespace. This removes the `web` Deployment, Service, ResourceQuota, and LimitRange inside it:

```bash
kubectl delete namespace dev
```

To fully reset after Part 1, also remove the `web` Service and Deployment left in `default`:

```bash
kubectl delete -f manifests/core-objects/web-service.yaml --ignore-not-found
kubectl delete -f manifests/core-objects/web-deployment.yaml --ignore-not-found
```

---

[← Service](service.md) · [↑ Contents](../../README.md) · [ConfigMap →](../config-and-data/configmap.md)
