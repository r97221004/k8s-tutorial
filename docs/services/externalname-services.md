# ExternalName Services

> Give an outside hostname an in-cluster Service name, and swap what's behind it without touching the clients.

---

Every Service so far has sent traffic to Pods. An **ExternalName** Service sends traffic nowhere. It has no selector, no Pods, no ClusterIP, and kube-proxy ignores it. It's a single DNS record: ask the cluster's DNS for the Service's name, and it answers "that's another name for `google.com`".

That sounds like very little, and it is. Its value is in **where the name lives**: your apps talk to an in-cluster name, and what that name points to is one field in one Service, which you can change without touching them.

## Before you start

You need `color-api-clusterip` from [ClusterIP Services](clusterip-services.md) for step 5. If you've cleaned up, or opened a new terminal since, set it up again:

```bash
DOCKERHUB_USER=your-dockerhub-user      # ← change this to your username
mkdir -p /tmp/services
cp manifests/services/color-api-deployment.yaml /tmp/services/
sed -i "s/<YOUR_DOCKERHUB_USER>/$DOCKERHUB_USER/" /tmp/services/color-api-deployment.yaml
kubectl apply -f /tmp/services/color-api-deployment.yaml
kubectl apply -f manifests/services/color-api-clusterip.yaml
kubectl rollout status deployment/color-api-deployment
```

The cluster also needs to reach the internet, to resolve and call `google.com`.

## 1. Create the Service

[`manifests/services/my-external-svc.yaml`](../../manifests/services/my-external-svc.yaml):

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-external-svc
spec:
  type: ExternalName
  externalName: google.com    # a DNS name, not an IP; no selector, no ports
```

Compare it with [`color-api-clusterip.yaml`](../../manifests/services/color-api-clusterip.yaml): no `selector`, because there are no Pods to find, and no `ports`, because nothing is forwarded. Just a type and a name. You'll change the name in step 5, so work on a copy:

```bash
cp manifests/services/my-external-svc.yaml /tmp/services/
kubectl apply -f /tmp/services/my-external-svc.yaml
kubectl get svc my-external-svc
```

```text
NAME              TYPE           CLUSTER-IP   EXTERNAL-IP   PORT(S)   AGE
my-external-svc   ExternalName   <none>       google.com    <none>    0s
```

`CLUSTER-IP` is `<none>`: there's no virtual IP and nothing for kube-proxy to route. `EXTERNAL-IP` shows the name it points to. And there are no endpoints either, because there's no selector to fill them:

```bash
kubectl get endpointslice -l kubernetes.io/service-name=my-external-svc
```

```text
No resources found in default namespace.
```

## 2. Look it up

Ask the cluster's DNS for the name, from a throwaway Pod. Use the full name, as in [ClusterIP Services](clusterip-services.md#5-how-the-name-works): busybox's `nslookup` doesn't always apply the search domains to a short one.

```bash
kubectl run dns-test --rm -i --image=busybox:1.36 --restart=Never -- \
  nslookup my-external-svc.default.svc.cluster.local
```

```text
Server:		10.96.0.10
Address:	10.96.0.10:53

my-external-svc.default.svc.cluster.local	canonical name = google.com
Name:	google.com
Address: 142.250.196.110
...
```

`canonical name = google.com` is a **CNAME** record. For a ClusterIP Service, CoreDNS answers with the Service's IP. For an ExternalName Service, it answers with **another name**, and the client then looks that one up like any other hostname on the internet. Your Google address will differ.

That's all an ExternalName Service does. Everything after the lookup happens directly between the Pod and `google.com`, with Kubernetes out of the way.

## 3. Call it over HTTP

So a Pod that calls `http://my-external-svc` is calling Google. Try it, with a throwaway `curl` Pod that prints only the HTTP status code:

```bash
kubectl run curl-test --rm -i --image=curlimages/curl:8.10.1 --restart=Never -- \
  -s -o /dev/null -w '%{http_code}\n' http://my-external-svc
```

```text
404
pod "curl-test" deleted
```

The connection reached Google, and Google answered `404 Not Found`. The DNS trick changed **where** the request went, but not what the request **says**. An HTTP request carries the hostname the client used, in its `Host` header, and Google's servers have never heard of a site called `my-external-svc`. Send the name Google expects, and the answer changes:

```bash
kubectl run curl-test --rm -i --image=curlimages/curl:8.10.1 --restart=Never -- \
  -s -o /dev/null -w '%{http_code}\n' -H 'Host: google.com' http://my-external-svc
```

```text
301
pod "curl-test" deleted
```

`301` is Google's normal redirect from `google.com` to `www.google.com`: the request was understood. HTTPS has the same problem, one step earlier. The client checks that the server's certificate is for the name it asked for, and Google's certificate doesn't list `my-external-svc`:

```bash
kubectl run curl-test --rm -i --image=curlimages/curl:8.10.1 --restart=Never -- \
  -sS -o /dev/null https://my-external-svc
```

```text
curl: (60) SSL: no alternative certificate subject name matches target host name 'my-external-svc'
More details here: https://curl.se/docs/sslcerts.html
...
```

(`-sS` keeps `curl` quiet, except for errors.) Error `60` is a certificate problem: the connection reached Google, and `curl` refused to trust it, exactly as it should.

So ExternalName fits some clients better than others:

| Client | Works through ExternalName? |
|---|---|
| Databases, caches, and other TCP protocols, like PostgreSQL or Redis, **without** certificate checks | ✓ They don't send the hostname anywhere it matters |
| HTTP to a server that hosts one site, and ignores the `Host` header | ✓ |
| HTTP to a server that hosts many sites, like Google or most cloud APIs | ✗ Unless the client sets the real `Host` header |
| Anything that verifies a TLS certificate: HTTPS, or a database connection with verification on, which managed cloud databases often require | ✗ The certificate is for the real name, not the alias |

## 4. What it doesn't do

Because it's only a DNS record, an ExternalName Service skips everything the other types do:

- **No ports.** The client connects to the external service's real port. There's no `port`/`targetPort` mapping to translate one into another.
- **No load balancing and no proxying.** The client connects directly to whatever address the external name resolves to.
- **No health checks.** If `google.com` is down, the name still resolves, and the client finds out on its own.
- **Names only, not IPs.** `externalName` must be a DNS name. Put an IP address in it, and it's treated as a name made of digits, which won't resolve. To give an in-cluster name to an outside **IP**, use a Service without a selector, and add an EndpointSlice by hand.

## 5. Swap what's behind the name

Here's what an ExternalName Service is really for. Say an app calls an API at `http://my-external-svc`. Today that API runs outside the cluster; tomorrow you move it in. With an ExternalName Service, the app never has to know.

Use color-api as the "API that moved in". Point the name at its ClusterIP Service, by its full DNS name:

```bash
sed -i 's/externalName: google.com/externalName: color-api-clusterip.default.svc.cluster.local/' \
  /tmp/services/my-external-svc.yaml
kubectl apply -f /tmp/services/my-external-svc.yaml
kubectl get svc my-external-svc
```

```text
NAME              TYPE           CLUSTER-IP   EXTERNAL-IP                                     PORT(S)   AGE
my-external-svc   ExternalName   <none>       color-api-clusterip.default.svc.cluster.local   <none>    2m
```

Call the **same** URL as before:

```bash
kubectl run curl-test --rm -i --image=curlimages/curl:8.10.1 --restart=Never -- \
  -s "http://my-external-svc/api?format=text"
```

```text
COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-2kfwp
pod "curl-test" deleted
```

Same name, same URL, a completely different backend. The client looked up `my-external-svc`, got the CNAME `color-api-clusterip.default.svc.cluster.local`, resolved that to the ClusterIP, and kube-proxy did the rest. It works over plain HTTP here because color-api ignores the `Host` header, and port `80` matches because `color-api-clusterip` listens on `80`.

Once nothing depends on the old target, the alias can go: change the clients to `color-api-clusterip` at your own pace, then delete `my-external-svc`. Or keep it, as the one place where the name is decided.

> Use the **full** name, `color-api-clusterip.default.svc.cluster.local`, in `externalName`. A CNAME is looked up as written, so a short name like `color-api-clusterip` wouldn't get the cluster's search domains and might not resolve.

## Clean up

```bash
kubectl delete -f /tmp/services/my-external-svc.yaml
```

That's the end of the Services part. To remove everything from it:

```bash
kubectl delete \
  -f /tmp/services/traffic-generator.yaml \
  -f manifests/services/color-api-nodeport.yaml \
  -f manifests/services/color-api-clusterip.yaml \
  -f /tmp/services/color-api-deployment.yaml \
  --ignore-not-found
rm -rf /tmp/services
```

## Best practices

- **Use ExternalName to give outside dependencies an in-cluster name**, so moving them, or switching providers, is a change to one Service, not to every client.
- **Check what the client sends besides the address.** HTTP `Host` headers and TLS certificates still carry the alias, and many servers reject it.
- **It fits plain TCP services best**, like a database or cache that doesn't verify a certificate. Once TLS verification is on, the alias breaks it, just as it breaks HTTPS.
- **Put full DNS names in `externalName`**, never IP addresses. For an outside IP, use a Service without a selector and a hand-made EndpointSlice.
- **Remember that it's only DNS.** No ports, no load balancing, and no health checks: the client talks to the outside service directly.

---

[← NodePort Services](nodeport-services.md) · [↑ Contents](../../README.md) · [Scheduling, Taints & Tolerations →](../core-objects/scheduling.md)
