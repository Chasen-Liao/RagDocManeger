"""Tool-service interaction layer with response parsing, error handling, and retry logic."""

import asyncio
import time
from typing import Any, Callable, Optional, List, Dict, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum
from logger import logger

T = TypeVar('T')


class RetryStrategy(Enum):
    """Retry strategy options."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    backoff_factor: float = 2.0
    timeout: float = 30.0


@dataclass
class ServiceResponse:
    """Standardized service response."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    execution_time: float = 0.0


class ServiceError(Exception):
    """Base exception for service errors."""
    
    def __init__(self, message: str, error_code: str = "SERVICE_ERROR", retryable: bool = False):
        """Initialize service error.
        
        Args:
            message: Error message
            error_code: Error code for categorization
            retryable: Whether the error is retryable
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.retryable = retryable


class TimeoutError(ServiceError):
    """Timeout error."""
    
    def __init__(self, message: str = "Service call timed out"):
        super().__init__(message, "TIMEOUT_ERROR", retryable=True)


class RetryableError(ServiceError):
    """Retryable error."""
    
    def __init__(self, message: str, error_code: str = "RETRYABLE_ERROR"):
        super().__init__(message, error_code, retryable=True)


class NonRetryableError(ServiceError):
    """Non-retryable error."""
    
    def __init__(self, message: str, error_code: str = "NON_RETRYABLE_ERROR"):
        super().__init__(message, error_code, retryable=False)


class ResponseParser:
    """Parses and validates service responses."""
    
    @staticmethod
    def parse_response(response: Any, expected_type: Optional[type] = None) -> ServiceResponse:
        """Parse service response.
        
        Args:
            response: Raw response from service
            expected_type: Expected type of response data
            
        Returns:
            Parsed ServiceResponse
            
        Raises:
            NonRetryableError: If response parsing fails
        """
        try:
            if isinstance(response, ServiceResponse):
                return response
            
            if isinstance(response, dict):
                # Handle dict responses
                if "success" in response:
                    return ServiceResponse(
                        success=response.get("success", False),
                        data=response.get("data"),
                        error=response.get("error"),
                        error_code=response.get("error_code"),
                        metadata=response.get("metadata")
                    )
                else:
                    # Assume successful response
                    return ServiceResponse(success=True, data=response)
            
            if isinstance(response, list):
                return ServiceResponse(success=True, data=response)
            
            if response is None:
                return ServiceResponse(success=True, data=None)
            
            # For other types, wrap in response
            return ServiceResponse(success=True, data=response)
        
        except Exception as e:
            logger.error(f"Failed to parse response: {str(e)}")
            raise NonRetryableError(
                f"Failed to parse service response: {str(e)}",
                "PARSE_ERROR"
            )
    
    @staticmethod
    def validate_response(response: ServiceResponse, required_fields: Optional[List[str]] = None) -> bool:
        """Validate service response.
        
        Args:
            response: ServiceResponse to validate
            required_fields: List of required fields in response data
            
        Returns:
            True if response is valid
            
        Raises:
            NonRetryableError: If validation fails
        """
        if not response.success and response.error:
            raise NonRetryableError(
                f"Service returned error: {response.error}",
                response.error_code or "SERVICE_ERROR"
            )
        
        if required_fields and response.data:
            if isinstance(response.data, dict):
                missing_fields = [f for f in required_fields if f not in response.data]
                if missing_fields:
                    raise NonRetryableError(
                        f"Response missing required fields: {missing_fields}",
                        "MISSING_FIELDS"
                    )
        
        return True


class RetryHandler:
    """Handles retry logic for service calls."""
    
    @staticmethod
    def calculate_delay(retry_count: int, config: RetryConfig) -> float:
        """Calculate delay for next retry.
        
        Args:
            retry_count: Current retry count (0-based)
            config: Retry configuration
            
        Returns:
            Delay in seconds
        """
        if config.strategy == RetryStrategy.FIXED:
            delay = config.initial_delay
        elif config.strategy == RetryStrategy.LINEAR:
            delay = config.initial_delay * (retry_count + 1)
        else:  # EXPONENTIAL
            delay = config.initial_delay * (config.backoff_factor ** retry_count)
        
        # Cap at max_delay
        return min(delay, config.max_delay)
    
    @staticmethod
    async def execute_with_retry(
        func: Callable,
        config: RetryConfig,
        *args,
        **kwargs
    ) -> ServiceResponse:
        """Execute function with retry logic.
        
        Args:
            func: Async function to execute
            config: Retry configuration
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            ServiceResponse with result or error
        """
        last_error = None
        retry_count = 0
        
        for attempt in range(config.max_retries + 1):
            try:
                start_time = time.time()
                
                # Execute with timeout
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=config.timeout
                )
                
                execution_time = time.time() - start_time
                
                # Parse response
                response = ResponseParser.parse_response(result)
                response.retry_count = retry_count
                response.execution_time = execution_time
                
                if response.success:
                    logger.info(f"Service call succeeded after {retry_count} retries")
                    return response
                
                # Check if error is retryable
                if attempt < config.max_retries:
                    logger.warning(f"Service returned error, retrying: {response.error}")
                    last_error = response.error
                    retry_count += 1
                    
                    # Wait before retry
                    delay = RetryHandler.calculate_delay(retry_count - 1, config)
                    await asyncio.sleep(delay)
                    continue
                
                return response
            
            except asyncio.TimeoutError:
                logger.warning(f"Service call timed out (attempt {attempt + 1}/{config.max_retries + 1})")
                last_error = "Service call timed out"
                
                if attempt < config.max_retries:
                    retry_count += 1
                    delay = RetryHandler.calculate_delay(retry_count - 1, config)
                    await asyncio.sleep(delay)
                    continue
                
                return ServiceResponse(
                    success=False,
                    error=last_error,
                    error_code="TIMEOUT_ERROR",
                    retry_count=retry_count,
                    execution_time=config.timeout
                )
            
            except Exception as e:
                logger.error(f"Service call failed: {str(e)}")
                last_error = str(e)
                
                if attempt < config.max_retries:
                    retry_count += 1
                    delay = RetryHandler.calculate_delay(retry_count - 1, config)
                    await asyncio.sleep(delay)
                    continue
                
                return ServiceResponse(
                    success=False,
                    error=last_error,
                    error_code="EXECUTION_ERROR",
                    retry_count=retry_count
                )
        
        return ServiceResponse(
            success=False,
            error=last_error or "Unknown error",
            error_code="MAX_RETRIES_EXCEEDED",
            retry_count=retry_count
        )


class BatchOperationHandler:
    """Handles batch operations for services."""
    
    @staticmethod
    async def execute_batch(
        items: List[Any],
        func: Callable,
        batch_size: int = 10,
        config: Optional[RetryConfig] = None
    ) -> List[ServiceResponse]:
        """Execute batch operation.
        
        Args:
            items: List of items to process
            func: Async function to execute for each item
            batch_size: Size of each batch
            config: Optional retry configuration
            
        Returns:
            List of ServiceResponse for each item
        """
        if config is None:
            config = RetryConfig()
        
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1} ({len(batch)} items)")
            
            # Process batch concurrently
            batch_tasks = [
                RetryHandler.execute_with_retry(func, config, item)
                for item in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    results.append(ServiceResponse(
                        success=False,
                        error=str(result),
                        error_code="BATCH_ERROR"
                    ))
                else:
                    results.append(result)
        
        logger.info(f"Batch operation completed: {len(results)} items processed")
        return results


class ToolServiceAdapter:
    """Adapter for tool-service interaction."""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """Initialize adapter.
        
        Args:
            config: Optional retry configuration
        """
        self.config = config or RetryConfig()
        self.response_parser = ResponseParser()
        self.retry_handler = RetryHandler()
        self.batch_handler = BatchOperationHandler()
    
    async def call_service(
        self,
        service_func: Callable,
        *args,
        **kwargs
    ) -> ServiceResponse:
        """Call service with retry and error handling.
        
        Args:
            service_func: Service function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            ServiceResponse with result or error
        """
        return await self.retry_handler.execute_with_retry(
            service_func,
            self.config,
            *args,
            **kwargs
        )
    
    async def call_service_batch(
        self,
        items: List[Any],
        service_func: Callable,
        batch_size: int = 10
    ) -> List[ServiceResponse]:
        """Call service in batch mode.
        
        Args:
            items: List of items to process
            service_func: Service function to call for each item
            batch_size: Size of each batch
            
        Returns:
            List of ServiceResponse for each item
        """
        return await self.batch_handler.execute_batch(
            items,
            service_func,
            batch_size,
            self.config
        )
    
    def parse_response(self, response: Any) -> ServiceResponse:
        """Parse service response.
        
        Args:
            response: Raw response from service
            
        Returns:
            Parsed ServiceResponse
        """
        return self.response_parser.parse_response(response)
    
    def validate_response(
        self,
        response: ServiceResponse,
        required_fields: Optional[List[str]] = None
    ) -> bool:
        """Validate service response.
        
        Args:
            response: ServiceResponse to validate
            required_fields: List of required fields
            
        Returns:
            True if valid
        """
        return self.response_parser.validate_response(response, required_fields)
