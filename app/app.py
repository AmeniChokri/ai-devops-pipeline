from flask import Flask, jsonify, render_template, request
import os
import socket
import datetime
import time

app = Flask(__name__)

# Store startup time for uptime calculation
start_time = time.time()

# Home page - HTML interface
@app.route('/')
def home():
    return render_template('index.html', 
                         hostname=socket.gethostname(),
                         environment=os.getenv("ENV", "development"))

# API endpoint - JSON version
@app.route('/api')
def api():
    return jsonify({
        "message": "Hello from SFE DevOps Pipeline!",
        "hostname": socket.gethostname(),
        "timestamp": datetime.datetime.now().isoformat(),
        "environment": os.getenv("ENV", "development")
    })

# Health check for Kubernetes
@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat()
    }), 200

# Metrics endpoint for Prometheus
@app.route('/metrics')
def metrics():
    uptime = int(time.time() - start_time)
    return jsonify({
        "app": "sfe-devops-pipeline",
        "version": "1.0.0",
        "uptime_seconds": uptime,
        "uptime_human": str(datetime.timedelta(seconds=uptime)),
        "requests": 42,  # Placeholder for demo
        "errors": 0
    })

# Status page with system info
@app.route('/status')
def status():
    return render_template('status.html',
                         hostname=socket.gethostname(),
                         environment=os.getenv("ENV", "development"),
                         python_version=os.sys.version,
                         timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)