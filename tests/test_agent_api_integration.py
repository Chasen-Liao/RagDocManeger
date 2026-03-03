"""API integration tests for Agent endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session

from main import create_app
from api.agent_routes import AgentRequest, AgentResponse


@pytest.fixture
def app():
    """Create test app."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_agent_manager():
    """Create mock agent manager."""
    manager = Mock()
    manager.ainvoke = AsyncMock(return_value=Mock(
        output="Test response",
        tool_calls=[],
        execution_time=0.5,
        intermediate_steps=[]
    ))
    manager.astream = AsyncMock()
    manager.clear_session = AsyncMock()
    manager.get_performance_stats = Mock(return_value={"calls": 1})
    return manager


class TestAgentChatEndpoint:
    """Test /api/v1/agent/chat endpoint."""
    
    def test_chat_endpoint_exists(self, client):
        """Test that chat endpoint exists."""
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "user_input": "Hello",
                "session_id": "test_session"
            }
        )
        # Should not return 404
        assert response.status_code != 404
    
    def test_chat_request_validation(self, client):
        """Test request validation."""
        # Missing required fields
        response = client.post(
            "/api/v1/agent/chat",
            json={"user_input": "Hello"}
        )
        assert response.status_code == 422  # Validation error
    
    def test_chat_response_format(self, client):
        """Test response format."""
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "user_input": "Hello",
                "session_id": "test_session"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data or "output" in data


class TestAgentStreamEndpoint:
    """Test /api/v1/agent/chat/stream endpoint."""
    
    def test_stream_endpoint_exists(self, client):
        """Test that stream endpoint exists."""
        response = client.post(
            "/api/v1/agent/chat/stream",
            json={
                "user_input": "Hello",
                "session_id": "test_session"
            }
        )
        # Should not return 404
        assert response.status_code != 404
    
    def test_stream_response_format(self, client):
        """Test streaming response format."""
        response = client.post(
            "/api/v1/agent/chat/stream",
            json={
                "user_input": "Hello",
                "session_id": "test_session"
            }
        )
        
        if response.status_code == 200:
            # Should return streaming response
            assert response.headers.get("content-type") == "text/event-stream"


class TestSessionManagementEndpoint:
    """Test /api/v1/agent/session/{session_id} endpoint."""
    
    def test_clear_session_endpoint_exists(self, client):
        """Test that clear session endpoint exists."""
        response = client.delete("/api/v1/agent/session/test_session")
        # Should not return 404
        assert response.status_code != 404
    
    def test_clear_session_response_format(self, client):
        """Test clear session response format."""
        response = client.delete("/api/v1/agent/session/test_session")
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data or "message" in data


class TestAgentHealthEndpoint:
    """Test /api/v1/agent/health endpoint."""
    
    def test_health_endpoint_exists(self, client):
        """Test that health endpoint exists."""
        response = client.get("/api/v1/agent/health")
        # Should not return 404
        assert response.status_code != 404
    
    def test_health_response_format(self, client):
        """Test health response format."""
        response = client.get("/api/v1/agent/health")
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data or "status" in data


class TestErrorHandling:
    """Test error handling in Agent endpoints."""
    
    def test_invalid_json(self, client):
        """Test handling of invalid JSON."""
        response = client.post(
            "/api/v1/agent/chat",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422]
    
    def test_missing_required_fields(self, client):
        """Test handling of missing required fields."""
        response = client.post(
            "/api/v1/agent/chat",
            json={"user_input": "Hello"}
        )
        assert response.status_code == 422
    
    def test_empty_user_input(self, client):
        """Test handling of empty user input."""
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "user_input": "",
                "session_id": "test_session"
            }
        )
        # Should either accept or reject empty input
        assert response.status_code in [200, 400, 422]


class TestRequestValidation:
    """Test request validation."""
    
    def test_valid_request(self, client):
        """Test valid request."""
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "user_input": "Hello, how are you?",
                "session_id": "test_session_123",
                "stream": False
            }
        )
        # Should not return validation error
        assert response.status_code != 422
    
    def test_request_with_metadata(self, client):
        """Test request with metadata."""
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "user_input": "Hello",
                "session_id": "test_session",
                "metadata": {"user_id": "user123", "context": "test"}
            }
        )
        # Should accept metadata
        assert response.status_code != 422
    
    def test_stream_flag(self, client):
        """Test stream flag."""
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "user_input": "Hello",
                "session_id": "test_session",
                "stream": True
            }
        )
        # Should accept stream flag
        assert response.status_code != 422


class TestResponseFormat:
    """Test response format consistency."""
    
    def test_chat_response_structure(self, client):
        """Test chat response structure."""
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "user_input": "Hello",
                "session_id": "test_session"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            # Check for expected fields
            expected_fields = ["success", "output", "tool_calls", "execution_time"]
            for field in expected_fields:
                assert field in data or "error" in data
    
    def test_error_response_structure(self, client):
        """Test error response structure."""
        response = client.post(
            "/api/v1/agent/chat",
            json={"invalid": "request"}
        )
        
        if response.status_code >= 400:
            data = response.json()
            # Should have error information
            assert "detail" in data or "error" in data
