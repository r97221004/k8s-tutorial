# Rollouts Under a Quota

> Fill dev's quota with a Deployment, watch its next rollout stall for lack of room, find out why, and fix it by raising the quota.

---

[Understanding Rollouts](../replicasets-deployments/understanding-rollouts.md#5-control-the-pace) showed that a rolling update briefly runs **more** Pods than `replicas`: with the default `maxSurge`, it starts a new Pod before retiring an old one. Without a quota, that extra Pod only needs a node with room. Under a quota, it also needs room in the namespace's total, and a Deployment that already uses all of the quota has none. In this chapter you'll set that up on purpose, and see what it does to a rollout.

## Before you start

You need dev and its quota from [Working with Resource Quotas](resource-quotas.md). If you cleaned up, create them again:

```bash
kubectl apply -f manifests/resources-probes/dev-ns.yaml
```

Copy this chapter's Deployment, and fill in your Docker Hub username:

```bash
DOCKERHUB_USER=your-dockerhub-user      # ← change this to your username
mkdir -p /tmp/resources
cp manifests/resources-probes/color-api-depl.yaml /tmp/resources/
sed -i "s/<YOUR_DOCKERHUB_USER>/$DOCKERHUB_USER/" /tmp/resources/color-api-depl.yaml
```

## 1. Fill the quota

[`color-api-depl.yaml`](../../manifests/resources-probes/color-api-depl.yaml) runs four replicas of color-api 1.1.0, each with the same requests and limits as in [Setting Requests and Limits](requests-limits.md#1-a-pod-that-fits):

```yaml
replicas: 4
...
          image: <YOUR_DOCKERHUB_USER>/color-api:1.1.0
          resources:
            requests:
              cpu: 200m
              memory: 256Mi
            limits:
              cpu: 500m                # 4 × 500m = 2: all of dev's limits.cpu
              memory: 512Mi
```

```bash
kubectl apply -f /tmp/resources/color-api-depl.yaml -n dev
kubectl rollout status deployment/color-api -n dev
kubectl describe quota dev-quota -n dev
```

```text
Resource         Used  Hard
--------         ----  ----
limits.cpu       2     2
limits.memory    2Gi   4Gi
requests.cpu     800m  1
requests.memory  1Gi   2Gi
```

All four Pods run, and `limits.cpu` is exactly full: four times 500m is 2. Nothing is wrong yet. The quota only refuses what goes **over**.

## 2. Roll out a new version

Change the image to 1.2.0 in your copy, and apply it:

```bash
sed -i 's/color-api:1.1.0/color-api:1.2.0/' /tmp/resources/color-api-depl.yaml
kubectl apply -f /tmp/resources/color-api-depl.yaml -n dev
kubectl rollout status deployment/color-api -n dev --timeout=60s
```

```text
deployment.apps/color-api configured
Waiting for deployment "color-api" rollout to finish: 0 out of 4 new replicas have been updated...
Waiting for deployment "color-api" rollout to finish: 1 out of 4 new replicas have been updated...
Waiting for deployment "color-api" rollout to finish: 1 out of 4 new replicas have been updated...
error: timed out waiting for the condition
```

It started, and then stopped. The ReplicaSets show where:

```bash
kubectl get rs -n dev
```

```text
NAME                   DESIRED   CURRENT   READY   AGE
color-api-6c8f48df87   2         2         2       62s
color-api-7fb8bd6c54   3         1         1       60s
```

The new ReplicaSet should have more Pods than it does: `CURRENT` is below `DESIRED`. Exactly where it stops changes from run to run; you may see 2 new Pods and 1 old. Either way, there are 3 Pods, one short of `replicas`, and it stays that way.

## 3. Find out why

The new ReplicaSet is the one that can't make progress, so its events say why:

```bash
kubectl get events -n dev --field-selector reason=FailedCreate
```

```text
LAST SEEN   TYPE      REASON         OBJECT                             MESSAGE
60s         Warning   FailedCreate   replicaset/color-api-7fb8bd6c54   Error creating: pods "color-api-7fb8bd6c54-k55jm" is forbidden: exceeded quota: dev-quota, requested: limits.cpu=500m, used: limits.cpu=2, limited: limits.cpu=2
...
```

The quota. To replace an old Pod, the rollout first creates a new one, the surge from [Understanding Rollouts](../replicasets-deployments/understanding-rollouts.md#5-control-the-pace). That Pod needs 500m more of `limits.cpu`, and all 2 are in use. The Deployment shows it too, as a condition:

```bash
kubectl describe deployment color-api -n dev | grep -A 5 Conditions
```

```text
Conditions:
  Type             Status  Reason
  ----             ------  ------
  Available        True    MinimumReplicasAvailable
  ReplicaFailure   True    FailedCreate
  Progressing      True    ReplicaSetUpdated
```

Retiring an old Pod frees some room, but only once it has fully shut down, which is how a new Pod or two got in. Until then, every create fails, and each failure makes the ReplicaSet wait longer before it tries again, until it's waiting minutes at a time. So in practice the rollout is stuck. After ten minutes, the Deployment reports it: `Progressing` turns `False`, with `ProgressDeadlineExceeded`, as in [Troubleshooting Failed Rollouts](../replicasets-deployments/troubleshooting-rollouts.md#3-the-deployment-reports-it).

Meanwhile, nothing is broken. Three Pods serve, a mix of old and new versions. It just never finishes.

## 4. Fix it: make room

The rollout needs room for one more Pod than `replicas`. The direct fix is a bigger quota: raise dev's `limits.cpu` from 2 to 3, leaving a full core of headroom. Do it in a copy of the namespace's file, so the change is written down:

```bash
sed 's/limits.cpu: "2000m"/limits.cpu: "3000m"/' manifests/resources-probes/dev-ns.yaml \
  > /tmp/resources/dev-ns.yaml
grep limits.cpu /tmp/resources/dev-ns.yaml
kubectl apply -f /tmp/resources/dev-ns.yaml
```

```text
    limits.cpu: "3000m"
namespace/dev unchanged
resourcequota/dev-quota configured
```

The ReplicaSet doesn't watch the quota, though. It's still waiting out its last delay, which can be several minutes. Start the rollout again, so it tries now:

```bash
kubectl rollout restart deployment/color-api -n dev
kubectl rollout status deployment/color-api -n dev
```

```text
deployment.apps/color-api restarted
Waiting for deployment "color-api" rollout to finish: 1 old replicas are pending termination...
deployment "color-api" successfully rolled out
```

All four Pods now run 1.2.0. Once the old Pods have finished shutting down, the quota has room to spare. If `Used` still shows more than 2, an old Pod is still on its way out; check again in a few seconds:

```bash
kubectl describe quota dev-quota -n dev
```

```text
Resource         Used  Hard
--------         ----  ----
limits.cpu       2     3
limits.memory    2Gi   4Gi
requests.cpu     800m  1
requests.memory  1Gi   2Gi
```

The extra core isn't used in normal running. It's there for the moment during a rollout when one Pod too many exists.

Check the other lines, too. A surge Pod needs room in **every** resource the quota counts, not just the one that ran out. Here, `requests.cpu` is at 800m of 1, so the surge Pod's 200m fits exactly, with nothing to spare. One more replica, or a bigger `maxSurge`, and the next rollout would stall again, this time on `requests.cpu`. To leave real headroom, raise that line as well.

A bigger quota isn't the only way out. You could also lower each Pod's limits, or run fewer replicas, so the Deployment no longer fills the quota. What they all have in common: **leave room for at least one surge Pod.**

## Clean up

```bash
kubectl delete -f manifests/resources-probes/dev-ns.yaml
rm -rf /tmp/resources
```

## Best practices

- **Size a quota for rollouts, not just for running.** Leave room for `maxSurge` extra Pods above what your Deployments use normally.
- **Check the quota before a rollout in a tight namespace.** `kubectl describe quota` shows how much room is left; one Pod's worth is the minimum.
- **Leave room in every line of the quota**, not just the one that ran out. A surge Pod needs all of its requests and limits to fit.
- **When a rollout stalls but no Pod shows an error, look at `FailedCreate` events.** A quota rejection never shows up on a Pod, because the Pod was never created.
- **After making room, restart the rollout.** The ReplicaSet doesn't notice a quota change, and may wait minutes before it tries again.

---

[← Setting Requests and Limits](requests-limits.md) · [↑ Contents](../../README.md) · [Health Probes →](health-probes.md)
