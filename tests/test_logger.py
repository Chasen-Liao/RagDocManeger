"""Tests for logging configuration."""
import pytest
import logging
from pathlib import Path
from logger import setup_logging, mask_sensitive_info


def test_logger_setup():
    """Test that logger is properly configured."""
    logger = setup_logging()
    
    assert logger is not None
    assert logger.name == "ragdocman"
    assert len(logger.handlers) > 0


def test_logger_has_console_handler():
    """Test that logger has console handler."""
    logger = setup_logging()
    
    has_console_handler = any(
        isinstance(h, logging.StreamHandler) 
        for h in logger.handlers
    )
    assert has_console_handler


def test_logger_has_file_handler():
    """Test that logger has file handler."""
    logger = setup_logging()
    
    has_file_handler = any(
        isinstance(h, logging.handlers.RotatingFileHandler)
        for h in logger.handlers
    )
    assert has_file_handler


def test_logger_creates_log_directory():
    """Test that logger creates logs directory."""
    logger = setup_logging()
    
    log_dir = Path("logs")
    assert log_dir.exists()


def test_mask_sensitive_info():
    """Test that sensitive information is masked."""
    # Test API key masking
    message = "api_key='secret123'"
    masked = mask_sensitive_info(message)
    assert "secret123" not in masked
    assert "***" in masked
    
    # Test password masking
    message = "password=mypassword123"
    masked = mask_sensitive_info(message)
    assert "mypassword123" not in masked
    assert "***" in masked
    
    # Test token masking
    message = "token: abc123def456"
    masked = mask_sensitive_info(message)
    assert "abc123def456" not in masked
    assert "***" in masked


def test_mask_sensitive_info_preserves_non_sensitive():
    """Test that non-sensitive information is preserved."""
    message = "User logged in successfully"
    masked = mask_sensitive_info(message)
    assert masked == message
