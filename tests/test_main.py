"""Tests for main FastAPI application."""
import pytest
from fastapi.testclient import TestClient
from main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app=app)


def test_app_creation():
    """Test that app can be created."""
    app = create_app()
    assert app is not None
    assert app.title == "RagDocMan"


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"
    assert data["data"]["app_name"] == "RagDocMan"


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Welcome to RagDocMan" in data["data"]["message"]
    assert data["data"]["docs"] == "/docs"


def test_response_format(client):
    """Test that responses follow unified format."""
    response = client.get("/health")
    data = response.json()
    
    # Check required fields
    assert "success" in data
    assert "data" in data
    assert "message" in data


def test_404_error(client):
    """Test 404 error handling."""
    response = client.get("/nonexistent")
    
    assert response.status_code == 404


def test_app_debug_mode():
    """Test app debug mode configuration."""
    app = create_app()
    # Debug mode should be configurable
    assert hasattr(app, 'debug')
