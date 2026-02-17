"""Knowledge Base management service."""
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.orm import KnowledgeBase, Document
from models.schemas import KnowledgeBaseCreate, KnowledgeBaseUpdate, KnowledgeBaseResponse
from exceptions import ResourceNotFoundError, ConflictError
from logger import logger


class KnowledgeBaseService:
    """Service for managing knowledge bases."""
    
    @staticmethod
    async def create_knowledge_base(
        db: Session,
        kb_create: KnowledgeBaseCreate
    ) -> KnowledgeBaseResponse:
        """Create a new knowledge base.
        
        Args:
            db: Database session
            kb_create: Knowledge base creation data
            
        Returns:
            KnowledgeBaseResponse with created knowledge base info
            
        Raises:
            ConflictError: If knowledge base name already exists
        """
        # Check if knowledge base name already exists
        existing_kb = db.query(KnowledgeBase).filter_by(name=kb_create.name).first()
        if existing_kb:
            logger.warning(f"Knowledge base with name '{kb_create.name}' already exists")
            raise ConflictError(f"Knowledge base with name '{kb_create.name}' already exists")
        
        # Create new knowledge base
        kb_id = f"kb_{uuid.uuid4().hex[:12]}"
        kb = KnowledgeBase(
            id=kb_id,
            name=kb_create.name,
            description=kb_create.description
        )
        
        db.add(kb)
        db.commit()
        db.refresh(kb)
        
        logger.info(f"Knowledge base created: {kb_id} - {kb_create.name}")
        
        return KnowledgeBaseService._to_response(db, kb)
    
    @staticmethod
    async def get_knowledge_bases(
        db: Session,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[KnowledgeBaseResponse], int]:
        """Get paginated list of knowledge bases.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            Tuple of (list of KnowledgeBaseResponse, total count)
        """
        # Get total count
        total = db.query(func.count(KnowledgeBase.id)).scalar()
        
        # Get paginated results
        kbs = db.query(KnowledgeBase).offset(skip).limit(limit).all()
        
        responses = [KnowledgeBaseService._to_response(db, kb) for kb in kbs]
        
        logger.info(f"Retrieved {len(responses)} knowledge bases (total: {total})")
        
        return responses, total
    
    @staticmethod
    async def get_knowledge_base(
        db: Session,
        kb_id: str
    ) -> KnowledgeBaseResponse:
        """Get knowledge base by ID.
        
        Args:
            db: Database session
            kb_id: Knowledge base ID
            
        Returns:
            KnowledgeBaseResponse
            
        Raises:
            ResourceNotFoundError: If knowledge base not found
        """
        kb = db.query(KnowledgeBase).filter_by(id=kb_id).first()
        if not kb:
            logger.warning(f"Knowledge base not found: {kb_id}")
            raise ResourceNotFoundError(f"Knowledge base not found: {kb_id}")
        
        return KnowledgeBaseService._to_response(db, kb)
    
    @staticmethod
    async def update_knowledge_base(
        db: Session,
        kb_id: str,
        kb_update: KnowledgeBaseUpdate
    ) -> KnowledgeBaseResponse:
        """Update knowledge base information.
        
        Args:
            db: Database session
            kb_id: Knowledge base ID
            kb_update: Update data
            
        Returns:
            Updated KnowledgeBaseResponse
            
        Raises:
            ResourceNotFoundError: If knowledge base not found
            ConflictError: If new name already exists
        """
        kb = db.query(KnowledgeBase).filter_by(id=kb_id).first()
        if not kb:
            logger.warning(f"Knowledge base not found: {kb_id}")
            raise ResourceNotFoundError(f"Knowledge base not found: {kb_id}")
        
        # Check if new name already exists (if name is being updated)
        if kb_update.name and kb_update.name != kb.name:
            existing_kb = db.query(KnowledgeBase).filter_by(name=kb_update.name).first()
            if existing_kb:
                logger.warning(f"Knowledge base with name '{kb_update.name}' already exists")
                raise ConflictError(f"Knowledge base with name '{kb_update.name}' already exists")
            kb.name = kb_update.name
        
        # Update description if provided
        if kb_update.description is not None:
            kb.description = kb_update.description
        
        db.commit()
        db.refresh(kb)
        
        logger.info(f"Knowledge base updated: {kb_id}")
        
        return KnowledgeBaseService._to_response(db, kb)
    
    @staticmethod
    async def delete_knowledge_base(
        db: Session,
        kb_id: str
    ) -> None:
        """Delete knowledge base and all associated data.
        
        Args:
            db: Database session
            kb_id: Knowledge base ID
            
        Raises:
            ResourceNotFoundError: If knowledge base not found
        """
        kb = db.query(KnowledgeBase).filter_by(id=kb_id).first()
        if not kb:
            logger.warning(f"Knowledge base not found: {kb_id}")
            raise ResourceNotFoundError(f"Knowledge base not found: {kb_id}")
        
        # Delete knowledge base (cascade will delete documents and chunks)
        db.delete(kb)
        db.commit()
        
        logger.info(f"Knowledge base deleted: {kb_id}")
    
    @staticmethod
    def _to_response(db: Session, kb: KnowledgeBase) -> KnowledgeBaseResponse:
        """Convert KnowledgeBase ORM to response schema.
        
        Args:
            db: Database session
            kb: KnowledgeBase ORM object
            
        Returns:
            KnowledgeBaseResponse
        """
        # Calculate document count
        doc_count = db.query(func.count(Document.id)).filter_by(kb_id=kb.id).scalar()
        
        # Calculate total size
        total_size = db.query(func.sum(Document.file_size)).filter_by(kb_id=kb.id).scalar() or 0
        
        return KnowledgeBaseResponse(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            document_count=doc_count,
            total_size=total_size,
            created_at=kb.created_at,
            updated_at=kb.updated_at
        )
