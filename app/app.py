from flask import Flask, jsonify
import os
import socket
import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "message": "Hello from SFE DevOps Pipeline!",
        "hostname": socket.gethostname(),
        "timestamp": datetime.datetime.now().isoformat(),
        "environment": os.getenv("ENV", "development")
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat()
    }), 200

@app.route('/metrics')
def metrics():
    # Simple metrics endpoint for Prometheus
    return jsonify({
        "requests": 42,
        "errors": 0,
        "uptime": "5m"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)