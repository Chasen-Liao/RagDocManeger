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
