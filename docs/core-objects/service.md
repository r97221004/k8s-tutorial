# Service

> A stable address and load balancer for a set of Pods, whose IPs come and go.

[← Job & CronJob](job-cronjob.md) · [↑ Contents](../../README.md) · [Namespace →](namespace.md)

---

_TODO — ClusterIP / NodePort / LoadBalancer. On vanilla kubeadm there is no LoadBalancer provider: use NodePort, or install MetalLB to make `type: LoadBalancer` work on bare metal._

> 📝 **Multi-node note:** all your Pod endpoints sit on one node here, so kube-proxy has nothing to balance across machines. On a multi-node cluster a Service load-balances traffic to Pods wherever they run.

---

[← Job & CronJob](job-cronjob.md) · [↑ Contents](../../README.md) · [Namespace →](namespace.md)
