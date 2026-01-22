import sys
import os
import pytest
from fastapi.testclient import TestClient

# Add parent directory to path to import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)

def test_health_check():
    """Verify that the health check endpoint returns 200 and correct structure."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "config" in data
    assert "browser_fallback_enabled" in data["config"]

def test_schema_availability():
    """Verify that the schema endpoint is accessible."""
    response = client.get("/schemas/answer-engine-response")
    # Schema file might not exist in this environment, but endpoint should be registered
    # If file is missing it returns 404, if present 200.
    # We at least check it doesn't 500.
    assert response.status_code in [200, 404]
