"""
Base Tool Classes for RagDocMan Agent

This module provides the foundational classes for all RagDocMan tools:
- ToolInput: Base model for tool inputs
- ToolOutput: Standardized output format for all tools
- BaseRagDocManTool: Base class extending LangChain's BaseTool with error handling and logging

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
"""

import logging
import time
from typing import Any, Dict, Optional, Type
from abc import ABC

from pydantic import BaseModel, Field, ConfigDict
from langchain_core.tools import BaseTool

from core.tool_monitor import get_tool_monitor

# Configure logger
logger = logging.getLogger(__name__)


class ToolInput(BaseModel):
    """
    Base model for tool inputs.
    
    All tool-specific input models should inherit from this class.
    This provides a common interface for validation and serialization.
    
    **Validates: Requirements 10.1, 10.2**
    """
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid"  # Prevent extra fields
    )


class ToolOutput(BaseModel):
    """
    Standardized output format for all tools.
    
    This ensures consistent response structure across all tools,
    making it easier for the Agent to process results.
    
    **Validates: Requirements 10.3**
    
    Attributes:
        success: Whether the tool execution was successful
        message: Human-readable message describing the result
        data: Optional dictionary containing the actual result data
        error: Optional error message if execution failed
    """
    
    success: bool = Field(
        description="Whether the tool execution was successful"
    )
    message: str = Field(
        description="Human-readable message describing the result"
    )
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional dictionary containing the actual result data"
    )
    error: Optional[str] = Field(
        default=None,
        description="Optional error message if execution failed"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {"result": "example data"},
                "error": None
            }
        }
    )


class BaseRagDocManTool(BaseTool, ABC):
    """
    Base class for all RagDocMan tools.
    
    This class extends LangChain's BaseTool and provides:
    - Standardized error handling
    - Logging infrastructure
    - Consistent execution patterns
    - Performance monitoring
    
    **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5**
    
    All RagDocMan tools should inherit from this class and implement
    the _run and _arun methods.
    """
    
    # Tool metadata
    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    args_schema: Type[BaseModel] = Field(description="Tool input schema")
    
    # Configuration
    handle_tool_error: bool = Field(
        default=True,
        description="Whether to handle tool errors gracefully"
    )
    verbose: bool = Field(
        default=False,
        description="Whether to log verbose execution details"
    )
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def _run(self, *args: Any, **kwargs: Any) -> ToolOutput:
        """
        Synchronous execution method.
        
        This method wraps the actual tool logic with error handling and logging.
        Subclasses should implement the actual logic in this method or override it.
        
        **Validates: Requirements 10.4, 10.5, 24.1, 24.2**
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            ToolOutput: Standardized tool output
        """
        tool_name = self.name
        monitor = get_tool_monitor()
        
        # Prepare input parameters for logging
        input_params = {
            "args": str(args)[:200],  # Truncate for logging
            "kwargs": str(kwargs)[:200]
        }
        
        # Log execution start
        start_time = monitor.log_execution_start(
            tool_name=tool_name,
            input_params=input_params
        )
        
        try:
            logger.info(f"[{tool_name}] Starting synchronous execution")
            if self.verbose:
                logger.debug(f"[{tool_name}] Input args: {args}")
                logger.debug(f"[{tool_name}] Input kwargs: {kwargs}")
            
            # Execute the tool logic
            result = self._execute(*args, **kwargs)
            
            # Log execution end with output
            output_data = {
                "success": result.success,
                "message": result.message,
                "has_data": result.data is not None
            }
            monitor.log_execution_end(
                tool_name=tool_name,
                start_time=start_time,
                output_result=output_data
            )
            
            execution_time = time.time() - start_time
            logger.info(
                f"[{tool_name}] Completed successfully in {execution_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            
            # Log execution error
            monitor.log_execution_error(
                tool_name=tool_name,
                start_time=start_time,
                error=e
            )
            
            logger.error(
                f"[{tool_name}] Failed: {error_msg}",
                exc_info=True
            )
            
            if self.handle_tool_error:
                return ToolOutput(
                    success=False,
                    message=f"Tool '{tool_name}' execution failed",
                    error=error_msg
                )
            else:
                raise
    
    async def _arun(self, *args: Any, **kwargs: Any) -> ToolOutput:
        """
        Asynchronous execution method.
        
        This method wraps the actual tool logic with error handling and logging.
        Subclasses should implement the actual async logic in this method or override it.
        
        **Validates: Requirements 10.4, 10.5, 24.1, 24.2**
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            ToolOutput: Standardized tool output
        """
        tool_name = self.name
        monitor = get_tool_monitor()
        
        # Prepare input parameters for logging
        input_params = {
            "args": str(args)[:200],  # Truncate for logging
            "kwargs": str(kwargs)[:200]
        }
        
        # Log execution start
        start_time = monitor.log_execution_start(
            tool_name=tool_name,
            input_params=input_params
        )
        
        try:
            logger.info(f"[{tool_name}] Starting asynchronous execution")
            if self.verbose:
                logger.debug(f"[{tool_name}] Input args: {args}")
                logger.debug(f"[{tool_name}] Input kwargs: {kwargs}")
            
            # Execute the tool logic asynchronously
            result = await self._aexecute(*args, **kwargs)
            
            # Log execution end with output
            output_data = {
                "success": result.success,
                "message": result.message,
                "has_data": result.data is not None
            }
            monitor.log_execution_end(
                tool_name=tool_name,
                start_time=start_time,
                output_result=output_data
            )
            
            execution_time = time.time() - start_time
            logger.info(
                f"[{tool_name}] Completed successfully in {execution_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            
            # Log execution error
            monitor.log_execution_error(
                tool_name=tool_name,
                start_time=start_time,
                error=e
            )
            
            logger.error(
                f"[{tool_name}] Failed: {error_msg}",
                exc_info=True
            )
            
            if self.handle_tool_error:
                return ToolOutput(
                    success=False,
                    message=f"Tool '{tool_name}' execution failed",
                    error=error_msg
                )
            else:
                raise
    
    def _execute(self, *args: Any, **kwargs: Any) -> ToolOutput:
        """
        Synchronous execution logic.
        
        Subclasses should override this method to implement their specific logic.
        This method is called by _run after setting up logging and error handling.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            ToolOutput: Standardized tool output
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError(
            f"Tool '{self.name}' must implement _execute method"
        )
    
    async def _aexecute(self, *args: Any, **kwargs: Any) -> ToolOutput:
        """
        Asynchronous execution logic.
        
        Subclasses should override this method to implement their specific async logic.
        This method is called by _arun after setting up logging and error handling.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            ToolOutput: Standardized tool output
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError(
            f"Tool '{self.name}' must implement _aexecute method"
        )
    
    def _log_execution_start(self, operation: str) -> None:
        """
        Log the start of an operation.
        
        Args:
            operation: Description of the operation
        """
        logger.info(f"[{self.name}] {operation}")
    
    def _log_execution_end(self, operation: str, execution_time: float) -> None:
        """
        Log the end of an operation.
        
        Args:
            operation: Description of the operation
            execution_time: Time taken to execute in seconds
        """
        logger.info(
            f"[{self.name}] {operation} completed in {execution_time:.2f}s"
        )
    
    def _log_error(self, operation: str, error: Exception) -> None:
        """
        Log an error during execution.
        
        Args:
            operation: Description of the operation that failed
            error: The exception that occurred
        """
        logger.error(
            f"[{self.name}] {operation} failed: {str(error)}",
            exc_info=True
        )
    
    def _create_success_output(
        self,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> ToolOutput:
        """
        Create a successful tool output.
        
        Args:
            message: Success message
            data: Optional result data
            
        Returns:
            ToolOutput: Successful output
        """
        return ToolOutput(
            success=True,
            message=message,
            data=data,
            error=None
        )
    
    def _create_error_output(
        self,
        message: str,
        error: str
    ) -> ToolOutput:
        """
        Create an error tool output.
        
        Args:
            message: Error message
            error: Detailed error information
            
        Returns:
            ToolOutput: Error output
        """
        return ToolOutput(
            success=False,
            message=message,
            data=None,
            error=error
        )
