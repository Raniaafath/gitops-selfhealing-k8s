# GitOps Self-Healing Kubernetes Demo

A production-grade DevOps project demonstrating GitOps principles, automated CI/CD, and self-healing infrastructure on Azure.

## Architecture

```
GitHub (source of truth)
    │
    ├── push ──► GitHub Actions ──► Docker Hub (image registry)
    │
    └── ArgoCD ──────────────────► watches k8s/ folder, auto-syncs cluster
                                          │
                                          ▼
                                 Azure AKS (Kubernetes)
                                          │
                                    ┌─────┴─────┐
                                    │  3 Pods   │  ← self-healing: auto-restarts on crash
                                    └─────┬─────┘
                                          │
                                   LoadBalancer Service
                                          │
                                     FastAPI app
                                          │
                               Prometheus + Grafana (monitoring)
```

## Tech Stack

| Tool | Purpose |
|------|---------|
| FastAPI | Python REST API |
| Docker | Containerization |
| GitHub Actions | CI/CD pipeline |
| Kubernetes (AKS) | Container orchestration |
| ArgoCD | GitOps continuous deployment |
| Helm | Kubernetes package manager |
| Prometheus | Metrics collection |
| Grafana | Monitoring dashboards |
| Terraform | Infrastructure as Code (Azure) |

## Key Features

- **Self-healing** — Kubernetes liveness probes auto-restart failed pods
- **GitOps** — Every push to `main` triggers automatic deployment via ArgoCD
- **CI/CD** — GitHub Actions builds and pushes Docker image on every commit
- **IaC** — Azure AKS cluster provisioned entirely with Terraform
- **Observability** — Full monitoring stack with Prometheus and Grafana

## How it works

1. Developer pushes code to GitHub
2. GitHub Actions builds Docker image and pushes to Docker Hub
3. ArgoCD detects changes and syncs the Kubernetes cluster automatically
4. Kubernetes liveness probes ensure zero-downtime self-healing
5. Prometheus collects metrics, Grafana displays dashboards

## Project Structure

```
├── app/
│   ├── main.py              # FastAPI application
│   ├── Dockerfile           # Container image definition
│   └── requirements.txt     # Python dependencies
├── k8s/
│   ├── deployment.yml       # 3 replicas with liveness probe
│   └── service.yml          # LoadBalancer service on port 80 → 8000
├── terraform/
│   └── main.tf              # Azure AKS cluster provisioning
├── argocd-app.yml           # ArgoCD Application manifest
└── .github/
    └── workflows/
        └── docker-build.yml # CI/CD pipeline
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Service status and version |
| `GET /health` | Health check (used by Kubernetes liveness probe) |
| `GET /metrics-info` | Uptime in seconds |

---

## Local Setup (minikube)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [minikube](https://minikube.sigs.k8s.io/docs/start/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Helm](https://helm.sh/docs/intro/install/)

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
kubectl apply -f k8s/
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

---

## Cloud Setup (Azure AKS)

### Prerequisites

- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- [Terraform](https://developer.hashicorp.com/terraform/install)

### 1. Login to Azure

On WSL2, use device code flow:

```bash
az login --use-device-code
```

### 2. Provision the cluster

```bash
cd terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### 3. Connect kubectl to AKS

```bash
az aks get-credentials --resource-group gitops-demo-rg --name gitops-demo-aks
kubectl get nodes
```

### 4. Deploy the application

```bash
kubectl apply -f k8s/
kubectl apply -f argocd-app.yml
```

### Destroy when done

```bash
terraform destroy
```

---

## CI/CD — GitHub Actions

On every push to `main`, the workflow automatically:
1. Sets up Docker Buildx
2. Logs in to Docker Hub
3. Builds and pushes `ranyaa164/gitops-demo:latest`

**Required GitHub Secrets:**

| Secret | Value |
|--------|-------|
| `DOCKER_USERNAME` | `ranyaa164` |
| `DOCKER_PASSWORD` | Docker Hub access token (Read & Write) |

---

## GitOps — ArgoCD

ArgoCD watches the `k8s/` folder and automatically syncs the cluster on every push.

### Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl apply -f argocd-app.yml
```

### Access the UI

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 -d
```

Open [https://localhost:8080](https://localhost:8080) — username: `admin`

---

## Monitoring — Prometheus + Grafana

### Install

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace
```

### Access Grafana

```bash
kubectl --namespace monitoring get secrets monitoring-grafana \
  -o jsonpath="{.data.admin-password}" | base64 -d ; echo

export POD_NAME=$(kubectl --namespace monitoring get pod \
  -l "app.kubernetes.io/name=grafana,app.kubernetes.io/instance=monitoring" -oname)
kubectl --namespace monitoring port-forward $POD_NAME 3000
```

Open [http://localhost:3000](http://localhost:3000) — username: `admin`

---

## Self-Healing Demo

The deployment has a liveness probe on `GET /health`. If a pod becomes unhealthy, Kubernetes automatically restarts it.

```bash
# Watch pods in real time
kubectl get pods -w

# Kill a pod manually to trigger self-healing
kubectl delete pod <pod-name>

# Kubernetes immediately creates a replacement
```
