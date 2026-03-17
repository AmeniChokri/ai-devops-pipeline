"""
AI Prediction Service for DevOps Anomaly Detection
Loads trained Isolation Forest model and uses Prometheus metrics for real-time predictions
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import numpy as np
import os
import logging
import requests
import time
from typing import Optional, List, Dict
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="DevOps Anomaly Detection API",
    description="AI-powered anomaly detection for CI/CD pipeline using Isolation Forest",
    version="1.0.0"
)

# Global variables for model and scaler
model = None
scaler = None
feature_columns = ['value', 'hour', 'day_of_week', 'day_of_month',
                   'rolling_mean_5', 'rolling_std_5',
                   'rolling_mean_20', 'rolling_std_20',
                   'lag_1', 'lag_2', 'lag_5']

# Prometheus configuration
PROMETHEUS_URL = "http://prometheus-kube-prometheus-prometheus.monitoring:9090"
APP_SERVICE = "sfe-devops-app-service"
APP_NAMESPACE = "default"

class MetricsData(BaseModel):
    """Input data format for prediction"""
    value: float
    hour: Optional[int] = None
    day_of_week: Optional[int] = None
    day_of_month: Optional[int] = None
    timestamp: Optional[str] = None

class PredictionResponse(BaseModel):
    """Prediction result format"""
    risk_score: float
    is_anomaly: bool
    confidence: float
    anomaly_score: float
    recommendation: str
    model_version: str
    metrics_used: Dict[str, float]
    timestamp: str

@app.on_event("startup")
async def load_model():
    """Load the trained Isolation Forest model and scaler on startup"""
    global model, scaler
    
    logger.info("🔍 Looking for trained model...")
    logger.info(f"Current working directory: {os.getcwd()}")
    
    # Get the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logger.info(f"Script directory: {current_dir}")
    
    # List all possible paths (in order of preference)
    possible_paths = [
        '/app/models/isolation_forest_model_fresh.pkl',  # Container path (Dockerfile copies here)
        '/app/models/models/isolation_forest_model_fresh.pkl',  # Alternative
        './models/isolation_forest_model_fresh.pkl',  # Relative to current dir
        '../models/isolation_forest_model_fresh.pkl',  # One level up
        os.path.join(current_dir, '../models/isolation_forest_model_fresh.pkl'),  # Relative to src
        os.path.join(current_dir, '../../models/isolation_forest_model_fresh.pkl'),  # Project root
        '/models/isolation_forest_model_fresh.pkl',  # Root models dir
    ]
    
    model_loaded = False
    
    # Check each path
    for path in possible_paths:
        exists = os.path.exists(path)
        logger.info(f"Checking: {path} - Exists: {exists}")
        if exists:
            try:
                model = joblib.load(path)
                logger.info(f"✅ Model loaded successfully from {path}")
                logger.info(f"   Model type: Isolation Forest")
                logger.info(f"   Estimators: {getattr(model, 'n_estimators', 'N/A')}")
                logger.info(f"   Contamination: {getattr(model, 'contamination', 'N/A')}")
                model_loaded = True
                
                # Look for scaler in same directory
                scaler_path = path.replace('isolation_forest_model_fresh.pkl', 'scaler.pkl')
                if os.path.exists(scaler_path):
                    scaler = joblib.load(scaler_path)
                    logger.info(f"✅ Scaler loaded from {scaler_path}")
                else:
                    logger.warning("⚠️ Scaler not found, predictions will use raw features")
                break
            except Exception as e:
                logger.error(f"❌ Error loading model from {path}: {e}")
    
    if not model_loaded:
        logger.error("❌ CRITICAL: Could not load model from any path!")
        logger.error("   Service will use FALLBACK mode - not recommended for production")
    else:
        logger.info("🎯 Model loading complete. Service ready for predictions.")

async def fetch_prometheus_metrics() -> Dict[str, float]:
    """Fetch real-time metrics from Prometheus"""
    metrics = {}
    
    try:
        # Query CPU usage
        cpu_query = f'sum(rate(container_cpu_usage_seconds_total{{namespace="{APP_NAMESPACE}", pod=~"sfe-devops-app.*"}}[1m]))'
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": cpu_query}, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['data']['result']:
                metrics['cpu_usage'] = float(data['data']['result'][0]['value'][1]) * 100
            else:
                metrics['cpu_usage'] = 0
        else:
            logger.warning(f"Prometheus CPU query failed: {response.status_code}")
            metrics['cpu_usage'] = 50  # Default fallback
    except Exception as e:
        logger.error(f"Error fetching CPU metrics: {e}")
        metrics['cpu_usage'] = 50
    
    try:
        # Query memory usage
        memory_query = f'sum(container_memory_working_set_bytes{{namespace="{APP_NAMESPACE}", pod=~"sfe-devops-app.*"}}) / sum(kube_pod_container_resource_limits{{resource="memory", namespace="{APP_NAMESPACE}"}}) * 100'
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": memory_query}, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['data']['result']:
                metrics['memory_usage'] = float(data['data']['result'][0]['value'][1])
            else:
                metrics['memory_usage'] = 50
        else:
            logger.warning(f"Prometheus memory query failed: {response.status_code}")
            metrics['memory_usage'] = 50
    except Exception as e:
        logger.error(f"Error fetching memory metrics: {e}")
        metrics['memory_usage'] = 50
    
    try:
        # Query request rate
        request_query = f'sum(rate(http_requests_total{{namespace="{APP_NAMESPACE}"}}[1m]))'
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": request_query}, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['data']['result']:
                metrics['request_rate'] = float(data['data']['result'][0]['value'][1])
            else:
                metrics['request_rate'] = 10
        else:
            logger.warning(f"Prometheus request query failed: {response.status_code}")
            metrics['request_rate'] = 10
    except Exception as e:
        logger.error(f"Error fetching request metrics: {e}")
        metrics['request_rate'] = 10
    
    try:
        # Query error rate
        error_query = f'sum(rate(http_errors_total{{namespace="{APP_NAMESPACE}"}}[1m])) / sum(rate(http_requests_total{{namespace="{APP_NAMESPACE}"}}[1m])) * 100'
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": error_query}, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['data']['result']:
                metrics['error_rate'] = float(data['data']['result'][0]['value'][1])
            else:
                metrics['error_rate'] = 0
        else:
            logger.warning(f"Prometheus error query failed: {response.status_code}")
            metrics['error_rate'] = 0
    except Exception as e:
        logger.error(f"Error fetching error metrics: {e}")
        metrics['error_rate'] = 0
    
    # Combined metric for prediction (weighted average)
    metrics['value'] = (
        metrics.get('cpu_usage', 50) * 0.3 +
        metrics.get('memory_usage', 50) * 0.3 +
        metrics.get('request_rate', 10) * 0.2 +
        metrics.get('error_rate', 0) * 0.2
    )
    
    # Add time features
    now = datetime.now()
    metrics['hour'] = now.hour
    metrics['day_of_week'] = now.weekday()
    metrics['day_of_month'] = now.day
    
    return metrics

def prepare_features(metrics: Dict[str, float]) -> np.ndarray:
    """Convert metrics to feature vector for model"""
    # Simplified feature engineering for demo
    # In production, you'd compute rolling windows and lags
    features = np.array([[
        metrics.get('value', 50),
        metrics.get('hour', 12),
        metrics.get('day_of_week', 3),
        metrics.get('day_of_month', 15),
        metrics.get('value', 50),  # rolling_mean_5
        0.0,                         # rolling_std_5
        metrics.get('value', 50),   # rolling_mean_20
        0.0,                         # rolling_std_20
        metrics.get('value', 50),   # lag_1
        metrics.get('value', 50),   # lag_2
        metrics.get('value', 50)    # lag_5
    ]])
    
    return features

@app.get("/")
async def root():
    return {
        "service": "DevOps Anomaly Detection API",
        "status": "operational" if model else "degraded (fallback mode)",
        "model_loaded": model is not None,
        "model_type": "Isolation Forest" if model else "None",
        "prometheus_connected": True,  # We'll check connectivity in a separate endpoint
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    if model is None:
        logger.warning("Health check: Model not loaded")
        return {"status": "degraded", "model_loaded": False}
    return {"status": "healthy", "model_loaded": True}

@app.get("/metrics/live")
async def get_live_metrics():
    """Fetch and return live metrics from Prometheus"""
    try:
        metrics = await fetch_prometheus_metrics()
        return {
            "status": "success",
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching live metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict", response_model=PredictionResponse)
async def predict(data: Optional[MetricsData] = None):
    """
    Predict anomaly risk.
    If data is provided, use it. Otherwise fetch live metrics from Prometheus.
    """
    # Fetch metrics (either from input or Prometheus)
    if data and data.value is not None:
        # Use provided data
        metrics = {
            'value': data.value,
            'hour': data.hour or datetime.now().hour,
            'day_of_week': data.day_of_week or datetime.now().weekday(),
            'day_of_month': data.day_of_month or datetime.now().day,
            'cpu_usage': data.value * 0.6,  # Estimate from value
            'memory_usage': data.value * 0.4,
            'request_rate': data.value * 0.2,
            'error_rate': data.value * 0.05
        }
        logger.info(f"Using provided metrics: value={data.value}")
    else:
        # Fetch from Prometheus
        logger.info("Fetching live metrics from Prometheus...")
        metrics = await fetch_prometheus_metrics()
        logger.info(f"Live metrics: CPU={metrics.get('cpu_usage', 0):.1f}%, "
                   f"Memory={metrics.get('memory_usage', 0):.1f}%, "
                   f"Requests={metrics.get('request_rate', 0):.1f}/s, "
                   f"Errors={metrics.get('error_rate', 0):.2f}%")
    
    # If real model is loaded, use it
    if model is not None:
        try:
            # Prepare features
            features = prepare_features(metrics)
            
            # Scale features if scaler is available
            if scaler is not None:
                features = scaler.transform(features)
            
            # Get anomaly score and prediction
            anomaly_score = model.decision_function(features)[0]
            prediction = model.predict(features)[0]
            
            # Calculate risk score (0-100)
            # Isolation Forest scores: lower = more anomalous
            risk_score = max(0, min(100, (0.5 - anomaly_score) * 100))
            is_anomaly = prediction == -1
            confidence = min(100, abs(anomaly_score) * 200)
            
            model_version = "isolation-forest-v1"
            logger.info(f"Prediction: risk={risk_score:.1f}%, anomaly={is_anomaly}, confidence={confidence:.1f}%")
            
        except Exception as e:
            logger.error(f"Error during model prediction: {e}")
            # Fall back to simple logic
            return fallback_prediction(metrics)
    
    else:
        # Use fallback logic if no model is loaded
        logger.warning("No model loaded, using fallback prediction")
        return fallback_prediction(metrics)
    
    # Generate recommendation based on risk score
    if risk_score > 80:
        recommendation = "🚨 HIGH RISK: Auto-rollback recommended. Investigate immediately."
    elif risk_score > 50:
        recommendation = "⚠️ MODERATE RISK: Manual review recommended before deployment."
    else:
        recommendation = "✅ LOW RISK: Safe to proceed with deployment."
    
    # Prepare metrics used for response
    metrics_used = {
        "cpu_usage": round(metrics.get('cpu_usage', 0), 2),
        "memory_usage": round(metrics.get('memory_usage', 0), 2),
        "request_rate": round(metrics.get('request_rate', 0), 2),
        "error_rate": round(metrics.get('error_rate', 0), 2),
        "combined_value": round(metrics.get('value', 0), 2)
    }
    
    return PredictionResponse(
        risk_score=round(risk_score, 2),
        is_anomaly=is_anomaly,
        confidence=round(confidence, 2),
        anomaly_score=round(anomaly_score, 4),
        recommendation=recommendation,
        model_version=model_version,
        metrics_used=metrics_used,
        timestamp=datetime.now().isoformat()
    )

def fallback_prediction(metrics: Dict[str, float]) -> PredictionResponse:
    """Fallback logic when model isn't available"""
    value = metrics.get('value', 50)
    error_rate = metrics.get('error_rate', 0)
    
    # Simple rule-based logic
    if value > 80 or error_rate > 5:
        risk_score = 85
        is_anomaly = True
        recommendation = "🚨 HIGH RISK (fallback): Rule-based detection"
    elif value > 60 or error_rate > 2:
        risk_score = 65
        is_anomaly = False
        recommendation = "⚠️ MODERATE RISK (fallback): Manual review recommended"
    else:
        risk_score = 25
        is_anomaly = False
        recommendation = "✅ LOW RISK (fallback): Safe to proceed"
    
    metrics_used = {
        "cpu_usage": round(metrics.get('cpu_usage', 0), 2),
        "memory_usage": round(metrics.get('memory_usage', 0), 2),
        "request_rate": round(metrics.get('request_rate', 0), 2),
        "error_rate": round(metrics.get('error_rate', 0), 2),
        "combined_value": round(metrics.get('value', 0), 2)
    }
    
    return PredictionResponse(
        risk_score=risk_score,
        is_anomaly=is_anomaly,
        confidence=70.0,
        anomaly_score=0.0,
        recommendation=recommendation,
        model_version="fallback-rule-based",
        metrics_used=metrics_used,
        timestamp=datetime.now().isoformat()
    )

@app.post("/predict/batch")
async def predict_batch(values: List[float]):
    """Batch prediction for multiple values"""
    results = []
    for val in values:
        result = await predict(MetricsData(value=val))
        results.append({
            "value": val,
            "risk_score": result.risk_score,
            "is_anomaly": result.is_anomaly
        })
    return {
        "results": results,
        "summary": {
            "total": len(results),
            "anomalies": sum(1 for r in results if r["is_anomaly"]),
            "avg_risk": sum(r["risk_score"] for r in results) / len(results)
        }
    }

@app.get("/model/info")
async def model_info():
    """Get information about the loaded model"""
    if model is None:
        return {
            "status": "no_model",
            "message": "No model loaded (using fallback)"
        }
    
    return {
        "model_type": "Isolation Forest",
        "version": "v1",
        "features": feature_columns,
        "n_estimators": getattr(model, 'n_estimators', 'N/A'),
        "contamination": getattr(model, 'contamination', 'N/A'),
        "feature_names": feature_columns,
        "status": "loaded",
        "scaler_loaded": scaler is not None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
