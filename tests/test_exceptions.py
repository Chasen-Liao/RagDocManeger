"""Tests for custom exceptions."""
import pytest
from exceptions import (
    RagDocManException,
    ValidationError,
    NotFoundError,
    ConflictError,
    DatabaseError,
    ExternalServiceError,
    ConfigurationError
)


def test_ragdocman_exception():
    """Test base RagDocManException."""
    exc = RagDocManException(
        message="Test error",
        error_code="TEST_ERROR",
        status_code=400
    )
    
    assert exc.message == "Test error"
    assert exc.error_code == "TEST_ERROR"
    assert exc.status_code == 400
    assert str(exc) == "Test error"


def test_validation_error():
    """Test ValidationError."""
    exc = ValidationError(
        message="Invalid input",
        details={"field": "email"}
    )
    
    assert exc.message == "Invalid input"
    assert exc.error_code == "INVALID_REQUEST"
    assert exc.status_code == 400
    assert exc.details == {"field": "email"}


def test_not_found_error():
    """Test NotFoundError."""
    exc = NotFoundError(
        message="Knowledge base not found",
        resource_type="KnowledgeBase"
    )
    
    assert exc.message == "Knowledge base not found"
    assert exc.error_code == "NOT_FOUND"
    assert exc.status_code == 404
    assert exc.details["resource_type"] == "KnowledgeBase"


def test_conflict_error():
    """Test ConflictError."""
    exc = ConflictError(
        message="Knowledge base already exists",
        details={"name": "test_kb"}
    )
    
    assert exc.message == "Knowledge base already exists"
    assert exc.error_code == "CONFLICT"
    assert exc.status_code == 409
    assert exc.details == {"name": "test_kb"}


def test_database_error():
    """Test DatabaseError."""
    exc = DatabaseError(
        message="Database connection failed",
        details={"reason": "timeout"}
    )
    
    assert exc.message == "Database connection failed"
    assert exc.error_code == "DATABASE_ERROR"
    assert exc.status_code == 500


def test_external_service_error():
    """Test ExternalServiceError."""
    exc = ExternalServiceError(
        message="LLM API call failed",
        service_name="SiliconFlow"
    )
    
    assert exc.message == "LLM API call failed"
    assert exc.error_code == "EXTERNAL_SERVICE_ERROR"
    assert exc.status_code == 503
    assert exc.details["service"] == "SiliconFlow"


def test_configuration_error():
    """Test ConfigurationError."""
    exc = ConfigurationError(
        message="Missing required configuration",
        details={"missing": "LLM_API_KEY"}
    )
    
    assert exc.message == "Missing required configuration"
    assert exc.error_code == "CONFIGURATION_ERROR"
    assert exc.status_code == 500
