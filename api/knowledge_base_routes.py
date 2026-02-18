"""Knowledge base API routes."""
from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional
from sqlalchemy.orm import Session
from models.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    PaginatedResponse
)
from services.knowledge_base_service import KnowledgeBaseService
from exceptions import NotFoundError, ConflictError, ValidationError
from logger import logger
from database import get_db

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(kb_data: KnowledgeBaseCreate, db: Session = Depends(get_db)):
    """Create a new knowledge base.
    
    Creates a new knowledge base with an independent vector index in ChromaDB.
    Each knowledge base is isolated and can contain multiple documents.
    
    **Request Example**:
    ```json
    {
      "name": "产品文档库",
      "description": "存储所有产品相关的文档"
    }
    ```
    
    **Response Example**:
    ```json
    {
      "success": true,
      "data": {
        "id": "kb_123456",
        "name": "产品文档库",
        "description": "存储所有产品相关的文档",
        "document_count": 0,
        "total_size": 0,
        "created_at": "2024-01-15T10:30:00",
        "updated_at": "2024-01-15T10:30:00"
      },
      "message": "Knowledge base created successfully"
    }
    ```
    
    **Error Cases**:
    - 409 Conflict: 知识库名称已存在
    - 400 Bad Request: 缺失必要字段或字段格式不正确
    
    Args:
        kb_data: Knowledge base creation data
        db: Database session
        
    Returns:
        Created knowledge base information
    """
    try:
        logger.info(f"Creating knowledge base: {kb_data.name}")
        kb_service = KnowledgeBaseService()
        kb = await kb_service.create_knowledge_base(db, kb_data)
        
        return {
            "success": True,
            "data": kb,
            "message": "Knowledge base created successfully"
        }
    except ConflictError as e:
        logger.warning(f"Conflict creating knowledge base: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error creating knowledge base: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create knowledge base"
        )


@router.get("", response_model=dict)
async def get_knowledge_bases(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get list of knowledge bases.
    
    Retrieves a paginated list of all knowledge bases with their metadata.
    
    **Query Parameters**:
    - `skip`: 跳过的记录数（默认 0）
    - `limit`: 返回的最大记录数（默认 20，最大 100）
    
    **Request Example**:
    ```
    GET /knowledge-bases?skip=0&limit=20
    ```
    
    **Response Example**:
    ```json
    {
      "success": true,
      "data": [
        {
          "id": "kb_123456",
          "name": "产品文档库",
          "description": "存储所有产品相关的文档",
          "document_count": 5,
          "total_size": 1024000,
          "created_at": "2024-01-15T10:30:00",
          "updated_at": "2024-01-15T10:30:00"
        }
      ],
      "meta": {
        "total": 10,
        "skip": 0,
        "limit": 20,
        "page": 1,
        "pages": 1
      },
      "message": null
    }
    ```
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        Paginated list of knowledge bases
    """
    try:
        logger.info(f"Fetching knowledge bases: skip={skip}, limit={limit}")
        kb_service = KnowledgeBaseService()
        kbs, total = await kb_service.get_knowledge_bases(db, skip=skip, limit=limit)
        
        # Calculate pagination info
        pages = (total + limit - 1) // limit if limit > 0 else 1
        page = (skip // limit) + 1 if limit > 0 else 1
        
        return {
            "success": True,
            "data": kbs,
            "meta": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "page": page,
                "pages": pages
            },
            "message": None
        }
    except Exception as e:
        logger.error(f"Error fetching knowledge bases: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch knowledge bases"
        )


@router.get("/{kb_id}", response_model=dict)
async def get_knowledge_base(kb_id: str, db: Session = Depends(get_db)):
    """Get knowledge base details.
    
    Retrieves detailed information about a specific knowledge base.
    
    **Path Parameters**:
    - `kb_id`: 知识库 ID
    
    **Request Example**:
    ```
    GET /knowledge-bases/kb_123456
    ```
    
    **Response Example**:
    ```json
    {
      "success": true,
      "data": {
        "id": "kb_123456",
        "name": "产品文档库",
        "description": "存储所有产品相关的文档",
        "document_count": 5,
        "total_size": 1024000,
        "created_at": "2024-01-15T10:30:00",
        "updated_at": "2024-01-15T10:30:00"
      },
      "message": null
    }
    ```
    
    **Error Cases**:
    - 404 Not Found: 知识库不存在
    
    Args:
        kb_id: Knowledge base ID
        db: Database session
        
    Returns:
        Knowledge base information
    """
    try:
        logger.info(f"Fetching knowledge base: {kb_id}")
        kb_service = KnowledgeBaseService()
        kb = await kb_service.get_knowledge_base(db, kb_id=kb_id)
        
        return {
            "success": True,
            "data": kb,
            "message": None
        }
    except NotFoundError as e:
        logger.warning(f"Knowledge base not found: {kb_id}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error fetching knowledge base: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch knowledge base"
        )


@router.put("/{kb_id}", response_model=dict)
async def update_knowledge_base(kb_id: str, kb_data: KnowledgeBaseUpdate, db: Session = Depends(get_db)):
    """Update knowledge base information.
    
    Updates the name and/or description of an existing knowledge base.
    
    **Path Parameters**:
    - `kb_id`: 知识库 ID
    
    **Request Example**:
    ```json
    {
      "name": "产品文档库 v2",
      "description": "更新的描述"
    }
    ```
    
    **Response Example**:
    ```json
    {
      "success": true,
      "data": {
        "id": "kb_123456",
        "name": "产品文档库 v2",
        "description": "更新的描述",
        "document_count": 5,
        "total_size": 1024000,
        "created_at": "2024-01-15T10:30:00",
        "updated_at": "2024-01-15T11:00:00"
      },
      "message": "Knowledge base updated successfully"
    }
    ```
    
    **Error Cases**:
    - 404 Not Found: 知识库不存在
    - 409 Conflict: 新名称已被其他知识库使用
    
    Args:
        kb_id: Knowledge base ID
        kb_data: Update data
        db: Database session
        
    Returns:
        Updated knowledge base information
    """
    try:
        logger.info(f"Updating knowledge base: {kb_id}")
        kb_service = KnowledgeBaseService()
        kb = await kb_service.update_knowledge_base(db, kb_id=kb_id, kb_update=kb_data)
        
        return {
            "success": True,
            "data": kb,
            "message": "Knowledge base updated successfully"
        }
    except NotFoundError as e:
        logger.warning(f"Knowledge base not found: {kb_id}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ConflictError as e:
        logger.warning(f"Conflict updating knowledge base: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error updating knowledge base: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update knowledge base"
        )


@router.delete("/{kb_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def delete_knowledge_base(kb_id: str, db: Session = Depends(get_db)):
    """Delete a knowledge base.
    
    Deletes a knowledge base and all its associated documents and vector embeddings.
    This operation is irreversible.
    
    **Path Parameters**:
    - `kb_id`: 知识库 ID
    
    **Request Example**:
    ```
    DELETE /knowledge-bases/kb_123456
    ```
    
    **Response Example**:
    ```json
    {
      "success": true,
      "data": null,
      "message": "Knowledge base deleted successfully"
    }
    ```
    
    **Error Cases**:
    - 404 Not Found: 知识库不存在
    
    Args:
        kb_id: Knowledge base ID
        db: Database session
        
    Returns:
        Success message
    """
    try:
        logger.info(f"Deleting knowledge base: {kb_id}")
        kb_service = KnowledgeBaseService()
        await kb_service.delete_knowledge_base(db, kb_id=kb_id)
        
        return {
            "success": True,
            "data": None,
            "message": "Knowledge base deleted successfully"
        }
    except NotFoundError as e:
        logger.warning(f"Knowledge base not found: {kb_id}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error deleting knowledge base: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete knowledge base"
        )
