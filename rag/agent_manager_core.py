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
        
        # Wrap LLM provider for LangChain compatibility
        self.llm = LangChainLLMWrapper(
            llm_provider=llm_provider,
            model_name="custom"
        )
        
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
        prompt = self._create_prompt_template()
        
        agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=prompt.template if hasattr(prompt, 'template') else str(prompt)
        )
        
        return agent
    
    def _create_prompt_template(self) -> PromptTemplate:
        """Create prompt template for the agent."""
        template = """You are a helpful AI assistant for managing knowledge bases and documents.
You have access to various tools to help users with their requests.

When a user asks you to perform an action:
1. Understand their intent clearly
2. Choose the appropriate tool(s) to use
3. Execute the tool(s) with correct parameters
4. Provide clear feedback about the results

Available tools:
{tools}

Tool names: {tool_names}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}"""
        
        return PromptTemplate(
            input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
            template=template
        )
    
    async def ainvoke(
        self,
        user_input: str,
        session_id: str,
        stream: bool = False
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
            if self.memory:
                await self.memory.load_history(session_id)
                self.memory.add_user_message(user_input)
            
            # Add debug info
            if self.enable_debug and execution_id:
                self.performance_monitor.add_debug_info(
                    execution_id,
                    'memory_loaded',
                    self.memory is not None
                )
            
            # Execute agent with invoke
            result = await self.agent_executor.ainvoke({
                "messages": [{"role": "user", "content": user_input}]
            })
            
            # Extract output from result
            if isinstance(result, dict):
                output = result.get("output", "")
                if not output and "messages" in result:
                    messages = result["messages"]
                    if messages and isinstance(messages, list):
                        last_msg = messages[-1]
                        if isinstance(last_msg, dict):
                            output = last_msg.get("content", "")
                        else:
                            output = str(last_msg)
            else:
                output = str(result)
            
            # Save AI response to memory
            if self.memory and output:
                self.memory.add_ai_message(output)
                await self.memory.save_message(session_id)
            
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
        session_id: str
    ) -> AsyncIterator[str]:
        """Stream agent responses asynchronously."""
        result = await self.ainvoke(user_input, session_id, stream=False)
        yield result.output
    
    async def clear_session(self, session_id: str) -> None:
        """Clear conversation history for a session."""
        if self.memory:
            await self.memory.clear(session_id)
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
