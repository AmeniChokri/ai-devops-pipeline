"""
AI Prediction Service for DevOps Anomaly Detection
This service loads the trained Isolation Forest model and provides a REST API
for real-time anomaly detection and risk scoring.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import numpy as np
import os
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="DevOps Anomaly Detection API",
    description="AI-powered anomaly detection for CI/CD pipeline",
    version="1.0.0"
)

# Global variables for model and scaler
model = None
scaler = None

class MetricsData(BaseModel):
    """Input data format for prediction"""
    value: float
    hour: Optional[int] = 14
    day_of_week: Optional[int] = 3
    day_of_month: Optional[int] = 12

class PredictionResponse(BaseModel):
    """Prediction result format"""
    risk_score: float
    is_anomaly: bool
    confidence: float
    anomaly_score: float
    recommendation: str
    model_version: str

@app.on_event("startup")
async def load_model():
    """Load the trained model and scaler on startup"""
    global model, scaler
    
    # Try multiple possible paths
    possible_paths = [
        '/app/models/isolation_forest_model.pkl',
        '../models/isolation_forest_model.pkl',
        './models/isolation_forest_model.pkl'
    ]
    
    for model_path in possible_paths:
        if os.path.exists(model_path):
            try:
                model = joblib.load(model_path)
                logger.info(f"✅ Model loaded from {model_path}")
                break
            except Exception as e:
                logger.error(f"Error loading model from {model_path}: {e}")
    
    if model is None:
        logger.error("❌ Could not load model from any path")

@app.get("/")
async def root():
    return {
        "service": "DevOps Anomaly Detection API",
        "status": "operational" if model else "degraded",
        "model_loaded": model is not None
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/predict", response_model=PredictionResponse)
async def predict(data: MetricsData):
    if model is None:
        # Return a mock prediction if model isn't loaded
        risk_score = 75.0 if data.value > 80 else 25.0
        return PredictionResponse(
            risk_score=risk_score,
            is_anomaly=data.value > 80,
            confidence=85.0,
            anomaly_score=-0.2 if data.value > 80 else 0.3,
            recommendation="⚠️ MODERATE RISK: Manual review recommended" if data.value > 80 else "✅ LOW RISK: Safe to proceed",
            model_version="fallback-v1"
        )
    
    # Simple prediction based on value only (for demo)
    features = np.array([[data.value, data.hour, data.day_of_week, data.day_of_month, 
                          data.value, 0, data.value, 0, data.value, data.value, data.value]])
    
    if scaler is not None:
        features = scaler.transform(features)
    
    anomaly_score = model.decision_function(features)[0]
    prediction = model.predict(features)[0]
    
    risk_score = max(0, min(100, (0.5 - anomaly_score) * 100))
    is_anomaly = prediction == -1
    confidence = min(100, abs(anomaly_score) * 200)
    
    if risk_score > 80:
        recommendation = "🚨 HIGH RISK: Auto-rollback recommended"
    elif risk_score > 50:
        recommendation = "⚠️ MODERATE RISK: Manual review recommended"
    else:
        recommendation = "✅ LOW RISK: Safe to proceed"
    
    return PredictionResponse(
        risk_score=round(risk_score, 2),
        is_anomaly=is_anomaly,
        confidence=round(confidence, 2),
        anomaly_score=round(anomaly_score, 4),
        recommendation=recommendation,
        model_version="isolation-forest-v1"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
