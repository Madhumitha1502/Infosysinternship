# Cloud Deployment Guide

Milestone 4 deliverable: *"Deploy the platform on cloud infrastructure such
as Azure, AWS, or GCP."* This project ships two deployment paths:

1. **Single-container / docker-compose** — already in the repo root
   (`Dockerfile`, `docker-compose.yml`), good for a VM, an App Service /
   Container App, or a quick demo.
2. **Kubernetes** (`deploy/k8s/`) — good for a managed cluster with
   autoscaling, used identically on AKS, EKS, or GKE.

The image is stateless-ish: SQLite (`memory/shared_memory.db`) and the
generated CSV/JSON/Markdown reports are the only local state, and are
already re-creatable by re-running the pipeline, so no special
stateful-set/database provisioning is required for a demo deployment. For a
real production deployment, swap the SQLite file for a managed Postgres and
point `memory/shared_memory.py` at it (see `Design Notes` in the main
README for the intended extension point).

---

## 1. Build & push the image

```bash
docker build -t ai-cyber-response:1.0.0 .

# Azure Container Registry
az acr login --name <your-acr-name>
docker tag ai-cyber-response:1.0.0 <your-acr-name>.azurecr.io/ai-cyber-response:1.0.0
docker push <your-acr-name>.azurecr.io/ai-cyber-response:1.0.0

# AWS ECR
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
docker tag ai-cyber-response:1.0.0 <account-id>.dkr.ecr.<region>.amazonaws.com/ai-cyber-response:1.0.0
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/ai-cyber-response:1.0.0

# Google Artifact Registry
gcloud auth configure-docker <region>-docker.pkg.dev
docker tag ai-cyber-response:1.0.0 <region>-docker.pkg.dev/<project-id>/<repo>/ai-cyber-response:1.0.0
docker push <region>-docker.pkg.dev/<project-id>/<repo>/ai-cyber-response:1.0.0
```

## 2a. Fastest path: single-container PaaS (no Kubernetes)

| Cloud | Service | One-liner |
|---|---|---|
| Azure | Container Apps | `az containerapp up --name ai-cyber-response --image <acr>.azurecr.io/ai-cyber-response:1.0.0 --target-port 8000 --ingress external` |
| AWS | App Runner | Create an App Runner service from the ECR image, container port `8000`, health check path `/health` |
| GCP | Cloud Run | `gcloud run deploy ai-cyber-response --image <region>-docker.pkg.dev/<project-id>/<repo>/ai-cyber-response:1.0.0 --port 8000 --allow-unauthenticated` |

Set `LLM_PROVIDER=none` (default) unless you're wiring up OpenAI/Ollama —
the system runs fully in heuristic mode with zero external calls, which is
ideal for these managed platforms.

## 2b. Kubernetes (AKS / EKS / GKE)

```bash
# Point kubectl at your cluster first (az aks get-credentials / aws eks update-kubeconfig / gcloud container clusters get-credentials)

# Update the image reference in deploy/k8s/deployment.yaml to the one you pushed above, then:
kubectl apply -f deploy/k8s/deployment.yaml
kubectl apply -f deploy/k8s/service.yaml
kubectl apply -f deploy/k8s/hpa.yaml   # optional: CPU-based autoscaling, 2-6 replicas

kubectl get svc ai-cyber-response   # grab the external IP / hostname once provisioned
```

- **Readiness/liveness probes** hit `/health`, so a bad rollout is caught
  and rolled back automatically by K8s before it takes traffic.
- **HPA** (`deploy/k8s/hpa.yaml`) scales 2→6 replicas on CPU > 70%,
  covering the "scalability" requirement without any custom autoscaling code.
- Swap the `LoadBalancer` Service for a `ClusterIP` + `Ingress` if the
  cluster already has an ingress controller (nginx, Traefik, cloud-native).

## 3. Monitoring in production

- `GET /health` — liveness/readiness probe (already wired into the K8s
  manifest and the Dockerfile's `HEALTHCHECK`).
- `GET /metrics` — Prometheus-exposition-format text endpoint (request
  counts/latency by route, pipeline run counts, per-stage durations,
  tracked-incident count). Point a Prometheus `scrape_config` at it:

  ```yaml
  scrape_configs:
    - job_name: ai-cyber-response
      metrics_path: /metrics
      static_configs:
        - targets: ["ai-cyber-response:80"]
  ```

- `GET /pipeline/status` — live per-agent workflow status, used by the
  dashboard's "Workflow" panel and equally useful for a synthetic-monitoring
  check ("is the pipeline stuck on `analysis`?").
- Structured logs are written under `logs/` (see `logging_setup.py`) and
  also go to stdout in the container, so any cloud's native log
  aggregation (Azure Monitor / CloudWatch Logs / Cloud Logging) picks them
  up automatically with no extra sidecar.

## 4. Performance testing before go-live

```bash
# zero-dependency load test (stdlib only)
python scripts/perf_test.py --base-url https://<your-deployed-url> --concurrency 10 --requests 100

# or, if you have locust installed, for a ramping profile + web UI:
locust -f tests/performance/locustfile.py --host https://<your-deployed-url>
```

See the main README's "Performance Testing" section for how to read the
output and what to tune if latency is too high.
