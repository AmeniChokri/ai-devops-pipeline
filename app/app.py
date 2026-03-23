from flask import Flask, jsonify, render_template
import os
import socket
import datetime
import time
import random
import requests
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint'])
ERROR_COUNT = Counter('http_errors_total', 'Total HTTP errors', ['method', 'endpoint'])
ACTIVE_REQUESTS = Gauge('http_active_requests', 'Active requests')

# Store startup time
start_time = time.time()

# AI service URL - use the ngrok URL for production
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "https://nonskeptical-jerald-nonformalistic.ngrok-free.dev")

def get_ai_metrics():
    """Fetch real-time metrics from AI service"""
    try:
        response = requests.get(f"{AI_SERVICE_URL}/prometheus/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('metrics', {})
    except Exception as e:
        print(f"Error fetching AI metrics: {e}")
    # Return simulated data if AI service unavailable
    hour = datetime.datetime.now().hour
    base_load = 10 if 9 <= hour <= 17 else 3
    return {
        'cpu_usage': min(95, base_load + random.uniform(0, 20)),
        'memory_usage': min(90, 30 + random.uniform(0, 30)),
        'request_rate': base_load * 10 + random.uniform(0, 50),
        'error_rate': random.uniform(0, 2) if base_load < 8 else random.uniform(0, 5)
    }

def get_risk_score():
    """Get current risk score from AI service"""
    try:
        response = requests.post(f"{AI_SERVICE_URL}/predict", json={}, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching risk score: {e}")
    return {
        'risk_score': random.uniform(0, 100),
        'is_anomaly': random.random() > 0.8,
        'recommendation': "AI service unavailable - using fallback"
    }

@app.route('/')
def home():
    ACTIVE_REQUESTS.inc()
    try:
        # Get current metrics for the dashboard
        ai_metrics = get_ai_metrics()
        risk_data = get_risk_score()
        
        response = render_template('index.html',
            hostname=socket.gethostname(),
            environment=os.getenv("ENV", "development"),
            timestamp=datetime.datetime.now().isoformat(),
            cpu_usage=round(ai_metrics.get('cpu_usage', 0), 1),
            memory_usage=round(ai_metrics.get('memory_usage', 0), 1),
            request_rate=round(ai_metrics.get('request_rate', 0), 1),
            error_rate=round(ai_metrics.get('error_rate', 0), 1),
            risk_score=round(risk_data.get('risk_score', 0), 1),
            is_anomaly=risk_data.get('is_anomaly', False),
            recommendation=risk_data.get('recommendation', 'Risk assessment complete'),
            uptime=int(time.time() - start_time)
        )
        REQUEST_COUNT.labels(method='GET', endpoint='/', status='200').inc()
        REQUEST_LATENCY.labels(method='GET', endpoint='/').observe(time.time() - start_time)
        return response
    finally:
        ACTIVE_REQUESTS.dec()

@app.route('/api')
def api():
    ACTIVE_REQUESTS.inc()
    start_req = time.time()
    try:
        response_data = {
            "message": "Hello from SFE AI DevOps Pipeline!",
            "hostname": socket.gethostname(),
            "timestamp": datetime.datetime.now().isoformat(),
            "environment": os.getenv("ENV", "development"),
            "uptime_seconds": int(time.time() - start_time)
        }
        REQUEST_COUNT.labels(method='GET', endpoint='/api', status='200').inc()
        REQUEST_LATENCY.labels(method='GET', endpoint='/api').observe(time.time() - start_req)
        return jsonify(response_data)
    except Exception as e:
        ERROR_COUNT.labels(method='GET', endpoint='/api').inc()
        REQUEST_COUNT.labels(method='GET', endpoint='/api', status='500').inc()
        return jsonify({"error": str(e)}), 500
    finally:
        ACTIVE_REQUESTS.dec()

@app.route('/health')
def health():
    REQUEST_COUNT.labels(method='GET', endpoint='/health', status='200').inc()
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "service": "sfe-ai-devops-pipeline",
        "version": "2.0.0"
    }), 200

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/api/live-metrics')
def live_metrics():
    """Dynamic endpoint for real-time metrics (for AJAX updates)"""
    REQUEST_COUNT.labels(method='GET', endpoint='/api/live-metrics', status='200').inc()
    ai_metrics = get_ai_metrics()
    risk_data = get_risk_score()
    
    return jsonify({
        "app": {
            "hostname": socket.gethostname(),
            "environment": os.getenv("ENV", "development"),
            "uptime": int(time.time() - start_time),
            "timestamp": datetime.datetime.now().isoformat()
        },
        "metrics": {
            "cpu_usage": round(ai_metrics.get('cpu_usage', 0), 1),
            "memory_usage": round(ai_metrics.get('memory_usage', 0), 1),
            "request_rate": round(ai_metrics.get('request_rate', 0), 1),
            "error_rate": round(ai_metrics.get('error_rate', 0), 1)
        },
        "risk": {
            "risk_score": round(risk_data.get('risk_score', 0), 1),
            "is_anomaly": risk_data.get('is_anomaly', False),
            "recommendation": risk_data.get('recommendation', 'Risk assessment complete')
        }
    })

@app.route('/status')
def status():
    uptime_seconds = int(time.time() - start_time)
    REQUEST_COUNT.labels(method='GET', endpoint='/status', status='200').inc()
    return render_template('status.html',
        hostname=socket.gethostname(),
        environment=os.getenv("ENV", "development"),
        python_version=os.sys.version.split()[0],
        timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        uptime=str(datetime.timedelta(seconds=uptime_seconds)),
        uptime_seconds=uptime_seconds
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)