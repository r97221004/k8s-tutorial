# Job & CronJob

> Run-to-completion batch work (Job), and Jobs on a schedule (CronJob).

---

Everything so far runs **forever** — a [Deployment](deployment.md) restarts a Pod that exits, because a web server stopping is a failure. But some work is *supposed* to finish: a database migration, a batch import, a nightly report. For that you want a workload that runs **to completion** and then stops. That's a **Job**.

## Job — run once, to completion

A Job runs its Pod until it succeeds (exit 0), retrying on failure up to `backoffLimit`.

▶ **Runnable manifest:** [`manifests/core-objects/pi-job.yaml`](../../manifests/core-objects/pi-job.yaml)

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: pi
spec:
  backoffLimit: 4          # retry the Pod up to 4 times before failing the Job
  template:
    spec:
      restartPolicy: Never # Jobs require Never or OnFailure (not Always)
      containers:
        - name: pi
          image: perl:5.40
          command: ["perl", "-Mbignum=bpi", "-wle", "print bpi(200)"]
```

```bash
kubectl apply -f manifests/core-objects/pi-job.yaml
kubectl get job pi              # watch COMPLETIONS go 0/1 → 1/1
kubectl logs job/pi            # the 200 digits of pi it computed
```

Key differences from a Deployment:

- **`restartPolicy: Never`** (or `OnFailure`) — `Always` is for things that should never stop, which is the opposite of a Job.
- The Job's Pod stays around `Completed` after finishing, so you can read its logs. Delete the Job to clean up its Pods (`kubectl delete -f …`).
- For parallel batch work, `completions` and `parallelism` let a Job run many Pods.

## CronJob — a Job on a schedule

A **CronJob** creates a Job on a cron schedule — the Kubernetes-native cron.

▶ **Runnable manifest:** [`manifests/core-objects/hello-cronjob.yaml`](../../manifests/core-objects/hello-cronjob.yaml)

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hello
spec:
  schedule: "*/1 * * * *"        # every minute (standard cron syntax)
  successfulJobsHistoryLimit: 3   # keep the last 3 completed Jobs
  failedJobsHistoryLimit: 1       # keep the last 1 failed Job
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: Never
          containers:
            - name: hello
              image: busybox:1.36
              command: ["sh", "-c", "date; echo Hello from a CronJob"]
```

```bash
kubectl apply -f manifests/core-objects/hello-cronjob.yaml
kubectl get cronjob hello       # see LAST SCHEDULE tick over
kubectl get jobs -w             # a new Job appears each minute
```

In [k9s](../getting-started/k9s.md), `:cronjobs` and `:jobs` let you watch each run spawn — a satisfying way to *see* the schedule fire.

## Best practices

- **Pick the right kind:** finishes once → **Job**; on a schedule → **CronJob**; runs forever → **Deployment**.
- **Set `backoffLimit`** so a broken Job doesn't retry endlessly.
- **Set history limits** (`successfulJobsHistoryLimit`/`failedJobsHistoryLimit`) so old CronJob runs don't pile up.
- **Make jobs idempotent** — a Job may retry, so running twice should be safe.

## Clean up

Delete the CronJob when you're done watching it; otherwise it keeps creating a new Job every minute. The one-off Job can be removed too once you've read its logs:

```bash
kubectl delete -f manifests/core-objects/hello-cronjob.yaml
kubectl delete -f manifests/core-objects/pi-job.yaml
```

---

[← DaemonSet (intro)](daemonset.md) · [↑ Contents](../../README.md) · [Service →](service.md)
