"""
Tests for AgentManager Core Implementation

Tests the core AgentManager class with LangChain 1.x integration,
tool binding, memory integration, and configuration support.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 19.1, 19.2, 19.3, 19.4, 19.5**
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import List

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from rag.agent_manager_core import (
    AgentManager,
    AgentResult,
    ResilientAgentManager,
    ToolCall,
    AgentExecutionError,
    ToolExecutionError,
)
from rag.agent_config import AgentConfig
from core.persistent_conversation_memory import PersistentConversationMemory


# Mock Tool for testing
class MockToolInput(BaseModel):
    """Mock tool input."""
    query: str = Field(description="Query string")


class MockTool(BaseTool):
    """Mock tool for testing."""
    name: str = "mock_tool"
    description: str = "A mock tool for testing"
    args_schema: type = MockToolInput
    
    def _run(self, query: str) -> str:
        """Run the tool."""
        return f"Result for: {query}"
    
    async def _arun(self, query: str) -> str:
        """Async run the tool."""
        return f"Async result for: {query}"


class TestAgentManagerInitialization:
    """Test AgentManager initialization."""
    
    def test_agent_manager_init_with_defaults(self):
        """Test AgentManager initialization with default config."""
        # Create mock LLM provider
        mock_llm_provider = Mock()
        mock_llm_provider.generate = AsyncMock(return_value="Test response")
        
        # Create tools
        tools = [MockTool()]
        
        # Initialize AgentManager
        agent_manager = AgentManager(
            llm_provider=mock_llm_provider,
            tools=tools
        )
        
        # Verify initialization
        assert agent_manager.llm_provider == mock_llm_provider
        assert agent_manager.tools == tools
        assert agent_manager.config is not None
        assert agent_manager.config.max_iterations == 10
        assert agent_manager.config.max_execution_time == 60
        assert agent_manager.agent_executor is not None
    
    def test_agent_manager_init_with_custom_config(self):
        """Test AgentManager initialization with custom config."""
        # Create mock LLM provider
        mock_llm_provider = Mock()
        
        # Create custom config
        config = AgentConfig(
            max_iterations=5,
            max_execution_time=30,
            verbose=True
        )
        
        # Create tools
        tools = [MockTool()]
        
        # Initialize AgentManager
        agent_manager = AgentManager(
            llm_provider=mock_llm_provider,
            tools=tools,
            config=config
        )
        
        # Verify configuration
        assert agent_manager.config.max_iterations == 5
        assert agent_manager.config.max_execution_time == 30
        assert agent_manager.config.verbose is True
    
    def test_agent_manager_init_with_memory(self):
        """Test AgentManager initialization with memory."""
        # Create mock LLM provider
        mock_llm_provider = Mock()
        
        # Create mock memory
        mock_memory = Mock(spec=PersistentConversationMemory)
        
        # Create tools
        tools = [MockTool()]
        
        # Initialize AgentManager
        agent_manager = AgentManager(
            llm_provider=mock_llm_provider,
            tools=tools,
            memory=mock_memory
        )
        
        # Verify memory is set
        assert agent_manager.memory == mock_memory


class TestAgentManagerExecution:
    """Test AgentManager execution."""
    
    @pytest.mark.asyncio
    async def test_ainvoke_basic(self):
        """Test basic async invocation."""
        # Create mock LLM provider
        mock_llm_provider = Mock()
        mock_llm_provider.generate = AsyncMock(return_value="Test response")
        
        # Create tools
        tools = [MockTool()]
        
        # Initialize AgentManager
        agent_manager = AgentManager(
            llm_provider=mock_llm_provider,
            tools=tools
        )
        
        # Mock the agent executor
        agent_manager.agent_executor = AsyncMock()
        agent_manager.agent_executor.ainvoke = AsyncMock(
            return_value={"output": "Test response"}
        )
        
        # Execute
        result = await agent_manager.ainvoke(
            user_input="Test query",
            session_id="test_session"
        )
        
        # Verify result
        assert isinstance(result, AgentResult)
        assert result.output == "Test response"
        assert result.error is None
        assert result.execution_time >= 0
    
    def test_invoke_sync(self):
        """Test synchronous invocation."""
        # Create mock LLM provider
        mock_llm_provider = Mock()
        mock_llm_provider.generate = AsyncMock(return_value="Test response")
        
        # Create tools
        tools = [MockTool()]
        
        # Initialize AgentManager
        agent_manager = AgentManager(
            llm_provider=mock_llm_provider,
            tools=tools
        )
        
        # Mock the agent executor
        agent_manager.agent_executor = AsyncMock()
        agent_manager.agent_executor.ainvoke = AsyncMock(
            return_value={"output": "Test response"}
        )
        
        # Execute
        result = agent_manager.invoke(
            user_input="Test query",
            session_id="test_session"
        )
        
        # Verify result
        assert isinstance(result, AgentResult)
        assert result.output == "Test response"
        assert result.error is None


class TestAgentConfig:
    """Test AgentConfig."""
    
    def test_agent_config_defaults(self):
        """Test AgentConfig default values."""
        config = AgentConfig()
        
        assert config.max_iterations == 10
        assert config.max_execution_time == 60
        assert config.handle_parsing_errors is True
        assert config.verbose is False
        assert config.return_intermediate_steps is True
        assert config.memory_max_history == 10
        assert config.early_stopping_method == "force"
    
    def test_agent_config_validation(self):
        """Test AgentConfig validation."""
        # Test max_iterations bounds
        with pytest.raises(ValueError):
            AgentConfig(max_iterations=0)
        
        with pytest.raises(ValueError):
            AgentConfig(max_iterations=51)
        
        # Test max_execution_time bounds
        with pytest.raises(ValueError):
            AgentConfig(max_execution_time=0)
        
        with pytest.raises(ValueError):
            AgentConfig(max_execution_time=301)


class TestToolCall:
    """Test ToolCall dataclass."""
    
    def test_tool_call_creation(self):
        """Test ToolCall creation."""
        tool_call = ToolCall(
            tool_name="test_tool",
            tool_input={"query": "test"},
            tool_output="result",
            execution_time=1.5,
            timestamp=1234567890.0
        )
        
        assert tool_call.tool_name == "test_tool"
        assert tool_call.tool_input == {"query": "test"}
        assert tool_call.tool_output == "result"
        assert tool_call.execution_time == 1.5
        assert tool_call.timestamp == 1234567890.0


class TestAgentResult:
    """Test AgentResult dataclass."""
    
    def test_agent_result_success(self):
        """Test successful AgentResult."""
        result = AgentResult(
            output="Test output",
            intermediate_steps=[],
            tool_calls=[],
            execution_time=1.0,
            error=None
        )
        
        assert result.output == "Test output"
        assert result.error is None
        assert result.execution_time == 1.0
    
    def test_agent_result_with_error(self):
        """Test AgentResult with error."""
        result = AgentResult(
            output="",
            intermediate_steps=[],
            tool_calls=[],
            execution_time=1.0,
            error="Test error"
        )
        
        assert result.output == ""
        assert result.error == "Test error"


class TestResilientAgentManager:
    """Test ResilientAgentManager."""
    
    def test_resilient_agent_manager_init(self):
        """Test ResilientAgentManager initialization."""
        # Create mock LLM provider
        mock_llm_provider = Mock()
        
        # Create tools
        tools = [MockTool()]
        
        # Initialize ResilientAgentManager
        agent_manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools,
            enable_fallback=True
        )
        
        # Verify initialization
        assert agent_manager.enable_fallback is True
        assert agent_manager.llm_provider == mock_llm_provider
        assert agent_manager.tools == tools
    
    @pytest.mark.asyncio
    async def test_resilient_agent_manager_timeout(self):
        """Test ResilientAgentManager timeout handling."""
        # Create mock LLM provider
        mock_llm_provider = Mock()
        
        # Create tools
        tools = [MockTool()]
        
        # Create config with short timeout
        config = AgentConfig(max_execution_time=1)
        
        # Initialize ResilientAgentManager
        agent_manager = ResilientAgentManager(
            llm_provider=mock_llm_provider,
            tools=tools,
            config=config,
            enable_fallback=True
        )
        
        # Mock the agent executor to timeout
        async def slow_invoke(*args, **kwargs):
            await asyncio.sleep(2)
            return {"output": "Should timeout"}
        
        agent_manager.agent_executor = AsyncMock()
        agent_manager.agent_executor.ainvoke = slow_invoke
        
        # Execute with fallback
        result = await agent_manager.ainvoke_with_fallback(
            user_input="Test query",
            session_id="test_session"
        )
        
        # Verify timeout was handled
        assert result.error is not None
        assert "timeout" in result.error.lower() or result.output != ""


class TestAgentManagerExceptions:
    """Test AgentManager exception handling."""
    
    def test_agent_execution_error(self):
        """Test AgentExecutionError."""
        error = AgentExecutionError("Test error")
        assert str(error) == "Test error"
    
    def test_tool_execution_error(self):
        """Test ToolExecutionError."""
        error = ToolExecutionError("Test error")
        assert str(error) == "Test error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
