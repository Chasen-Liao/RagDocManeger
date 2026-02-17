"""Main FastAPI application entry point."""
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import settings
from database import init_db, close_db
from logger import logger
from middleware import ErrorHandlingMiddleware, RequestLoggingMiddleware
from api.knowledge_base_routes import router as kb_router
from api.document_routes import router as doc_router
from api.search_routes import router as search_router
from api.config_routes import router as config_router
from api.rag_routes import router as rag_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    init_db()
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    close_db()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    # Validate configuration
    try:
        settings.validate_config()
    except ValueError as e:
        logger.error(f"Configuration validation failed: {str(e)}")
        raise
    
    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan
    )
    
    # Add middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins (can be restricted to specific domains)
        allow_credentials=True,
        allow_methods=["*"],  # Allow all HTTP methods
        allow_headers=["*"],  # Allow all headers
    )
    
    # Include routers
    app.include_router(kb_router)
    app.include_router(doc_router)
    app.include_router(search_router)
    app.include_router(config_router)
    app.include_router(rag_router)
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "status": "healthy",
                    "app_name": settings.app_name,
                    "version": settings.app_version
                },
                "message": None
            }
        )
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint."""
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "message": f"Welcome to {settings.app_name}",
                    "version": settings.app_version,
                    "docs": "/docs"
                },
                "message": None
            }
        )
    
    logger.info("FastAPI application created successfully")
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
