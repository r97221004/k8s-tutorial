# Ingress

> One entry point that routes outside traffic to many Services by host and path.

---

Exposing every [Service](../core-objects/service.md) with its own NodePort or LoadBalancer gets ugly fast — many ports, many IPs, no shared TLS. An **Ingress** is one HTTP(S) entry point that routes by **host and path** to many Services behind it: `demo.com/` → web, `demo.com/api` → api, all on port 443 with one certificate.

## Ingress needs a controller

An `Ingress` object is just *rules* — inert until something enforces them. That something is an **ingress controller** (ingress-nginx, Traefik, …) running in the cluster. k3s bundles Traefik; **vanilla kubeadm ships none**, so install one first:

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.14.5/deploy/static/provider/baremetal/deploy.yaml
kubectl get pods -n ingress-nginx        # wait for the controller to be Running
```

The version in the URL is pinned so this lab does not follow whatever changed on the upstream branch. `controller-v1.14.5` supports Kubernetes 1.30 in the ingress-nginx supported versions table.

> **Production note:** ingress-nginx has been retired and archived. It is still useful for this lab because the artifacts remain available, but for new production designs evaluate Gateway API or an actively maintained ingress/gateway controller.

## A routing rule

▶ **Runnable manifest:** [`manifests/networking/web-ingress.yaml`](../../manifests/networking/web-ingress.yaml) (routes to the `web` Service)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web
spec:
  ingressClassName: nginx
  rules:
    - host: demo.localdev.me      # *.localdev.me resolves to 127.0.0.1
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web
                port:
                  number: 80
```

```bash
kubectl apply -f manifests/networking/web-ingress.yaml
kubectl get ingress web                    # shows the host and the controller's address
curl http://demo.localdev.me               # reaches the web Service through the Ingress
```

`demo.localdev.me` resolves to `127.0.0.1`, which is handy only when the request runs on the same machine that exposes the ingress controller. If your kubeadm node is a remote VM, run the `curl` from inside that VM, SSH-forward the ingress controller's NodePort to your laptop, or map a hostname to the VM's IP in your local `/etc/hosts`.

Add more `paths` (e.g. `/api` → an `api` Service) to fan one host out to several backends — the whole point of an Ingress.

## TLS shape

TLS termination is just another part of the Ingress rule: put the certificate/key in a Secret, then reference it from `spec.tls`.

```bash
kubectl create secret tls demo-tls \
  --cert=demo.crt \
  --key=demo.key \
  --dry-run=client -o yaml
```

```yaml
spec:
  tls:
    - hosts:
        - demo.localdev.me
      secretName: demo-tls
  rules:
    - host: demo.localdev.me
```

In real clusters, cert-manager usually creates and renews that TLS Secret for you.

## Ingress vs LoadBalancer Service

- A **LoadBalancer Service** exposes **one** Service at L4 (TCP) — one external IP per Service.
- An **Ingress** is L7 (HTTP): **one** entry point routing to **many** Services by host/path, with shared TLS termination. You typically run *one* ingress controller (itself behind a LoadBalancer/NodePort) and many Ingress rules.

## Ingress vs Gateway API

Ingress is stable and widely understood, but it is intentionally small: host/path HTTP routing with controller-specific behavior around the edges. **Gateway API** is the newer direction for richer, more portable traffic management: separate Gateway infrastructure from app-owned routes, model more protocols, and reduce controller-specific annotations. You don't need Gateway API for this beginner lab, but expect to see it in modern production designs.

## Best practices

- **Terminate TLS at the Ingress** (a `tls:` block referencing a [Secret](../config-and-data/secret.md), often automated with cert-manager).
- **One controller, many Ingress resources** — don't expose Services individually.
- **Set `ingressClassName`** explicitly so the right controller picks up the rule.
- **Keep app Services as ClusterIP** behind the Ingress; only the controller is exposed.

---

[← Service Discovery & DNS](dns.md) · [↑ Contents](../../README.md) · [Helm (intro) →](../packaging/helm.md)
