# Deployment

> The controller you'll actually use — declare how many replicas of a Pod you want, and it keeps them running, replaces dead ones, and rolls out new versions.

---

## Before you start

Start from a clean `default` namespace. If an old `web` Deployment exists from a previous run, delete it first:

```bash
kubectl delete -f manifests/core-objects/web-deployment.yaml --ignore-not-found
```

## Why you don't deploy Pods directly

A bare [Pod](pod.md) has no safety net: if it crashes hard or its node dies, nothing brings it back. You also can't scale it, and updating its image means deleting and recreating it by hand — with downtime.

A **Deployment** fixes all of that. You declare a *desired state* — "run 3 replicas of this Pod template" — and a controller continuously works to make it true. This is the [declarative model](../getting-started/what-is-kubernetes.md) in action:

- **Self-healing** — a Pod (or whole node) dies → the Deployment creates a replacement to get back to 3.
- **Scaling** — change `replicas: 3` to `replicas: 5` and the cluster converges.
- **Rolling updates** — change the image and Pods are replaced gradually, with zero downtime (see [Rolling Update & Rollback](../running-and-operating/rolling-updates.md)).

> **Analogy:** a Deployment is like a **thermostat**. You set a target — _"3 replicas"_ — and it constantly checks the room and nudges reality back toward that number. Individual Pods come and go; the target is what you manage, not each Pod by hand.

Under the hood a Deployment manages a [ReplicaSet](replicaset.md), which manages the Pods. You almost always work at the Deployment level.

```
Deployment  ──manages──▶  ReplicaSet  ──manages──▶  Pods
```

## A classic example

This Deployment runs three nginx replicas. The `selector` must match the Pod template's `labels` — that's how the Deployment knows which Pods are "its".

▶ **Runnable manifest:** [`manifests/core-objects/web-deployment.yaml`](../../manifests/core-objects/web-deployment.yaml)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  labels:
    app: web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web              # ← must match template.metadata.labels below
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: web
          image: nginx:1.27   # pin a version — never rely on :latest
          ports:
            - containerPort: 80
          resources:           # best practice: always set requests/limits
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 200m
              memory: 128Mi
```

**Reading it top to bottom:**

- `replicas: 3` — how many copies you want running.
- `template:` — the blueprint the Deployment stamps out, copy by copy. It's just the [Pod](pod.md) spec you already know (without a name — each Pod gets an auto-generated one like `web-6f8c…-2kx9q`).
- `selector.matchLabels` — how the Deployment finds the Pods it owns. **It must equal the template's `labels`**, which is why `app: web` appears in both the `selector` and the `template`. Mismatch them and the Deployment won't recognize its own Pods — a classic first-timer trip-up.
- `resources` — reserves a little CPU/memory for each Pod; don't fuss over the exact numbers yet ([Resource Requests & Limits](../running-and-operating/resources.md) explains them).

> 💡 **Don't memorize YAML.** Generate a starting point and edit it — this is how most people write manifests:
>
> ```bash
> kubectl create deployment web --image=nginx:1.27 --dry-run=client -o yaml > web-deployment.yaml
> ```
>
> This example is deliberately minimal. A production Deployment also adds [health probes](../running-and-operating/health-checks.md), covered in their own chapter.

Apply it and watch the three layers appear:

```bash
kubectl apply -f manifests/core-objects/web-deployment.yaml
kubectl rollout status deployment/web    # blocks until all replicas are ready
kubectl get deploy,rs,pods -l app=web
```

```
NAME                  READY   UP-TO-DATE   AVAILABLE
deployment.apps/web   3/3     3            3

NAME                             DESIRED   CURRENT   READY
replicaset.apps/web-6f8c…        3         3         3

NAME                   READY   STATUS    RESTARTS
pod/web-6f8c…-2kx9q    1/1     Running   0
pod/web-6f8c…-7nv4d    1/1     Running   0
pod/web-6f8c…-q8m2l    1/1     Running   0
```

## Watch self-healing (with k9s)

This is the single best thing to *see* rather than read about. Launch [k9s](../getting-started/k9s.md):

```bash
k9s
```

Type `:pods` ⏎ to list Pods, then delete one and watch it return. In k9s, highlight a `web-…` Pod and press `Ctrl-D` (delete) — or from another terminal, delete a single Pod by name:

```bash
kubectl delete pod "$(kubectl get pod -l app=web -o name | head -1)"
```

You'll watch that Pod go `Terminating` and **a fresh one appear within seconds** — the Deployment noticed it dropped below 3 replicas and reconciled. You never told it to; that's the controller doing its job. (In k9s, press `d` on a Pod for `describe`, `l` for logs.)

> **No k9s?** `kubectl get pods -l app=web -w` shows the same thing — the `-w` (watch) flag streams changes live as the replacement is created.

## Scaling

Two equivalent ways — declarative (preferred, stays in Git) and imperative (quick):

```bash
# Declarative: edit replicas: 3 -> replicas: 5 in the manifest, then re-apply
kubectl apply -f manifests/core-objects/web-deployment.yaml

# Imperative: one-off, handy for experiments
kubectl scale deployment/web --replicas=5
```

Watch the new Pods schedule live in k9s. More on automatic scaling in [Scaling](../running-and-operating/scaling.md).

## Best practices

- **Pin image tags** (`nginx:1.27`, not `nginx:latest`) so rollouts are reproducible.
- **Always set `resources.requests`/`limits`** — the scheduler needs requests to place Pods well; limits stop one Pod starving the node. See [Resource Requests & Limits](../running-and-operating/resources.md).
- **Add health probes** so Kubernetes knows when a Pod is truly ready/alive. See [Health Checks](../running-and-operating/health-checks.md).
- **Treat `selector` as immutable** — it's fixed after creation; choose stable labels like `app: web`.
- **Keep Deployments as YAML in version control**, not as imperative commands, so cluster state is reproducible.

## Clean up

If you're reading straight through, **leave this Deployment running** for the next few chapters. [ReplicaSet](replicaset.md), [DaemonSet](daemonset.md), [Job & CronJob](job-cronjob.md), and especially [Service](service.md) all build on or compare against it.

If you're done experimenting and want to reset the lab, delete it:

```bash
kubectl delete -f manifests/core-objects/web-deployment.yaml   # removes the Deployment, its ReplicaSet, and all Pods
```

---

[← Labels & Selectors](labels-selectors.md) · [↑ Contents](../../README.md) · [ReplicaSet →](replicaset.md)
