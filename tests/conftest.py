"""Pytest configuration and fixtures."""
import pytest
import os
from pathlib import Path


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment."""
    # Create .env file for testing if it doesn't exist
    env_file = Path(".env")
    if not env_file.exists():
        env_file.write_text(
            "DATABASE_URL=sqlite:///./test_ragdocman.db\n"
            "LOG_LEVEL=DEBUG\n"
            "DEBUG=True\n"
        )
    
    yield
    
    # Cleanup
    if env_file.exists():
        env_file.unlink()
    
    # Clean up test database
    test_db = Path("test_ragdocman.db")
    if test_db.exists():
        test_db.unlink()


@pytest.fixture
def temp_env_file(tmp_path):
    """Create a temporary .env file."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=sqlite:///./test.db\n"
        "LOG_LEVEL=INFO\n"
    )
    return env_file
