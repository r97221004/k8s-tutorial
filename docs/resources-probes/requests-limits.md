# Setting Requests and Limits

> Put Pods under dev's and prod's quotas, see a container killed at its memory limit, and rescue a Deployment with a LimitRange's defaults.

---

[Working with Resource Quotas](resource-quotas.md) gave `dev` and `prod` their quotas, with nothing running under them. Now you'll fill them. You'll create a Pod that fits dev's quota and one that doesn't, then meet the other checks from the [introduction](introduction-to-resources.md#4-how-they-decide-together) in turn: what leaves a Pod `Pending`, a container slowed down, a container killed, and a Deployment that can't create Pods until a LimitRange gives it defaults.

## Before you start

You need the color-api image from [Traffic Generator](../services/traffic-generator.md), and the two namespaces with their quotas from the previous chapter, which deleted them in its clean-up. Create them again:

```bash
kubectl apply -f manifests/resources-probes/dev-ns.yaml -f manifests/resources-probes/prod-ns.yaml
```

Two of this chapter's manifests use your color-api image. Copy them, and fill in your Docker Hub username:

```bash
DOCKERHUB_USER=your-dockerhub-user      # ← change this to your username
mkdir -p /tmp/resources
cp manifests/resources-probes/color-api-pod.yaml manifests/resources-probes/heavy-api-pod.yaml /tmp/resources/
sed -i "s/<YOUR_DOCKERHUB_USER>/$DOCKERHUB_USER/" /tmp/resources/*.yaml
grep image: /tmp/resources/*.yaml        # check: your username
```

None of the Pod manifests names a namespace, so you choose one with `-n` each time.

## 1. A Pod that fits

[`color-api-pod.yaml`](../../manifests/resources-probes/color-api-pod.yaml) is a single color-api Pod with requests and limits:

```yaml
containers:
  - name: color-api
    image: <YOUR_DOCKERHUB_USER>/color-api:1.2.0
    resources:
      requests:
        cpu: 200m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 512Mi
```

Create it in dev, and look at the quota again:

```bash
kubectl apply -f /tmp/resources/color-api-pod.yaml -n dev
kubectl describe quota dev-quota -n dev
```

```text
Name:            dev-quota
Namespace:       dev
Resource         Used   Hard
--------         ----   ----
limits.cpu       500m   2
limits.memory    512Mi  4Gi
requests.cpu     200m   1
requests.memory  256Mi  2Gi
```

`Used` is exactly what the Pod declared. The Pod has barely started, and color-api uses almost nothing, but the quota counts the numbers in the spec, not the real usage. Dev now has 800m of CPU requests left.

## 2. A Pod that doesn't

[`heavy-api-pod.yaml`](../../manifests/resources-probes/heavy-api-pod.yaml) runs the same image, but asks for much more: a whole core as its request, and two as its limit.

```yaml
resources:
  requests:
    cpu: "1"                 # a whole core: all of dev's quota
    memory: 1Gi
  limits:
    cpu: "2"
    memory: 2Gi
```

```bash
kubectl apply -f /tmp/resources/heavy-api-pod.yaml -n dev
```

```text
Error from server (Forbidden): error when creating "/tmp/resources/heavy-api-pod.yaml": pods "heavy-api" is forbidden: exceeded quota: dev-quota, requested: limits.cpu=2,requests.cpu=1, used: limits.cpu=500m,requests.cpu=200m, limited: limits.cpu=2,requests.cpu=1
```

This time two sums are over, and the message lists both, in the same order in each part: `requests.cpu` would be 200m + 1 out of 1, and `limits.cpu` would be 500m + 2 out of 2. Memory fits, so it isn't mentioned. The Pod was never created, so there's nothing to delete.

The same file fits prod, which has six times as much:

```bash
kubectl apply -f /tmp/resources/heavy-api-pod.yaml -n prod
kubectl get quota -A
```

```text
pod/heavy-api created
NAMESPACE   NAME         AGE   REQUEST                                            LIMIT
dev         dev-quota    1m    requests.cpu: 200m/1, requests.memory: 256Mi/2Gi   limits.cpu: 500m/2, limits.memory: 512Mi/4Gi
prod        prod-quota   1m    requests.cpu: 1/6, requests.memory: 1Gi/12Gi       limits.cpu: 2/12, limits.memory: 2Gi/24Gi
```

Each namespace keeps its own count. Prod's Pod used up nothing of dev's.

## 3. Requests and the scheduler

heavy-api fit prod's quota, but a quota only checks a namespace's **total**. Whether a **node** has room is the scheduler's job, and it goes by requests alone. prod's quota allows 6 cores of requests; if your node had only 4 cores unreserved, a Pod requesting 5 would pass the quota, be created, and then have nowhere to go. It would stay `Pending`, and `kubectl describe pod` would show why, in its events:

```text
Events:
  Type     Reason            Age   From               Message
  ----     ------            ----  ----               -------
  Warning  FailedScheduling  4s    default-scheduler  0/1 nodes are available: 1 Insufficient cpu. preemption: 0/1 nodes are available: 1 No preemption victims found for incoming pod.
```

`Insufficient cpu`: no node has that much CPU left unreserved. The Pod waits until one does, and that's the first thing to check when a Pod is stuck `Pending`. Note the difference from step 2: a Pod over the quota is never created, and a Pod no node can take is created and waits.

## 4. Past a limit: slowed down or killed

The two limits behave very differently, because CPU and memory do.

**CPU** can be shared out over time. The kernel gives a container with a 200m limit 20 milliseconds of CPU in every 100. Once it has used them, it waits for the next 100. A container at its CPU limit is **throttled**: it keeps running, just slower. For a web app, that shows up as slow responses, not as errors or restarts, which makes a tight CPU limit easy to miss.

**Memory** can't be taken back once a process has it, so there's nothing to slow down. A container that goes past its memory limit is **killed**. This one is worth seeing. [`memory-hog.yaml`](../../manifests/resources-probes/memory-hog.yaml) runs `tail /dev/zero`, which reads an endless stream with no line breaks, and keeps it all in memory, waiting for a line to end. Its limit is 64Mi:

```bash
kubectl apply -f manifests/resources-probes/memory-hog.yaml -n dev
```

Within seconds:

```bash
kubectl get pod memory-hog -n dev
```

```text
NAME         READY   STATUS             RESTARTS      AGE
memory-hog   0/1     CrashLoopBackOff   1 (13s ago)   20s
```

It has already died and been restarted. Depending on when you look, `STATUS` says `OOMKilled`, right after a kill, or `CrashLoopBackOff`, while Kubernetes waits before the next restart, as in [Pod Lifecycle](../pods/pod-lifecycle.md). Either way, the reason it died is kept in `Last State`:

```bash
kubectl describe pod memory-hog -n dev | grep -A 3 -E 'State:|Last State:'
```

```text
    State:          Waiting
      Reason:       CrashLoopBackOff
    Last State:     Terminated
      Reason:       OOMKilled
      Exit Code:    137
      Started:      Fri, 27 Nov 2026 15:35:38 +0800
```

`OOMKilled`: when the container went past 64Mi, the kernel killed it. Exit code 137 means it was killed with `SIGKILL`, with no warning and no chance to clean up. Kubernetes restarts it, it fills up again, and it's killed again, with longer and longer waits in between. A real app with a memory leak, or a limit set too low, looks just like this: restarts that climb, and `OOMKilled` in `Last State`.

| | Past the CPU limit | Past the memory limit |
|---|---|---|
| What happens | The container waits for its next slice of CPU time | The kernel kills the container |
| You see | Slow responses | `OOMKilled`, exit code 137, restarts climbing |
| The container | Keeps running | Is restarted, and may end in `CrashLoopBackOff` |

Delete it, to free up dev's quota for the last step:

```bash
kubectl delete pod memory-hog -n dev --now
```

## 5. QoS classes

The requests and limits a Pod sets also put it in a **Quality of Service class**. Kubernetes works it out; you don't set it. You can read it with `kubectl get pod <name> -o jsonpath='{.status.qosClass}'`.

| Class | When | Under memory pressure |
|---|---|---|
| `Guaranteed` | Every container's requests equal its limits, for both CPU and memory | Evicted last |
| `Burstable` | At least one request or limit is set, but not equal all round, like `color-api` | In between |
| `BestEffort` | Nothing set at all | Evicted first |

When a node runs short of memory, the kubelet evicts Pods to free some, and the class decides the order. `BestEffort` can't exist in dev, since the quota insists on requests and limits. But every Pod you created before this Part set nothing, so every one of them was `BestEffort`: first in line to go.

## 6. Defaults with a LimitRange

The [introduction](introduction-to-resources.md#5-a-quota-makes-requests-and-limits-required) warned of a trap: in a namespace with a quota, a Deployment without resources is accepted, and then can't create a single Pod. Make it happen:

```bash
kubectl create deployment web --image=nginx:1.27 -n dev
kubectl get deployment web -n dev
```

```text
deployment.apps/web created
NAME   READY   UP-TO-DATE   AVAILABLE   AGE
web    0/1     0            0           3s
```

No error from `create`, and no Pod. The reason is on the ReplicaSet, which keeps trying:

```bash
kubectl describe rs -n dev -l app=web | grep -A 4 Events
```

```text
Events:
  Type     Reason        Age   From                   Message
  ----     ------        ----  ----                   -------
  Warning  FailedCreate  5s    replicaset-controller  Error creating: pods "web-7b86f8987b-n2wwm" is forbidden: failed quota: dev-quota: must specify limits.cpu for: nginx; limits.memory for: nginx; requests.cpu for: nginx; requests.memory for: nginx
  Warning  FailedCreate  5s    replicaset-controller  Error creating: pods "web-7b86f8987b-dwzvf" is forbidden: ...
```

You could add `resources` to the Deployment. But every app in dev would need the same fix, and the next one someone deploys would fall into the same trap. A **LimitRange** fixes it for the whole namespace, by filling in defaults for any container that doesn't set its own. [`dev-limitrange.yaml`](../../manifests/resources-probes/dev-limitrange.yaml):

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: dev-defaults
  namespace: dev
spec:
  limits:
    - type: Container
      defaultRequest:            # used when a container sets no request
        cpu: 100m
        memory: 128Mi
      default:                   # used when a container sets no limit
        cpu: 200m
        memory: 256Mi
```

Apply it, and watch the Deployment. You don't touch the Deployment at all:

```bash
kubectl apply -f manifests/resources-probes/dev-limitrange.yaml
kubectl get deployment web -n dev
```

A few seconds later:

```text
NAME   READY   UP-TO-DATE   AVAILABLE   AGE
web    1/1     1            1           11s
```

The ReplicaSet tried again, and this time the API server filled in the defaults before the quota checked the Pod. The Pod's spec shows them:

```bash
kubectl get pod -n dev -l app=web -o jsonpath='{.spec.containers[0].resources}{"\n"}'
```

```text
{"limits":{"cpu":"200m","memory":"256Mi"},"requests":{"cpu":"100m","memory":"128Mi"}}
```

Defaults only fill gaps. A container that sets its own values, like color-api, keeps them. `kubectl describe namespace dev` now lists the LimitRange under the quota, where [Working with Resource Quotas](resource-quotas.md#4-see-all-of-a-namespaces-rules) said `No LimitRange resource`. Its table also has `Min` and `Max` columns: a LimitRange can reject a container whose values fall outside a range, which stops one Pod from taking the whole quota.

## Clean up

```bash
kubectl delete -f manifests/resources-probes/dev-ns.yaml -f manifests/resources-probes/prod-ns.yaml
rm -rf /tmp/resources
```

Deleting the namespaces removes everything in them: the Pods, the Deployment, the quotas, and the LimitRange.

## Best practices

- **Set requests from what the app really uses.** They're what the scheduler places by, and what the quota counts.
- **Always set a memory limit.** A leak then kills one container, with a clear `OOMKilled`, instead of starving the node.
- **Be careful with tight CPU limits.** A throttled app doesn't fail; it just gets slow. If responses are slow and CPU sits at the limit, raise it.
- **Use `Guaranteed` for what matters most.** Requests equal to limits put a Pod last in line for eviction.
- **Give every namespace with a quota a LimitRange.** Apps that forget `resources` then get sensible defaults, instead of a Deployment that silently creates nothing.
- **When a Pod won't start, find out which check stopped it.** `Forbidden` is the quota, `Pending` is the scheduler, and `OOMKilled` is the memory limit.

---

[← Working with Resource Quotas](resource-quotas.md) · [↑ Contents](../../README.md) · [Rollouts Under a Quota →](rollouts-and-quotas.md)
