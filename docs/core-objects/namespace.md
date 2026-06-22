# Namespace

> A virtual partition of the cluster — scope names, quotas, and access by environment or team.

---

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
kubectl get pods -n dev                                              # view dev only
kubectl get pods -A                                                  # every namespace
```

Tired of typing `-n dev`? Pin it to your context:

```bash
kubectl config set-context --current --namespace=dev
```

That default sticks until you change it again. When a later command seems to "lose" an object, check your current namespace with `kubectl config get-contexts`.

In [k9s](../getting-started/k9s.md), press `:ns` to switch, or `0` to see all namespaces at once.

## Capping usage with a ResourceQuota

A namespace by itself doesn't stop one team from eating all the cluster's CPU/memory. A **ResourceQuota** sets hard caps on a namespace — total Pod count, total requested/limited CPU and memory.

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

```bash
kubectl apply -f manifests/core-objects/dev-resourcequota.yaml
kubectl describe resourcequota dev-quota -n dev   # USED vs HARD for each resource
```

Once a quota exists, **every Pod in that namespace must declare `resources.requests`/`limits`** — the [Deployment](deployment.md) example already does, which is why it works here unmodified. Try pushing past the cap:

```bash
kubectl scale deployment/web -n dev --replicas=5
kubectl get pods -n dev                  # only 4 Running — quota caps at pods: "4"
kubectl get events -n dev | grep quota   # "exceeded quota: dev-quota …" for the 5th Pod
```

The 5th Pod never gets created — the apiserver rejects it at admission time, before the scheduler even sees it. Scale back down to clean up:

```bash
kubectl scale deployment/web -n dev --replicas=3
```

## What a namespace does and doesn't isolate

- ✅ **Names** — `web` in `dev` and `web` in `prod` are different objects.
- ✅ **A scope for `ResourceQuota`, `LimitRange`, and RBAC** — cap resources or restrict access per namespace.
- ✅ **DNS** — a Service is reachable cross-namespace as `web.dev.svc.cluster.local` (see [Service Discovery & DNS](../networking/dns.md)).
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

Then delete the lab namespace. This removes the `web` Deployment and quota inside it:

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
