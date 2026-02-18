"""Configuration API routes."""
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any, Optional
from config import settings
from exceptions import ConfigurationError, ValidationError
from logger import logger, mask_sensitive_info

router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=dict)
async def get_config():
    """Get current configuration (non-sensitive fields only).
    
    Retrieves the current system configuration. Sensitive fields like API keys
    are masked for security reasons.
    
    **Request Example**:
    ```
    GET /config
    ```
    
    **Response Example**:
    ```json
    {
      "success": true,
      "data": {
        "app_name": "RagDocMan",
        "app_version": "1.0.0",
        "debug": false,
        "log_level": "INFO",
        "database_url": "***",
        "chroma_db_path": "./chroma_data",
        "llm_provider": "siliconflow",
        "embedding_provider": "siliconflow",
        "embedding_model": "BAAI/bge-small-zh-v1.5",
        "reranker_provider": "siliconflow",
        "reranker_model": "BAAI/bge-reranker-large",
        "max_file_size_mb": 100,
        "supported_file_types": ["pdf", "docx", "md"],
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "retrieval_top_k": 10,
        "reranking_top_k": 5
      },
      "message": null
    }
    ```
    
    Returns:
        Current configuration
    """
    try:
        logger.info("Fetching configuration")
        
        config_data = {
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "debug": settings.debug,
            "log_level": settings.log_level,
            "database_url": "***" if settings.database_url else None,
            "chroma_db_path": settings.chroma_db_path,
            "llm_provider": settings.llm_provider,
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model,
            "reranker_provider": settings.reranker_provider,
            "reranker_model": settings.reranker_model,
            "max_file_size_mb": settings.max_file_size_mb,
            "supported_file_types": settings.supported_file_types,
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "retrieval_top_k": settings.retrieval_top_k,
            "reranking_top_k": settings.reranking_top_k,
        }
        
        return {
            "success": True,
            "data": config_data,
            "message": None
        }
    except Exception as e:
        logger.error(f"Error fetching configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch configuration"
        )


@router.put("", response_model=dict)
async def update_config(config_update: Dict[str, Any]):
    """Update configuration.
    
    Updates system configuration parameters. Only non-sensitive fields can be updated.
    
    **Updatable Fields**:
    - `debug`: 调试模式开关
    - `log_level`: 日志级别 (DEBUG, INFO, WARNING, ERROR)
    - `llm_provider`: LLM 服务商
    - `embedding_provider`: 嵌入模型服务商
    - `embedding_model`: 嵌入模型名称
    - `reranker_provider`: 重排序模型服务商
    - `reranker_model`: 重排序模型名称
    - `chunk_size`: 文本块大小
    - `chunk_overlap`: 块重叠大小
    - `retrieval_top_k`: 检索返回的最大块数
    - `reranking_top_k`: 重排序返回的最大块数
    
    **Request Example**:
    ```json
    {
      "debug": true,
      "log_level": "DEBUG",
      "chunk_size": 1500,
      "retrieval_top_k": 15
    }
    ```
    
    **Response Example**:
    ```json
    {
      "success": true,
      "data": {
        "app_name": "RagDocMan",
        "app_version": "1.0.0",
        "debug": true,
        "log_level": "DEBUG",
        "chunk_size": 1500,
        "retrieval_top_k": 15
      },
      "message": "Configuration updated successfully"
    }
    ```
    
    **Error Cases**:
    - 400 Bad Request: 包含无效的配置字段或值
    - 422 Unprocessable Entity: 配置验证失败
    
    Args:
        config_update: Configuration fields to update
        
    Returns:
        Updated configuration
    """
    try:
        logger.info(f"Updating configuration: {mask_sensitive_info(str(config_update))}")
        
        # Validate configuration update
        allowed_fields = {
            "debug",
            "log_level",
            "llm_provider",
            "embedding_provider",
            "embedding_model",
            "reranker_provider",
            "reranker_model",
            "chunk_size",
            "chunk_overlap",
            "retrieval_top_k",
            "reranking_top_k",
        }
        
        invalid_fields = set(config_update.keys()) - allowed_fields
        if invalid_fields:
            raise ValidationError(
                f"Invalid configuration fields: {', '.join(invalid_fields)}",
                details={"invalid_fields": list(invalid_fields)}
            )
        
        # Update settings
        for key, value in config_update.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        # Validate updated configuration
        settings.validate_config()
        
        # Return updated config
        config_data = {
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "debug": settings.debug,
            "log_level": settings.log_level,
            "llm_provider": settings.llm_provider,
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model,
            "reranker_provider": settings.reranker_provider,
            "reranker_model": settings.reranker_model,
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "retrieval_top_k": settings.retrieval_top_k,
            "reranking_top_k": settings.reranking_top_k,
        }
        
        return {
            "success": True,
            "data": config_data,
            "message": "Configuration updated successfully"
        }
    except ValidationError as e:
        logger.warning(f"Validation error updating configuration: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ConfigurationError as e:
        logger.warning(f"Configuration error: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error updating configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration"
        )
