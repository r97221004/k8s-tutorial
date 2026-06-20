# kubectl Cheat Sheet

> The commands from this guide on one page.

---

Every command this guide uses, on one page. Add `-n <ns>` to target a namespace, `-A` for all namespaces.

### Inspect

```bash
kubectl get pods                       # list (pods, deploy, svc, rs, sts, ds, pvc, ingress, nodes…)
kubectl get pods -o wide               # + node and Pod IP
kubectl get pods -l app=web            # filter by label
kubectl get pods -w                    # watch live changes
kubectl get all -n demo                # most namespaced objects at once
kubectl describe pod <name>            # full detail + events (start debugging here)
kubectl get events --sort-by=.lastTimestamp
kubectl explain deployment.spec.replicas   # discover any field
```

### Create / change / delete

```bash
kubectl apply -f file.yaml             # declarative create/update
kubectl apply -f manifests/dir/        # a whole directory
kubectl apply -k overlays/prod         # a Kustomize overlay
kubectl delete -f file.yaml            # remove what a manifest created
kubectl delete namespace demo          # remove a namespace and everything in it
kubectl create deploy web --image=nginx:1.27 --dry-run=client -o yaml > web.yaml   # generate a manifest
```

### Debug

```bash
kubectl logs <pod>                     # add -f to follow
kubectl logs <pod> --previous          # the crashed container's logs
kubectl exec -it <pod> -- sh           # shell inside a container
kubectl port-forward <pod|svc>/<name> 8080:80   # reach it locally
kubectl get endpoints <svc>            # which Pods a Service actually fronts
```

### Scale & roll out

```bash
kubectl scale deploy/web --replicas=5
kubectl autoscale deploy/web --cpu-percent=50 --min=2 --max=10
kubectl set image deploy/web web=nginx:1.28
kubectl rollout status deploy/web
kubectl rollout history deploy/web
kubectl rollout undo deploy/web [--to-revision=N]
```

### Namespaces & contexts

```bash
kubectl config get-contexts
kubectl config set-context --current --namespace=demo   # stop typing -n
kubectl get namespaces
```

> 💡 Prefer the live dashboard? [k9s](../getting-started/k9s.md) covers most of this with single keystrokes (`d` describe, `l` logs, `s` shell, `Ctrl-D` delete).

---

[← Cleanup](../capstone/cleanup.md) · [↑ Contents](../../README.md) · [Troubleshooting →](troubleshooting.md)
