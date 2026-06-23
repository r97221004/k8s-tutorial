# Cleanup

> Tear the app (and the cluster) back down so you end where you started.

---

Leaving workloads running costs resources (and, in the cloud, money). Tear down what you created so the cluster is clean.

## Remove the capstone app

The whole [demo namespace](../core-objects/namespace.md) goes in one command — deleting a namespace deletes everything in it:

```bash
kubectl delete namespace demo
```

Prefer to delete just the objects (keeping the namespace)? Delete by the manifests you applied:

```bash
kubectl delete -f manifests/capstone/ -n demo
```

## ⚠️ PVCs and data don't always go quietly

This is the gotcha worth knowing:

- Deleting the **namespace** *does* remove its PVCs (and, depending on the StorageClass reclaim policy, the underlying data).
- Deleting a **StatefulSet** does **not** delete its PVCs — they're kept on purpose so you don't lose a database by accident. Check and remove them explicitly:

```bash
kubectl get pvc -n demo               # any left behind?
kubectl delete pvc --all -n demo      # remove them (and their data)
```

Always confirm storage is gone if you truly want a clean slate:

```bash
kubectl get pv                        # released/orphaned PersistentVolumes?
```

## Reset the whole cluster

To go all the way back to bare machines, tear the cluster down with the companion Ansible tutorial's uninstall play (it runs `kubeadm reset` and cleans up) — see **[r97221004/ansible-tutorial → kubeadm Role](https://github.com/r97221004/ansible-tutorial#kubeadm-role)**. On a k3s fast-lane cluster, `/usr/local/bin/k3s-uninstall.sh` removes everything.

## Best practices

- **Namespace-per-environment makes cleanup trivial** — one `delete namespace` removes everything.
- **Remember PVCs survive** their StatefulSet — clean them up deliberately when you mean to discard data.
- **Don't delete what you didn't create** — scope deletes with `-n`, labels, or `-f <your manifests>`, never a blanket delete in `kube-system`.

---

That's the whole guide — from a bare kubeadm cluster to a running, configured, persistent, exposed two-tier app, and back to a clean slate. Revisit any topic from the [Contents](../../README.md), or go deeper with [Further Reading](../appendix/further-reading.md).

---

[← Deploy a Two-Tier App](two-tier-app.md) · [↑ Contents](../../README.md) · [Cluster Lifecycle (kubeadm) →](../appendix/cluster-lifecycle.md)
