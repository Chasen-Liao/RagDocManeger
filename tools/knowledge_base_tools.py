"""
Knowledge Base Management Tools for RagDocMan Agent

This module provides tools for managing knowledge bases through natural language:
- CreateKnowledgeBaseTool: Create new knowledge bases
- ListKnowledgeBasesTool: List all knowledge bases
- GetKnowledgeBaseTool: Get knowledge base details
- UpdateKnowledgeBaseTool: Update knowledge base information
- DeleteKnowledgeBaseTool: Delete knowledge bases

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 15.1, 15.2, 15.3
"""

import logging
from typing import Optional, Type, Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from tools.base import BaseRagDocManTool, ToolInput, ToolOutput
from services.knowledge_base_service import KnowledgeBaseService
from models.schemas import KnowledgeBaseCreate, KnowledgeBaseUpdate
from exceptions import ResourceNotFoundError, ConflictError

# Configure logger
logger = logging.getLogger(__name__)


# ============================================================================
# Input Schemas
# ============================================================================

class CreateKnowledgeBaseInput(ToolInput):
    """Input schema for creating a knowledge base.
    
    **Validates: Requirements 6.1, 10.2**
    """
    kb_name: str = Field(
        description="Name of the knowledge base to create",
        min_length=1,
        max_length=255
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional description of the knowledge base",
        max_length=1000
    )


class ListKnowledgeBasesInput(ToolInput):
    """Input schema for listing knowledge bases.
    
    **Validates: Requirements 6.3, 10.2**
    """
    skip: int = Field(
        default=0,
        ge=0,
        description="Number of records to skip for pagination"
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of records to return"
    )


class GetKnowledgeBaseInput(ToolInput):
    """Input schema for getting a knowledge base.
    
    **Validates: Requirements 6.4, 10.2**
    """
    kb_id: str = Field(
        description="ID of the knowledge base to retrieve",
        min_length=1
    )


class UpdateKnowledgeBaseInput(ToolInput):
    """Input schema for updating a knowledge base.
    
    **Validates: Requirements 6.5, 10.2**
    """
    kb_id: str = Field(
        description="ID of the knowledge base to update",
        min_length=1
    )
    kb_name: Optional[str] = Field(
        default=None,
        description="New name for the knowledge base",
        min_length=1,
        max_length=255
    )
    description: Optional[str] = Field(
        default=None,
        description="New description for the knowledge base",
        max_length=1000
    )


class DeleteKnowledgeBaseInput(ToolInput):
    """Input schema for deleting a knowledge base.
    
    **Validates: Requirements 6.2, 10.2**
    """
    kb_id: str = Field(
        description="ID of the knowledge base to delete",
        min_length=1
    )


# ============================================================================
# Tool Implementations
# ============================================================================

class CreateKnowledgeBaseTool(BaseRagDocManTool):
    """
    Tool for creating a new knowledge base.
    
    This tool allows the Agent to create knowledge bases through natural language
    commands like "Create a knowledge base called 'Product Documentation'".
    
    **Validates: Requirements 6.1, 15.1, 15.2, 15.3**
    
    Example usage:
        User: "Create a knowledge base called 'Product Docs' for storing product documentation"
        Agent calls: CreateKnowledgeBaseTool(kb_name="Product Docs", description="...")
    """
    
    name: str = "create_knowledge_base"
    description: str = (
        "Create a new knowledge base. Use this tool when the user wants to create "
        "a new knowledge base. Provide a name and optional description."
    )
    args_schema: Type[BaseModel] = CreateKnowledgeBaseInput
    db_session: Any = Field(description="Database session")
    
    def __init__(self, db_session: Session):
        """Initialize the tool with a database session.
        
        Args:
            db_session: SQLAlchemy database session
        """
        super().__init__(db_session=db_session)
    
    async def _aexecute(
        self,
        kb_name: str,
        description: Optional[str] = None
    ) -> ToolOutput:
        """
        Asynchronously create a knowledge base.
        
        **Validates: Requirements 6.1, 15.1, 15.2, 15.3**
        
        Args:
            kb_name: Name of the knowledge base
            description: Optional description
            
        Returns:
            ToolOutput with success status and knowledge base details
        """
        try:
            self._log_execution_start(f"Creating knowledge base: {kb_name}")
            
            # Create knowledge base using service
            kb_create = KnowledgeBaseCreate(
                name=kb_name,
                description=description
            )
            kb_response = await KnowledgeBaseService.create_knowledge_base(
                db=self.db_session,
                kb_create=kb_create
            )
            
            return self._create_success_output(
                message=f"Successfully created knowledge base: {kb_name}",
                data={
                    "kb_id": kb_response.id,
                    "kb_name": kb_response.name,
                    "description": kb_response.description,
                    "created_at": kb_response.created_at.isoformat()
                }
            )
            
        except ConflictError as e:
            logger.warning(f"Knowledge base name conflict: {str(e)}")
            return self._create_error_output(
                message=f"Failed to create knowledge base: name already exists",
                error=str(e)
            )
        except Exception as e:
            self._log_error("Creating knowledge base", e)
            return self._create_error_output(
                message=f"Failed to create knowledge base: {kb_name}",
                error=str(e)
            )


class ListKnowledgeBasesTool(BaseRagDocManTool):
    """
    Tool for listing all knowledge bases.
    
    This tool allows the Agent to retrieve a list of all knowledge bases
    in response to commands like "List all knowledge bases" or "Show me my knowledge bases".
    
    **Validates: Requirements 6.3, 15.1, 15.2, 15.3**
    
    Example usage:
        User: "Show me all my knowledge bases"
        Agent calls: ListKnowledgeBasesTool(skip=0, limit=20)
    """
    
    name: str = "list_knowledge_bases"
    description: str = (
        "List all knowledge bases with pagination support. Use this tool when the user "
        "wants to see all available knowledge bases or get a list of knowledge bases."
    )
    args_schema: Type[BaseModel] = ListKnowledgeBasesInput
    db_session: Any = Field(description="Database session")
    
    def __init__(self, db_session: Session):
        """Initialize the tool with a database session.
        
        Args:
            db_session: SQLAlchemy database session
        """
        super().__init__(db_session=db_session)
    
    async def _aexecute(
        self,
        skip: int = 0,
        limit: int = 20
    ) -> ToolOutput:
        """
        Asynchronously list knowledge bases.
        
        **Validates: Requirements 6.3, 15.1, 15.2, 15.3**
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            ToolOutput with list of knowledge bases
        """
        try:
            self._log_execution_start(f"Listing knowledge bases (skip={skip}, limit={limit})")
            
            # Get knowledge bases using service
            kb_list, total = await KnowledgeBaseService.get_knowledge_bases(
                db=self.db_session,
                skip=skip,
                limit=limit
            )
            
            # Format knowledge bases for output
            kb_data = [
                {
                    "kb_id": kb.id,
                    "kb_name": kb.name,
                    "description": kb.description,
                    "document_count": kb.document_count,
                    "total_size": kb.total_size,
                    "created_at": kb.created_at.isoformat(),
                    "updated_at": kb.updated_at.isoformat()
                }
                for kb in kb_list
            ]
            
            message = f"Found {len(kb_data)} knowledge base(s) (total: {total})"
            if len(kb_data) == 0:
                message = "No knowledge bases found"
            
            return self._create_success_output(
                message=message,
                data={
                    "knowledge_bases": kb_data,
                    "total": total,
                    "skip": skip,
                    "limit": limit
                }
            )
            
        except Exception as e:
            self._log_error("Listing knowledge bases", e)
            return self._create_error_output(
                message="Failed to list knowledge bases",
                error=str(e)
            )


class GetKnowledgeBaseTool(BaseRagDocManTool):
    """
    Tool for getting knowledge base details.
    
    This tool allows the Agent to retrieve detailed information about a specific
    knowledge base in response to commands like "Get details of knowledge base X".
    
    **Validates: Requirements 6.4, 15.1, 15.2, 15.3**
    
    Example usage:
        User: "Show me details of the Product Docs knowledge base"
        Agent calls: GetKnowledgeBaseTool(kb_id="kb_123abc")
    """
    
    name: str = "get_knowledge_base"
    description: str = (
        "Get detailed information about a specific knowledge base. Use this tool when "
        "the user wants to see details, statistics, or information about a particular "
        "knowledge base. Requires the knowledge base ID."
    )
    args_schema: Type[BaseModel] = GetKnowledgeBaseInput
    db_session: Any = Field(description="Database session")
    
    def __init__(self, db_session: Session):
        """Initialize the tool with a database session.
        
        Args:
            db_session: SQLAlchemy database session
        """
        super().__init__(db_session=db_session)
    
    async def _aexecute(self, kb_id: str) -> ToolOutput:
        """
        Asynchronously get knowledge base details.
        
        **Validates: Requirements 6.4, 15.1, 15.2, 15.3**
        
        Args:
            kb_id: Knowledge base ID
            
        Returns:
            ToolOutput with knowledge base details
        """
        try:
            self._log_execution_start(f"Getting knowledge base: {kb_id}")
            
            # Get knowledge base using service
            kb_response = await KnowledgeBaseService.get_knowledge_base(
                db=self.db_session,
                kb_id=kb_id
            )
            
            return self._create_success_output(
                message=f"Successfully retrieved knowledge base: {kb_response.name}",
                data={
                    "kb_id": kb_response.id,
                    "kb_name": kb_response.name,
                    "description": kb_response.description,
                    "document_count": kb_response.document_count,
                    "total_size": kb_response.total_size,
                    "created_at": kb_response.created_at.isoformat(),
                    "updated_at": kb_response.updated_at.isoformat()
                }
            )
            
        except ResourceNotFoundError as e:
            logger.warning(f"Knowledge base not found: {kb_id}")
            return self._create_error_output(
                message=f"Knowledge base not found: {kb_id}",
                error=str(e)
            )
        except Exception as e:
            self._log_error("Getting knowledge base", e)
            return self._create_error_output(
                message=f"Failed to get knowledge base: {kb_id}",
                error=str(e)
            )


class UpdateKnowledgeBaseTool(BaseRagDocManTool):
    """
    Tool for updating knowledge base information.
    
    This tool allows the Agent to update knowledge base metadata like name and
    description in response to commands like "Update the description of knowledge base X".
    
    **Validates: Requirements 6.5, 15.1, 15.2, 15.3**
    
    Example usage:
        User: "Update the description of Product Docs to 'All product documentation'"
        Agent calls: UpdateKnowledgeBaseTool(kb_id="kb_123abc", description="...")
    """
    
    name: str = "update_knowledge_base"
    description: str = (
        "Update knowledge base information such as name or description. Use this tool "
        "when the user wants to modify or update a knowledge base's metadata. "
        "Requires the knowledge base ID and at least one field to update."
    )
    args_schema: Type[BaseModel] = UpdateKnowledgeBaseInput
    db_session: Any = Field(description="Database session")
    
    def __init__(self, db_session: Session):
        """Initialize the tool with a database session.
        
        Args:
            db_session: SQLAlchemy database session
        """
        super().__init__(db_session=db_session)
    
    async def _aexecute(
        self,
        kb_id: str,
        kb_name: Optional[str] = None,
        description: Optional[str] = None
    ) -> ToolOutput:
        """
        Asynchronously update knowledge base.
        
        **Validates: Requirements 6.5, 15.1, 15.2, 15.3**
        
        Args:
            kb_id: Knowledge base ID
            kb_name: New name (optional)
            description: New description (optional)
            
        Returns:
            ToolOutput with updated knowledge base details
        """
        try:
            # Validate that at least one field is provided
            if kb_name is None and description is None:
                return self._create_error_output(
                    message="No fields to update",
                    error="At least one of kb_name or description must be provided"
                )
            
            self._log_execution_start(f"Updating knowledge base: {kb_id}")
            
            # Update knowledge base using service
            kb_update = KnowledgeBaseUpdate(
                name=kb_name,
                description=description
            )
            kb_response = await KnowledgeBaseService.update_knowledge_base(
                db=self.db_session,
                kb_id=kb_id,
                kb_update=kb_update
            )
            
            return self._create_success_output(
                message=f"Successfully updated knowledge base: {kb_response.name}",
                data={
                    "kb_id": kb_response.id,
                    "kb_name": kb_response.name,
                    "description": kb_response.description,
                    "document_count": kb_response.document_count,
                    "total_size": kb_response.total_size,
                    "updated_at": kb_response.updated_at.isoformat()
                }
            )
            
        except ResourceNotFoundError as e:
            logger.warning(f"Knowledge base not found: {kb_id}")
            return self._create_error_output(
                message=f"Knowledge base not found: {kb_id}",
                error=str(e)
            )
        except ConflictError as e:
            logger.warning(f"Knowledge base name conflict: {str(e)}")
            return self._create_error_output(
                message="Failed to update knowledge base: name already exists",
                error=str(e)
            )
        except Exception as e:
            self._log_error("Updating knowledge base", e)
            return self._create_error_output(
                message=f"Failed to update knowledge base: {kb_id}",
                error=str(e)
            )


class DeleteKnowledgeBaseTool(BaseRagDocManTool):
    """
    Tool for deleting a knowledge base.
    
    This tool allows the Agent to delete knowledge bases and all associated data
    in response to commands like "Delete knowledge base X".
    
    **Validates: Requirements 6.2, 15.1, 15.2, 15.3**
    
    Example usage:
        User: "Delete the Product Docs knowledge base"
        Agent calls: DeleteKnowledgeBaseTool(kb_id="kb_123abc")
    """
    
    name: str = "delete_knowledge_base"
    description: str = (
        "Delete a knowledge base and all its associated documents and data. "
        "Use this tool when the user wants to remove or delete a knowledge base. "
        "This operation is irreversible. Requires the knowledge base ID."
    )
    args_schema: Type[BaseModel] = DeleteKnowledgeBaseInput
    db_session: Any = Field(description="Database session")
    
    def __init__(self, db_session: Session):
        """Initialize the tool with a database session.
        
        Args:
            db_session: SQLAlchemy database session
        """
        super().__init__(db_session=db_session)
    
    async def _aexecute(self, kb_id: str) -> ToolOutput:
        """
        Asynchronously delete knowledge base.
        
        **Validates: Requirements 6.2, 15.1, 15.2, 15.3**
        
        Args:
            kb_id: Knowledge base ID
            
        Returns:
            ToolOutput with deletion confirmation
        """
        try:
            self._log_execution_start(f"Deleting knowledge base: {kb_id}")
            
            # Delete knowledge base using service
            await KnowledgeBaseService.delete_knowledge_base(
                db=self.db_session,
                kb_id=kb_id
            )
            
            return self._create_success_output(
                message=f"Successfully deleted knowledge base: {kb_id}",
                data={
                    "kb_id": kb_id,
                    "deleted": True
                }
            )
            
        except ResourceNotFoundError as e:
            logger.warning(f"Knowledge base not found: {kb_id}")
            return self._create_error_output(
                message=f"Knowledge base not found: {kb_id}",
                error=str(e)
            )
        except Exception as e:
            self._log_error("Deleting knowledge base", e)
            return self._create_error_output(
                message=f"Failed to delete knowledge base: {kb_id}",
                error=str(e)
            )
