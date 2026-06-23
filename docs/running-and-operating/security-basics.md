# Security Basics

> The minimum security model to understand before running real workloads: identity, permissions, secrets, and network boundaries.

---

Kubernetes security is layered. A namespace organizes objects, but it does not automatically isolate them. A Secret hides values from casual display, but anyone allowed to read the Secret can decode it. A Pod has an identity, and RBAC decides what that identity may do.

This chapter is the beginner map, not a hardening checklist.

## Pod identity: ServiceAccounts

Every Pod runs as a **ServiceAccount**. If you don't specify one, it uses the namespace's `default` ServiceAccount.

```bash
kubectl create namespace security-demo
kubectl create serviceaccount viewer -n security-demo
kubectl get serviceaccount -n security-demo
```

Attach one to a Pod with:

```yaml
spec:
  serviceAccountName: viewer
```

That identity matters only when the Pod talks to the Kubernetes API. Most app Pods do not need API access at all.

## Permissions: RBAC

RBAC answers: "who can do which verbs on which resources?"

- **Role**: permissions inside one namespace.
- **ClusterRole**: permissions that can be reused cluster-wide, or permissions for cluster-scoped resources.
- **RoleBinding**: grants a Role or ClusterRole to a user, group, or ServiceAccount in one namespace.
- **ClusterRoleBinding**: grants cluster-wide.

Create a read-only Role for Pods in `security-demo`:

```bash
kubectl create role pod-reader \
  --verb=get,list,watch \
  --resource=pods \
  -n security-demo

kubectl create rolebinding viewer-reads-pods \
  --role=pod-reader \
  --serviceaccount=security-demo:viewer \
  -n security-demo
```

Ask the API what that ServiceAccount can do:

```bash
kubectl auth can-i list pods \
  --as=system:serviceaccount:security-demo:viewer \
  -n security-demo

kubectl auth can-i delete pods \
  --as=system:serviceaccount:security-demo:viewer \
  -n security-demo
```

The first should be `yes`; the second should be `no`.

## Secrets depend on access control

As the [Secret](../config-and-data/secret.md) chapter showed, base64 is not encryption. The main protection is RBAC: restrict who can `get`, `list`, or `watch` Secrets.

```bash
kubectl auth can-i get secrets \
  --as=system:serviceaccount:security-demo:viewer \
  -n security-demo
```

This should be `no` unless you granted it. Avoid giving broad roles like `edit` to workloads that don't need them, because broad permissions often include access to Secrets.

For real clusters, also enable **encryption at rest** for Secrets in etcd and use a secret-management flow such as External Secrets, Sealed Secrets, SOPS, or your CI/CD system.

## NetworkPolicy: namespaces are not firewalls

By default, Pods in different namespaces can usually talk to each other. A **NetworkPolicy** defines allowed ingress/egress traffic for selected Pods.

Example shape:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
spec:
  podSelector: {}
  policyTypes:
    - Ingress
```

That policy selects every Pod in the namespace and denies inbound traffic unless another policy allows it.

> **CNI matters:** NetworkPolicy only works if your CNI enforces it. Flannel by itself does not enforce NetworkPolicies. Use a policy-capable CNI such as Calico or Cilium when network isolation matters.

## Clean up

```bash
kubectl delete namespace security-demo
```

## Best practices

- **Use dedicated ServiceAccounts** for workloads that call the Kubernetes API.
- **Grant least privilege** with Role/RoleBinding; avoid broad ClusterRoleBinding unless truly needed.
- **Do not give app Pods Secret access by default.**
- **Treat namespaces as organization, not isolation**; add RBAC and NetworkPolicy for real boundaries.
- **Verify permissions with `kubectl auth can-i`** before assuming an identity is locked down.

---

[← Debugging](debugging.md) · [↑ Contents](../../README.md) · [Service Discovery & DNS →](../networking/dns.md)
