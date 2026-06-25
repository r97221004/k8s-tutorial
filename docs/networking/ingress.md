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

▶ **Runnable manifest:** [`manifests/networking/web-ingress.yaml`](../../manifests/networking/web-ingress.yaml) (routes to the `web` and `api` Services)

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
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api
                port:
                  number: 80
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

## Fan one host out to two Services

The manifest above already routes by path. To see it actually pick the right backend, give it a second Service to route to:

▶ **Runnable manifest:** [`manifests/networking/api-echo.yaml`](../../manifests/networking/api-echo.yaml) (a tiny echo backend standing in for a real API)

```bash
kubectl apply -f manifests/networking/api-echo.yaml
kubectl rollout status deployment/api

curl http://demo.localdev.me/api           # -> "api backend" — routed to the api Service
curl http://demo.localdev.me/               # -> the web Service, unchanged
```

Both paths share the same host, same Ingress, same controller, same certificate (once TLS is added below) — only the `path` decides which Service gets the request. This is the core value an Ingress adds over plain Services: one entry point, many backends.

> ingress-nginx matches by **longest prefix wins**, not list order — `/api` and `/` can be written in either order in the manifest with the same result. Other controllers may differ; check their docs if routing looks unexpected.

### `pathType` reference

| `pathType` | Matches | Example |
|---|---|---|
| `Exact` | The URL path must match exactly, including case | `path: /api` matches `/api` only, not `/api/` or `/api/v1` |
| `Prefix` | Matches on element-by-element path segments | `path: /api` matches `/api`, `/api/`, `/api/v1` — but not `/apiv1` |
| `ImplementationSpecific` | Controller-defined (often regex with ingress-nginx) | Avoid unless you need a specific controller's extensions — it's the least portable choice |

Default to `Prefix` unless you have a specific reason not to — it's predictable and what every example in this chapter uses.

## TLS shape

TLS termination is just another part of the Ingress rule: put the certificate/key in a Secret, then reference it from `spec.tls`.

```bash
openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout demo.key \
  -out demo.crt \
  -days 7 \
  -subj "/CN=demo.localdev.me"

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

For a self-signed lab certificate, verify with:

```bash
curl -k https://demo.localdev.me
```

## What `ingressClassName: nginx` actually points to

`nginx` isn't a magic string — it's the name of an `IngressClass` object that the controller registered when you installed it. An Ingress with no matching class (or no `ingressClassName` at all, on a cluster with several controllers) never gets a backend address.

```bash
kubectl get ingressclass                      # see what controller(s) are available
kubectl get ingressclass nginx -o yaml         # .spec.controller ties it to ingress-nginx
```

If `kubectl get ingress web` shows no `ADDRESS`, this is the first thing to check — a typo'd `ingressClassName` is a common cause of an Ingress that silently does nothing.

## Controller-specific behavior via annotations

The Ingress spec only standardizes host/path routing. Anything beyond that — rewrites, redirects, rate limits, auth — is controller-specific and expressed as annotations on `metadata.annotations`. This is also the main reason Gateway API exists: to move these out of opaque annotations into a portable API.

A common one with ingress-nginx is rewriting the path before it reaches the backend, so the app doesn't need to know about the prefix it was reached through. This is the "specific reason" the `pathType` table above hedges on — regex capture groups need `ImplementationSpecific`, the one case where it's the right tool.

▶ **Runnable manifest:** [`manifests/networking/rewrite-demo.yaml`](../../manifests/networking/rewrite-demo.yaml) (an independent nginx backend + Ingress — doesn't touch the `web`/`api` resources above)

```yaml
metadata:
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$2   # $2 = the second capture group below
spec:
  rules:
    - host: demo.localdev.me
      http:
        paths:
          - path: /rewrite-demo(/|$)(.*)   # group 2 is everything after the prefix
            pathType: ImplementationSpecific
```

```bash
kubectl apply -f manifests/networking/rewrite-demo.yaml
kubectl rollout status deployment/rewrite-demo

curl http://demo.localdev.me/rewrite-demo/    # 200, "Welcome to nginx!"
```

That 200 is the proof the rewrite happened: the backend nginx has no `/rewrite-demo/` location, only `/`. If the request reached it unrewritten, you'd get a `404`. Confirm what the backend actually received:

```bash
kubectl logs deployment/rewrite-demo --tail=5    # access log shows "GET / HTTP/1.1", not "/rewrite-demo/"
```

This particular annotation only works with ingress-nginx — moving controllers means re-reading its annotation reference, which is exactly the portability problem Gateway API addresses.

## Troubleshooting

Work through these in order when an Ingress doesn't route as expected:

```bash
kubectl get ingress web                              # is ADDRESS populated?
kubectl describe ingress web                         # events + resolved backend per path
kubectl get pods -n ingress-nginx                     # is the controller actually Running?
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller --tail=50
```

| Symptom | Likely cause |
|---|---|
| `ADDRESS` stays empty | `ingressClassName` doesn't match an installed `IngressClass`, or no controller is running |
| `curl` hangs or connection refused | Wrong host/IP, or nothing is forwarding to the controller's NodePort/LoadBalancer |
| `404` from the controller itself (not your app) | No `path` rule matched — check `pathType` and exact path spelling |
| `502`/`503` from the controller | Path matched, but the backend Service has no Ready endpoints — same checklist as [debugging an empty Service](../core-objects/service.md#debug-an-empty-service) |
| Works on `/` but not `/api` | Backend app expects requests without the `/api` prefix — see the rewrite annotation above |

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

## Clean up

The `api` echo backend and `rewrite-demo` were only for the exercises above; remove them once you've seen the routing work:

```bash
kubectl delete -f manifests/networking/api-echo.yaml --ignore-not-found
kubectl delete -f manifests/networking/rewrite-demo.yaml --ignore-not-found
```

The `web` Ingress stays up by default — the [Helm](../packaging/helm.md) chapter is self-contained and doesn't need it, so delete it too if you'd rather not leave it running: `kubectl delete -f manifests/networking/web-ingress.yaml --ignore-not-found`.

---

[← Service Discovery & DNS](dns.md) · [↑ Contents](../../README.md) · [Helm (intro) →](../packaging/helm.md)
