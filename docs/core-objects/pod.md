# Pod

> The smallest thing Kubernetes runs — one (or a few) containers that share a network and storage, scheduled together onto one node.

---

## Before you start

You should have a healthy cluster and be in the `default` namespace:

```bash
kubectl get nodes
kubectl config set-context --current --namespace=default
```

## Why a Pod, not just a container?

You might expect Kubernetes to run *containers* directly. It doesn't — it runs **Pods**. A Pod is a thin wrapper around one or more containers that:

- **share one network identity** — the same IP and port space, so containers in a Pod reach each other over `localhost`;
- **can share storage** — the same volumes are mountable by every container in the Pod;
- **live and die together** — they're always scheduled onto the **same node** and started/stopped as a unit.

Most Pods hold exactly one container. The multi-container case is for tightly-coupled helpers (a logging "sidecar", a proxy) that must sit right next to the main app — see [init containers & sidecars](../appendix/further-reading.md).

> **The key idea:** the Pod — not the container — is Kubernetes' unit of scheduling, networking, and lifecycle.

## Your first Pod

Notice the four fields every object has — `apiVersion`, `kind`, `metadata`, `spec` (see [Anatomy of a Manifest](../getting-started/manifest-anatomy.md)):

▶ **Runnable manifest:** [`manifests/core-objects/nginx-pod.yaml`](../../manifests/core-objects/nginx-pod.yaml)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
  labels:
    app: nginx
spec:
  containers:
    - name: nginx
      image: nginx:1.27
      ports:
        - containerPort: 80
```

Apply it and watch it come up:

```bash
kubectl apply -f manifests/core-objects/nginx-pod.yaml
kubectl get pods            # STATUS: ContainerCreating → Running
kubectl get pods -o wide    # which node it landed on, its Pod IP
```

## Look inside

The four commands you'll reach for constantly:

```bash
kubectl describe pod nginx       # events, image, state — your first stop when debugging
kubectl logs nginx               # stdout/stderr of the container
kubectl exec -it nginx -- bash   # a shell inside the container
kubectl port-forward pod/nginx 8080:80   # reach it at http://localhost:8080
```

If a Pod won't start, `describe` and `logs` almost always tell you why — see [Debugging](../running-and-operating/debugging.md).

## Clean up

This Pod was only for learning the shape of a Pod. Delete it before moving on so the next examples start clean:

```bash
kubectl delete pod nginx
```

## You rarely create bare Pods

A standalone Pod has no safety net: delete it, or let its node fail, and it's simply **gone** — nothing recreates it. In practice you almost never write `kind: Pod` by hand. Instead a controller like a [Deployment](deployment.md) creates and manages Pods for you — keeping the desired number running, replacing dead ones, and rolling out new versions. Understanding the bare Pod first is what makes those controllers make sense.

---

[← Inspect with k9s](../getting-started/k9s.md) · [↑ Contents](../../README.md) · [Labels & Selectors →](labels-selectors.md)
