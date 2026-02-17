"""Custom exception classes for the application."""
from typing import Optional, Dict, Any


class RagDocManException(Exception):
    """Base exception for RagDocMan application."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(RagDocManException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="INVALID_REQUEST",
            status_code=400,
            details=details
        )


class NotFoundError(RagDocManException):
    """Raised when a resource is not found."""
    
    def __init__(self, message: str, resource_type: str = "Resource"):
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=404,
            details={"resource_type": resource_type}
        )


# Alias for convenience
ResourceNotFoundError = NotFoundError


class ConflictError(RagDocManException):
    """Raised when there's a conflict (e.g., duplicate resource)."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFLICT",
            status_code=409,
            details=details
        )


class DatabaseError(RagDocManException):
    """Raised when database operation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=500,
            details=details
        )


class ExternalServiceError(RagDocManException):
    """Raised when external service call fails."""
    
    def __init__(self, message: str, service_name: str = "Unknown"):
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=503,
            details={"service": service_name}
        )


class ConfigurationError(RagDocManException):
    """Raised when configuration is invalid."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=500,
            details=details
        )
