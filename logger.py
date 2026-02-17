"""Logging configuration."""
import logging
import logging.handlers
import sys
from pathlib import Path
from config import settings


def setup_logging() -> logging.Logger:
    """Configure logging system with file and console handlers."""
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("ragdocman")
    logger.setLevel(getattr(logging, settings.log_level))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level))
    console_handler.setFormatter(detailed_formatter)
    logger.addHandler(console_handler)
    
    # File handler (rotating)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "ragdocman.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(getattr(logging, settings.log_level))
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    return logger


logger = setup_logging()


def mask_sensitive_info(message: str) -> str:
    """Mask sensitive information in log messages."""
    sensitive_keys = ["api_key", "password", "token", "secret"]
    
    for key in sensitive_keys:
        # Simple masking: replace values after = with ***
        import re
        pattern = rf"({key}['\"]?\s*[:=]\s*['\"]?)([^'\"\s]+)"
        message = re.sub(pattern, r"\1***", message, flags=re.IGNORECASE)
    
    return message
