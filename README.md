# SFE AI DevOps Pipeline

## Project Overview

An end-to-end AI-powered DevOps pipeline that automates the entire software delivery lifecycle with intelligent anomaly detection, real-time monitoring, and automated rollbacks.

### Key Features

- Automated CI/CD pipeline with GitHub Actions
- Containerization with Docker and orchestration with Kubernetes
- Real-time monitoring with Prometheus and Grafana
- AI-powered anomaly detection using Isolation Forest
- Automated risk scoring and intelligent rollbacks
- DevSecOps security scanning (Trivy, Snyk, GitLeaks)
- Email notifications for high-risk deployments
- Beautiful dashboard with live metrics

## Technology Stack

| Category | Technologies |
|----------|--------------|
| CI/CD | GitHub Actions |
| Containerization | Docker |
| Orchestration | Kubernetes (Kind, Minikube) |
| Monitoring | Prometheus, Grafana |
| AI/ML | Python, scikit-learn, Isolation Forest |
| Backend | Flask, FastAPI |
| Security | Trivy, Snyk, GitLeaks |
| Cloud | Render, ngrok |
| Database | PostgreSQL (for metadata) |

## Quick Start

### Prerequisites

- Docker Desktop (with WSL2 integration)
- Minikube or Kind
- kubectl
- Helm
- Python 3.9+
- Git

### Clone and Run Locally

```bash
git clone https://github.com/AmeniChokri/ai-devops-pipeline.git
cd ai-devops-pipeline

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r app/requirements.txt

# Run the application
python app/app.py

### Project Structure

ai-devops-pipeline/
├── .github/workflows/ci-cd.yml   # GitHub Actions pipeline
├── app/
│   ├── app.py                    # Main Flask application
│   ├── requirements.txt          # Python dependencies
│   └── templates/                # HTML templates
├── ai/
│   ├── Dockerfile                # AI service container
│   ├── src/predict.py            # FastAPI prediction service
│   ├── src/train.py              # Model training script
│   ├── models/                   # Trained model files
│   └── notebooks/                # Jupyter notebooks
├── k8s/                          # Kubernetes manifests
├── tests/test_app.py             # Unit tests
├── monitoring/dashboards/        # Grafana dashboard JSONs
└── Dockerfile                    # Main app container

### CI/CD Pipeline
The pipeline is triggered on every push to main, develop, and ai-integration branches.
##Pipeline Stages
test - Runs unit tests with pytest

build-and-push - Builds Docker images and pushes to GHCR

security-scan - Scans for vulnerabilities (Trivy, Snyk, GitLeaks)

check-ai-risk - Calls AI service for risk assessment

deploy-to-kind - Deploys to Kind cluster

post-deployment - Health check and auto-rollback if needed

## Risk Thresholds
Risk Score	Action
Less than 70%	Safe to deploy
70-90%	Warning, manual review recommended
Greater than 90%	Block deployment + Auto-rollback


### AI Service
## Model Information

Algorithm: Isolation Forest

Features: 11 time-series features (CPU, memory, request rate, error rate, rolling statistics, lag features)

Training Data: Numenta Anomaly Benchmark (NAB) - real AWS CPU metrics

Performance: F1-score of 0.84, Precision 0.85, Recall 0.83

### Monitoring Stack
##Prometheus

Prometheus scrapes metrics from both the main application and the AI service every 15 seconds. Available metrics include:

http_requests_total - Total HTTP requests

http_request_duration_seconds - Request latency

risk_score - Current AI risk score

confidence - Model confidence

anomaly_score - Raw anomaly score

## Grafana Dashboards

The following dashboards are available:

AI Performance Dashboard - Model confidence, prediction latency, risk distribution

Application Health & SLA - Uptime, request rates, error rates

Kubernetes Resources - CPU/Memory usage by pod

Deployment History - Deployment frequency, versions, rollback tracking

### Security Scanning

The pipeline includes automated security scans:

Tool	What it scans
Trivy	Docker images for CVEs
Trivy (filesystem)	Code vulnerabilities
Snyk	Python dependencies
GitLeaks	Secrets in git history

### Auto-Rollback
When the AI risk score exceeds 90%, the pipeline automatically:

Blocks the deployment

Executes kubectl rollout undo to revert to previous version

Sends an email notification to the team

Fails the pipeline with an error

### Email Notifications

Email alerts are sent to the Team when:

Risk score exceeds 70% (warning)

Risk score exceeds 90% (block + rollback)

Security scan finds vulnerabilities (optional)

### Public URLs

Service	URL
Main Application (Render)	https://sfe-devops-app.onrender.com
AI Service (ngrok)	https://nonskeptical-jerald-nonformalistic.ngrok-free.dev

## Contributors
Ameni Chokri - Project Lead & Developer