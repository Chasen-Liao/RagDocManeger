"""Tests for configuration management."""
import pytest
import os
from pathlib import Path
from config import Settings


def test_settings_load_from_env(tmp_path):
    """Test that settings load from environment variables."""
    # Create a temporary .env file
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=sqlite:///./test.db\n"
        "LOG_LEVEL=DEBUG\n"
        "APP_NAME=TestApp\n"
    )
    
    # Change to temp directory
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        
        # Create new settings instance
        settings = Settings(_env_file=str(env_file))
        
        assert settings.database_url == "sqlite:///./test.db"
        assert settings.log_level == "DEBUG"
        assert settings.app_name == "TestApp"
    finally:
        os.chdir(original_cwd)


def test_settings_default_values():
    """Test that settings have proper default values."""
    # Create settings without loading from .env
    settings = Settings(_env_file=None)
    
    assert settings.log_level == "INFO"
    assert settings.app_name == "RagDocMan"
    assert settings.debug is False
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000


def test_settings_validate_config():
    """Test configuration validation."""
    settings = Settings()
    
    # Should not raise for valid config
    settings.validate_config()
    
    # Test with empty database_url
    settings.database_url = ""
    with pytest.raises(ValueError, match="DATABASE_URL is required"):
        settings.validate_config()
    
    # Test with empty vector_store_path
    settings.database_url = "sqlite:///./test.db"
    settings.vector_store_path = ""
    with pytest.raises(ValueError, match="VECTOR_STORE_PATH is required"):
        settings.validate_config()


def test_settings_case_insensitive():
    """Test that settings are case insensitive."""
    settings = Settings(
        database_url="sqlite:///./test.db",
        log_level="debug"
    )
    
    assert settings.log_level == "debug"
