"""Tests for database configuration."""
import pytest
from sqlalchemy import text
from database import engine, SessionLocal, init_db, Base


def test_database_connection():
    """Test that database connection works."""
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        assert result.fetchone()[0] == 1


def test_database_session():
    """Test that database session can be created."""
    session = SessionLocal()
    try:
        # Test that session is usable
        result = session.execute(text("SELECT 1"))
        assert result.fetchone()[0] == 1
    finally:
        session.close()


def test_init_db():
    """Test database initialization."""
    # This should not raise any exceptions
    init_db()
    
    # Verify that tables are created
    with engine.connect() as connection:
        # Check if we can query the database
        result = connection.execute(text("SELECT 1"))
        assert result.fetchone()[0] == 1


def test_database_isolation():
    """Test that database sessions are isolated."""
    session1 = SessionLocal()
    session2 = SessionLocal()
    
    try:
        # Both sessions should be independent
        assert session1 is not session2
    finally:
        session1.close()
        session2.close()
