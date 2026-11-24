# Understanding Rollouts

> Revisions, change causes, rollbacks, and how to control the pace of a rollout.

---

Every time you change a Deployment's Pod template, it starts a **rollout**, and each rollout becomes a numbered **revision**, backed by its own ReplicaSet. You saw the mechanics in [Updating the Pod Template](updating-pod-template.md). This chapter is about working with that history: recording *why* each revision exists, looking at old ones, rolling back, and controlling how fast a rollout moves.

Start from a fresh copy, and create the Deployment:

```bash
mkdir /tmp/deploy
cp manifests/replicasets-deployments/nginx-deployment.yaml /tmp/deploy/
kubectl apply -f /tmp/deploy/nginx-deployment.yaml
kubectl rollout status deployment/nginx-deployment
```

## 1. Revisions and history

```bash
kubectl rollout history deployment/nginx-deployment
```

```text
deployment.apps/nginx-deployment
REVISION  CHANGE-CAUSE
1         <none>
```

One revision so far: the template you just created. `CHANGE-CAUSE` is empty, because nobody said why it exists. With one revision that's fine. With ten, a list of numbers and `<none>` won't tell you which one to go back to.

## 2. Record why: the change cause

`CHANGE-CAUSE` comes from an annotation named **`kubernetes.io/change-cause`**. Put it on the Deployment, and the Deployment copies it to the ReplicaSet of the revision being rolled out.

### In the manifest

The declarative way is to change the cause **in the same edit** as the change itself. Upgrade nginx to `1.28`, and say so. Open `/tmp/deploy/nginx-deployment.yaml` and make two changes:

```yaml
metadata:
  name: nginx-deployment
  annotations:                                           # add these two lines
    kubernetes.io/change-cause: "Upgrade nginx to 1.28"
  labels:
    app: nginx
...
          image: nginx:1.28                              # was nginx:1.27
```

(Or with GNU `sed` on the node: `sed -i 's/^  labels:$/  annotations:\n    kubernetes.io\/change-cause: "Upgrade nginx to 1.28"\n  labels:/; s/image: nginx:1.27$/image: nginx:1.28/' /tmp/deploy/nginx-deployment.yaml`.)

Apply it, and look at the history:

```bash
kubectl apply -f /tmp/deploy/nginx-deployment.yaml
kubectl rollout status deployment/nginx-deployment
kubectl rollout history deployment/nginx-deployment
```

```text
REVISION  CHANGE-CAUSE
1         <none>
2         Upgrade nginx to 1.28
```

The cause lives on each revision's ReplicaSet, next to its revision number:

```bash
kubectl get rs -l app=nginx -o custom-columns=NAME:.metadata.name,REVISION:.metadata.annotations.deployment\\.kubernetes\\.io/revision,CAUSE:.metadata.annotations.kubernetes\\.io/change-cause
```

```text
NAME                          REVISION   CAUSE
nginx-deployment-7b848bf6bc   2          Upgrade nginx to 1.28
nginx-deployment-86d7c4cfc4   1          <none>
```

### The trap: forgetting to update it

The annotation stays on the Deployment until you change it. Make another template change, adding the `GREETING` environment variable from [Updating the Pod Template](updating-pod-template.md#4-which-changes-cause-a-rollout), **without** touching the cause:

```yaml
          image: nginx:1.28
          env:                       # add these three lines
            - name: GREETING
              value: hello
```

(Or with GNU `sed` on the node: `sed -i '/^          image: nginx:1.28$/a\          env:\n            - name: GREETING\n              value: hello' /tmp/deploy/nginx-deployment.yaml`.)

```bash
kubectl apply -f /tmp/deploy/nginx-deployment.yaml
kubectl rollout status deployment/nginx-deployment
kubectl rollout history deployment/nginx-deployment
```

```text
REVISION  CHANGE-CAUSE
1         <none>
2         Upgrade nginx to 1.28
3         Upgrade nginx to 1.28
```

Revision 3 says it upgraded nginx, which isn't what it did. A stale cause is worse than none. To fix the current revision, overwrite the annotation:

```bash
kubectl annotate deployment/nginx-deployment kubernetes.io/change-cause="Add GREETING env var" --overwrite
kubectl rollout history deployment/nginx-deployment
```

```text
REVISION  CHANGE-CAUSE
1         <none>
2         Upgrade nginx to 1.28
3         Add GREETING env var
```

Then put the same text in your file too, or the next `apply` sets it back. Change the annotation's value to `"Add GREETING env var"` in your editor, or:

```bash
sed -i 's/Upgrade nginx to 1.28"/Add GREETING env var"/' /tmp/deploy/nginx-deployment.yaml
```

The habit to build: **every template change in the file comes with a new `change-cause` in the same edit.**

> You may see `kubectl apply --record` in older guides. It filled in the cause automatically with the command you ran, but it's deprecated. Write the cause yourself.

## 3. Inspect a revision

To see exactly what a revision ran, ask for it by number:

```bash
kubectl rollout history deployment/nginx-deployment --revision=2
```

```text
deployment.apps/nginx-deployment with revision #2
Pod Template:
  Labels:	app=nginx
	pod-template-hash=7b848bf6bc
  Annotations:	kubernetes.io/change-cause: Upgrade nginx to 1.28
  Containers:
   nginx:
    Image:	nginx:1.28
    Port:	<none>
    Host Port:	<none>
    Environment:	<none>
...
```

`1.28`, and no environment variables. That's the template you'd get back by rolling back to it.

## 4. Roll back

Say revision 3 turns out to be a mistake. Go back one revision:

```bash
kubectl rollout undo deployment/nginx-deployment
kubectl rollout status deployment/nginx-deployment
kubectl rollout history deployment/nginx-deployment
```

```text
REVISION  CHANGE-CAUSE
1         <none>
3         Add GREETING env var
4         Upgrade nginx to 1.28
```

Revision 2 is gone from the list, and there's a **4** with its change cause. A rollback doesn't move the Deployment backwards in history; it rolls **forward to a copy** of an old template, which becomes the newest revision. No new ReplicaSet was made, though. The old one is simply scaled back up:

```bash
kubectl get rs -l app=nginx
```

```text
NAME                          DESIRED   CURRENT   READY   AGE
nginx-deployment-69d97f8956   0         0         0       16s
nginx-deployment-7b848bf6bc   3         3         3       28s
nginx-deployment-86d7c4cfc4   0         0         0       29s
```

`7b848bf6bc` is the `1.28` ReplicaSet from revision 2, back in charge. That reuse is why a rollback is fast: the Pods run an image the node has already pulled, through a rollout like any other.

To go further back than one step, name the revision:

```bash
kubectl rollout undo deployment/nginx-deployment --to-revision=1
kubectl rollout history deployment/nginx-deployment
```

```text
REVISION  CHANGE-CAUSE
3         Add GREETING env var
4         Upgrade nginx to 1.28
5         <none>
```

Revision 1 became 5: `nginx:1.27` again, with no cause, because revision 1 never had one.

### Rollbacks and your file

`rollout undo` changes the live Deployment, not your file. Ask `diff` what the next `apply` would do:

```bash
kubectl diff -f /tmp/deploy/nginx-deployment.yaml
```

```diff
-      - image: nginx:1.27
+      - env:
+        - name: GREETING
+          value: hello
+        image: nginx:1.28
```

It would roll forward again, straight back to the version you just rolled back from. That's the rule from [Declarative Object Management](../object-management/declarative-management.md#dont-mix-approaches-on-one-object) once more: the file wins. Treat `rollout undo` as the emergency brake. It gets you back to safety in seconds, and then you **update the file** to match, so the next `apply` doesn't undo the undo.

## 5. Control the pace

Two settings in `spec.strategy.rollingUpdate` decide how a rollout moves, as introduced in [Introduction to Deployments](introduction-to-deployments.md#what-happens-when-you-change-the-template):

| Setting | Means | Default |
|---|---|---|
| `maxSurge` | How many Pods **above** `replicas` may exist during a rollout | `25%` |
| `maxUnavailable` | How many Pods **below** `replicas` may be unavailable during a rollout | `25%` |

Each can be a percentage or a number. For three replicas, some useful combinations:

| `maxSurge` | `maxUnavailable` | What happens | Trade-off |
|---|---|---|---|
| `25%` (=1) | `25%` (=0) | Start one extra, retire one old, repeat | **The default.** Never below 3 available; needs room for a 4th Pod |
| `0` | `1` | Retire one old, start one new, repeat | No extra Pods, but only **2** available during the rollout |
| `3` | `0` | Start all three new Pods at once, then retire the old ones | Fastest, but briefly needs room for **6** Pods |

`maxSurge` and `maxUnavailable` can't both be `0`: the rollout could never make a move.

Try the second combination. Add a `rollingUpdate` block under `strategy` in your file:

```yaml
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 0
      maxUnavailable: 1
```

You don't need another change to trigger a rollout. After the rollback in step 4, the live Deployment runs `1.27`, while your file still says `1.28` with `GREETING`, so applying the file rolls forward, this time with the new settings. Start `kubectl get deploy nginx-deployment -w` in a second terminal, then apply:

```bash
kubectl apply -f /tmp/deploy/nginx-deployment.yaml
kubectl rollout status deployment/nginx-deployment
```

The watch shows the difference:

```text
NAME               READY   UP-TO-DATE   AVAILABLE   AGE
nginx-deployment   3/3     0            3           2s
nginx-deployment   2/3     0            2           2s
nginx-deployment   2/3     1            2           2s
nginx-deployment   3/3     1            3           3s
nginx-deployment   2/3     1            2           3s
nginx-deployment   2/3     2            2           3s
nginx-deployment   3/3     2            3           4s
nginx-deployment   2/3     2            2           4s
nginx-deployment   2/3     3            2           4s
nginx-deployment   3/3     3            3           5s
```

`READY` never goes above `3/3` (no surge), and `AVAILABLE` dips to `2` each time an old Pod goes before its replacement is up. Compare the default, where `READY` reached `4/3` and `AVAILABLE` never left `3`.

> **"Available" depends on readiness.** A new Pod counts as available once it's ready. Without a [readiness probe](../running-and-operating/health-checks.md), "ready" just means the container started, so a broken version can look healthy and the rollout carries on regardless. With one, a version that never gets ready stalls the rollout instead, while the old Pods keep serving. [Troubleshooting Failed Rollouts](troubleshooting-rollouts.md) shows what that looks like.

## 6. Pause and resume

Each template change is normally its own rollout. If you're about to make several changes, you can **pause** the Deployment, make them all, and **resume** to roll them out once:

```bash
kubectl rollout pause deployment/nginx-deployment
kubectl set image deployment/nginx-deployment nginx=nginx:1.27
kubectl set env deployment/nginx-deployment GREETING=hi
kubectl get deploy nginx-deployment
```

```text
NAME               READY   UP-TO-DATE   AVAILABLE   AGE
nginx-deployment   3/3     0            3           5s
```

`UP-TO-DATE 0`: the template changed twice, but no Pods were replaced and no ReplicaSet was created. Resume, and both changes go out together, as **one** new revision:

```bash
kubectl rollout resume deployment/nginx-deployment
kubectl rollout status deployment/nginx-deployment
kubectl rollout history deployment/nginx-deployment
```

```text
REVISION  CHANGE-CAUSE
4         Upgrade nginx to 1.28
5         <none>
6         Add GREETING env var
7         Add GREETING env var
```

Two changes, one new revision, 7. Notice its cause, though: `set image` and `set env` don't touch `change-cause`, so revision 7 inherited the stale text from 6, the trap from step 2 again. The `set` commands are used here for brevity; in real work, make the changes and the new cause in your file, and apply while paused.

## 7. Restart without changing anything

Sometimes you want fresh Pods without changing the app: say, to pick up a new [ConfigMap](../config-and-data/configmap.md) that the containers only read at startup. Deleting the Pods would work, but all at once, like the outage in [ReplicaSets Can't Update Pods](replicaset-updates.md#4-delete-them-all). Instead, ask the Deployment for a rollout:

```bash
kubectl rollout restart deployment/nginx-deployment
kubectl rollout status deployment/nginx-deployment
kubectl get rs -l app=nginx
```

```text
deployment.apps/nginx-deployment restarted

NAME                          DESIRED   CURRENT   READY   AGE
nginx-deployment-…            3         3         3       4s
...
```

A new ReplicaSet, and every Pod replaced through a normal rolling update, with `AVAILABLE` held up as usual. There was no template change from you, so how? `restart` makes one, by stamping the time into the template:

```bash
kubectl get deploy nginx-deployment -o jsonpath='{.spec.template.metadata.annotations}'
```

```
{"kubectl.kubernetes.io/restartedAt":"2026-11-24T20:03:18+08:00"}
```

A changed template means a new revision, like any other rollout (with, again, whatever stale `change-cause` was there before). Unlike `set image`, it doesn't fight your file: the `restartedAt` annotation was never in your manifest, so `apply` [leaves it alone](../object-management/declarative-management.md#4-how-apply-remembers-what-it-manages), and `kubectl diff` stays empty.

## How much history is kept

A Deployment keeps the ReplicaSets of its last **10** revisions by default, scaled to zero. Older ones are deleted, and you can't roll back to them. Change the number with `spec.revisionHistoryLimit`. Setting it to `0` deletes every old ReplicaSet as soon as a rollout finishes, which also means **no rollbacks at all**.

## Clean up

```bash
kubectl delete deployment nginx-deployment
rm -rf /tmp/deploy
```

## Best practices

- **Set `kubernetes.io/change-cause` with every template change, in the same edit.** A history of numbers and `<none>` is no help in an emergency.
- **Use `kubectl rollout undo` to stop the bleeding, then fix the file.** Otherwise the next `apply` rolls you forward again.
- **Pin image tags** (`nginx:1.28`, never `latest`), so every revision means one exact version, and rolling back to it gives you that version.
- **Keep `maxUnavailable` at `0` for services that can't lose capacity**, and give the cluster room for the surge Pods.
- **Wait on `kubectl rollout status` in scripts and CI**, and fail the pipeline if it doesn't finish.
- **Need fresh Pods without changing the app? Use `kubectl rollout restart`**, not `kubectl delete pod`. It replaces them through a normal rolling update, so nothing goes down.
- **Add readiness probes**, so a broken version stalls the rollout instead of replacing your working Pods.

---

[← Updating the Pod Template](updating-pod-template.md) · [↑ Contents](../../README.md) · [Scaling Deployments →](scaling-deployments.md)
