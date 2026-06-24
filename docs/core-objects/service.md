# Service

> A stable address and load balancer for a set of Pods, whose IPs come and go.

---

## Before you start

This chapter expects three `web` Pods from the Deployment chapter. Recreate them if needed:

```bash
kubectl apply -f manifests/core-objects/web-deployment.yaml
kubectl rollout status deployment/web
```

Pods are disposable: every time one is recreated it gets a **new IP**. So you can't hand out a Pod's IP and expect it to keep working — the [Deployment](deployment.md) replaces Pods all the time. A **Service** solves this: it's a *stable* name and IP in front of a changing set of Pods, and it load-balances across them.

> **Analogy:** Pods are staff who come and go; a Service is the **front desk phone number** that always reaches whoever's on duty. Callers never need to know individual names.

## How it finds its Pods

A Service selects Pods by **label** — the same [labels & selectors](labels-selectors.md) mechanism as everywhere else. Any Pod matching the selector becomes an *endpoint*.

▶ **Runnable manifest:** [`manifests/core-objects/web-service.yaml`](../../manifests/core-objects/web-service.yaml) (pairs with the [Deployment](deployment.md)'s `app: web` Pods)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  type: ClusterIP        # default; reachable only inside the cluster
  selector:
    app: web             # send traffic to Pods with this label
  ports:
    - port: 80           # the Service's port
      targetPort: http   # the container port name to forward to
```

```bash
kubectl apply -f manifests/core-objects/web-service.yaml
kubectl get svc web
kubectl get endpoints web      # the Pod IPs it's actually fronting — should list 3
kubectl get endpointslice -l kubernetes.io/service-name=web
```

`Endpoints` is the older, simpler view of a Service's backends. `EndpointSlice` is the newer, more scalable version Kubernetes uses to split large backend lists into smaller chunks; in this lab, both are useful ways to confirm which Pods the Service can reach.

> If `endpoints` is empty, your Service `selector` doesn't match any Pod's labels — the #1 Service bug. Check with `kubectl get pods -l app=web`.

## Ports decoded

Service ports have three names that are easy to mix up. Read them as one traffic path:

```text
client -> Service port -> Pod targetPort
```

In this chapter, `http://web:80` means "connect to the Service named `web` on port `80`." The Service then forwards that traffic to the selected Pods' container port named `http`:

```yaml
ports:
  - port: 80          # clients connect here: http://web:80
    targetPort: http  # forward to the Pod's container port named "http"
```

| Field | Meaning |
|-------|---------|
| `port` | The Service-facing port. Other Pods use this when they call `http://web:80`. |
| `targetPort` | The Pod-facing port. This is where traffic lands inside each selected Pod. It can be a number (`80`) or a named container port (`http`). |
| `nodePort` | The node-facing port added only for `type: NodePort`. It opens a high port like `31234` on every node, forwarding into the Service's `port`. |

For a `ClusterIP` Service, you usually only care about `port` and `targetPort`. For a `NodePort` Service, traffic takes one extra hop:

```text
outside client -> nodeIP:nodePort -> Service port -> Pod targetPort
```

The name `http` isn't magic — it's defined on the Deployment's container, as an alias for whatever port number is there today:

```yaml
ports:
  - name: http
    containerPort: 80
```

`targetPort: http` just means "look up the container port named `http`, whatever number it currently is." Named ports are useful because the Service can keep saying `targetPort: http` even if the container later moves from port `80` to another number. Update the Deployment's named container port, and the Service can stay the same — the name is the indirection layer, the number is just today's value behind it.

## Debug an empty Service

Use this quick path when a Service has no backends:

```bash
kubectl get svc web
kubectl get pods --show-labels
kubectl get pods -l app=web
kubectl describe svc web
kubectl get endpoints web
kubectl get endpointslice -l kubernetes.io/service-name=web
```

If `kubectl get pods -l app=web` returns nothing, fix the Service `selector` or the Pod labels. If Pods match but endpoints are still empty, check whether the Pods are `Ready`; Services normally route only to ready endpoints.

## The three types you'll meet

| Type | Reachable from | Use when |
|------|----------------|----------|
| **ClusterIP** (default) | inside the cluster only | service-to-service traffic (e.g. web → database) |
| **NodePort** | `nodeIP:30000–32767` | quick external access in a lab / no load balancer |
| **LoadBalancer** | an external IP | cloud production (the cloud provisions a real LB) |

Try reaching the ClusterIP from inside, and via NodePort from your machine:

```bash
# From inside the cluster (ClusterIP works here):
kubectl run tmp --rm -it --image=busybox:1.36 -- wget -qO- http://web

# Expose it on a node port instead:
kubectl patch svc web -p '{"spec":{"type":"NodePort"}}'
kubectl get svc web            # note the PORT(S) like 80:31234/TCP
NODE_PORT=$(kubectl get svc web -o jsonpath='{.spec.ports[0].nodePort}')
curl http://localhost:$NODE_PORT
```

> 💡 **Where should you curl from?** `localhost:$NODE_PORT` only works on the node itself. From your laptop, use a reachable node IP instead: `kubectl get nodes -o wide` shows it under `INTERNAL-IP`, then `curl http://<node-ip>:$NODE_PORT`.

> 📝 **Multi-node note:** all your Pod endpoints sit on one node here, so kube-proxy has nothing to balance across machines. On a multi-node cluster a Service load-balances traffic to Pods wherever they run.

## A note on LoadBalancer (vanilla kubeadm)

`type: LoadBalancer` only works if something provisions the external IP. Clouds do this automatically; **bare kubeadm has no LB provider**, so a `LoadBalancer` Service sits `<pending>` forever. Options:

- Use **NodePort** (fine for this lab), or
- Install **[MetalLB](https://metallb.universe.tf/)** to make `LoadBalancer` work on bare metal.

For routing real HTTP traffic by host/path, you usually put an [Ingress](../networking/ingress.md) in front of ClusterIP Services rather than exposing each one.

## Best practices

- **Default to ClusterIP**; only expose externally what truly needs it.
- **Keep `selector` labels stable** and matching your Deployment's Pod labels.
- **Name ports** when a Service has more than one, so other objects can refer to them by name.
- **Reach Services by DNS name**, not IP — see [Service Discovery & DNS](../networking/dns.md).

## Clean up or continue

If you're moving on to [Namespace](namespace.md), you can leave the `web` Deployment running, but reset the Service back to the manifest's `ClusterIP` shape after the NodePort experiment:

```bash
kubectl apply -f manifests/core-objects/web-service.yaml
```

If you're done with the lab for now, delete both:

```bash
kubectl delete -f manifests/core-objects/web-service.yaml
kubectl delete -f manifests/core-objects/web-deployment.yaml
```

---

[← Job & CronJob](job-cronjob.md) · [↑ Contents](../../README.md) · [Namespace →](namespace.md)
