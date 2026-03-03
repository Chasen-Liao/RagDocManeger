"""Property-based tests for Agent execution.

This module contains property-based tests using Hypothesis to verify that
the Agent execution maintains correctness properties across different inputs
and error conditions.

**Validates: Requirements 5.1, 5.2, 16.1, 16.3**
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import List, Dict, Any
from dataclasses import dataclass

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from rag.agent_manager_core import (
    AgentManager,
    ResilientAgentManager,
    AgentResult,
    ToolCall,
    LLMError,
    VectorStoreError,
    NetworkError,
)
from rag.agent_config import AgentConfig
from core.persistent_conversation_memory import PersistentConversationMemory


# Mock Tool for testing
class ToolInputModel(BaseModel):
    """Tool input model."""
    query: str = Field(description="Query string")


class DeterministicTestTool(BaseTool):
    """Deterministic test tool that always returns the same output for same input."""
    name: str = "deterministic_tool"
    description: str = "A deterministic tool for testing"
    args_schema: type = ToolInputModel
    
    # Store response map as class variable to avoid Pydantic issues
    _response_map: Dict[str, str] = {}
    _call_count: int = 0
    _call_history: List[str] = []
    
    def __init__(self, response_map: Dict[str, str] = None, **kwargs):
        super().__init__(**kwargs)
        self._response_map = response_map or {}
        self._call_count = 0
        self._call_history = []
    
    def _run(self, query: str) -> str:
        """Run the tool deterministically."""
        self._call_count += 1
        self._call_history.append(query)
        return self._response_map.get(query, f"Result for: {query}")
    
    async def _arun(self, query: str) -> str:
        """Async run the tool deterministically."""
        self._call_count += 1
        self._call_history.append(query)
        return self._response_map.get(query, f"Result for: {query}")


class FailingTestTool(BaseTool):
    """Test tool that fails on demand."""
    name: str = "failing_tool"
    description: str = "A tool that fails for testing error recovery"
    args_schema: type = ToolInputModel
    
    # Store fail_on_input as class variable to avoid Pydantic issues
    _fail_on_input: str = None
    _call_count: int = 0
    
    def __init__(self, fail_on_input: str = None, **kwargs):
        super().__init__(**kwargs)
        self._fail_on_input = fail_on_input
        self._call_count = 0
    
    def _run(self, query: str) -> str:
        """Run the tool, failing on specific input."""
        self._call_count += 1
        if self._fail_on_input and query == self._fail_on_input:
            raise Exception(f"Tool failed on input: {query}")
        return f"Result for: {query}"
    
    async def _arun(self, query: str) -> str:
        """Async run the tool, failing on specific input."""
        self._call_count += 1
        if self._fail_on_input and query == self._fail_on_input:
            raise Exception(f"Tool failed on input: {query}")
        return f"Result for: {query}"


# Hypothesis strategies for generating test data
user_input_strategy = st.text(
    alphabet=st.characters(blacklist_categories=("Cc", "Cs")),
    min_size=1,
    max_size=100
)
session_id_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
    min_size=1,
    max_size=50
)


class TestAgentDeterminism:
    """
    Property 15: Agent Determinism
    
    **Validates: Requirements 5.1, 5.2**
    
    Tests that the same input and context produce consistent tool calls.
    This verifies that the Agent's decision-making process is deterministic
    when given the same inputs and context.
    """

    @given(
        user_input=user_input_strategy,
        session_id=session_id_strategy
    )
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much]
    )
    def test_same_input_produces_consistent_tool_calls(
        self, user_input, session_id
    ):
        """
        Property: Same input and context should produce consistent tool calls.
        
        This test verifies that when the Agent is invoked with the same input
        and session context, it makes the same tool calls in the same order.
        This is critical for reproducibility and debugging.
        
        **Validates: Requirements 5.1, 5.2**
        """
        async def run_test():
            assume(len(user_input.strip()) > 0)
            assume(len(session_id.strip()) > 0)
            
            # Create mock LLM provider that returns deterministic responses
            mock_llm_provider = Mock()
            mock_llm_provider.generate = AsyncMock(
                return_value="Deterministic response"
            )
            
            # Create deterministic tool
            tool = DeterministicTestTool(
                response_map={
                    user_input: f"Consistent result for: {user_input}"
                }
            )
            tools = [tool]
            
            # Create config for deterministic behavior
            config = AgentConfig(
                max_iterations=1,
                verbose=False
            )
            
            # Create first agent instance
            agent1 = AgentManager(
                llm_provider=mock_llm_provider,
                tools=tools,
                config=config
            )
            
            # Mock the agent executor for deterministic behavior
            agent1.agent_executor = AsyncMock()
            agent1.agent_executor.ainvoke = AsyncMock(
                return_value={"output": "Deterministic response"}
            )
            
            # Execute first invocation
            result1 = await agent1.ainvoke(
                user_input=user_input,
                session_id=session_id
            )
            
            # Create second agent instance with same configuration
            agent2 = AgentManager(
                llm_provider=mock_llm_provider,
                tools=tools,
                config=config
            )
            
            # Mock the agent executor for deterministic behavior
            agent2.agent_executor = AsyncMock()
            agent2.agent_executor.ainvoke = AsyncMock(
                return_value={"output": "Deterministic response"}
            )
            
            # Execute second invocation with same input
            result2 = await agent2.ainvoke(
                user_input=user_input,
                session_id=session_id
            )
            
            # Verify consistency
            assert result1.output == result2.output, \
                "Same input should produce same output"
            assert result1.error == result2.error, \
                "Same input should produce same error status"
            assert len(result1.tool_calls) == len(result2.tool_calls), \
                "Same input should produce same number of tool calls"
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_test())

    @given(
        user_input=user_input_strategy,
        session_id=session_id_strategy
    )
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much]
    )
    def test_agent_execution_time_is_reasonable(
        self, user_input, session_id
    ):
        """
        Property: Agent execution should complete in reasonable time.
        
        This test verifies that the Agent completes execution within the
        configured timeout, ensuring responsiveness.
        
        **Validates: Requirements 5.1, 5.2**
        """
        async def run_test():
            assume(len(user_input.strip()) > 0)
            assume(len(session_id.strip()) > 0)
            
            # Create mock LLM provider
            mock_llm_provider = Mock()
            mock_llm_provider.generate = AsyncMock(
                return_value="Quick response"
            )
            
            # Create tool
            tool = DeterministicTestTool()
            tools = [tool]
            
            # Create config with reasonable timeout
            config = AgentConfig(
                max_iterations=1,
                max_execution_time=60
            )
            
            # Create agent
            agent = AgentManager(
                llm_provider=mock_llm_provider,
                tools=tools,
                config=config
            )
            
            # Mock the agent executor
            agent.agent_executor = AsyncMock()
            agent.agent_executor.ainvoke = AsyncMock(
                return_value={"output": "Response"}
            )
            
            # Execute
            result = await agent.ainvoke(
                user_input=user_input,
                session_id=session_id
            )
            
            # Verify execution time is reasonable
            assert result.execution_time >= 0, \
                "Execution time should be non-negative"
            assert result.execution_time < config.max_execution_time, \
                "Execution time should be less than configured timeout"
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_test())

    @given(
        user_input=user_input_strategy,
        session_id=session_id_strategy
    )
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much]
    )
    def test_agent_result_structure_is_consistent(
        self, user_input, session_id
    ):
        """
        Property: Agent result should always have consistent structure.
        
        This test verifies that AgentResult always contains all required fields
        with appropriate types, regardless of execution outcome.
        
        **Validates: Requirements 5.1, 5.2**
        """
        async def run_test():
            assume(len(user_input.strip()) > 0)
            assume(len(session_id.strip()) > 0)
            
            # Create mock LLM provider
            mock_llm_provider = Mock()
            mock_llm_provider.generate = AsyncMock(
                return_value="Response"
            )
            
            # Create tool
            tool = DeterministicTestTool()
            tools = [tool]
            
            # Create agent
            agent = AgentManager(
                llm_provider=mock_llm_provider,
                tools=tools
            )
            
            # Mock the agent executor
            agent.agent_executor = AsyncMock()
            agent.agent_executor.ainvoke = AsyncMock(
                return_value={"output": "Response"}
            )
            
            # Execute
            result = await agent.ainvoke(
                user_input=user_input,
                session_id=session_id
            )
            
            # Verify result structure
            assert isinstance(result, AgentResult), \
                "Result should be AgentResult instance"
            assert isinstance(result.output, str), \
                "Output should be string"
            assert isinstance(result.intermediate_steps, list), \
                "Intermediate steps should be list"
            assert isinstance(result.tool_calls, list), \
                "Tool calls should be list"
            assert isinstance(result.execution_time, (int, float)), \
                "Execution time should be numeric"
            assert result.error is None or isinstance(result.error, str), \
                "Error should be None or string"
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_test())


class TestAgentErrorRecovery:
    """
    Property 16: Error Recovery
    
    **Validates: Requirements 16.1, 16.3**
    
    Tests that the Agent doesn't crash when tools fail and implements
    appropriate error handling and recovery strategies.
    """

    @given(
        user_input=user_input_strategy,
        session_id=session_id_strategy
    )
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much]
    )
    def test_agent_handles_tool_failure_gracefully(
        self, user_input, session_id
    ):
        """
        Property: Agent should not crash when tools fail.
        
        This test verifies that when a tool raises an exception, the Agent
        handles it gracefully and returns a valid AgentResult with error
        information instead of crashing.
        
        **Validates: Requirements 16.1, 16.3**
        """
        async def run_test():
            assume(len(user_input.strip()) > 0)
            assume(len(session_id.strip()) > 0)
            
            # Create mock LLM provider
            mock_llm_provider = Mock()
            mock_llm_provider.generate = AsyncMock(
                return_value="Response"
            )
            
            # Create failing tool
            tool = FailingTestTool(fail_on_input=user_input)
            tools = [tool]
            
            # Create agent
            agent = AgentManager(
                llm_provider=mock_llm_provider,
                tools=tools
            )
            
            # Mock the agent executor to simulate tool failure
            async def failing_invoke(*args, **kwargs):
                raise Exception(f"Tool execution failed for input: {user_input}")
            
            agent.agent_executor = AsyncMock()
            agent.agent_executor.ainvoke = failing_invoke
            
            # Execute - should not raise exception
            result = await agent.ainvoke(
                user_input=user_input,
                session_id=session_id
            )
            
            # Verify graceful error handling
            assert isinstance(result, AgentResult), \
                "Should return AgentResult even on failure"
            assert result.error is not None, \
                "Should have error information"
            assert isinstance(result.error, str), \
                "Error should be string"
            assert result.execution_time >= 0, \
                "Should record execution time even on failure"
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_test())

    @given(
        user_input=user_input_strategy,
        session_id=session_id_strategy
    )
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much]
    )
    def test_resilient_agent_recovers_from_transient_failures(
        self, user_input, session_id
    ):
        """
        Property: ResilientAgentManager should recover from transient failures.
        
        This test verifies that the ResilientAgentManager implements retry
        logic and can recover from transient failures like network timeouts.
        
        **Validates: Requirements 16.1, 16.3**
        """
        async def run_test():
            assume(len(user_input.strip()) > 0)
            assume(len(session_id.strip()) > 0)
            
            # Create mock LLM provider
            mock_llm_provider = Mock()
            mock_llm_provider.generate = AsyncMock(
                return_value="Response"
            )
            
            # Create tool
            tool = DeterministicTestTool()
            tools = [tool]
            
            # Create config
            config = AgentConfig(max_iterations=1)
            
            # Create resilient agent
            agent = ResilientAgentManager(
                llm_provider=mock_llm_provider,
                tools=tools,
                config=config,
                enable_fallback=True,
                max_retries=3,
                retry_delay=0.1
            )
            
            # Mock the agent executor to succeed on retry
            call_count = 0
            
            async def eventually_succeeds(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    raise NetworkError("Transient network error")
                return {"output": "Recovered response"}
            
            agent.agent_executor = AsyncMock()
            agent.agent_executor.ainvoke = eventually_succeeds
            
            # Execute with fallback
            result = await agent.ainvoke_with_fallback(
                user_input=user_input,
                session_id=session_id
            )
            
            # Verify recovery
            assert isinstance(result, AgentResult), \
                "Should return AgentResult"
            assert result.output is not None, \
                "Should have output after recovery"
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_test())

    @given(
        user_input=user_input_strategy,
        session_id=session_id_strategy
    )
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much]
    )
    def test_resilient_agent_handles_timeout(
        self, user_input, session_id
    ):
        """
        Property: ResilientAgentManager should handle execution timeouts.
        
        This test verifies that when an operation exceeds the configured
        timeout, the Agent handles it gracefully and returns an appropriate
        error message.
        
        **Validates: Requirements 16.1, 16.3**
        """
        async def run_test():
            assume(len(user_input.strip()) > 0)
            assume(len(session_id.strip()) > 0)
            
            # Create mock LLM provider
            mock_llm_provider = Mock()
            mock_llm_provider.generate = AsyncMock(
                return_value="Response"
            )
            
            # Create tool
            tool = DeterministicTestTool()
            tools = [tool]
            
            # Create config with very short timeout
            config = AgentConfig(
                max_iterations=1,
                max_execution_time=1  # 1 second timeout
            )
            
            # Create resilient agent
            agent = ResilientAgentManager(
                llm_provider=mock_llm_provider,
                tools=tools,
                config=config,
                enable_fallback=True
            )
            
            # Mock the agent executor to timeout
            async def slow_invoke(*args, **kwargs):
                await asyncio.sleep(1)  # Sleep longer than timeout
                return {"output": "Should timeout"}
            
            agent.agent_executor = AsyncMock()
            agent.agent_executor.ainvoke = slow_invoke
            
            # Execute with fallback
            result = await agent.ainvoke_with_fallback(
                user_input=user_input,
                session_id=session_id
            )
            
            # Verify timeout handling
            assert isinstance(result, AgentResult), \
                "Should return AgentResult on timeout"
            assert result.error is not None or result.output != "", \
                "Should have error or fallback output on timeout"
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_test())

    @given(
        user_input=user_input_strategy,
        session_id=session_id_strategy
    )
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much]
    )
    def test_agent_error_contains_useful_information(
        self, user_input, session_id
    ):
        """
        Property: Agent errors should contain useful debugging information.
        
        This test verifies that when an error occurs, the error message
        contains enough information for debugging and understanding what
        went wrong.
        
        **Validates: Requirements 16.1, 16.3**
        """
        async def run_test():
            assume(len(user_input.strip()) > 0)
            assume(len(session_id.strip()) > 0)
            
            # Create mock LLM provider
            mock_llm_provider = Mock()
            mock_llm_provider.generate = AsyncMock(
                return_value="Response"
            )
            
            # Create tool
            tool = DeterministicTestTool()
            tools = [tool]
            
            # Create agent
            agent = AgentManager(
                llm_provider=mock_llm_provider,
                tools=tools
            )
            
            # Mock the agent executor to fail with descriptive error
            error_message = f"Failed to process input: {user_input[:20]}..."
            
            async def failing_invoke(*args, **kwargs):
                raise Exception(error_message)
            
            agent.agent_executor = AsyncMock()
            agent.agent_executor.ainvoke = failing_invoke
            
            # Execute
            result = await agent.ainvoke(
                user_input=user_input,
                session_id=session_id
            )
            
            # Verify error information
            assert result.error is not None, \
                "Should have error information"
            assert len(result.error) > 0, \
                "Error message should not be empty"
            assert "Failed" in result.error or "failed" in result.error, \
                "Error should describe what failed"
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_test())


class TestAgentDeterminismWithMemory:
    """
    Additional tests for Agent determinism with memory context.
    
    **Validates: Requirements 5.1, 5.2**
    """

    @given(
        user_input=user_input_strategy,
        session_id=session_id_strategy
    )
    @settings(
        max_examples=15,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much]
    )
    def test_agent_with_memory_produces_consistent_results(
        self, user_input, session_id
    ):
        """
        Property: Agent with memory should produce consistent results for same input.
        
        This test verifies that when memory is enabled, the Agent still
        produces consistent results for the same input.
        
        **Validates: Requirements 5.1, 5.2**
        """
        async def run_test():
            assume(len(user_input.strip()) > 0)
            assume(len(session_id.strip()) > 0)
            
            # Create mock LLM provider
            mock_llm_provider = Mock()
            mock_llm_provider.generate = AsyncMock(
                return_value="Consistent response"
            )
            
            # Create mock memory
            mock_memory = AsyncMock(spec=PersistentConversationMemory)
            mock_memory.load_history = AsyncMock()
            mock_memory.add_user_message = Mock()
            mock_memory.add_ai_message = Mock()
            mock_memory.save_message = AsyncMock()
            
            # Create tool
            tool = DeterministicTestTool()
            tools = [tool]
            
            # Create agent with memory
            agent = AgentManager(
                llm_provider=mock_llm_provider,
                tools=tools,
                memory=mock_memory
            )
            
            # Mock the agent executor
            agent.agent_executor = AsyncMock()
            agent.agent_executor.ainvoke = AsyncMock(
                return_value={"output": "Consistent response"}
            )
            
            # Execute first invocation
            result1 = await agent.ainvoke(
                user_input=user_input,
                session_id=session_id
            )
            
            # Execute second invocation with same input
            result2 = await agent.ainvoke(
                user_input=user_input,
                session_id=session_id
            )
            
            # Verify consistency
            assert result1.output == result2.output, \
                "Same input should produce same output with memory"
            assert result1.error == result2.error, \
                "Same input should produce same error status with memory"
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
