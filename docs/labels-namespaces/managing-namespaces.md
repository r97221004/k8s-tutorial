# Creating and Managing Namespaces

> Create `dev` and `prod`, run the same Deployment in both, switch your current namespace, and delete one with everything in it.

---

[Namespaces](namespaces.md) showed what a namespace is, and what it does and doesn't keep apart. Now you'll use them. You'll build the picture from that chapter: one cluster, a `dev` and a `prod` namespace, and the same `web` Deployment in each. Along the way you'll see how `kubectl` decides which namespace an object goes to, prove that namespaces don't stop network traffic, and delete a whole environment with one command.

## Before you start

You only need a running cluster. Check that `kubectl` is using the `default` namespace:

```bash
kubectl config get-contexts
```

```text
CURRENT   NAME                          CLUSTER      AUTHINFO           NAMESPACE
*         kubernetes-admin@kubernetes   kubernetes   kubernetes-admin
```

An empty `NAMESPACE` column means `default`. If it shows something else, step 3 explains how to change it.

## 1. Create `dev` and `prod`

A namespace is an object like any other. `kubectl create namespace dev` would make one, but a manifest lets you label it too. [`manifests/labels-namespaces/environments.yaml`](../../manifests/labels-namespaces/environments.yaml) holds two:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: dev
  labels:
    env: dev
---
apiVersion: v1
kind: Namespace
metadata:
  name: prod
  labels:
    env: prod
```

```bash
kubectl apply -f manifests/labels-namespaces/environments.yaml
kubectl get namespaces --show-labels
```

```text
NAME              STATUS   AGE   LABELS
default           Active   5d    kubernetes.io/metadata.name=default
dev               Active   3s    env=dev,kubernetes.io/metadata.name=dev
kube-flannel      Active   5d    k8s-app=flannel,kubernetes.io/metadata.name=kube-flannel,...
kube-node-lease   Active   5d    kubernetes.io/metadata.name=kube-node-lease
kube-public       Active   5d    kubernetes.io/metadata.name=kube-public
kube-system       Active   5d    kubernetes.io/metadata.name=kube-system
prod              Active   3s    env=prod,kubernetes.io/metadata.name=prod
```

Namespaces take labels like anything else, so `kubectl get namespaces -l env` lists just your two environments. Kubernetes also adds `kubernetes.io/metadata.name` to every namespace, holding its name. That one's there so a selector can pick a namespace by name: a [NetworkPolicy](../running-and-operating/security-basics.md#networkpolicy-namespaces-are-not-firewalls), for example, uses a `namespaceSelector` on it to allow traffic from one namespace only.

A namespace's name ends up in DNS names, as [Cross-Namespace Service Communication](cross-namespace-services.md) shows, so the rules are strict: lowercase letters, digits, and `-`, up to 63 characters.

```bash
kubectl create namespace Dev_Team
```

```text
The Namespace "Dev_Team" is invalid: metadata.name: Invalid value: "Dev_Team": a lowercase RFC 1123 label must consist of lower case alphanumeric characters or '-', and must start and end with an alphanumeric character ...
```

## 2. The same Deployment in both

[`manifests/labels-namespaces/web.yaml`](../../manifests/labels-namespaces/web.yaml) is a small nginx Deployment called `web`. Its `metadata` has no `namespace`, so it goes wherever you send it. Send it to both:

```bash
kubectl apply -f manifests/labels-namespaces/web.yaml -n dev
kubectl apply -f manifests/labels-namespaces/web.yaml -n prod
```

```text
deployment.apps/web created
deployment.apps/web created
```

Two objects named `web`, both `created`. In one namespace, the second would have been `unchanged`, since it's the same object. Now look:

```bash
kubectl get deployments
```

```text
No resources found in default namespace.
```

Nothing, because you're still in `default`. Each namespace has its own:

```bash
kubectl get deployments -n dev
```

```text
NAME   READY   UP-TO-DATE   AVAILABLE   AGE
web    2/2     2            2           10s
```

`-A` shows both, and works with `-l`:

```bash
kubectl get pods -A -l app=web
```

```text
NAMESPACE   NAME                   READY   STATUS    RESTARTS   AGE
dev         web-7b86f8987b-28gsr   1/1     Running   0          15s
dev         web-7b86f8987b-7gls8   1/1     Running   0          15s
prod        web-7b86f8987b-r5csv   1/1     Running   0          14s
prod        web-7b86f8987b-zh67f   1/1     Running   0          14s
```

Even the ReplicaSets share a name, `web-7b86f8987b`. That hash comes from the Pod template, and the template is the same in both. Within a namespace, though, names stay unique, as before:

```bash
kubectl create deployment web --image=nginx:1.27 -n dev
```

```text
error: failed to create deployment: deployments.apps "web" already exists
```

## 3. `-n`, `metadata.namespace`, and your current namespace

There are three ways an object's namespace gets decided, and it's worth knowing which one wins.

### In the manifest

A manifest can name its namespace in `metadata.namespace`. Then it goes there, with or without `-n`. [`manifests/labels-namespaces/web-prod.yaml`](../../manifests/labels-namespaces/web-prod.yaml) is the same Deployment, with one line added:

```yaml
metadata:
  name: web
  namespace: prod               # always goes to prod
```

```bash
kubectl apply -f manifests/labels-namespaces/web-prod.yaml
```

```text
deployment.apps/web unchanged
```

`unchanged`, from `default`: the file sent it to `prod`, where `web` already is. If `-n` and the file disagree, `kubectl` refuses, rather than guess:

```bash
kubectl apply -f manifests/labels-namespaces/web-prod.yaml -n dev
```

```text
error: the namespace from the provided object "prod" does not match the namespace "dev". You must pass '--namespace=prod' to perform this operation.
```

### Your current namespace

Without `-n` or `metadata.namespace`, the object goes to your **current namespace**. That's a setting in your kubeconfig, stored with the context. It's been empty all along, which means `default`. Change it to `dev`:

```bash
kubectl config set-context --current --namespace=dev
kubectl config get-contexts
```

```text
CURRENT   NAME                          CLUSTER      AUTHINFO           NAMESPACE
*         kubernetes-admin@kubernetes   kubernetes   kubernetes-admin   dev
```

Now every command without `-n` works in `dev`:

```bash
kubectl get deployments
```

```text
NAME   READY   UP-TO-DATE   AVAILABLE   AGE
web    2/2     2            2           1m
```

`-n` still overrides it for a single command, so `kubectl get deployments -n prod` shows prod's `web`.

In [k9s](../cluster-setup/k9s.md), type `:ns` and press Enter on a namespace to switch to it, or press `0` in any list to see all namespaces at once.

This setting is convenient, and also the classic way to lose track of your objects. It lives in `~/.kube/config`, so it stays after you close the terminal. If, days later, `kubectl get pods` says `No resources found` for Pods you know are there, read the namespace in that message, or check `kubectl config get-contexts`. Switch back now:

```bash
kubectl config set-context --current --namespace=default
```

To sum up, from strongest to weakest:

| Where the namespace comes from | Example | Used when |
|---|---|---|
| `metadata.namespace` in the file | `namespace: prod` | Always. If `-n` says something else, `kubectl` stops with an error |
| `-n` on the command | `-n dev` | The file doesn't name one |
| Your current namespace | `kubectl config set-context --current --namespace=dev` | Neither of the above |
| Nothing set | | `default` |

Which should a manifest use? If the same file deploys to several environments, like `web.yaml` here, leave `metadata.namespace` out and pass `-n`. If an object only ever belongs in one place, such as an add-on that lives in its own namespace, write the namespace into the file, so nobody applies it to the wrong one.

## 4. Namespaces don't stop traffic

[Namespaces](namespaces.md#3-what-a-namespace-does-and-doesnt-separate) said that any Pod can reach any other Pod's IP, whatever their namespaces. Prove it. Take the IP of one of prod's Pods, and call it from a temporary Pod in dev:

```bash
PROD_IP=$(kubectl get pod -n prod -l app=web -o jsonpath='{.items[0].status.podIP}')
kubectl run net-test -n dev --rm -i --restart=Never --image=busybox:1.36 \
  -- wget -qO- -T 3 "$PROD_IP" | grep '<title>'
```

```text
<title>Welcome to nginx!</title>
```

Dev just talked to prod, with nothing in between. Until you add a [NetworkPolicy](../running-and-operating/security-basics.md#networkpolicy-namespaces-are-not-firewalls), the namespaces are only names on the two groups.

## 5. Deleting a namespace deletes everything in it

Deleting a namespace deletes every object inside it. Look at what dev holds:

```bash
kubectl get all -n dev
```

```text
NAME                       READY   STATUS    RESTARTS   AGE
pod/web-7b86f8987b-28gsr   1/1     Running   0          3m
pod/web-7b86f8987b-7gls8   1/1     Running   0          3m

NAME                  READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/web   2/2     2            2           3m

NAME                             DESIRED   CURRENT   READY   AGE
replicaset.apps/web-7b86f8987b   2         2         2       3m
```

Delete it. `--wait=false` returns right away, so you can watch what happens:

```bash
kubectl delete namespace dev --wait=false
kubectl get namespace dev
```

```text
namespace "dev" deleted
NAME   STATUS        AGE
dev    Terminating   3m
```

`Terminating` means Kubernetes is deleting everything inside first: the Deployment, its ReplicaSet, the Pods, and anything else in there. The namespace goes last. If you already see `NotFound`, it was simply faster than you.

A few seconds later:

```bash
kubectl get namespace dev
```

```text
Error from server (NotFound): namespaces "dev" not found
```

Prod didn't notice:

```bash
kubectl get deployments -A -l app=web
```

```text
NAMESPACE   NAME   READY   UP-TO-DATE   AVAILABLE   AGE
prod        web    2/2     2            2           3m
```

This is both the danger and the use of a namespace. One command removes a whole environment, with no confirmation and no undo, which is a good reason to keep RBAC in mind. But it's also the cleanest way to tear down a test setup: put it in its own namespace, and delete just that when you're done.

"Everything inside" means namespaced objects. A PersistentVolumeClaim is deleted with its namespace, but the PersistentVolume behind it belongs to the cluster, and whether it and its data survive depends on its [reclaim policy](../config-and-data/volumes.md#reclaim-policy): `Delete` destroys the data, `Retain` keeps it. Check that before you delete a namespace that holds a database.

Kubernetes protects a few of its own: `kubectl delete namespace default` is refused with `this namespace may not be deleted`, and so are `kube-system` and `kube-public`. `kube-node-lease` isn't on that list, so don't count on the API server to stop you there.

## Clean up

```bash
kubectl delete -f manifests/labels-namespaces/environments.yaml --ignore-not-found
kubectl config get-contexts
```

Deleting `prod` removes its `web` Deployment too. Check that the `NAMESPACE` column is empty or says `default`, so the next chapter starts where it expects.

## Best practices

- **Know your current namespace.** When objects seem to be missing, check `kubectl config get-contexts`, and prefer `-n` in scripts over relying on the current namespace.
- **Leave `metadata.namespace` out of files you deploy to several places.** Pass `-n` instead. Write it in only for objects that belong in exactly one namespace.
- **Label your namespaces**, like `env: prod`, so you can select them the same way as anything else.
- **Use a namespace for anything temporary.** One `kubectl delete namespace` removes everything in it, and leaves the rest of the cluster alone.
- **Check what a namespace holds before you delete it**, especially PersistentVolumeClaims, and their PersistentVolumes' reclaim policy.

---

[← Namespaces](namespaces.md) · [↑ Contents](../../README.md) · [Cross-Namespace Service Communication →](cross-namespace-services.md)
