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
    
    # Create FastAPI app with enhanced documentation
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
## RagDocMan - 智能知识库管理与 RAG 增强系统

一个基于高级 RAG（检索增强生成）技术的智能知识库管理系统。

### 核心功能

- **知识库管理**: 创建、更新、删除多个独立的知识库
- **文档处理**: 支持 PDF、Word、Markdown 等多种格式的文档上传和自动处理
- **混合检索**: 结合 BM25 关键词检索和向量相似度检索
- **结果重排序**: 使用 Cross-Encoder 模型对检索结果进行精准排序
- **查询改写**: 通过 HyDE 方法和查询扩展优化用户查询
- **意图识别**: 自动识别用户操作意图并提取相关实体

### API 文档

- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI Schema**: `/openapi.json`

### 响应格式

所有 API 接口使用统一的响应格式：

**成功响应**:
```json
{
  "success": true,
  "data": { ... },
  "message": null
}
```

**错误响应**:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述"
  }
}
```

**分页响应**:
```json
{
  "success": true,
  "data": [...],
  "meta": {
    "total": 100,
    "page": 1,
    "limit": 20,
    "pages": 5
  }
}
```
        """,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
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
