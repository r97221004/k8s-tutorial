# Deploy Todo Board

> Put it all together: a Vue front end, a FastAPI back end, and SQLite data persisted on a PVC.

---

Time to assemble the guide into one small but real app: **Todo Board**. The browser loads a Vue app, Vue calls a FastAPI API under `/api`, FastAPI stores todos in SQLite at `/data/todo.db`, and Kubernetes keeps the SQLite file on a [PVC](../config-and-data/volumes.md). Traffic enters through an [Ingress](../networking/ingress.md).

▶ **App source:** [`backend/`](../../backend/) and [`frontend/`](../../frontend/)  
▶ **Runnable manifests:** [`manifests/capstone/`](../../manifests/capstone/)

> **Prereqs:** a default StorageClass ([Volumes](../config-and-data/volumes.md)), an ingress controller ([Ingress](../networking/ingress.md)), and container images that your cluster can pull. On k3s, storage and ingress may already exist; on kubeadm, install them from the earlier chapters.

## The pieces and how they connect

```
Ingress (demo.localdev.me)
  ├─ /api ─▶ Service todo-backend ─▶ Deployment todo-backend (FastAPI, 1 replica)
  │                                      │ env from ConfigMap
  │                                      └─ PVC mounted at /data (SQLite todo.db)
  └─ /   ─▶ Service todo-frontend ─▶ Deployment todo-frontend (Vue static files)
```

Every relationship you learned shows up here: labels wire Services to Pods, config reaches the backend through a ConfigMap, data survives on a PVC, probes guard rollout health, and Ingress routes `/api` and `/` to different Services.

> **SQLite lab note:** SQLite is intentionally used to keep the capstone small. The backend runs with `replicas: 1` because multiple writers sharing one SQLite file is not a production scaling pattern. For real multi-replica writes, use PostgreSQL, MySQL, or a managed database.

## Build the images

The manifests use local image names:

- `todo-backend:0.1.0`
- `todo-frontend:0.1.0`

Build them from the repo root:

```bash
docker build -t todo-backend:0.1.0 backend
docker build -t todo-frontend:0.1.0 frontend
```

Your cluster nodes must be able to pull those images. Pick the path that matches where you built them:

**If Docker is running on the same single node as kubeadm**, export each image and import it into containerd's Kubernetes namespace:

```bash
docker save todo-backend:0.1.0 | sudo ctr -n k8s.io images import -
docker save todo-frontend:0.1.0 | sudo ctr -n k8s.io images import -
sudo ctr -n k8s.io images list | grep todo-
```

**If you built on your laptop but the kubeadm node is a VM**, copy the tarballs to the node first:

```bash
docker save todo-backend:0.1.0 -o todo-backend-0.1.0.tar
docker save todo-frontend:0.1.0 -o todo-frontend-0.1.0.tar
scp todo-*-0.1.0.tar <user>@<node-ip>:/tmp/

ssh <user>@<node-ip>
sudo ctr -n k8s.io images import /tmp/todo-backend-0.1.0.tar
sudo ctr -n k8s.io images import /tmp/todo-frontend-0.1.0.tar
```

**If you prefer a registry**, push both images and update the `image:` fields in `manifests/capstone/backend.yaml` and `manifests/capstone/frontend.yaml`:

```bash
docker tag todo-backend:0.1.0 registry.example.com/todo-backend:0.1.0
docker tag todo-frontend:0.1.0 registry.example.com/todo-frontend:0.1.0
docker push registry.example.com/todo-backend:0.1.0
docker push registry.example.com/todo-frontend:0.1.0
```

On k3s, use its bundled containerd importer instead:

```bash
docker save todo-backend:0.1.0 -o todo-backend-0.1.0.tar
docker save todo-frontend:0.1.0 -o todo-frontend-0.1.0.tar
sudo k3s ctr images import todo-backend-0.1.0.tar
sudo k3s ctr images import todo-frontend-0.1.0.tar
```

Keep the tags pinned. Avoid `latest`, so rollouts and rollbacks stay deliberate.

## Optional local checks

Before building images, you can run the app checks locally. Install the backend dev dependencies once:

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest tests

cd ../frontend
npm ci
npm run build
```

The backend test command is run from `backend/` so Python can import the local `app` package exactly like the container does.

## Deploy it

Use a dedicated [namespace](../core-objects/namespace.md):

```bash
kubectl create namespace demo
kubectl apply -f manifests/capstone/ -n demo
```

Watch both Deployments come up:

```bash
kubectl get deploy,pods,svc,pvc,ingress -n demo
kubectl rollout status deployment/todo-backend -n demo
kubectl rollout status deployment/todo-frontend -n demo
```

Or open [k9s](../getting-started/k9s.md), press `:ns` → `demo`, and watch the backend, frontend, and PVC.

## Verify the wiring

```bash
# Backend config reached the Pod:
kubectl exec deploy/todo-backend -n demo -- printenv APP_NAME APP_VERSION DATABASE_PATH

# Backend can write to its mounted PVC:
kubectl exec deploy/todo-backend -n demo -- ls -l /data

# Backend health:
kubectl exec deploy/todo-backend -n demo -- python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/healthz').read().decode())"

# Reach through the Ingress:
curl http://demo.localdev.me/api/healthz
curl http://demo.localdev.me
```

If your kubeadm node is remote, remember the [Ingress chapter](../networking/ingress.md) note: `demo.localdev.me` resolves to `127.0.0.1`, so run `curl` on the node, forward the ingress port, or map the hostname to the VM's IP.

## Use the API directly

Create, list, update, and delete a todo through the backend:

```bash
curl -s -X POST http://demo.localdev.me/api/todos \
  -H 'Content-Type: application/json' \
  -d '{"title":"Ship the capstone"}'

curl -s http://demo.localdev.me/api/todos

curl -s -X PATCH http://demo.localdev.me/api/todos/1 \
  -H 'Content-Type: application/json' \
  -d '{"completed":true}'

curl -i -X DELETE http://demo.localdev.me/api/todos/1
```

The Vue UI does the same calls from the browser.

## Prove SQLite persists

Create a todo, delete the backend Pod, and list todos again:

```bash
curl -s -X POST http://demo.localdev.me/api/todos \
  -H 'Content-Type: application/json' \
  -d '{"title":"Survive a Pod restart"}'

kubectl delete pod "$(kubectl get pod -n demo -l app.kubernetes.io/component=backend -o name | head -1)" -n demo
kubectl rollout status deployment/todo-backend -n demo

curl -s http://demo.localdev.me/api/todos
```

The todo should still be there because `/data/todo.db` lives on the PVC, not inside the container filesystem.

## Rolling update + rollback

After changing frontend code, build a new image tag, update the Deployment, and watch the rollout:

```bash
docker build -t todo-frontend:0.1.1 frontend
kubectl set image deployment/todo-frontend frontend=todo-frontend:0.1.1 -n demo
kubectl rollout status deployment/todo-frontend -n demo
kubectl rollout history deployment/todo-frontend -n demo
kubectl rollout undo deployment/todo-frontend -n demo
```

Readiness probes gate the rollout so new frontend Pods must serve `/` before old Pods leave.

## What you just used

Pod · Deployment · Service · Ingress · ConfigMap · PVC · probes · resources · labels/selectors · DNS · rolling update + rollback — plus a real browser-to-API-to-database path.

Next: [tear it down cleanly](cleanup.md).

---

[← Kustomize (intro)](../packaging/kustomize.md) · [↑ Contents](../../README.md) · [Cleanup →](cleanup.md)
