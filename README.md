# gitops-selfhealing-k8s

A GitOps demo project that runs a FastAPI app on Kubernetes with self-healing capabilities, automated CI/CD via GitHub Actions, and observability via Prometheus + Grafana.

## Architecture

```
GitHub (source of truth)
    │
    ├── GitHub Actions ──► builds & pushes Docker image to Docker Hub
    │
    └── ArgoCD ──────────► watches k8s/ folder, syncs cluster automatically
                               │
                               ▼
                        Kubernetes (minikube)
                               │
                         ┌─────┴─────┐
                         │  3 Pods   │  ← self-healing: auto-restarts on crash
                         └─────┬─────┘
                               │
                          Service (NodePort)
                               │
                          FastAPI app
                               │
                    Prometheus + Grafana (monitoring)
```

## Project Structure

```
.
├── app/
│   ├── main.py            # FastAPI application
│   ├── Dockerfile         # Container image definition
│   └── requirements.txt   # Python dependencies
├── k8s/
│   ├── deployment.yml     # 3 replicas with liveness probe
│   └── service.yml        # NodePort service on port 80 → 8000
├── .github/
│   └── workflows/
│       └── docker-build.yml  # CI: build & push image on push to main
└── argocd-app.yml         # ArgoCD Application manifest
```

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [minikube](https://minikube.sigs.k8s.io/docs/start/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Helm](https://helm.sh/docs/intro/install/)

## Local Setup

### 1. Start minikube

```bash
minikube start
```

### 2. Build the image inside minikube

```bash
eval $(minikube docker-env)
docker build -t ranyaa164/gitops-demo:latest ./app
```

### 3. Deploy the app

```bash
kubectl apply -f k8s/deployment.yml
kubectl apply -f k8s/service.yml
```

### 4. Access the app

```bash
kubectl port-forward deployment/gitops-demo 8000:8000
curl http://localhost:8000/
```

Expected response:
```json
{"status": "ok", "service": "gitops-selfhealing-demo", "version": "v2"}
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Status and version |
| `GET /health` | Health check (used by liveness probe) |
| `GET /metrics-info` | Uptime in seconds |

## CI/CD — GitHub Actions

On every push to `main`, the workflow in `.github/workflows/docker-build.yml`:
1. Checks out the code
2. Sets up Docker Buildx
3. Logs in to Docker Hub
4. Builds and pushes `ranyaa164/gitops-demo:latest`

**Required GitHub Secrets:**

| Secret | Value |
|--------|-------|
| `DOCKER_USERNAME` | `ranyaa164` |
| `DOCKER_PASSWORD` | Docker Hub access token (Read & Write) |

## GitOps — ArgoCD

ArgoCD watches the `k8s/` folder in this repo and automatically syncs the cluster when changes are pushed.

### Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

### Deploy the ArgoCD Application

```bash
kubectl apply -f argocd-app.yml
```

### Access ArgoCD UI

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Open [https://localhost:8080](https://localhost:8080) — default username is `admin`.

Get the password:
```bash
kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 -d
```

## Monitoring — Prometheus + Grafana

### Install

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
kubectl create namespace monitoring
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack -n monitoring
```

### Access Grafana

```bash
# Get admin password
kubectl --namespace monitoring get secrets monitoring-grafana \
  -o jsonpath="{.data.admin-password}" | base64 -d ; echo

# Forward to localhost
export POD_NAME=$(kubectl --namespace monitoring get pod \
  -l "app.kubernetes.io/name=grafana,app.kubernetes.io/instance=monitoring" -oname)
kubectl --namespace monitoring port-forward $POD_NAME 3000
```

Open [http://localhost:3000](http://localhost:3000) — login with `admin` and the password above.

## Self-Healing Demo

The deployment has a liveness probe on `GET /health`. If a pod becomes unhealthy, Kubernetes automatically restarts it.

To observe this:
```bash
# Watch pods in real time
kubectl get pods -w

# Kill a pod manually
kubectl delete pod <pod-name>

# Kubernetes will immediately create a replacement
```
