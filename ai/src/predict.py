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
from typing import Optional, List, Dict, Any
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
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus-kube-prometheus-prometheus.monitoring:9090")
APP_NAMESPACE = os.getenv("APP_NAMESPACE", "default")
APP_SERVICE = os.getenv("APP_SERVICE", "sfe-devops-app-service")
TIMEOUT = int(os.getenv("PROMETHEUS_TIMEOUT", "5"))

class MetricsData(BaseModel):
    """Input data format for prediction"""
    value: Optional[float] = None
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

class PrometheusStatus(BaseModel):
    """Prometheus connection status"""
    connected: bool
    metrics: Dict[str, float]
    error: Optional[str] = None

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
        '/app/models/isolation_forest_model_fresh.pkl',  # Container path
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
        
        # Test Prometheus connection after model loads
        await test_prometheus_connection()

async def test_prometheus_connection() -> bool:
    """Test connection to Prometheus"""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": "up"},
            timeout=TIMEOUT
        )
        if response.status_code == 200:
            logger.info("✅ Successfully connected to Prometheus")
            return True
        else:
            logger.warning(f"⚠️ Prometheus connection returned status {response.status_code}")
            return False
    except Exception as e:
        logger.warning(f"⚠️ Could not connect to Prometheus: {e}")
        logger.info(f"   Prometheus URL configured as: {PROMETHEUS_URL}")
        return False

async def fetch_prometheus_metrics() -> Dict[str, float]:
    """Fetch real-time metrics from Prometheus"""
    metrics = {
        'cpu_usage': 50.0,
        'memory_usage': 50.0,
        'request_rate': 10.0,
        'error_rate': 0.0,
        'value': 50.0,
        'hour': datetime.now().hour,
        'day_of_week': datetime.now().weekday(),
        'day_of_month': datetime.now().day
    }
    
    # Query CPU usage
    try:
        cpu_query = f'sum(rate(container_cpu_usage_seconds_total{{namespace="{APP_NAMESPACE}", pod=~"sfe-devops-app.*"}}[1m]))'
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": cpu_query},
            timeout=TIMEOUT
        )
        if response.status_code == 200:
            data = response.json()
            if data['data']['result']:
                # Convert cores to percentage (assuming 2 cores limit)
                cpu_cores = float(data['data']['result'][0]['value'][1])
                metrics['cpu_usage'] = min(100, cpu_cores * 50)  # Rough estimate
                logger.info(f"📊 CPU usage: {metrics['cpu_usage']:.1f}%")
    except Exception as e:
        logger.warning(f"⚠️ Error fetching CPU metrics: {e}")
    
    # Query memory usage
    try:
        memory_query = f'sum(container_memory_working_set_bytes{{namespace="{APP_NAMESPACE}", pod=~"sfe-devops-app.*"}})'
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": memory_query},
            timeout=TIMEOUT
        )
        if response.status_code == 200:
            data = response.json()
            if data['data']['result']:
                memory_bytes = float(data['data']['result'][0]['value'][1])
                # Assume 512Mi limit
                memory_limit = 512 * 1024 * 1024
                metrics['memory_usage'] = min(100, (memory_bytes / memory_limit) * 100)
                logger.info(f"📊 Memory usage: {metrics['memory_usage']:.1f}%")
    except Exception as e:
        logger.warning(f"⚠️ Error fetching memory metrics: {e}")
    
    # Query request rate
    try:
        request_query = f'sum(rate(http_requests_total{{namespace="{APP_NAMESPACE}"}}[1m]))'
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": request_query},
            timeout=TIMEOUT
        )
        if response.status_code == 200:
            data = response.json()
            if data['data']['result']:
                metrics['request_rate'] = float(data['data']['result'][0]['value'][1])
                logger.info(f"📊 Request rate: {metrics['request_rate']:.1f} req/s")
    except Exception as e:
        logger.warning(f"⚠️ Error fetching request metrics: {e}")
    
    # Query error rate
    try:
        error_query = f'sum(rate(http_errors_total{{namespace="{APP_NAMESPACE}"}}[1m])) / sum(rate(http_requests_total{{namespace="{APP_NAMESPACE}"}}[1m])) * 100'
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": error_query},
            timeout=TIMEOUT
        )
        if response.status_code == 200:
            data = response.json()
            if data['data']['result']:
                metrics['error_rate'] = float(data['data']['result'][0]['value'][1])
                logger.info(f"📊 Error rate: {metrics['error_rate']:.2f}%")
    except Exception as e:
        logger.warning(f"⚠️ Error fetching error metrics: {e}")
    
    # Combined metric for prediction (weighted average)
    metrics['value'] = (
        metrics['cpu_usage'] * 0.3 +
        metrics['memory_usage'] * 0.3 +
        metrics['request_rate'] * 0.2 +
        metrics['error_rate'] * 0.2
    )
    
    # Add time features
    now = datetime.now()
    metrics['hour'] = now.hour
    metrics['day_of_week'] = now.weekday()
    metrics['day_of_month'] = now.day
    
    return metrics

def prepare_features(metrics: Dict[str, float]) -> np.ndarray:
    """Convert metrics to feature vector for model"""
    features = np.array([[
        metrics.get('value', 50),
        metrics.get('hour', 12),
        metrics.get('day_of_week', 3),
        metrics.get('day_of_month', 15),
        metrics.get('value', 50),  # rolling_mean_5
        5.0,                         # rolling_std_5 (estimate)
        metrics.get('value', 50),   # rolling_mean_20
        10.0,                         # rolling_std_20 (estimate)
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
        "prometheus_url": PROMETHEUS_URL,
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "model_loaded": model is not None}

@app.get("/prometheus/status", response_model=PrometheusStatus)
async def prometheus_status():
    """Check Prometheus connection status and return current metrics"""
    try:
        metrics = await fetch_prometheus_metrics()
        return PrometheusStatus(
            connected=True,
            metrics=metrics
        )
    except Exception as e:
        return PrometheusStatus(
            connected=False,
            metrics={},
            error=str(e)
        )

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
        logger.info(f"Live metrics: CPU={metrics['cpu_usage']:.1f}%, "
                   f"Memory={metrics['memory_usage']:.1f}%, "
                   f"Requests={metrics['request_rate']:.1f}/s, "
                   f"Errors={metrics['error_rate']:.2f}%")
    
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
        "cpu_usage": round(metrics['cpu_usage'], 2),
        "memory_usage": round(metrics['memory_usage'], 2),
        "request_rate": round(metrics['request_rate'], 2),
        "error_rate": round(metrics['error_rate'], 2),
        "combined_value": round(metrics['value'], 2)
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
