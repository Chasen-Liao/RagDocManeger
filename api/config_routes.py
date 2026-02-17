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
