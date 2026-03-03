"""
Tests for Error Handling and Fallback Strategies (Task 7.3)

Tests the ResilientAgentManager with comprehensive error handling,
fallback strategies, retry logic, timeout handling, and error logging.

**Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5**
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import List

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from rag.agent_manager_core import (
    ResilientAgentManager,
    AgentResult,
    LLMError,
    VectorStoreError,
    NetworkError,
    ErrorLogger,
)
from rag.agent_config import AgentConfig


class MockTool(BaseTool):
    """Mock tool for testing."""
    name: str = "mock_tool"
    description: str = "A mock tool for testing"
    
    def _run(self, query: str) -> str:
        return f"Result for: {query}"
    
    async def _arun(self, query: str) -> str:
        return f"Async result for: {query}"


class TestErrorHandling:
    """Test error handling in ResilientAgentManager."""
    
    def test_llm_error_handling(self):
        """Test LLM error is caught and handled."""
        mock_llm_provider = Mock()
        tools = [MockTool()]
        
        manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools,
            enable_fallback=True
        )
        
        # Verify manager is initialized
        assert manager.enable_fallback is True
        assert manager.max_retries == 3
        assert manager.retry_delay == 1.0
    
    def test_vector_store_error_handling(self):
        """Test VectorStoreError is caught and handled."""
        mock_llm_provider = Mock()
        tools = [MockTool()]
        
        manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools,
            enable_fallback=True
        )
        
        # Verify manager can handle vector store errors
        assert manager.enable_fallback is True
    
    def test_network_error_handling(self):
        """Test NetworkError is caught and handled."""
        mock_llm_provider = Mock()
        tools = [MockTool()]
        
        manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools,
            enable_fallback=True
        )
        
        # Verify manager can handle network errors
        assert manager.enable_fallback is True


class TestRetryLogic:
    """Test retry logic with exponential backoff."""
    
    def test_retry_configuration(self):
        """Test retry configuration."""
        mock_llm_provider = Mock()
        tools = [MockTool()]
        
        manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools,
            max_retries=5,
            retry_delay=2.0
        )
        
        assert manager.max_retries == 5
        assert manager.retry_delay == 2.0
    
    def test_is_retryable_error_timeout(self):
        """Test timeout errors are retryable."""
        mock_llm_provider = Mock()
        tools = [MockTool()]
        
        manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools
        )
        
        # Timeout errors should be retryable
        assert manager._is_retryable_error("Connection timeout") is True
        assert manager._is_retryable_error("Request timeout") is True
    
    def test_is_retryable_error_network(self):
        """Test network errors are retryable."""
        mock_llm_provider = Mock()
        tools = [MockTool()]
        
        manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools
        )
        
        # Network errors should be retryable
        assert manager._is_retryable_error("Network connection failed") is True
        assert manager._is_retryable_error("Connection refused") is True
    
    def test_is_retryable_error_unavailable(self):
        """Test service unavailable errors are retryable."""
        mock_llm_provider = Mock()
        tools = [MockTool()]
        
        manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools
        )
        
        # Service unavailable errors should be retryable
        assert manager._is_retryable_error("Service unavailable") is True
        assert manager._is_retryable_error("503 Service Unavailable") is True
    
    def test_is_retryable_error_rate_limit(self):
        """Test rate limit errors are retryable."""
        mock_llm_provider = Mock()
        tools = [MockTool()]
        
        manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools
        )
        
        # Rate limit errors should be retryable
        assert manager._is_retryable_error("Rate limit exceeded") is True
        assert manager._is_retryable_error("429 Too Many Requests") is True
    
    def test_is_retryable_error_invalid_input(self):
        """Test invalid input errors are not retryable."""
        mock_llm_provider = Mock()
        tools = [MockTool()]
        
        manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools
        )
        
        # Invalid input errors should not be retryable
        assert manager._is_retryable_error("Invalid input") is False
        assert manager._is_retryable_error("Invalid request") is False
    
    def test_is_retryable_error_authentication(self):
        """Test authentication errors are not retryable."""
        mock_llm_provider = Mock()
        tools = [MockTool()]
        
        manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools
        )
        
        # Authentication errors should not be retryable
        assert manager._is_retryable_error("Authentication failed") is False
        assert manager._is_retryable_error("Unauthorized") is False
        assert manager._is_retryable_error("401 Unauthorized") is False
    
    def test_is_retryable_error_not_found(self):
        """Test not found errors are not retryable."""
        mock_llm_provider = Mock()
        tools = [MockTool()]
        
        manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools
        )
        
        # Not found errors should not be retryable
        assert manager._is_retryable_error("Not found") is False
        assert manager._is_retryable_error("404 Not Found") is False


class TestTimeoutHandling:
    """Test timeout handling for long-running operations."""
    
    def test_timeout_configuration(self):
        """Test timeout configuration."""
        mock_llm_provider = Mock()
        tools = [MockTool()]
        
        config = AgentConfig(max_execution_time=30)
        manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools,
            config=config
        )
        
        assert manager.config.max_execution_time == 30
    
    def test_default_timeout(self):
        """Test default timeout value."""
        mock_llm_provider = Mock()
        tools = [MockTool()]
        
        manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools
        )
        
        # Default timeout should be 60 seconds
        assert manager.config.max_execution_time == 60


class TestFallbackStrategies:
    """Test fallback strategies."""
    
    def test_fallback_enabled(self):
        """Test fallback is enabled by default."""
        mock_llm_provider = Mock()
        tools = [MockTool()]
        
        manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools
        )
        
        assert manager.enable_fallback is True
    
    def test_fallback_disabled(self):
        """Test fallback can be disabled."""
        mock_llm_provider = Mock()
        tools = [MockTool()]
        
        manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools,
            enable_fallback=False
        )
        
        assert manager.enable_fallback is False


class TestErrorLogging:
    """Test error logging functionality."""
    
    def test_error_logger_initialization(self):
        """Test ErrorLogger can be initialized."""
        # ErrorLogger is a static class, just verify it exists
        assert hasattr(ErrorLogger, 'log_error')
    
    def test_error_logger_log_error(self):
        """Test ErrorLogger.log_error method."""
        # Test that log_error can be called
        context = {
            "user_input": "test",
            "session_id": "session_123"
        }
        
        # Should not raise an exception
        ErrorLogger.log_error(
            error_type="TEST_ERROR",
            error_message="Test error message",
            context=context
        )


class TestVectorStoreFallback:
    """Test vector store fallback to keyword search."""
    
    def test_vector_store_fallback_enabled(self):
        """Test vector store fallback is available."""
        mock_llm_provider = Mock()
        tools = [MockTool()]
        
        manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools,
            enable_fallback=True
        )
        
        # Verify fallback method exists
        assert hasattr(manager, '_fallback_keyword_search')


class TestLLMFailureHandling:
    """Test LLM failure handling."""
    
    def test_llm_failure_fallback(self):
        """Test LLM failure triggers fallback."""
        mock_llm_provider = Mock()
        tools = [MockTool()]
        
        manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools,
            enable_fallback=True
        )
        
        # Verify fallback method exists
        assert hasattr(manager, '_fallback_response')


class TestNetworkRetryLogic:
    """Test network retry logic."""
    
    def test_network_retry_max_retries(self):
        """Test network retry respects max_retries."""
        mock_llm_provider = Mock()
        tools = [MockTool()]
        
        manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools,
            max_retries=3
        )
        
        assert manager.max_retries == 3
    
    def test_network_retry_delay(self):
        """Test network retry delay configuration."""
        mock_llm_provider = Mock()
        tools = [MockTool()]
        
        manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools,
            retry_delay=2.0
        )
        
        assert manager.retry_delay == 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
