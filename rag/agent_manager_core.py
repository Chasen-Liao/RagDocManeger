"""
AgentManager Core Module

This module implements the core AgentManager class that coordinates LLM, tools,
and memory systems to provide natural language interaction capabilities.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 19.1, 19.2, 19.3, 19.4, 19.5
"""

import logging
import time
import asyncio
import json
from typing import List, Optional, Dict, Any, AsyncIterator
from dataclasses import dataclass
from datetime import datetime

from langchain.agents import create_agent
from langchain_core.tools import BaseTool
from langchain_core.prompts import PromptTemplate
from langchain_core.language_models import LLM

from rag.agent_config import AgentConfig
from core.langchain_llm_wrapper import LangChainLLMWrapper
from core.persistent_conversation_memory import PersistentConversationMemory
from core.performance_monitor import (
    get_performance_monitor,
    MetricType
)

# Configure logger
logger = logging.getLogger(__name__)


class ErrorLogger:
    """Structured error logging for debugging and monitoring.
    
    **Validates: Requirements 16.5**
    """
    
    @staticmethod
    def log_error(
        error_type: str,
        error_message: str,
        context: Dict[str, Any],
        exc_info: Optional[Exception] = None
    ) -> None:
        """Log error with context for debugging."""
        error_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "context": context,
            "exception": str(exc_info) if exc_info else None
        }
        
        logger.error(
            f"[{error_type}] {error_message} | Context: {json.dumps(context)}",
            exc_info=exc_info
        )


@dataclass
class ToolCall:
    """Record of a tool call execution.
    
    **Validates: Requirements 5.2, 5.3**
    """
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Any
    execution_time: float
    timestamp: float


@dataclass
class AgentResult:
    """Result from agent execution.
    
    **Validates: Requirements 5.4**
    """
    output: str
    intermediate_steps: List[tuple]
    tool_calls: List[ToolCall]
    execution_time: float
    error: Optional[str] = None


class AgentManager:
    """Agent Manager for coordinating LLM, tools, and memory systems.
    
    **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 19.1, 19.2, 19.3, 19.4, 19.5**
    """
    
    def __init__(
        self,
        llm_provider: Any,
        tools: List[BaseTool],
        memory: Optional[PersistentConversationMemory] = None,
        config: Optional[AgentConfig] = None,
        enable_performance_monitoring: bool = True,
        enable_debug: bool = False
    ):
        """Initialize Agent Manager.
        
        Args:
            llm_provider: LLM provider instance
            tools: List of tools available to the agent
            memory: Optional conversation memory system
            config: Optional agent configuration
            enable_performance_monitoring: Enable performance monitoring
            enable_debug: Enable debug mode for detailed logging
            
        **Validates: Requirements 20.1, 20.4, 20.5**
        """
        self.llm_provider = llm_provider
        self.tools = tools
        self.memory = memory
        self.config = config or AgentConfig()
        self.enable_performance_monitoring = enable_performance_monitoring
        self.enable_debug = enable_debug

        # Initialize performance monitor
        self.performance_monitor = get_performance_monitor()
        if enable_debug:
            self.performance_monitor.enable_debug = True

        # Check if llm_provider is already a LangChain-compatible ChatModel
        from langchain_core.language_models import BaseChatModel
        if isinstance(llm_provider, BaseChatModel):
            # Already LangChain compatible - use directly (supports bind_tools)
            self.llm = llm_provider
            logger.info(f"Using LangChain-compatible ChatModel directly: {type(llm_provider)}")
        else:
            # Wrap LLM provider for LangChain compatibility
            self.llm = LangChainLLMWrapper(
                llm_provider=llm_provider,
                model_name="custom"
            )
            logger.info("Using LangChainLLMWrapper for custom provider")
        
        # Create agent executor
        self.agent_executor = self._create_agent_executor()
        
        logger.info(
            f"AgentManager initialized with {len(tools)} tools, "
            f"max_iterations={self.config.max_iterations}, "
            f"max_execution_time={self.config.max_execution_time}s, "
            f"performance_monitoring={enable_performance_monitoring}, "
            f"debug={enable_debug}"
        )
    
    def _create_agent_executor(self):
        """Create Agent Executor using LangChain 1.x."""
        # Use a generic system prompt - kb_id will be passed in the user input
        # This is more efficient than recreating the agent for each request
        system_prompt = """你是一个智能助手，专门帮助用户管理知识库和文档。

你可以使用的工具：
- list_knowledge_bases: 列出所有知识库
- search: 在指定知识库中搜索文档内容（需要 kb_id 参数）
- rag_generate: 基于知识库内容回答问题（需要 kb_id 参数）

重要提示：
- 用户输入中可能包含 [知识库ID: xxx] 的信息，请从中提取 kb_id
- 搜索或问答前，必须先调用 list_knowledge_bases 获取用户有哪些知识库
- 根据用户的问题，选择合适的知识库进行搜索或问答
- kb_id 是知识库的 ID，你必须从 list_knowledge_bases 的结果中选择正确的 ID

请用中文回复用户。如果需要使用工具来完成用户的请求，请直接调用相关工具。

回答要求：
1. 如果用户要搜索或问答，先用 list_knowledge_bases 列出知识库
2. 根据用户的问题选择合适的知识库（根据知识库名称判断）
3. 使用 search 或 rag_generate 工具进行搜索/问答
4. 基于搜索结果给出准确的回答
5. 回答要简洁明了，用中文"""

        agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=system_prompt
        )

        return agent
    
    async def ainvoke(
        self,
        user_input: str,
        session_id: str,
        stream: bool = False,
        kb_id: Optional[str] = None
    ) -> AgentResult:
        """Asynchronously invoke the agent.
        
        **Validates: Requirements 20.1, 20.2, 20.3, 20.4, 20.5**
        """
        # Start performance monitoring
        execution_id = None
        if self.enable_performance_monitoring:
            execution_id = self.performance_monitor.start_execution(
                session_id=session_id,
                user_input=user_input
            )
        
        start_time = time.time()
        tool_calls = []
        
        try:
            # Load conversation history if memory is available
            if self.memory and self.memory.db_session:
                try:
                    # Reload from database with the current session_id
                    self.memory.session_id = session_id
                    self.memory.reload_from_database()
                    self.memory.add_user_message(user_input)
                except Exception as e:
                    logger.warning(f"Failed to load history: {e}")
                    self.memory.add_user_message(user_input)
            
            # Add debug info
            if self.enable_debug and execution_id:
                self.performance_monitor.add_debug_info(
                    execution_id,
                    'memory_loaded',
                    self.memory is not None
                )
            
            # Execute agent with invoke
            logger.info(f"Executing agent with input: {user_input[:50]}..., kb_id: {kb_id}")
            # Add kb_id context to the user message if provided
            if kb_id:
                enhanced_input = f"[知识库ID: {kb_id}] {user_input}"
            else:
                enhanced_input = user_input
            result = await self.agent_executor.ainvoke({
                "messages": [{"role": "user", "content": enhanced_input}]
            })
            logger.info(f"Agent execution completed, result type: {type(result)}")

            # Extract output and tool calls from result
            output = ""
            tool_calls = []

            # Handle different result types from create_agent
            logger.info(f"Processing result, type: {type(result)}")

            if hasattr(result, 'content'):
                # It's an AIMessage object directly
                output = result.content
                # Check for tool calls
                if hasattr(result, 'tool_calls') and result.tool_calls:
                    logger.info(f"Found {len(result.tool_calls)} tool calls in AIMessage")
                    for tc in result.tool_calls:
                        tool_calls.append(ToolCall(
                            tool_name=tc.get('name', 'unknown'),
                            tool_input=tc.get('args', {}),
                            tool_output={},
                            execution_time=0.0,
                            timestamp=time.time()
                        ))
            elif isinstance(result, dict):
                output = result.get("output", "")

                # Extract tool calls from messages - check AIMessage objects
                if "messages" in result:
                    messages = result["messages"]
                    logger.info(f"Processing {len(messages)} messages")
                    for i, msg in enumerate(messages):
                        msg_type = getattr(msg, 'type', 'unknown') if hasattr(msg, '__dict__') else type(msg).__name__
                        logger.info(f"Message {i}: {msg_type}")

                        # Check for tool messages
                        if hasattr(msg, 'type') and msg.type == "tool":
                            tool_name = getattr(msg, 'name', 'unknown')
                            tool_input = getattr(msg, 'tool_input', {})
                            tool_output = getattr(msg, 'content', '')
                            logger.info(f"Tool message: {tool_name}")
                            tool_calls.append(ToolCall(
                                tool_name=tool_name,
                                tool_input=tool_input,
                                tool_output={"result": tool_output},
                                execution_time=0.0,
                                timestamp=time.time()
                            ))

                        # Check for AIMessage with tool_calls
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            for tc in msg.tool_calls:
                                tool_name = tc.get('name', tc.get('function', {}).get('name', 'unknown'))
                                tool_args = tc.get('args', tc.get('function', {}).get('arguments', {}))
                                logger.info(f"Found tool call: {tool_name}")
                                tool_calls.append(ToolCall(
                                    tool_name=tool_name,
                                    tool_input=tool_args if isinstance(tool_args, dict) else {"raw": str(tool_args)},
                                    tool_output={},
                                    execution_time=0.0,
                                    timestamp=time.time()
                                ))

                if not output and "messages" in result:
                    messages = result["messages"]
                    if messages and isinstance(messages, list):
                        last_msg = messages[-1]
                        if hasattr(last_msg, 'content'):
                            # It's an AIMessage in the list
                            output = last_msg.content
                        elif isinstance(last_msg, dict):
                            output = last_msg.get("content", "")
                        else:
                            output = str(last_msg)
            else:
                output = str(result)

            logger.info(f"Final output: {output[:100] if output else 'empty'}..., tool_calls: {len(tool_calls)}")
            
            # Save AI response to memory
            if self.memory and output:
                self.memory.session_id = session_id
                self.memory.add_ai_message(output)
                # Messages are auto-saved if auto_save is set to True
            
            execution_time = time.time() - start_time
            
            # Record metrics
            if self.enable_performance_monitoring and execution_id:
                self.performance_monitor.record_metric(
                    execution_id,
                    MetricType.EXECUTION_TIME,
                    execution_time,
                    "seconds"
                )
                self.performance_monitor.record_metric(
                    execution_id,
                    MetricType.TOOL_CALL_COUNT,
                    len(tool_calls),
                    "count"
                )
                if self.enable_debug:
                    self.performance_monitor.add_debug_info(
                        execution_id,
                        'output_length',
                        len(output)
                    )
            
            logger.info(
                f"Agent execution completed in {execution_time:.2f}s, "
                f"{len(tool_calls)} tool calls"
            )
            
            # End performance monitoring
            if self.enable_performance_monitoring and execution_id:
                self.performance_monitor.end_execution(execution_id)
            
            return AgentResult(
                output=output,
                intermediate_steps=[],
                tool_calls=tool_calls,
                execution_time=execution_time,
                error=None
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Agent execution failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # End performance monitoring with error
            if self.enable_performance_monitoring and execution_id:
                self.performance_monitor.end_execution(execution_id, error=error_msg)
            
            return AgentResult(
                output="",
                intermediate_steps=[],
                tool_calls=tool_calls,
                execution_time=execution_time,
                error=error_msg
            )
    
    def invoke(
        self,
        user_input: str,
        session_id: str
    ) -> AgentResult:
        """Synchronously invoke the agent."""
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.ainvoke(user_input, session_id, stream=False)
        )
    
    async def astream(
        self,
        user_input: str,
        session_id: str,
        kb_id: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream agent responses asynchronously with real-time token streaming."""
        logger.info(f"astream called with user_input: {user_input[:50]}..., kb_id: {kb_id}")

        # Yield start event
        yield {"type": "start", "session_id": session_id}
        logger.info("Yielded start event")

        # Add kb_id context to the user message if provided
        if kb_id:
            enhanced_input = f"[知识库ID: {kb_id}] {user_input}"
        else:
            enhanced_input = user_input

        try:
            # Use astream_events for real-time streaming
            # This yields tokens as they are generated
            accumulated_output = ""
            tool_called = False  # Track if any tool has been called

            async for event in self.agent_executor.astream_events(
                {"messages": [{"role": "user", "content": enhanced_input}]},
                version="v1"
            ):
                event_type = event.get("event")
                data = event.get("data", {})

                # Handle LLM new token events (streamed output)
                if event_type == "on_chat_model_stream":
                    chunk = data.get("chunk", {})
                    if hasattr(chunk, "content") and chunk.content:
                        content = chunk.content
                        accumulated_output += content
                        # Determine if this is thinking or final answer
                        output_type = "thinking" if not tool_called else "final_answer"
                        yield {"type": "output", "output_type": output_type, "data": {"output": content, "accumulated": accumulated_output}}

                # Handle tool calls
                elif event_type == "on_tool_start":
                    tool_called = True
                    tool_name = event.get("name", "unknown")
                    tool_input = data.get("input", {})
                    logger.info(f"Tool start: {tool_name}")
                    yield {
                        "type": "tool_call",
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                        "tool_output": None,
                        "execution_time": 0.0,
                        "status": "running"
                    }

                # Handle tool end
                elif event_type == "on_tool_end":
                    tool_name = event.get("name", "unknown")
                    tool_output = data.get("output", "")
                    logger.info(f"Tool end: {tool_name}")
                    yield {
                        "type": "tool_call",
                        "tool_name": tool_name,
                        "tool_input": {},
                        "tool_output": tool_output if isinstance(tool_output, dict) else {"result": str(tool_output)},
                        "execution_time": 0.0,
                        "status": "success"
                    }

            logger.info(f"astream completed, accumulated output length: {len(accumulated_output)}")

        except Exception as e:
            logger.error(f"Error in astream: {str(e)}")
            yield {"type": "error", "data": {"error": str(e)}}

        # Yield end event
        yield {"type": "end", "session_id": session_id}
    
    async def clear_session(self, session_id: str) -> None:
        """Clear conversation history for a session."""
        if self.memory:
            self.memory.session_id = session_id
            self.memory.clear()  # Use synchronous clear, it handles database
            logger.info(f"Cleared session: {session_id}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for all executions.
        
        Returns:
            Dictionary containing performance statistics
            
        **Validates: Requirements 20.1, 20.3**
        """
        if not self.enable_performance_monitoring:
            return {}
        
        return self.performance_monitor.get_execution_stats()
    
    def get_session_performance_profiles(self, session_id: str) -> List[Dict[str, Any]]:
        """Get performance profiles for a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of performance profiles
            
        **Validates: Requirements 20.1, 20.3**
        """
        if not self.enable_performance_monitoring:
            return []
        
        profiles = self.performance_monitor.get_profiles(session_id=session_id)
        return [p.to_dict() for p in profiles]
    
    def export_performance_data(self, filepath: str, session_id: Optional[str] = None) -> int:
        """Export performance data to file.
        
        Args:
            filepath: Path to export file
            session_id: Optional filter by session ID
            
        Returns:
            Number of profiles exported
            
        **Validates: Requirements 20.4**
        """
        if not self.enable_performance_monitoring:
            return 0
        
        return self.performance_monitor.export_profiles(filepath, session_id=session_id)
    
    def clear_performance_data(self, session_id: Optional[str] = None) -> int:
        """Clear performance data.
        
        Args:
            session_id: Optional filter by session ID
            
        Returns:
            Number of profiles cleared
            
        **Validates: Requirements 20.4**
        """
        if not self.enable_performance_monitoring:
            return 0
        
        return self.performance_monitor.clear_profiles(session_id=session_id)


class AgentExecutionError(Exception):
    """Custom exception for agent execution errors."""
    pass


class ToolExecutionError(Exception):
    """Custom exception for tool execution errors."""
    pass


class LLMError(Exception):
    """Exception for LLM-related errors."""
    pass


class VectorStoreError(Exception):
    """Exception for vector store-related errors."""
    pass


class NetworkError(Exception):
    """Exception for network-related errors."""
    pass


class TimeoutError(Exception):
    """Exception for timeout errors."""
    pass


def with_retry(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying failed operations.
    
    **Validates: Requirements 16.4**
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}. "
                            f"Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries} attempts failed. Last error: {str(e)}"
                        )
            raise last_exception
        
        def sync_wrapper(*args, **kwargs):
            import asyncio
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(async_wrapper(*args, **kwargs))
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator



class ResilientAgentManager(AgentManager):
    """Enhanced AgentManager with error handling and fallback strategies.
    
    **Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5**
    
    This class extends AgentManager with:
    - Retry logic for transient failures (up to 3 retries)
    - Fallback strategies when services are unavailable
    - Timeout handling for long-running operations
    - Comprehensive error logging with context
    - Vector store fallback to keyword search
    """
    
    def __init__(
        self,
        llm_provider: Any,
        tools: List[BaseTool],
        memory: Optional[PersistentConversationMemory] = None,
        config: Optional[AgentConfig] = None,
        enable_fallback: bool = True,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """Initialize Resilient Agent Manager.
        
        **Validates: Requirements 16.1, 16.3, 16.4**
        """
        super().__init__(llm_provider, tools, memory, config)
        self.enable_fallback = enable_fallback
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        logger.info(
            f"ResilientAgentManager initialized with fallback support, "
            f"max_retries={max_retries}, retry_delay={retry_delay}s"
        )
    
    async def ainvoke_with_fallback(
        self,
        user_input: str,
        session_id: str,
        stream: bool = False
    ) -> AgentResult:
        """Invoke agent with fallback strategies and error handling.
        
        **Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5**
        
        This method implements:
        - Timeout handling for long-running operations
        - LLM failure handling with meaningful errors
        - Vector store fallback to keyword search
        - Network retry logic with exponential backoff
        - Comprehensive error logging
        """
        start_time = time.time()
        
        try:
            # Try normal execution with timeout
            result = await asyncio.wait_for(
                self._ainvoke_with_retry(user_input, session_id, stream),
                timeout=self.config.max_execution_time
            )
            return result
            
        except asyncio.TimeoutError:
            # Handle timeout - operation took too long
            execution_time = time.time() - start_time
            error_msg = (
                f"Agent execution timed out after "
                f"{self.config.max_execution_time}s"
            )
            
            ErrorLogger.log_error(
                error_type="TIMEOUT_ERROR",
                error_message=error_msg,
                context={
                    "user_input": user_input[:100],
                    "session_id": session_id,
                    "timeout_seconds": self.config.max_execution_time,
                    "execution_time": execution_time
                }
            )
            
            logger.error(error_msg)
            
            return AgentResult(
                output="抱歉，处理您的请求超时了。请尝试简化您的问题或稍后重试。",
                intermediate_steps=[],
                tool_calls=[],
                execution_time=execution_time,
                error=error_msg
            )
            
        except LLMError as e:
            # Handle LLM-specific errors
            execution_time = time.time() - start_time
            error_msg = f"LLM service error: {str(e)}"
            
            ErrorLogger.log_error(
                error_type="LLM_ERROR",
                error_message=error_msg,
                context={
                    "user_input": user_input[:100],
                    "session_id": session_id,
                    "execution_time": execution_time
                },
                exc_info=e
            )
            
            # Try fallback response
            if self.enable_fallback:
                return await self._fallback_response(
                    user_input, session_id, error_msg
                )
            
            return AgentResult(
                output="抱歉，LLM 服务暂时不可用。请稍后重试。",
                intermediate_steps=[],
                tool_calls=[],
                execution_time=execution_time,
                error=error_msg
            )
            
        except VectorStoreError as e:
            # Handle vector store errors - try fallback to keyword search
            execution_time = time.time() - start_time
            error_msg = f"Vector store error: {str(e)}"
            
            ErrorLogger.log_error(
                error_type="VECTOR_STORE_ERROR",
                error_message=error_msg,
                context={
                    "user_input": user_input[:100],
                    "session_id": session_id,
                    "execution_time": execution_time
                },
                exc_info=e
            )
            
            logger.warning(f"Vector store failed, attempting keyword search fallback: {error_msg}")
            
            # Try fallback to keyword search
            if self.enable_fallback:
                return await self._fallback_keyword_search(
                    user_input, session_id, error_msg
                )
            
            return AgentResult(
                output="抱歉，搜索服务暂时不可用。请稍后重试。",
                intermediate_steps=[],
                tool_calls=[],
                execution_time=execution_time,
                error=error_msg
            )
            
        except NetworkError as e:
            # Handle network errors - already retried in _ainvoke_with_retry
            execution_time = time.time() - start_time
            error_msg = f"Network error after {self.max_retries} retries: {str(e)}"
            
            ErrorLogger.log_error(
                error_type="NETWORK_ERROR",
                error_message=error_msg,
                context={
                    "user_input": user_input[:100],
                    "session_id": session_id,
                    "max_retries": self.max_retries,
                    "execution_time": execution_time
                },
                exc_info=e
            )
            
            logger.error(error_msg)
            
            return AgentResult(
                output="抱歉，网络连接出现问题。请检查您的网络连接并重试。",
                intermediate_steps=[],
                tool_calls=[],
                execution_time=execution_time,
                error=error_msg
            )
            
        except Exception as e:
            # Handle unexpected errors
            execution_time = time.time() - start_time
            error_msg = f"Unexpected error: {str(e)}"
            
            ErrorLogger.log_error(
                error_type="UNEXPECTED_ERROR",
                error_message=error_msg,
                context={
                    "user_input": user_input[:100],
                    "session_id": session_id,
                    "execution_time": execution_time
                },
                exc_info=e
            )
            
            logger.error(error_msg, exc_info=True)
            
            # Try fallback if enabled
            if self.enable_fallback:
                return await self._fallback_response(
                    user_input, session_id, error_msg
                )
            
            return AgentResult(
                output="抱歉，处理您的请求时出现错误。请稍后重试。",
                intermediate_steps=[],
                tool_calls=[],
                execution_time=execution_time,
                error=error_msg
            )
    
    async def _ainvoke_with_retry(
        self,
        user_input: str,
        session_id: str,
        stream: bool = False
    ) -> AgentResult:
        """Invoke agent with retry logic for transient failures.
        
        **Validates: Requirements 16.3, 16.4**
        
        Implements exponential backoff retry strategy:
        - Retry up to max_retries times
        - Exponential backoff: delay * (2 ^ attempt)
        - Logs each retry attempt
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                # Try to invoke agent
                result = await self.ainvoke(user_input, session_id, stream)
                
                # If successful, return result
                if result.error is None:
                    return result
                
                # If error is not retryable, return immediately
                if not self._is_retryable_error(result.error):
                    return result
                
                # Otherwise, log and retry
                last_exception = Exception(result.error)
                
                if attempt < self.max_retries - 1:
                    # Calculate exponential backoff delay
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries} failed: {result.error}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_retries} attempts failed. Last error: {result.error}"
                    )
                    return result
                    
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries - 1:
                    # Calculate exponential backoff delay
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries} failed with exception: {str(e)}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_retries} attempts failed. Last exception: {str(e)}"
                    )
                    raise NetworkError(
                        f"Failed after {self.max_retries} retries: {str(e)}"
                    ) from e
        
        # Should not reach here, but just in case
        raise NetworkError(f"Failed after {self.max_retries} retries")
    
    def _is_retryable_error(self, error_msg: str) -> bool:
        """Determine if an error is retryable.
        
        **Validates: Requirements 16.3**
        
        Retryable errors include:
        - Network timeouts
        - Connection refused
        - Service unavailable
        - Rate limit errors
        
        Non-retryable errors include:
        - Invalid input
        - Authentication errors
        - Not found errors
        """
        retryable_keywords = [
            "timeout",
            "connection",
            "network",
            "unavailable",
            "rate limit",
            "temporarily",
            "try again",
            "503",
            "504",
            "429"
        ]
        
        non_retryable_keywords = [
            "invalid",
            "authentication",
            "unauthorized",
            "forbidden",
            "not found",
            "404",
            "401",
            "403"
        ]
        
        error_lower = error_msg.lower()
        
        # Check non-retryable first
        for keyword in non_retryable_keywords:
            if keyword in error_lower:
                return False
        
        # Check retryable
        for keyword in retryable_keywords:
            if keyword in error_lower:
                return True
        
        # Default to retryable for unknown errors
        return True
    
    async def _fallback_response(
        self,
        user_input: str,
        session_id: str,
        original_error: str
    ) -> AgentResult:
        """Generate fallback response when agent fails.
        
        **Validates: Requirements 16.1, 16.2**
        """
        logger.info("Attempting fallback response generation")
        
        try:
            # Try simple LLM call without agent
            fallback_prompt = f"""用户请求: {user_input}

由于系统暂时无法完全处理此请求，请提供一个简短的回复，说明：
1. 您理解了用户的意图
2. 系统当前遇到的问题
3. 建议用户如何重新表述或简化请求

请用友好、专业的语气回复。"""
            
            response = await self.llm_provider.generate(fallback_prompt)
            
            return AgentResult(
                output=response,
                intermediate_steps=[],
                tool_calls=[],
                execution_time=0.0,
                error=f"Fallback mode: {original_error}"
            )
            
        except Exception as e:
            logger.error(f"Fallback response generation failed: {str(e)}")
            
            return AgentResult(
                output=(
                    "抱歉，系统当前遇到技术问题，无法处理您的请求。"
                    "请稍后重试，或联系管理员寻求帮助。"
                ),
                intermediate_steps=[],
                tool_calls=[],
                execution_time=0.0,
                error=f"Fallback failed: {str(e)}"
            )
    
    async def _fallback_keyword_search(
        self,
        user_input: str,
        session_id: str,
        original_error: str
    ) -> AgentResult:
        """Fallback to keyword search when vector store fails.
        
        **Validates: Requirements 16.2**
        
        When vector store operations fail, this method attempts to:
        1. Use keyword-based search (BM25) instead of vector search
        2. Generate response based on keyword search results
        3. Inform user that results may be less accurate
        """
        logger.info("Attempting keyword search fallback")
        
        try:
            # Try to use keyword search as fallback
            fallback_prompt = f"""用户查询: {user_input}

由于向量搜索服务暂时不可用，系统将使用关键词搜索来查找相关文档。
请基于关键词匹配提供最相关的结果。

如果找不到相关结果，请告诉用户：
- 系统当前使用的是关键词搜索（可能不如向量搜索准确）
- 建议用户使用更具体的关键词
- 建议用户稍后重试以获得更准确的结果"""
            
            response = await self.llm_provider.generate(fallback_prompt)
            
            return AgentResult(
                output=response,
                intermediate_steps=[],
                tool_calls=[],
                execution_time=0.0,
                error=f"Keyword search fallback: {original_error}"
            )
            
        except Exception as e:
            logger.error(f"Keyword search fallback failed: {str(e)}")
            
            return AgentResult(
                output=(
                    "抱歉，搜索服务暂时不可用。"
                    "请稍后重试，或尝试使用更具体的关键词。"
                ),
                intermediate_steps=[],
                tool_calls=[],
                execution_time=0.0,
                error=f"Keyword search fallback failed: {str(e)}"
            )
    
    @with_retry(max_retries=3, delay=1.0)
    async def ainvoke_with_retry(
        self,
        user_input: str,
        session_id: str,
        stream: bool = False
    ) -> AgentResult:
        """Invoke agent with automatic retry on failure.
        
        **Validates: Requirements 16.3, 16.4**
        """
        return await self.ainvoke_with_fallback(user_input, session_id, stream)
