# Troubleshooting Failed Rollouts

> Spot a rollout that's stuck, find out why, and recover.

---

So far every rollout in this part has finished. This chapter breaks one on purpose, with the most common mistake there is: a typo in the image tag. You'll see what a stuck rollout looks like from the Deployment down to the Pod, how Kubernetes reports it, and the two ways out.

Start from a fresh copy. Before creating the Deployment, add one line to the file, so you won't have to wait ten minutes later on. Step 3 explains it.

```bash
mkdir -p /tmp/deploy
cp manifests/replicasets-deployments/nginx-deployment.yaml /tmp/deploy/
sed -i 's/^  replicas: 3$/  replicas: 3\n  progressDeadlineSeconds: 60/' /tmp/deploy/nginx-deployment.yaml
kubectl apply -f /tmp/deploy/nginx-deployment.yaml
kubectl rollout status deployment/nginx-deployment
```

The top of the `spec` now reads:

```yaml
spec:
  replicas: 3
  progressDeadlineSeconds: 60    # the line you added
```

## 1. Break it

You meant to upgrade to `1.28`, and typed `1.277`. Make the same mistake in the file, and apply:

```bash
sed -i 's/image: nginx:1.27$/image: nginx:1.277/' /tmp/deploy/nginx-deployment.yaml
kubectl apply -f /tmp/deploy/nginx-deployment.yaml
kubectl rollout status deployment/nginx-deployment
```

```text
deployment.apps/nginx-deployment configured
Waiting for deployment "nginx-deployment" rollout to finish: 1 out of 3 new replicas have been updated...
```

The `apply` succeeded: `nginx:1.277` is a perfectly valid image name, so the API server has no reason to reject it. Nobody checks whether the tag **exists** until a node tries to pull it. `rollout status` waits, and waits. After about a minute it gives up:

```text
error: deployment "nginx-deployment" exceeded its progress deadline
```

It exits with a non-zero code, too, which is what makes it useful in a CI pipeline: the deploy step fails instead of reporting success.

## 2. What a stuck rollout looks like

Start at the top:

```bash
kubectl get deploy nginx-deployment
kubectl get rs -l app=nginx
```

```text
NAME               READY   UP-TO-DATE   AVAILABLE   AGE
nginx-deployment   3/3     1            3           2m

NAME                          DESIRED   CURRENT   READY   AGE
nginx-deployment-6b8f7c9d45   1         1         0       70s
nginx-deployment-86d7c4cfc4   3         3         3       2m
```

Read the two outputs together:

- **`READY 3/3` and `AVAILABLE 3`**: the good news. The app is still fully up, on the **old** version. For 3 replicas, the default pace from [Introduction to Deployments](introduction-to-deployments.md#what-happens-when-you-change-the-template) allows zero unavailable Pods, so no old Pod is retired until a new one is ready, and none ever will be.
- **`UP-TO-DATE 1`**: the bad news. Only one Pod runs the new template, and the number isn't moving.
- **The new ReplicaSet** (`6b8f7c9d45`) has its one surge Pod, with `READY 0`. The old one still has all three.

That's the signature of a stuck rollout: the new ReplicaSet has Pods that never get ready, and the old one can't shrink. **Nothing is down, but nothing is moving either.**

> **With more replicas, a stuck rollout does cost capacity.** `maxUnavailable: 25%` rounds down to `0` only below 4 replicas. With 8, it's 2: the Deployment retires two old Pods straight away, their replacements never get ready, and you're stuck with 6 available Pods out of 8 until you act. If you can't afford that, set `maxUnavailable: 0` ([Understanding Rollouts](understanding-rollouts.md#5-control-the-pace)).

This example stalls even without a readiness probe, because a container that can't be pulled never starts, so it's never ready. A version that starts but misbehaves is different. Without a [readiness probe](../running-and-operating/health-checks.md), it counts as ready the moment its container starts, and the rollout carries on, replacing your working Pods with broken ones.

## 3. The Deployment reports it

You didn't have to notice on your own. Look at the Deployment's conditions:

```bash
kubectl describe deploy nginx-deployment
```

```text
...
Conditions:
  Type           Status  Reason
  ----           ------  ------
  Available      True    MinimumReplicasAvailable
  Progressing    False   ProgressDeadlineExceeded
OldReplicaSets:  nginx-deployment-86d7c4cfc4 (3/3 replicas created)
NewReplicaSet:   nginx-deployment-6b8f7c9d45 (1/1 replicas created)
...
```

- **`Available True`**: enough Pods are up to serve. Same good news as before.
- **`Progressing False`, `ProgressDeadlineExceeded`**: the rollout made no progress for `progressDeadlineSeconds`.

That's the line you added. The Deployment counts any step forward, such as a new Pod becoming ready or an old one being retired, as progress, and resets the clock. If the clock runs out, it marks the rollout as failed. The default is **600** seconds, ten minutes, which is why you set it to 60 for this chapter. `rollout status` simply watches this condition, which is why it gave up when it did.

Note what the Deployment **didn't** do: roll back. Kubernetes reports a failed rollout, and leaves it exactly where it stopped. Deciding what to do next is your job.

## 4. Find out why

The Deployment tells you **that** it's stuck. The reason is two layers down, on the Pod, so follow the chain from [Creating and Managing Deployments](creating-deployments.md#3-follow-the-chain-of-owners) downwards:

```bash
kubectl get pods -l app=nginx
```

```text
NAME                                READY   STATUS             RESTARTS   AGE
nginx-deployment-6b8f7c9d45-x2kqp   0/1     ImagePullBackOff   0          90s
nginx-deployment-86d7c4cfc4-4fjzm   1/1     Running            0          2m
nginx-deployment-86d7c4cfc4-9wdlq   1/1     Running            0          2m
nginx-deployment-86d7c4cfc4-tq7nb   1/1     Running            0          2m
```

The new Pod's name starts with the new ReplicaSet's hash, and its `STATUS` says it: [`ImagePullBackOff`](../pods/pod-lifecycle.md#status-is-not-the-phase). (You may catch it as `ErrImagePull` instead. The kubelet alternates between trying, failing, and waiting longer before the next try.) Its Events say exactly what went wrong:

```bash
kubectl describe pod nginx-deployment-6b8f7c9d45-x2kqp     # use your Pod's name
```

```text
...
Events:
  Type     Reason     Age                From               Message
  ----     ------     ----               ----               -------
  Normal   Scheduled  90s                default-scheduler  Successfully assigned default/nginx-deployment-6b8f7c9d45-x2kqp to node-1
  Normal   Pulling    40s (x4 over 90s)  kubelet            Pulling image "nginx:1.277"
  Warning  Failed     39s (x4 over 90s)  kubelet            Failed to pull image "nginx:1.277": rpc error: code = NotFound desc = failed to pull and unpack image "docker.io/library/nginx:1.277": failed to resolve reference "docker.io/library/nginx:1.277": docker.io/library/nginx:1.277: not found
  Warning  Failed     39s (x4 over 90s)  kubelet            Error: ErrImagePull
  Normal   BackOff    5s (x6 over 90s)   kubelet            Back-off pulling image "nginx:1.277"
  Warning  Failed     5s (x6 over 90s)   kubelet            Error: ImagePullBackOff
```

**`not found`**: the registry has an `nginx` repository, but no `1.277` tag. The other messages you might see here point elsewhere: `pull access denied` or `unauthorized` usually means a private repository or missing credentials, not a typo. [From Dockerfile to Pod](../pods/from-dockerfile-to-pod.md) lists the common causes.

## 5. Recover

There are two ways out, and in a real incident you'll often use both, in this order.

### Roll back first

`rollout undo` puts the last working template back, without needing to know what's wrong:

```bash
kubectl rollout undo deployment/nginx-deployment
kubectl rollout status deployment/nginx-deployment
kubectl get rs -l app=nginx
```

```text
deployment.apps/nginx-deployment rolled back
deployment "nginx-deployment" successfully rolled out

NAME                          DESIRED   CURRENT   READY   AGE
nginx-deployment-6b8f7c9d45   0         0         0       3m
nginx-deployment-86d7c4cfc4   3         3         3       4m
```

The broken ReplicaSet is scaled to zero, and its Pod is gone. The old Pods were never replaced, so the undo didn't need to start any new ones. The old ReplicaSet, still at full size, simply became the current one again. The Deployment's `Progressing` condition is `True` again.

But your file still says `1.277`. As in [Understanding Rollouts](understanding-rollouts.md#rollbacks-and-your-file), the next `apply` would break it all over again:

```bash
kubectl diff -f /tmp/deploy/nginx-deployment.yaml
```

```diff
-      - image: nginx:1.27
+      - image: nginx:1.277
```

### Then fix forward

Fix the file to say what you meant all along, and apply:

```bash
sed -i 's/image: nginx:1.277$/image: nginx:1.28/' /tmp/deploy/nginx-deployment.yaml
kubectl apply -f /tmp/deploy/nginx-deployment.yaml
kubectl rollout status deployment/nginx-deployment
kubectl get rs -l app=nginx
```

```text
deployment.apps/nginx-deployment configured
deployment "nginx-deployment" successfully rolled out

NAME                          DESIRED   CURRENT   READY   AGE
nginx-deployment-6b8f7c9d45   0         0         0       4m
nginx-deployment-7b848bf6bc   3         3         3       20s
nginx-deployment-86d7c4cfc4   0         0         0       5m
```

A third ReplicaSet, for `1.28`, with all three Pods. File, cluster, and intention finally agree.

You could also have skipped the undo and applied the fixed file straight away. A new template replaces a stuck rollout at any point, so fixing forward works on its own. Roll back first when you **don't** know the cause yet, or the fix will take a while: it gets you to a known-good state while you investigate.

## 6. Other ways a rollout gets stuck

The image typo is the most common case, but the investigation is always the same: the Deployment says it's stuck, the ReplicaSets show which Pods are new, and the new Pods' `STATUS` and Events say why. What you find there points to the cause:

| What you see on the new Pods | Likely cause | Look at |
|---|---|---|
| `ErrImagePull`, `ImagePullBackOff` | Wrong image name or tag, or a private registry without credentials | `describe pod` → Events |
| `CrashLoopBackOff` | The app starts, then exits: bad config, a missing env var, a bug | `kubectl logs <pod> --previous` ([CrashLoopBackOff](../pods/pod-lifecycle.md#crashloopbackoff)) |
| `Running`, but `READY 0/1` | The readiness probe keeps failing | `describe pod` → `Readiness probe failed` events ([Health Checks](../running-and-operating/health-checks.md)) |
| `Pending`, never scheduled | No node has room for the requested CPU or memory | `describe pod` → `FailedScheduling` events ([Resource Requests & Limits](../running-and-operating/resources.md)) |
| **No** new Pods at all | The ReplicaSet can't create them, for example because of a quota | `describe rs` on the new ReplicaSet → `FailedCreate` events |

In each case, the same two ways out apply: `rollout undo` to get back to safety, then fix the file and apply.

## Clean up

```bash
kubectl delete deployment nginx-deployment
rm -rf /tmp/deploy
```

## Best practices

- **Wait on `kubectl rollout status` in CI.** It exits non-zero when the progress deadline passes, so a broken deploy fails the pipeline.
- **Set `progressDeadlineSeconds` to fit your app.** A bit longer than your slowest healthy rollout: short enough to fail fast, long enough not to fail a slow but working one.
- **Remember that Kubernetes reports a failed rollout, but doesn't undo it.** The rollout stays stuck until you roll back or apply a fix.
- **Go Deployment → ReplicaSet → Pod.** The Deployment says it's stuck; the reason is in the new Pods' `STATUS` and Events.
- **Roll back first when you're not sure, then fix the file.** `rollout undo` buys time, and fixing the file keeps the next `apply` from breaking it again.
- **Add readiness probes.** They're what make a broken version stall, with the old Pods still serving, instead of quietly replacing them.

---

[← Scaling Deployments](scaling-deployments.md) · [↑ Contents](../../README.md) · [Scheduling, Taints & Tolerations →](../core-objects/scheduling.md)
