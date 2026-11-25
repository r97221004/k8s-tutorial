# NodePort Services

> Open a port on every node, and reach color-api from your laptop.

---

A ClusterIP only exists inside the cluster. The traffic generator can reach color-api through one, but your laptop can't: as [ClusterIP Services](clusterip-services.md#5-how-the-name-works) showed, even the node can only reach it by IP, and nothing outside can reach it at all.

A **NodePort Service** adds the missing piece. It's a ClusterIP Service, **plus** one port opened on every node, so anything that can reach a node can reach the Service. In this chapter you'll create one, try it on the node, and then get through from your laptop, which takes one more step outside Kubernetes.

## Before you start

You need the color-api Deployment from the previous chapters. The traffic generator and `color-api-clusterip` can keep running: this chapter doesn't use them, and doesn't get in their way.

If you've cleaned up, or opened a new terminal since, set the Deployment up again:

```bash
DOCKERHUB_USER=your-dockerhub-user      # ← change this to your username
mkdir -p /tmp/services
cp manifests/services/color-api-deployment.yaml /tmp/services/
sed -i "s/<YOUR_DOCKERHUB_USER>/$DOCKERHUB_USER/" /tmp/services/color-api-deployment.yaml
kubectl apply -f /tmp/services/color-api-deployment.yaml
kubectl rollout status deployment/color-api-deployment
```

For steps 3 and 4 you'll also need a terminal on your **laptop**, and access to your VM's network settings in your cloud provider: the portal, or its CLI. On Azure, the commands below use the [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli); run `az login` once before you start.

## 1. Create the Service

[`manifests/services/color-api-nodeport.yaml`](../../manifests/services/color-api-nodeport.yaml):

```yaml
apiVersion: v1
kind: Service
metadata:
  name: color-api-nodeport
  labels:
    app: color-api
spec:
  type: NodePort
  selector:
    app: color-api        # the same Pods as color-api-clusterip
  ports:
    - port: 80            # the Service's own port, on its ClusterIP
      targetPort: 8080    # color-api listens on 8080
      nodePort: 30007     # opened on every node; must be in 30000-32767
```

It's the ClusterIP Service with two changes: `type: NodePort`, and a third port. The three ports are the ones from [What Are Services](what-are-services.md#the-manifest), now all in use.

`nodePort` is optional. Leave it out, and Kubernetes picks a free one from `30000–32767`. Here it's set, because in step 4 you'll open **exactly** this port in a firewall, and a port that's different on every `apply` would make that a guessing game. If another Service already holds the port, the API server rejects the manifest with `provided port is already allocated`.

There's nothing to fill in, so apply it straight from the repo:

```bash
kubectl apply -f manifests/services/color-api-nodeport.yaml
kubectl get svc -l app=color-api
```

```text
NAME                  TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
color-api-clusterip   ClusterIP   10.109.33.72    <none>        80/TCP         20m
color-api-nodeport    NodePort    10.104.82.19    <none>        80:30007/TCP   0s
```

Two Services, side by side. (If you cleaned up after the last chapter, you'll see only `color-api-nodeport`. The rest still applies.)

- **`80:30007/TCP`** reads as "port `80` on the ClusterIP, port `30007` on every node".
- **The NodePort Service has a `CLUSTER-IP` too.** Every NodePort Service is also a ClusterIP Service, so Pods can still reach it as `http://color-api-nodeport`.
- **Both select `app: color-api`**, so both send traffic to the same five Pods. A Pod doesn't belong to a Service; any number of Services can select it.

## 2. Try it on the node

You're working on the node, so start there:

```bash
for i in 1 2 3 4 5; do curl -s "http://localhost:30007/api?format=text"; done
```

```text
COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-5hhm4
COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-2kfwp
COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-5hhm4
COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-b6754
COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-pd62n
```

Each `curl` is a new connection, so the requests spread across the Pods, just as they did through the ClusterIP. That's because, past the node port, it **is** the ClusterIP: kube-proxy's rules on the node send traffic for port `30007` on to the Service, and from there to a Pod.

`localhost` works because you're on the node. Anything else has to use the node's address. Kubernetes knows it:

```bash
kubectl get nodes -o wide
```

```text
NAME     STATUS   ROLES           AGE   VERSION   INTERNAL-IP      EXTERNAL-IP   ...
node-1   Ready    control-plane   4d    v1.30.x   172.28.125.129   <none>        ...
```

```bash
curl -s "http://172.28.125.129:30007/api?format=text"     # use your INTERNAL-IP
```

```text
COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-2kfwp
```

On a cluster with more nodes, every node's address would work the same way, even one that runs none of the color-api Pods: kube-proxy runs on every node, and forwards the traffic to a Pod wherever it is.

## 3. Why your laptop can't use that address

`INTERNAL-IP` is the address the VM has on its cloud provider's **private** network. Your laptop isn't on that network, so `172.28.125.129` leads nowhere from there. And `EXTERNAL-IP` is `<none>`: the VM's public address belongs to the cloud provider, and kubeadm doesn't know it.

The public address is the one you already use every day: the `<YOUR_VM_IP>` you SSH to, from [Before You Start](../cluster-setup/before-you-start.md#2-work-on-the-node). On your **laptop**, try it:

```bash
VM_IP=your-vm-ip        # ← change this to the address you SSH to
curl -m 5 "http://$VM_IP:30007/api?format=text"
```

```text
curl: (28) Connection timed out after 5001 milliseconds
```

A timeout, not an error from color-api. The request never reached the VM. Kubernetes opened port `30007` on the node, but between your laptop and the node there's the **cloud provider's firewall**, on Azure a Network Security Group (NSG), and it only lets in what it's told to. Out of the box, that's SSH on port `22`. Port `30007` is dropped before the VM ever sees it.

So reaching a NodePort from outside takes two things, and Kubernetes only does the first:

| Layer | Who opens it | Status |
|---|---|---|
| The port on the node | Kubernetes, when you create the NodePort Service | ✓ Done in step 1 |
| The path from your laptop to the node | You, in the cloud provider's firewall | ✗ Next |

## 4. Open the firewall, for your laptop only

Find your laptop's public address first, so the rule lets in **only you**, not the whole internet:

```bash
MY_IP=$(curl -4 -s https://ifconfig.me)
echo $MY_IP
```

`-4` matters: if your network also has IPv6, `ifconfig.me` would otherwise answer with your IPv6 address, while your connection to the VM goes over IPv4. A rule for the wrong address lets nothing in, and the timeout would look exactly the same.

Then add an inbound rule for TCP port `30007` from that address. On Azure, with the Azure CLI on your laptop, set your VM's resource group and NSG name once:

```bash
RESOURCE_GROUP=your-resource-group      # ← change these two
NSG_NAME=your-vm-nsg
```

And create the rule:

```bash
az network nsg rule create \
  --resource-group $RESOURCE_GROUP \
  --nsg-name $NSG_NAME \
  --name allow-nodeport-30007 \
  --priority 1010 \
  --protocol Tcp \
  --destination-port-ranges 30007 \
  --source-address-prefixes $MY_IP
```

Rules are inbound and allowing by default, so that's all it needs. The NSG's name is on the VM's **Networking** page in the Azure portal, where you can also add the same rule by hand. On another cloud, the idea is identical: an inbound rule for TCP `30007` from your IP, in an AWS security group or a GCP firewall rule.

> If `ufw` or another firewall is enabled on the VM itself, it needs the port too: `sudo ufw allow 30007/tcp`. Most cloud images ship with it inactive; `sudo ufw status` tells you.

Try again from your laptop:

```bash
for i in 1 2 3 4 5; do curl -s "http://$VM_IP:30007/api?format=text"; done
```

```text
COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-b6754
COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-4h7tr
COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-b6754
COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-hv7pt
COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-2kfwp
```

color-api, from outside the cluster. Now open `http://<YOUR_VM_IP>:30007/` in your browser:

```text
Hello from color-api!
Served by color-api-deployment-579dc9c56-b6754
```

Refresh quickly, several times in a row. The Pod name **stays the same**, unlike with `curl`. The browser keeps its connection open and reuses it, and kube-proxy picks a Pod per **connection**, not per request. Now wait ten seconds and refresh again: color-api closes a connection after about five idle seconds, so the browser has to open a new one, and you'll likely land on another Pod.

## 5. Where NodePort falls short

NodePort is the simplest way in from outside, and for a lab or a quick test, it's enough. For real users, it has limits:

| Limit | Why it matters |
|---|---|
| **Ports `30000–32767` only** | Users have to type `:30007`. Ports `80` and `443`, the ones browsers use by default, aren't available |
| **Clients pick a node** | On a cluster with several nodes, clients need one node's address. If that node goes down, they have to switch to another themselves |
| **One port per Service** | Ten web apps means ten ports, ten firewall rules, and ten URLs to hand out |
| **The firewall is on you** | Kubernetes opens the port on the node, but you open, and close, the path to it |

The next layers up fix these. A **LoadBalancer** Service puts one stable address in front of all the nodes, on normal ports; it builds on a NodePort, and needs a cloud provider or something like MetalLB, as [What Are Services](what-are-services.md#loadbalancer-on-a-bare-kubeadm-cluster) showed. An **[Ingress](../networking/ingress.md)** routes HTTP for many apps through one entry point, by hostname or path.

## Clean up

Close the firewall first: a rule you've forgotten about is an open door. On your laptop, in the terminal where you set `RESOURCE_GROUP` and `NSG_NAME`:

```bash
az network nsg rule delete \
  --resource-group $RESOURCE_GROUP \
  --nsg-name $NSG_NAME \
  --name allow-nodeport-30007
```

Then, on the node, delete the NodePort Service:

```bash
kubectl delete -f manifests/services/color-api-nodeport.yaml
```

If you're stopping here, remove everything else from this part too:

```bash
kubectl delete \
  -f /tmp/services/traffic-generator.yaml \
  -f manifests/services/color-api-clusterip.yaml \
  -f /tmp/services/color-api-deployment.yaml \
  --ignore-not-found
rm -rf /tmp/services
```

## Best practices

- **Use NodePort for labs and tests**, and a LoadBalancer or an Ingress for real users.
- **Pin `nodePort` when something outside depends on it**, like a firewall rule. Otherwise, let Kubernetes pick one.
- **Open the firewall for your own IP, not for everyone.** A NodePort with a world-open rule is reachable by anyone who scans the port.
- **Delete the firewall rule with the Service.** Kubernetes cleans up the port on the node, but not the cloud provider's rule.
- **Remember that a NodePort Service is still a ClusterIP Service.** Pods in the cluster should keep using its name, not the node port.

---

[← ClusterIP Services](clusterip-services.md) · [↑ Contents](../../README.md) · [ExternalName Services →](externalname-services.md)
