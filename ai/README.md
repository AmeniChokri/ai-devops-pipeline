# AI Module - Anomaly Detection for DevOps Pipeline

## Purpose
This module provides machine learning-based anomaly detection for the DevOps pipeline. It analyzes metrics from Prometheus to:
- Detect anomalies in system behavior
- Calculate risk scores for deployments
- Trigger auto-rollback when risk exceeds threshold

## Structure
- `notebooks/` - Jupyter notebooks for experimentation and model selection
- `models/` - Saved trained models (.pkl files)
- `src/` - Production code for training and prediction
- `data/` - Datasets used for training/evaluation

## Workflow
1. Explore data in notebooks
2. Train and compare models
3. Save best model as .pkl
4. Deploy prediction service with FastAPI
5. Integrate with CI/CD pipeline
