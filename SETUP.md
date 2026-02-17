# RagDocMan - Project Setup Guide

## Overview

RagDocMan is a FastAPI-based RAG (Retrieval-Augmented Generation) system with comprehensive infrastructure setup including database configuration, logging, error handling, and environment management.

## Project Structure

```
RagDocMan/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration management
├── database.py            # Database setup and connection
├── logger.py              # Logging configuration
├── exceptions.py          # Custom exception classes
├── middleware.py          # Error handling and request logging middleware
├── requirements.txt       # Python dependencies
├── .env.example           # Example environment variables
├── pytest.ini             # Pytest configuration
├── .gitignore             # Git ignore rules
│
├── api/                   # API routes (to be implemented)
│   └── __init__.py
├── services/              # Business logic services (to be implemented)
│   └── __init__.py
├── rag/                   # RAG core modules (to be implemented)
│   └── __init__.py
├── models/                # Data models (to be implemented)
│   └── __init__.py
├── core/                  # External service integrations (to be implemented)
│   └── __init__.py
├── tests/                 # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_logger.py
│   ├── test_exceptions.py
│   └── test_main.py
│
└── logs/                  # Application logs (created at runtime)
```

## Installation

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
DATABASE_URL=sqlite:///./ragdocman.db
LLM_PROVIDER=siliconflow
LLM_API_KEY=your_api_key_here
LLM_MODEL=your_model_name
# ... other configurations
```

## Running the Application

### Development Server

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Health Check

```bash
curl http://localhost:8000/health
```

### API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Running Tests

### All Tests

```bash
pytest tests/ -v
```

### Specific Test File

```bash
pytest tests/test_config.py -v
```

### With Coverage

```bash
pytest tests/ --cov=. --cov-report=html
```

## Configuration Management

### Environment Variables

All configuration is managed through environment variables loaded from `.env` file:

- **DATABASE_URL**: SQLite database connection string
- **LLM_PROVIDER**: LLM service provider (e.g., siliconflow)
- **LLM_API_KEY**: API key for LLM service
- **LOG_LEVEL**: Logging level (DEBUG, INFO, WARNING, ERROR)
- **DEBUG**: Debug mode (True/False)

### Configuration Validation

The application validates critical configuration on startup:

```python
settings.validate_config()
```

## Logging System

### Features

- Console and file logging
- Rotating file handler (10MB max, 5 backups)
- Sensitive information masking
- Structured logging with timestamps

### Log Files

Logs are stored in `logs/ragdocman.log`

### Sensitive Information Protection

The logger automatically masks sensitive information:
- API keys
- Passwords
- Tokens
- Secrets

## Error Handling

### Custom Exceptions

The application provides custom exception classes for different error scenarios:

- `ValidationError` (400): Input validation failures
- `NotFoundError` (404): Resource not found
- `ConflictError` (409): Resource conflicts
- `DatabaseError` (500): Database operation failures
- `ExternalServiceError` (503): External service failures
- `ConfigurationError` (500): Configuration issues

### Error Response Format

All errors follow a unified format:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error message",
    "details": {}
  }
}
```

## Database

### Setup

Database tables are automatically created on application startup via SQLAlchemy ORM.

### Connection

- **Type**: SQLite (default)
- **File**: `ragdocman.db`
- **Connection String**: `sqlite:///./ragdocman.db`

### Session Management

Database sessions are managed through dependency injection:

```python
from database import get_db

@app.get("/example")
async def example(db: Session = Depends(get_db)):
    # Use db session
    pass
```

## API Response Format

All API responses follow a unified format:

### Success Response

```json
{
  "success": true,
  "data": { /* response data */ },
  "message": null
}
```

### Error Response

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description",
    "details": {}
  }
}
```

## Middleware

### ErrorHandlingMiddleware

- Catches all exceptions
- Converts custom exceptions to proper HTTP responses
- Logs errors with unique error IDs
- Masks sensitive information

### RequestLoggingMiddleware

- Logs all incoming requests
- Tracks request duration
- Logs response status codes

## Testing

### Test Structure

- Unit tests for individual components
- Integration tests for API endpoints
- Property-based tests for core logic

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test
pytest tests/test_config.py::test_settings_default_values -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

## Next Steps

1. Implement data models (Task 2)
2. Implement knowledge base management service (Task 3)
3. Implement external service integrations (Task 4)
4. Implement vector database integration (Task 5)
5. Continue with remaining tasks...

## Troubleshooting

### Database Issues

If you encounter database errors:

1. Delete `ragdocman.db` file
2. Restart the application (tables will be recreated)

### Import Errors

Ensure you're in the correct virtual environment:

```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Configuration Errors

Check that `.env` file exists and contains required variables:

```bash
cat .env
```

## Development Guidelines

- Follow PEP 8 style guide
- Use type hints for all functions
- Write tests for new functionality
- Mask sensitive information in logs
- Use custom exceptions for error handling
- Document complex logic with comments

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python Logging](https://docs.python.org/3/library/logging.html)
