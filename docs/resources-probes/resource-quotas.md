# Working with Resource Quotas

> Create `dev` and `prod`, each with its own quota, and find out what a namespace's quota allows and how much of it is used.

---

[Introduction to Resource Quotas, Requests, and Limits](introduction-to-resources.md) showed two quotas, one for dev and one for prod. Now you'll create them, and learn the commands for reading a quota: which namespaces have one, what each caps, and how much is already used. Nothing runs in either namespace yet. You'll put Pods under these quotas in [Setting Requests and Limits](requests-limits.md).

## Before you start

You need a running cluster with no `dev` or `prod` namespace. [Cross-Namespace Service Communication](../labels-namespaces/cross-namespace-services.md) deleted both in its clean-up, so check they're gone:

```bash
kubectl get namespace dev prod
```

```text
Error from server (NotFound): namespaces "dev" not found
Error from server (NotFound): namespaces "prod" not found
```

If either still exists, delete it with `kubectl delete namespace <name>`.

## 1. A namespace and its quota, in one file

A quota belongs to a namespace, so it's handy to keep the two together. [`manifests/resources-probes/dev-ns.yaml`](../../manifests/resources-probes/dev-ns.yaml) holds the dev namespace and the dev quota from the introduction:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: dev
  labels:
    env: dev
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: dev-quota
  namespace: dev
spec:
  hard:
    requests.cpu: "1000m"
    requests.memory: "2Gi"
    limits.cpu: "2000m"
    limits.memory: "4Gi"
```

The Namespace comes first on purpose. `kubectl apply` creates the objects in the order they appear in the file, and a quota can't be created in a namespace that doesn't exist yet. [`prod-ns.yaml`](../../manifests/resources-probes/prod-ns.yaml) is the same for prod, with six times as much. Apply both:

```bash
kubectl apply -f manifests/resources-probes/dev-ns.yaml -f manifests/resources-probes/prod-ns.yaml
```

```text
namespace/dev created
resourcequota/dev-quota created
namespace/prod created
resourcequota/prod-quota created
```

## 2. Find the quotas

A ResourceQuota is a namespaced object, like a Pod, so `kubectl get` looks in one namespace at a time. Its short name is `quota`. From `default`, you won't see either:

```bash
kubectl get quota
```

```text
No resources found in default namespace.
```

Name the namespace with `-n`:

```bash
kubectl get quota -n dev
```

```text
NAME        AGE   REQUEST                                     LIMIT
dev-quota   10s   requests.cpu: 0/1, requests.memory: 0/2Gi   limits.cpu: 0/2, limits.memory: 0/4Gi
```

Or use `-A` to see every quota in the cluster:

```bash
kubectl get quota -A
```

```text
NAMESPACE   NAME         AGE   REQUEST                                      LIMIT
dev         dev-quota    10s   requests.cpu: 0/1, requests.memory: 0/2Gi    limits.cpu: 0/2, limits.memory: 0/4Gi
prod        prod-quota   10s   requests.cpu: 0/6, requests.memory: 0/12Gi   limits.cpu: 0/12, limits.memory: 0/24Gi
```

Each entry reads **used / hard**. Nothing runs in either namespace yet, so everything used is `0`.

`-A` is the quickest way to answer "which namespaces have a quota at all?". A quota counts only its own namespace: dev's caps say nothing about prod, and `default`, which isn't listed, has no cap at all.

Your `"1000m"` came back as `1`. Kubernetes stores every quantity in its simplest exact form, so `1000m` becomes `1` and `6000m` becomes `6`. Memory works the same way: `2048Mi` would come back as `2Gi`, and `2Gi` is already in that form, so it doesn't change. Expect `1`, not `1000m`, in every output and error from now on.

## 3. Read one quota

The one-line `REQUEST` and `LIMIT` columns get hard to read once there's more in them. `kubectl describe` lays the same numbers out as a table:

```bash
kubectl describe quota dev-quota -n dev
```

```text
Name:            dev-quota
Namespace:       dev
Resource         Used  Hard
--------         ----  ----
limits.cpu       0     2
limits.memory    0     4Gi
requests.cpu     0     1
requests.memory  0     2Gi
```

Leave out the name, and `kubectl describe quota -n dev` describes every quota in the namespace. A namespace can have more than one, and a Pod has to fit within all of them.

`Hard` is what you wrote in `spec.hard`. `Used` is kept by Kubernetes, in the quota's `status`. You can see both in the object itself:

```bash
kubectl get quota dev-quota -n dev -o yaml
```

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: dev-quota
  namespace: dev
  ...
spec:
  hard:
    limits.cpu: "2"
    limits.memory: 4Gi
    requests.cpu: "1"
    requests.memory: 2Gi
status:
  hard:
    limits.cpu: "2"
    limits.memory: 4Gi
    requests.cpu: "1"
    requests.memory: 2Gi
  used:
    limits.cpu: "0"
    limits.memory: "0"
    requests.cpu: "0"
    requests.memory: "0"
```

`status.used` is what the API server checks a new Pod against, and Kubernetes keeps it up to date as Pods are created and deleted. To pull out a single number, say how much CPU dev has already requested, use `jsonpath`:

```bash
kubectl get quota dev-quota -n dev -o jsonpath='{.status.used.requests\.cpu}{"\n"}'
```

```text
0
```

The `\.` keeps the dot in `requests.cpu` from being read as a step into a nested field.

In [k9s](../cluster-setup/k9s.md), type `:quota` to list the quotas, and press `d` on one to describe it.

## 4. See all of a namespace's rules

A quota is one of the rules a namespace can set. To see them all at once, describe the namespace itself:

```bash
kubectl describe namespace dev
```

```text
Name:         dev
Labels:       env=dev
              kubernetes.io/metadata.name=dev
Annotations:  <none>
Status:       Active

Resource Quotas
  Name:            dev-quota
  Resource         Used  Hard
  --------         ----  ----
  limits.cpu       0     2
  limits.memory    0     4Gi
  requests.cpu     0     1
  requests.memory  0     2Gi

No LimitRange resource.
```

It lists every quota in the namespace, and its LimitRange if it has one. Dev has a quota and no LimitRange yet. Try it on `default`, which has neither:

```bash
kubectl describe namespace default
```

```text
Name:         default
Labels:       kubernetes.io/metadata.name=default
Annotations:  <none>
Status:       Active

No resource quota.

No LimitRange resource.
```

## Clean up

```bash
kubectl delete -f manifests/resources-probes/dev-ns.yaml -f manifests/resources-probes/prod-ns.yaml
```

Deleting the namespaces deletes their quotas with them. [Setting Requests and Limits](requests-limits.md) creates them again from the same files.

## Best practices

- **Keep a namespace and its quota in one file**, Namespace first, so an environment never exists without its cap.
- **Check `kubectl get quota -A`** to see at a glance which namespaces are capped, and which aren't.
- **Use `kubectl describe namespace`** to see all of a namespace's rules in one place: its quotas and its LimitRange.
- **Check `Used` against `Hard` before a big deploy**, with `kubectl describe quota`, so you know how much room is left.

---

[← Introduction to Resource Quotas, Requests, and Limits](introduction-to-resources.md) · [↑ Contents](../../README.md) · [Setting Requests and Limits →](requests-limits.md)
