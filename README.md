# SFE AI DevOps Pipeline

## Project Overview
CI/CD pipeline with automated testing, Docker containerization, and Kubernetes deployment.

## Application
Simple Flask API with health check and metrics endpoints.

## Branch Strategy
- `main`: production-ready code
- `develop`: integration branch
- `feature/*`: feature branches

## CI/CD Pipeline
GitHub Actions automates:
1. Testing on every push
2. Docker image build on main branch
3. Kubernetes deployment

## Local Development
```bash
# Run locally
cd app
pip install -r requirements.txt
python app.py

# Run tests
cd tests
pytest -v

# Build Docker image
docker build -t sfe-devops-app .

# Run Docker container
docker run -p 5000:5000 sfe-devops-app

# Deploy to local K8s
kubectl apply -f k8s/