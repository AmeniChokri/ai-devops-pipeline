import pytest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_endpoint(client):
    """Test the home endpoint returns 200"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'SFE DevOps Pipeline' in response.data

def test_health_endpoint(client):
    """Test the health endpoint returns healthy status"""
    response = client.get('/health')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'healthy'

def test_metrics_endpoint(client):
    """Test the metrics endpoint exists"""
    response = client.get('/metrics')
    assert response.status_code == 200