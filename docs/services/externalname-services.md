# ExternalName Services

> Give an outside hostname an in-cluster name, so it can move without your apps noticing.

---

Every Service so far has sent traffic to Pods. An **ExternalName** Service sends traffic nowhere. It has no selector, no Pods, no ClusterIP, and kube-proxy ignores it. It's a single DNS record that says "this name is another name for that one".

That sounds like very little, and it is. Its value is in **where the name is decided**.

## Why you'd want one

Say your apps use a database that runs outside the cluster, at `db.example.com`. You could write that hostname into every app's configuration. Or you could give it an in-cluster name:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: external-db
spec:
  type: ExternalName
  externalName: db.example.com
```

The apps connect to `external-db`. One day the database moves to `new-db.example.com`. With the hostname in every app, that's a change to every app. With the Service, it's a change to **one field**:

```yaml
spec:
  type: ExternalName
  externalName: new-db.example.com
```

The apps still connect to `external-db`, and their configuration doesn't change. Each part has one job:

| Part | Knows | Changes when the database moves? |
|---|---|---|
| **Your apps** | Only the in-cluster name, `external-db` | No |
| **The Service** | Which outside name `external-db` stands for | Yes: one field |
| **The cluster's DNS** | How to answer for `external-db`: with a CNAME to the outside name | No: it follows the Service |

That's **decoupling**: the apps depend on a name the cluster controls, not on wherever the database happens to live. It's why ExternalName is useful even though it has no ClusterIP, no load balancing, and no proxying.

You don't need a real database to see how it works, because the Service never touches the database. All of it happens in DNS.

## 1. Create the Service

The manifest is [`manifests/services/external-db.yaml`](../../manifests/services/external-db.yaml), the one above. You'll move the database in step 3, so work on a copy:

```bash
mkdir -p /tmp/services
cp manifests/services/external-db.yaml /tmp/services/
kubectl apply -f /tmp/services/external-db.yaml
kubectl get svc external-db
```

```text
NAME          TYPE           CLUSTER-IP   EXTERNAL-IP      PORT(S)   AGE
external-db   ExternalName   <none>       db.example.com   <none>    0s
```

Compare it with [`color-api-clusterip.yaml`](../../manifests/services/color-api-clusterip.yaml):

- **No `selector`**, because there are no Pods to find. So there are no endpoints either: `kubectl get endpointslice -l kubernetes.io/service-name=external-db` finds nothing.
- **No `ports`**, because nothing is forwarded.
- **`CLUSTER-IP` is `<none>`**: there's no virtual IP and nothing for kube-proxy to route. `EXTERNAL-IP` shows the name it stands for.

## 2. Look it up

Ask the cluster's DNS for the name, from a throwaway Pod. This one uses `dig`, from the image the [Kubernetes DNS debugging guide](https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/) uses. `+short` prints only the answer. `dig` doesn't apply the search domains, so give it the full name from [ClusterIP Services](clusterip-services.md#5-how-the-name-works):

```bash
kubectl run dns-test --rm -i --restart=Never \
  --image=registry.k8s.io/e2e-test-images/jessie-dnsutils:1.3 -- \
  dig +short external-db.default.svc.cluster.local
```

```text
db.example.com.
pod "dns-test" deleted
```

The answer to "what is `external-db`?" is **another name**. That's a **CNAME** record. For a ClusterIP Service, CoreDNS answers with the Service's IP; for an ExternalName Service, it answers with the outside name, and that name is then resolved like any hostname on the internet. (The trailing `.` just marks a complete DNS name.)

For a real database, an IP address would follow on the next line. Here there's none: `example.com` is reserved for examples, and there's no database there. Notice that Kubernetes didn't object when you created the Service. It never checks that the outside name exists, or that anything answers there. It only hands out the alias.

## 3. Move the database

Now the database moves. Change one field, and apply:

```bash
sed -i 's/externalName: db.example.com/externalName: new-db.example.com/' \
  /tmp/services/external-db.yaml
kubectl apply -f /tmp/services/external-db.yaml
kubectl run dns-test --rm -i --restart=Never \
  --image=registry.k8s.io/e2e-test-images/jessie-dnsutils:1.3 -- \
  dig +short external-db.default.svc.cluster.local
```

```text
new-db.example.com.
pod "dns-test" deleted
```

Same name, new target. An app configured with `external-db` would now be sent to `new-db.example.com`, and nothing about the app changed: not its code, not its configuration, not its Deployment.

## 4. What to watch out for

"Nothing about the app changed" is true for its configuration. A few things still depend on how the app behaves:

| Watch out for | Why |
|---|---|
| **Existing connections** | The switch only affects **new** lookups. A database client with a connection pool keeps its open connections to the old database until they're closed. Plan for the app to reconnect, or restart it |
| **DNS caching** | CoreDNS, and some clients, cache the old answer for a little while, so the switch isn't instant |
| **TLS certificates** | A client that verifies the server's certificate checks it against the name **it** used, `external-db`. The certificate is for `new-db.example.com`, so verification fails. Managed cloud databases often require verification |
| **HTTP `Host` headers** | An HTTP client sends `Host: external-db`. A server that hosts many sites, like most cloud APIs, won't recognize it |

And because it's only a DNS record, an ExternalName Service skips everything the other types do:

- **No ports.** The client connects to the outside service's real port. There's no `port`/`targetPort` mapping.
- **No load balancing and no proxying.** The client connects directly to whatever the outside name resolves to.
- **No health checks.** If the database is down, the name still resolves, and the client finds out on its own.
- **Names only, not IPs.** `externalName` must be a DNS name. An IP address is treated as a name made of digits, which won't resolve. To give an in-cluster name to an outside **IP**, use a Service without a selector, and add an EndpointSlice by hand.

ExternalName fits best with clients that only need an address: a database or cache connection without certificate checks, or a service that ignores the `Host` header.

## Clean up

```bash
kubectl delete -f /tmp/services/external-db.yaml
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

- **Give outside dependencies an in-cluster name**, so moving them, or switching providers, is a change to one Service, not to every app.
- **Plan how clients pick up a switch.** Connection pools and DNS caches hold on to the old target until they reconnect.
- **Check what the client sends besides the address.** TLS certificates and HTTP `Host` headers still carry the alias, and many servers reject it.
- **Put DNS names in `externalName`**, never IP addresses. For an outside IP, use a Service without a selector and a hand-made EndpointSlice.
- **Remember that it's only DNS.** No ports, no load balancing, and no health checks: the client talks to the outside service directly.

---

[← NodePort Services](nodeport-services.md) · [↑ Contents](../../README.md) · [Labels and Selectors in Depth →](../labels-namespaces/labels-selectors.md)
