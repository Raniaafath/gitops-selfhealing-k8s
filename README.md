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

- **Self-healing** — Kubernetes liveness probes auto-restart failed pods, and the ReplicaSet auto-recreates deleted pods
- **GitOps** — Every push to `main` triggers automatic deployment via ArgoCD, with drift correction (`selfHeal: true`)
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
│   └── service.yml          # NodePort service on port 80 → 8000
├── terraform/
│   ├── main.tf               # Azure AKS cluster provisioning
│   ├── variables.tf          # Configurable inputs (region, node count, VM size)
│   ├── outputs.tf             # Resource group / cluster name / kubectl credentials command
│   └── providers.tf           # azurerm provider configuration
├── argocd-app.yml            # ArgoCD Application manifest
└── .github/
    └── workflows/
        └── docker-build.yml   # CI pipeline (build + push image)
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service status and version |
| `/health` | GET | Health check used by the Kubernetes liveness probe. Returns `200` normally, `500` after `/break-health` is called |
| `/break-health` | POST | Flips the app into an unhealthy state, for demonstrating liveness-probe-triggered container restarts (see below) |
| `/metrics-info` | GET | Uptime in seconds |
| `/metrics` | GET | Prometheus-formatted metrics (exposed automatically by `prometheus-fastapi-instrumentator`) |

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

If your minikube uses the **docker** driver:

```bash
eval $(minikube docker-env)
docker build -t ranyaa164/gitops-demo:latest ./app
```

If your minikube uses the **containerd** runtime (the `docker-env` + `buildx` combo is experimental there and may fail), build directly into minikube's image cache instead:

```bash
minikube image build -t ranyaa164/gitops-demo:latest ./app
```

### 3. Deploy the app

```bash
kubectl apply -f k8s/
```

### 4. Access the app

```bash
kubectl port-forward svc/gitops-demo-service 8000:80
curl http://localhost:8000/
```

Expected response:
```json
{"status": "ok", "service": "gitops-selfhealing-demo", "version": "v2"}
```

> Prefer forwarding the **Service** (`svc/gitops-demo-service`) over the Deployment — a Service always routes to a live pod, so the tunnel survives even if you kill a pod mid-demo.

### 5. Rebuilding after a code change

Since `k8s/deployment.yml` uses `imagePullPolicy: Never`, Kubernetes never re-pulls the image on its own. After rebuilding the image with the same tag, force the pods to pick up the new version:

```bash
kubectl rollout restart deployment/gitops-demo
kubectl rollout status deployment/gitops-demo
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

> Note: on AKS, `imagePullPolicy: Never` (set for local minikube use) must be changed to `IfNotPresent` or `Always` so nodes actually pull the image from Docker Hub.

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

This is CI only — it builds and publishes the image but never touches the cluster directly. Deployment is deliberately decoupled and handled by ArgoCD (see below), which is the core GitOps principle: the CI pipeline never pushes to the cluster; a controller inside the cluster pulls from Git instead.

**Required GitHub Secrets:**

| Secret | Value |
|--------|-------|
| `DOCKER_USERNAME` | `ranyaa164` |
| `DOCKER_PASSWORD` | Docker Hub access token (Read & Write) |

---

## GitOps — ArgoCD

ArgoCD watches the `k8s/` folder and automatically syncs the cluster on every push, with two automation flags enabled in [argocd-app.yml](argocd-app.yml):

- `prune: true` — resources removed from the `k8s/` folder are removed from the cluster too
- `selfHeal: true` — if the live cluster state drifts from what's declared in Git (e.g. someone runs `kubectl edit` by hand, or a resource is deleted), ArgoCD automatically reverts it back to match Git

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

The app exposes Prometheus-formatted metrics at `/metrics` via `prometheus-fastapi-instrumentator`, so it can be scraped directly (request counts, latencies, status codes) in addition to the cluster-level metrics from `kube-prometheus-stack`.

---

## Self-Healing Demo

Kubernetes self-heals this app at **two independent levels**. Both are backed by the `livenessProbe` on `GET /health` declared in [k8s/deployment.yml](k8s/deployment.yml) (`initialDelaySeconds: 10`, `periodSeconds: 5`), combined with the `replicas: 3` guarantee.

### Scenario 1 — Pod deletion → ReplicaSet recreates it

If a pod disappears entirely (crash, manual deletion, node issue), the **ReplicaSet** notices the live pod count has dropped below the desired `replicas: 3` and creates a brand-new pod (new name) to replace it.

```bash
# Watch pods in real time (run in a separate terminal)
kubectl get pods -w

# Kill a pod manually to trigger self-healing
kubectl delete pod $(kubectl get pods -l app=gitops-demo -o jsonpath='{.items[0].metadata.name}')

# Kubernetes immediately creates a replacement (new pod name, RESTARTS stays 0)
```

Confirm it with the event log:

```bash
kubectl get events --sort-by='.lastTimestamp' | grep gitops-demo | tail -10
# Look for: Killing (old pod) → SuccessfulCreate (new pod)
```

### Scenario 2 — Liveness probe failure → kubelet restarts the container

If the app itself becomes unhealthy while the pod is still alive, the **kubelet** restarts just the container in place — same pod name, `RESTARTS` counter increments.

```bash
kubectl port-forward svc/gitops-demo-service 8000:80 &

# Flip the app into an unhealthy state
curl -X POST http://localhost:8000/break-health

# Watch the same pod get restarted in place once the probe fails enough times
kubectl get pods -l app=gitops-demo -w
```

Within a few seconds (`periodSeconds: 5` × failure threshold), the pod's `RESTARTS` count goes from `0` to `1` while its **name stays identical** — the key difference from Scenario 1. On restart, the app process starts fresh with `is_healthy = True` again, so it recovers automatically.

| | Scenario 1: pod deletion | Scenario 2: liveness probe failure |
|---|---|---|
| Trigger | Pod removed/crashes | `/health` starts failing |
| Controller responsible | ReplicaSet | kubelet |
| Pod name | Changes (new pod) | Stays the same |
| Signal | New pod, `RESTARTS=0` | Same pod, `RESTARTS` increments |
