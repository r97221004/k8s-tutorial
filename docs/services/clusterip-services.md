# ClusterIP Services

> Give color-api a stable in-cluster address and DNS name, and watch requests spread across its Pods.

---

In [Deploying Color API and Traffic Generator](deploying-color-api.md), pointing the traffic generator at one Pod's IP had two problems: every request went to that one Pod, and when the Pod was replaced, the traffic generator was left talking to nobody. A **ClusterIP Service**, the default type from [What Are Services](what-are-services.md#the-types-of-service), fixes both.

In this chapter you'll put one in front of color-api, point the traffic generator at it, and then see why you should point it at the Service's **name** rather than its IP.

## Before you start

You need the color-api Deployment from the previous chapter. The traffic generator gets recreated in step 2 anyway, so it doesn't matter whether it's still running.

If you've cleaned up, or opened a new terminal since, set things up again. Always work on copies in `/tmp`, never on the files in `manifests/`:

```bash
DOCKERHUB_USER=your-dockerhub-user      # ← change this to your username
mkdir -p /tmp/services
cp manifests/services/color-api-deployment.yaml /tmp/services/
sed -i "s/<YOUR_DOCKERHUB_USER>/$DOCKERHUB_USER/" /tmp/services/color-api-deployment.yaml
kubectl apply -f /tmp/services/color-api-deployment.yaml
kubectl rollout status deployment/color-api-deployment
```

## 1. Create the Service

[`manifests/services/color-api-clusterip.yaml`](../../manifests/services/color-api-clusterip.yaml):

```yaml
apiVersion: v1
kind: Service
metadata:
  name: color-api-clusterip
  labels:
    app: color-api
spec:
  type: ClusterIP
  selector:
    app: color-api        # the color-api Deployment's Pods
  ports:
    - port: 80            # clients connect to the Service on 80
      targetPort: 8080    # color-api listens on 8080
```

There's nothing to fill in, so apply it straight from the repo:

```bash
kubectl apply -f manifests/services/color-api-clusterip.yaml
kubectl get svc color-api-clusterip
```

```text
NAME                  TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
color-api-clusterip   ClusterIP   10.111.36.227   <none>        80/TCP    0s
```

Which Pods is it sending traffic to? Ask for its endpoints:

```bash
kubectl get endpointslice -l kubernetes.io/service-name=color-api-clusterip
```

```text
NAME                        ADDRESSTYPE   PORTS   ENDPOINTS                                      AGE
color-api-clusterip-kkfzw   IPv4          8080    10.244.0.4,10.244.0.7,10.244.0.6 + 2 more...   0s
```

Five addresses on port `8080`: the five color-api Pods, found by the selector. `kubectl describe svc color-api-clusterip` shows the same list on its `Endpoints:` line.

## 2. Point the traffic generator at the ClusterIP

A Pod's `args` can't be changed once it's running (most of a [Pod's spec is immutable](../pods/working-with-pods.md#8-changing-a-pod)), so delete the old traffic generator:

```bash
kubectl delete pod traffic-generator --ignore-not-found
```

Save the Service's IP:

```bash
CLUSTER_IP=$(kubectl get svc color-api-clusterip -o jsonpath='{.spec.clusterIP}')
```

Then fill it into a fresh copy of the manifest. The Service listens on port `80`, the default for `http://`, so the URL needs no port:

```bash
cp manifests/services/traffic-generator.yaml /tmp/services/
sed -i \
  -e "s/<YOUR_DOCKERHUB_USER>/$DOCKERHUB_USER/" \
  -e "s#http://<COLOR_API_POD_IP>:8080#http://$CLUSTER_IP#" \
  /tmp/services/traffic-generator.yaml
```

Check the URL that went into the file:

```bash
grep -o 'http://[^"]*' /tmp/services/traffic-generator.yaml
```

```text
http://10.111.36.227/api?format=text
```

Then create the new traffic generator:

```bash
kubectl apply -f /tmp/services/traffic-generator.yaml
kubectl wait --for=condition=Ready pod/traffic-generator --timeout=60s
```

In a **second terminal**, follow its output:

```bash
kubectl logs traffic-generator -f
```

```text
[2026-11-25 08:26:46] COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-hv7pt
[2026-11-25 08:26:46] COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-hv7pt
[2026-11-25 08:26:47] COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-2kfwp
[2026-11-25 08:26:48] COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-hv7pt
[2026-11-25 08:26:48] COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-5hhm4
```

Different hostnames. After 15 seconds or so, count who answered:

```bash
kubectl logs traffic-generator | grep -o 'HOSTNAME: .*' | sort | uniq -c
```

```text
      9 HOSTNAME: color-api-deployment-579dc9c56-2kfwp
      3 HOSTNAME: color-api-deployment-579dc9c56-4h7tr
     11 HOSTNAME: color-api-deployment-579dc9c56-5hhm4
      4 HOSTNAME: color-api-deployment-579dc9c56-b6754
      5 HOSTNAME: color-api-deployment-579dc9c56-hv7pt
```

All five Pods get requests: **problem one solved**. The split isn't even, and it isn't meant to be. kube-proxy picks a Pod at random for each new connection; over many requests it evens out, but it's not round-robin.

## 3. Delete a color-api Pod

In the first terminal, delete one of the Pods behind the Service:

```bash
kubectl delete pod $(kubectl get pods -l app=color-api -o jsonpath='{.items[0].metadata.name}')
```

Watch the second terminal: not a single `no response`. The Deployment starts a replacement with a new IP, the EndpointSlice is updated to drop the old address and add the new one, and the very next requests include the new Pod:

```text
[2026-11-25 08:26:59] COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-pd62n
[2026-11-25 08:26:59] COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-b6754
```

**Problem two solved**: the traffic generator's address, the ClusterIP, didn't change, even though the Pods behind it did.

## 4. Use the name, not the IP

The ClusterIP stays put for as long as the Service exists. But Services do get deleted and created again: someone cleans up and re-applies, a namespace is rebuilt, or you set up the same app in another cluster. Try it:

```bash
kubectl get svc color-api-clusterip -o jsonpath='{.spec.clusterIP}'; echo
kubectl delete -f manifests/services/color-api-clusterip.yaml
kubectl apply -f manifests/services/color-api-clusterip.yaml
kubectl get svc color-api-clusterip -o jsonpath='{.spec.clusterIP}'; echo
```

```text
10.111.36.227
10.110.150.3
```

Same Service, same manifest, **new IP**. The second terminal:

```text
[2026-11-25 08:27:01] (no response from http://10.111.36.227/api?format=text)
[2026-11-25 08:27:03] (no response from http://10.111.36.227/api?format=text)
```

And it will never recover: nothing will ever answer at `10.111.36.227` again, until you change the traffic generator's configuration by hand.

Now point it at the Service's **name** instead. Replace the IP in your copy, and recreate the traffic generator:

```bash
sed -i "s#http://[0-9.]*/api#http://color-api-clusterip/api#" /tmp/services/traffic-generator.yaml
grep -o 'http://[^"]*' /tmp/services/traffic-generator.yaml
```

```text
http://color-api-clusterip/api?format=text
```

```bash
kubectl delete pod traffic-generator
kubectl apply -f /tmp/services/traffic-generator.yaml
```

Run `kubectl logs traffic-generator -f` in the second terminal again: requests are answered, by all the Pods. Then recreate the Service once more, in the first terminal:

```bash
kubectl delete -f manifests/services/color-api-clusterip.yaml
kubectl apply -f manifests/services/color-api-clusterip.yaml
```

A few failures appear, and then, without you touching anything, it recovers:

```text
[2026-11-25 08:27:20] (no response from http://color-api-clusterip/api?format=text)
...
[2026-11-25 08:27:45] (no response from http://color-api-clusterip/api?format=text)
[2026-11-25 08:27:46] COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-hv7pt
```

The name `color-api-clusterip` now leads to the new Service, whatever its IP is. The short gap is DNS caching: CoreDNS remembers an answer for up to 30 seconds (`cache 30` in its configuration), so for a little while the name still led to the deleted Service's IP.

| The client uses | Pods replaced | Service recreated |
|---|---|---|
| A Pod IP | ✗ Broken for good | ✗ Broken for good |
| The ClusterIP | ✓ Keeps working | ✗ Broken for good: the IP changes |
| The Service name | ✓ Keeps working | ✓ Recovers by itself, within about 30 seconds |

The name is the only thing that's the same in every case, and in every cluster: deploy the same manifests somewhere else, and the ClusterIP will be different, but `color-api-clusterip` won't. **Configure clients with the Service name.**

## 5. How the name works

Every Pod gets the cluster's DNS server, and a list of domains to try, in its `/etc/resolv.conf`:

```bash
kubectl exec traffic-generator -- cat /etc/resolv.conf
```

```text
search default.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.96.0.10
options ndots:5
```

`10.96.0.10` is CoreDNS, itself behind a Service. The `search` line is why the short name works: `color-api-clusterip` is tried as `color-api-clusterip.default.svc.cluster.local` first, which is the Service's full name. So from a Pod, all three of these reach the same Service:

| Name | Works from |
|---|---|
| `color-api-clusterip` | Pods in the **same** namespace |
| `color-api-clusterip.default` | Pods in **any** namespace |
| `color-api-clusterip.default.svc.cluster.local` | Anywhere that uses the cluster's DNS: the full name |

Check the full name's answer, from a throwaway Pod:

```bash
kubectl run dns-test --rm -i --image=busybox:1.36 --restart=Never -- nslookup color-api-clusterip.default.svc.cluster.local
```

```text
Server:		10.96.0.10
Address:	10.96.0.10:53

Name:	color-api-clusterip.default.svc.cluster.local
Address: 10.109.33.72
```

Two limits to remember:

- **The ClusterIP only exists inside the cluster.** On the node itself, `curl http://<ClusterIP>/api` works, because kube-proxy sets up its rules on the node. From your laptop it doesn't: getting in from outside is [NodePort Services](nodeport-services.md)' job.
- **The name only works in Pods.** The node doesn't use CoreDNS, so `curl http://color-api-clusterip` on the node fails with `Could not resolve host`. See [Service Discovery & DNS](../networking/dns.md) for more on how names resolve.

## 6. Debug a Service with no endpoints

The most common Service bug is a selector that matches no Pods. Break yours on purpose, with a one-letter typo in the selector, applied from a corrected copy of the manifest:

```bash
sed '/selector:/{n;s/app: color-api$/app: color-apii/}' manifests/services/color-api-clusterip.yaml | kubectl apply -f -
```

(`/selector:/{n;…}` edits only the line right after `selector:`. A plain `s/app: color-api/…/` would also change the Service's own label, which looks exactly the same.) The second terminal fills with failures, and each one fails **instantly**, not after the 2-second timeout:

```bash
kubectl exec traffic-generator -- curl -s -m 2 http://color-api-clusterip/api
```

```text
command terminated with exit code 7
```

Exit code 7 is "couldn't connect": a Service with no endpoints refuses connections right away. Work through it:

```bash
kubectl describe svc color-api-clusterip | grep -E 'Selector|Endpoints'
kubectl get pods -l app=color-apii
kubectl get pods --show-labels
```

```text
Selector:                 app=color-apii
Endpoints:
No resources found in default namespace.
NAME                                   READY   STATUS    RESTARTS   AGE   LABELS
color-api-deployment-579dc9c56-4h7tr   1/1     Running   0          2m    app=color-api,pod-template-hash=579dc9c56
...
```

| Check | What it tells you |
|---|---|
| `Endpoints:` is empty | The Service has nothing to send traffic to |
| `kubectl get pods -l <the selector>` finds nothing | The selector matches no Pod: compare it with the Pods' labels |
| Pods match, but endpoints are still empty | The Pods aren't **ready** (see [Health Checks](../running-and-operating/health-checks.md)) |
| Endpoints are there, but requests fail | `targetPort` doesn't match the port the app listens on |

Here, `app=color-apii` against `app=color-api`. Fix it by applying the real manifest again, and the traffic generator recovers at once:

```bash
kubectl apply -f manifests/services/color-api-clusterip.yaml
```

## Clean up, or keep going

[NodePort Services](nodeport-services.md) continues with the same Deployment and traffic generator, so you can leave everything running. To remove it all:

```bash
kubectl delete -f /tmp/services/traffic-generator.yaml -f manifests/services/color-api-clusterip.yaml -f /tmp/services/color-api-deployment.yaml
rm -rf /tmp/services
```

## Best practices

- **Point clients at the Service name, never at an IP.** Pod IPs change with every Pod, and a ClusterIP with every Service; the name doesn't change at all.
- **Use the short name within a namespace**, and `<service>.<namespace>` to reach across namespaces.
- **When a Service doesn't answer, check its endpoints first.** An empty list is almost always a selector that doesn't match the Pods' labels.
- **Name the Service for what it serves.** Clients will write the name into their configuration, and it's awkward to change later.

---

[← Deploying Color API and Traffic Generator](deploying-color-api.md) · [↑ Contents](../../README.md) · [NodePort Services →](nodeport-services.md)
