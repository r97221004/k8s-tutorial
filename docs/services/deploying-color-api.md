# Deploying Color API and Traffic Generator

> Run color-api as a Deployment and point the traffic generator at one of its Pods, to see why you need a Service.

---

You have two images: color-api, which says which Pod answered, and the [traffic generator](traffic-generator.md), which keeps asking. Now run them in the cluster, **without** a Service: point the traffic generator straight at one color-api Pod's IP, the way you reached Pods in [Working with Pods](../pods/working-with-pods.md#4-pod-ip--name-why-you-cant-connect-yet).

It works, but only just. By the end of this chapter you'll have seen both problems a Service solves.

## Before you start

You need both images on Docker Hub, from the previous chapter: `<YOUR_DOCKERHUB_USER>/color-api:1.2.0` and `<YOUR_DOCKERHUB_USER>/traffic-generator:1.0.0`. color-api has reported the Pod's name since you [first built it](../pods/from-dockerfile-to-pod.md#1-the-app), and `1.2.0` adds the one-line `?format=text` output that the traffic generator prints.

The two manifests are in [`manifests/services/`](../../manifests/services/). You'll fill in your username and a Pod IP, so work on copies:

Set your Docker Hub username once, then fill it into the copies:

```bash
DOCKERHUB_USER=your-dockerhub-user      # ← change this to your username
mkdir /tmp/services
cp manifests/services/color-api-deployment.yaml manifests/services/traffic-generator.yaml /tmp/services/
sed -i "s/<YOUR_DOCKERHUB_USER>/$DOCKERHUB_USER/" /tmp/services/*.yaml
grep image: /tmp/services/*.yaml        # check: your username, not "your-dockerhub-user"
```

If you leave the username as is, the Pods can't pull their images and get stuck in `ImagePullBackOff`.

## 1. Deploy color-api

[`color-api-deployment.yaml`](../../manifests/services/color-api-deployment.yaml):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: color-api-deployment
  labels:
    app: color-api
spec:
  replicas: 5
  selector:
    matchLabels:
      app: color-api
  template:
    metadata:
      labels:
        app: color-api
    spec:
      containers:
        - name: color-api
          image: <YOUR_DOCKERHUB_USER>/color-api:1.2.0
          ports:
            - containerPort: 8080
```

A [Deployment](../replicasets-deployments/creating-deployments.md) like the nginx one in Part 5, with five replicas so there's plenty to spread traffic across. `containerPort: 8080` is where color-api listens: it runs as a non-root user, so it can't use port 80.

```bash
kubectl apply -f /tmp/services/color-api-deployment.yaml
kubectl rollout status deployment/color-api-deployment
kubectl get pods -l app=color-api -o wide
```

```text
NAME                                   READY   STATUS    RESTARTS   AGE   IP             NODE     ...
color-api-deployment-579dc9c56-6kr62   1/1     Running   0          12s   10.244.0.246   node-1   ...
color-api-deployment-579dc9c56-c7vrk   1/1     Running   0          12s   10.244.0.243   node-1   ...
color-api-deployment-579dc9c56-fhslz   1/1     Running   0          12s   10.244.0.245   node-1   ...
color-api-deployment-579dc9c56-lwmcp   1/1     Running   0          12s   10.244.0.244   node-1   ...
color-api-deployment-579dc9c56-p64wf   1/1     Running   0          12s   10.244.0.242   node-1   ...
```

Five Pods, five IPs.

## 2. Point the traffic generator at one Pod

[`traffic-generator.yaml`](../../manifests/services/traffic-generator.yaml) runs the traffic generator as a plain Pod:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: traffic-generator
  labels:
    app: traffic-generator
spec:
  containers:
    - name: traffic-generator
      image: <YOUR_DOCKERHUB_USER>/traffic-generator:1.0.0
      args:
        - "http://<COLOR_API_POD_IP>:8080/api?format=text"
        - "0.5"
```

`args` are the script's two arguments from [Traffic Generator](traffic-generator.md#1-the-script): the URL, and the interval, two requests a second. They become the arguments of the image's `ENTRYPOINT`. Both are quoted: `0.5` unquoted would be a number, and `args` must be strings.

The URL needs a color-api Pod's IP. Take the first one, remember its name, and fill it in:

```bash
POD_NAME=$(kubectl get pods -l app=color-api -o jsonpath='{.items[0].metadata.name}')
POD_IP=$(kubectl get pod $POD_NAME -o jsonpath='{.status.podIP}')
echo $POD_NAME $POD_IP
sed -i "s/<COLOR_API_POD_IP>/$POD_IP/" /tmp/services/traffic-generator.yaml
```

```
color-api-deployment-579dc9c56-6kr62 10.244.0.246
```

Create the Pod:

```bash
kubectl apply -f /tmp/services/traffic-generator.yaml
kubectl wait --for=condition=Ready pod/traffic-generator --timeout=60s
```

Open a **second terminal** and follow its output there. Keep the first terminal for commands: it holds the `$POD_NAME` you'll need in a moment.

```bash
# in the second terminal
kubectl logs traffic-generator -f
```

```text
Sending requests to http://10.244.0.246:8080/api?format=text every 0.5 seconds.
[2026-11-25 07:48:37] COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-6kr62
[2026-11-25 07:48:38] COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-6kr62
[2026-11-25 07:48:38] COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-6kr62
[2026-11-25 07:48:39] COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-6kr62
```

It works. Leave `logs -f` running.

## 3. Problem one: all the traffic goes to one Pod

Look at the hostnames. Every single request was answered by `6kr62`. You have five color-api Pods, and four of them get nothing. Scaling the Deployment to ten wouldn't help either: the traffic generator only knows one address.

## 4. Problem two: the address breaks

Pods get replaced: a node fails, a rollout happens, someone deletes one. Back in the **first** terminal, delete the Pod the traffic generator is talking to:

```bash
kubectl delete pod $POD_NAME
```

The log in the second terminal turns into:

```text
[2026-11-25 07:48:40] COLOR: blue, HOSTNAME: color-api-deployment-579dc9c56-6kr62
[2026-11-25 07:48:41] (no response from http://10.244.0.246:8080/api?format=text)
[2026-11-25 07:48:43] (no response from http://10.244.0.246:8080/api?format=text)
```

And it stays that way. The Deployment did its job: there are five color-api Pods again.

```bash
kubectl get pods -l app=color-api -o wide
```

```text
NAME                                   READY   STATUS    RESTARTS   AGE   IP             ...
color-api-deployment-579dc9c56-4tcx6   1/1     Running   0          8s    10.244.0.248   ...
color-api-deployment-579dc9c56-c7vrk   1/1     Running   0          50s   10.244.0.243   ...
...
```

But the replacement, `4tcx6`, has a **new** IP, `10.244.0.248`. The traffic generator is still knocking on `10.244.0.246`, where nobody lives anymore. Four healthy color-api Pods are running, and the client can't reach any of them.

(The failures arrive every 2.5 seconds rather than every 0.5: each request now waits out the traffic generator's 2-second timeout.)

## What you need instead

| Problem | What would fix it |
|---|---|
| All traffic goes to one Pod | Something that spreads requests across **all** Pods with `app: color-api` |
| The address dies with the Pod | An address that **stays the same** while the Pods behind it change |

That's a Service: a stable name and IP, with a selector that always matches the Pods that exist right now. Press Ctrl+C in the second terminal to stop the `logs -f`, and **leave both apps running**: in [ClusterIP Services](clusterip-services.md) you'll put a Service in front of color-api and repoint the traffic generator at it.

## Clean up (only if you're stopping here)

```bash
kubectl delete -f /tmp/services/traffic-generator.yaml -f /tmp/services/color-api-deployment.yaml
rm -rf /tmp/services
```

## Best practices

- **Never point a client at a Pod's IP.** Pod IPs belong to one Pod's lifetime, and a Deployment replaces Pods all the time.
- **Pass a client its target as configuration**, like the traffic generator's `args`, so changing where it points doesn't mean rebuilding the image.
- **Quote every `args` value** in YAML. Arguments are strings; `0.5` or `true` unquoted become a number or a boolean, and the Pod is rejected.

---

[← Traffic Generator](traffic-generator.md) · [↑ Contents](../../README.md) · [ClusterIP Services →](clusterip-services.md)
