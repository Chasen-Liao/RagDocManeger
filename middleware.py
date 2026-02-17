"""Middleware for error handling and request/response processing."""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from exceptions import RagDocManException
from logger import logger, mask_sensitive_info
import traceback
import time


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for global error handling."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request and handle exceptions."""
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Log request
            process_time = time.time() - start_time
            logger.info(
                f"{request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Duration: {process_time:.3f}s"
            )
            
            return response
            
        except RagDocManException as e:
            # Handle custom application exceptions
            logger.warning(
                f"Application error: {e.error_code} - {e.message}"
            )
            
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "success": False,
                    "data": None,
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details
                    }
                }
            )
            
        except Exception as e:
            # Handle unexpected exceptions
            error_id = f"{int(time.time() * 1000)}"
            
            logger.error(
                f"Unexpected error (ID: {error_id}): {str(e)}\n"
                f"{traceback.format_exc()}"
            )
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred",
                        "details": {"error_id": error_id}
                    }
                }
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for detailed request logging."""
    
    async def dispatch(self, request: Request, call_next):
        """Log request details."""
        # Log request info (excluding sensitive data)
        logger.debug(
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        response = await call_next(request)
        return response
