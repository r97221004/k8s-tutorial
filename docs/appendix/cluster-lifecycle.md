# Cluster Lifecycle (kubeadm)

> The maintenance topics to know once the lab cluster is running: upgrades, etcd backup, certificates, and reset.

---

This guide focuses on learning Kubernetes objects, not operating a production control plane. Still, a kubeadm cluster is a real cluster, so you should know the maintenance map.

## Upgrade path

kubeadm upgrades are deliberate and staged. The usual order is:

1. Read the release notes for the target Kubernetes minor version.
2. Upgrade `kubeadm`.
3. Run `kubeadm upgrade plan`.
4. Upgrade the control plane with `kubeadm upgrade apply`.
5. Upgrade `kubelet` and `kubectl`.
6. Restart kubelet and verify the node.

On multi-node clusters, upgrade one node at a time: drain, upgrade, restart, uncordon, verify, then move to the next.

## etcd backup

In a kubeadm control plane, etcd stores cluster state. Backing up etcd is how you protect the cluster's source of truth.

The real command depends on your certificate paths and etcd endpoint, but the shape is:

```bash
sudo ETCDCTL_API=3 etcdctl snapshot save /var/backups/etcd-snapshot.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key
```

Practice restore procedures before you need them. A backup you have never restored is only a hope with a filename.

## Certificates

kubeadm creates the control-plane certificates under `/etc/kubernetes/pki`. Check expiration before it surprises you:

```bash
sudo kubeadm certs check-expiration
```

Renewal is usually handled during kubeadm upgrades, but you can renew manually with:

```bash
sudo kubeadm certs renew all
```

After cert renewal, restart affected static Pods or the kubelet so components reload credentials.

## Reset and leftovers

`kubeadm reset` removes the cluster components from a node, but it may not clean every networking artifact or data directory. For a lab rebuild, expect to check:

- `/etc/kubernetes/`
- `/var/lib/etcd/`
- CNI config under `/etc/cni/net.d/`
- iptables/IPVS rules if networking behaves strangely after a rebuild
- kubeconfig files such as `~/.kube/config`

Prefer the companion Ansible uninstall flow when using this tutorial's kubeadm role, because it encodes the exact cleanup for this lab.

## Best practices

- **Read release notes before upgrading**; Kubernetes version skew rules matter.
- **Back up etcd before control-plane upgrades.**
- **Drain nodes before maintenance** on multi-node clusters.
- **Check certificate expiration periodically.**
- **Test rebuild/restore in a lab** before treating a cluster as important.

---

[← Cleanup](../capstone/cleanup.md) · [↑ Contents](../../README.md) · [kubectl Cheat Sheet →](cheatsheet.md)
