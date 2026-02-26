from flask import Flask, jsonify, render_template
import os
import socket
import datetime
import time
import random
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint'])
ERROR_COUNT = Counter('http_errors_total', 'Total HTTP errors', ['method', 'endpoint'])
ACTIVE_REQUESTS = Gauge('http_active_requests', 'Active requests')  # Fixed: Changed from Counter to Gauge

# Store startup time for uptime calculation
start_time = time.time()

def get_simulated_metrics():
    hour = datetime.datetime.now().hour
    base_load = 10 if 9 <= hour <= 17 else 3
    return {
        'cpu_usage': min(95, base_load + random.uniform(0, 20)),
        'memory_usage': min(90, 30 + random.uniform(0, 30)),
        'request_rate': base_load * 10 + random.uniform(0, 50),
        'error_rate': random.uniform(0, 2) if base_load < 8 else random.uniform(0, 5)
    }

@app.route('/')
def home():
    ACTIVE_REQUESTS.inc()
    try:
        response = render_template('index.html', 
                                 hostname=socket.gethostname(),
                                 environment=os.getenv("ENV", "development"))
        REQUEST_COUNT.labels(method='GET', endpoint='/', status='200').inc()
        return response
    finally:
        ACTIVE_REQUESTS.dec()

@app.route('/api')
def api():
    ACTIVE_REQUESTS.inc()
    start_time = time.time()
    try:
        time.sleep(random.uniform(0.01, 0.1))
        response_data = {
            "message": "Hello from SFE DevOps Pipeline!",
            "hostname": socket.gethostname(),
            "timestamp": datetime.datetime.now().isoformat(),
            "environment": os.getenv("ENV", "development")
        }
        REQUEST_COUNT.labels(method='GET', endpoint='/api', status='200').inc()
        REQUEST_LATENCY.labels(method='GET', endpoint='/api').observe(time.time() - start_time)
        return jsonify(response_data)
    except Exception as e:
        ERROR_COUNT.labels(method='GET', endpoint='/api').inc()
        REQUEST_COUNT.labels(method='GET', endpoint='/api', status='500').inc()
        return jsonify({"error": str(e)}), 500
    finally:
        ACTIVE_REQUESTS.dec()

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat()
    }), 200

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint - returns Prometheus formatted metrics"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/status')
def status():
    uptime = int(time.time() - start_time)
    simulated = get_simulated_metrics()
    return render_template('status.html',
                         hostname=socket.gethostname(),
                         environment=os.getenv("ENV", "development"),
                         python_version=os.sys.version,
                         timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                         uptime=str(datetime.timedelta(seconds=uptime)),
                         cpu_usage=simulated['cpu_usage'],
                         memory_usage=simulated['memory_usage'],
                         request_rate=simulated['request_rate'],
                         error_rate=simulated['error_rate'])

@app.route('/simulate/error')
def simulate_error():
    if random.random() < 0.7:
        ERROR_COUNT.labels(method='GET', endpoint='/simulate/error').inc()
        REQUEST_COUNT.labels(method='GET', endpoint='/simulate/error', status='500').inc()
        return jsonify({"error": "Simulated error"}), 500
    REQUEST_COUNT.labels(method='GET', endpoint='/simulate/error', status='200').inc()
    return jsonify({"message": "Success"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)