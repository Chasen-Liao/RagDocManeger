"""
Document Management Tools for RagDocMan Agent

This module provides tools for managing documents through natural language:
- UploadDocumentTool: Upload documents to knowledge bases
- ListDocumentsTool: List documents with pagination
- GetDocumentTool: Get document details
- UpdateDocumentTool: Update documents with re-embedding
- DeleteDocumentTool: Delete documents and clean up vectors

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 15.1, 15.2, 15.3
"""

import logging
from typing import Optional, Type, Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from tools.base import BaseRagDocManTool, ToolInput, ToolOutput
from services.document_service import DocumentService
from core.vector_store import VectorStore
from exceptions import ResourceNotFoundError

# Configure logger
logger = logging.getLogger(__name__)


# ============================================================================
# Input Schemas
# ============================================================================

class UploadDocumentInput(ToolInput):
    """Input schema for uploading a document.
    
    **Validates: Requirements 7.1, 10.2**
    """
    kb_id: str = Field(
        description="ID of the knowledge base to upload the document to",
        min_length=1
    )
    file_path: str = Field(
        description="Path to the file to upload",
        min_length=1
    )
    file_name: str = Field(
        description="Name of the file",
        min_length=1
    )


class ListDocumentsInput(ToolInput):
    """Input schema for listing documents.
    
    **Validates: Requirements 7.3, 10.2**
    """
    kb_id: str = Field(
        description="ID of the knowledge base to list documents from",
        min_length=1
    )
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


class GetDocumentInput(ToolInput):
    """Input schema for getting a document.
    
    **Validates: Requirements 7.4, 10.2**
    """
    kb_id: str = Field(
        description="ID of the knowledge base",
        min_length=1
    )
    doc_id: str = Field(
        description="ID of the document to retrieve",
        min_length=1
    )


class UpdateDocumentInput(ToolInput):
    """Input schema for updating a document.
    
    **Validates: Requirements 7.5, 10.2**
    """
    kb_id: str = Field(
        description="ID of the knowledge base",
        min_length=1
    )
    doc_id: str = Field(
        description="ID of the document to update",
        min_length=1
    )
    file_path: str = Field(
        description="Path to the new file content",
        min_length=1
    )
    file_name: str = Field(
        description="Name of the new file",
        min_length=1
    )


class DeleteDocumentInput(ToolInput):
    """Input schema for deleting a document.
    
    **Validates: Requirements 7.2, 10.2**
    """
    kb_id: str = Field(
        description="ID of the knowledge base",
        min_length=1
    )
    doc_id: str = Field(
        description="ID of the document to delete",
        min_length=1
    )


# ============================================================================
# Tool Implementations
# ============================================================================

class UploadDocumentTool(BaseRagDocManTool):
    """
    Tool for uploading documents to a knowledge base.
    
    This tool allows the Agent to upload and process documents through natural
    language commands like "Upload file X to knowledge base Y".
    
    **Validates: Requirements 7.1, 15.1, 15.2, 15.3**
    
    Example usage:
        User: "Upload the product_manual.pdf to the Product Docs knowledge base"
        Agent calls: UploadDocumentTool(kb_id="kb_123", file_path="...", file_name="product_manual.pdf")
    """
    
    name: str = "upload_document"
    description: str = (
        "Upload a document to a knowledge base. Use this tool when the user wants to "
        "add a new document to a knowledge base. The document will be processed, "
        "chunked, and embedded automatically. Requires knowledge base ID, file path, "
        "and file name."
    )
    args_schema: Type[BaseModel] = UploadDocumentInput
    db_session: Any = Field(description="Database session")
    vector_store: Any = Field(description="Vector store instance")
    embedding_provider: Any = Field(default=None, description="Embedding provider")
    
    def __init__(
        self,
        db_session: Session,
        vector_store: VectorStore,
        embedding_provider=None
    ):
        """Initialize the tool with required services.
        
        Args:
            db_session: SQLAlchemy database session
            vector_store: Vector store instance
            embedding_provider: Embedding provider for generating embeddings
        """
        super().__init__(
            db_session=db_session,
            vector_store=vector_store,
            embedding_provider=embedding_provider
        )
    
    async def _aexecute(
        self,
        kb_id: str,
        file_path: str,
        file_name: str
    ) -> ToolOutput:
        """
        Asynchronously upload a document.
        
        **Validates: Requirements 7.1, 15.1, 15.2, 15.3**
        
        Args:
            kb_id: Knowledge base ID
            file_path: Path to the file
            file_name: Name of the file
            
        Returns:
            ToolOutput with success status and document details
        """
        try:
            self._log_execution_start(f"Uploading document: {file_name} to KB: {kb_id}")
            
            # Create document service
            doc_service = DocumentService(
                db=self.db_session,
                vector_store=self.vector_store,
                embedding_provider=self.embedding_provider
            )
            
            # Upload document
            doc_response = await doc_service.upload_document(
                kb_id=kb_id,
                file_path=file_path,
                file_name=file_name
            )
            
            return self._create_success_output(
                message=f"Successfully uploaded document: {file_name}",
                data={
                    "doc_id": doc_response.id,
                    "doc_name": doc_response.name,
                    "kb_id": doc_response.kb_id,
                    "file_size": doc_response.file_size,
                    "file_type": doc_response.file_type,
                    "chunk_count": doc_response.chunk_count,
                    "created_at": doc_response.created_at.isoformat()
                }
            )
            
        except ValueError as e:
            logger.warning(f"Validation error uploading document: {str(e)}")
            return self._create_error_output(
                message=f"Failed to upload document: validation error",
                error=str(e)
            )
        except Exception as e:
            self._log_error("Uploading document", e)
            return self._create_error_output(
                message=f"Failed to upload document: {file_name}",
                error=str(e)
            )


class ListDocumentsTool(BaseRagDocManTool):
    """
    Tool for listing documents in a knowledge base.
    
    This tool allows the Agent to retrieve a paginated list of documents
    in response to commands like "List all documents in knowledge base X".
    
    **Validates: Requirements 7.3, 15.1, 15.2, 15.3**
    
    Example usage:
        User: "Show me all documents in the Product Docs knowledge base"
        Agent calls: ListDocumentsTool(kb_id="kb_123", skip=0, limit=20)
    """
    
    name: str = "list_documents"
    description: str = (
        "List all documents in a knowledge base with pagination support. Use this tool "
        "when the user wants to see all documents in a knowledge base or get a list of "
        "documents. Requires knowledge base ID."
    )
    args_schema: Type[BaseModel] = ListDocumentsInput
    db_session: Any = Field(description="Database session")
    vector_store: Any = Field(description="Vector store instance")
    
    def __init__(self, db_session: Session, vector_store: VectorStore):
        """Initialize the tool with required services.
        
        Args:
            db_session: SQLAlchemy database session
            vector_store: Vector store instance
        """
        super().__init__(db_session=db_session, vector_store=vector_store)
    
    async def _aexecute(
        self,
        kb_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> ToolOutput:
        """
        Asynchronously list documents.
        
        **Validates: Requirements 7.3, 15.1, 15.2, 15.3**
        
        Args:
            kb_id: Knowledge base ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            ToolOutput with list of documents
        """
        try:
            self._log_execution_start(
                f"Listing documents in KB: {kb_id} (skip={skip}, limit={limit})"
            )
            
            # Create document service
            doc_service = DocumentService(
                db=self.db_session,
                vector_store=self.vector_store
            )
            
            # Get documents
            paginated_response = await doc_service.get_documents(
                kb_id=kb_id,
                skip=skip,
                limit=limit
            )
            
            # Format documents for output
            doc_data = [
                {
                    "doc_id": doc.id,
                    "doc_name": doc.name,
                    "kb_id": doc.kb_id,
                    "file_size": doc.file_size,
                    "file_type": doc.file_type,
                    "chunk_count": doc.chunk_count,
                    "created_at": doc.created_at.isoformat()
                }
                for doc in paginated_response.items
            ]
            
            total = paginated_response.meta.total
            message = f"Found {len(doc_data)} document(s) (total: {total})"
            if len(doc_data) == 0:
                message = f"No documents found in knowledge base: {kb_id}"
            
            return self._create_success_output(
                message=message,
                data={
                    "documents": doc_data,
                    "total": total,
                    "skip": skip,
                    "limit": limit,
                    "page": paginated_response.meta.page,
                    "pages": paginated_response.meta.pages
                }
            )
            
        except ValueError as e:
            logger.warning(f"Knowledge base not found: {kb_id}")
            return self._create_error_output(
                message=f"Knowledge base not found: {kb_id}",
                error=str(e)
            )
        except Exception as e:
            self._log_error("Listing documents", e)
            return self._create_error_output(
                message=f"Failed to list documents in knowledge base: {kb_id}",
                error=str(e)
            )


class GetDocumentTool(BaseRagDocManTool):
    """
    Tool for getting document details.
    
    This tool allows the Agent to retrieve detailed information about a specific
    document in response to commands like "Get details of document X".
    
    **Validates: Requirements 7.4, 15.1, 15.2, 15.3**
    
    Example usage:
        User: "Show me details of the product_manual.pdf document"
        Agent calls: GetDocumentTool(kb_id="kb_123", doc_id="doc_456")
    """
    
    name: str = "get_document"
    description: str = (
        "Get detailed information about a specific document. Use this tool when "
        "the user wants to see details, metadata, or information about a particular "
        "document. Requires knowledge base ID and document ID."
    )
    args_schema: Type[BaseModel] = GetDocumentInput
    db_session: Any = Field(description="Database session")
    vector_store: Any = Field(description="Vector store instance")
    
    def __init__(self, db_session: Session, vector_store: VectorStore):
        """Initialize the tool with required services.
        
        Args:
            db_session: SQLAlchemy database session
            vector_store: Vector store instance
        """
        super().__init__(db_session=db_session, vector_store=vector_store)
    
    async def _aexecute(self, kb_id: str, doc_id: str) -> ToolOutput:
        """
        Asynchronously get document details.
        
        **Validates: Requirements 7.4, 15.1, 15.2, 15.3**
        
        Args:
            kb_id: Knowledge base ID
            doc_id: Document ID
            
        Returns:
            ToolOutput with document details
        """
        try:
            self._log_execution_start(f"Getting document: {doc_id} from KB: {kb_id}")
            
            # Create document service
            doc_service = DocumentService(
                db=self.db_session,
                vector_store=self.vector_store
            )
            
            # Get document
            doc_response = await doc_service.get_document(
                kb_id=kb_id,
                doc_id=doc_id
            )
            
            return self._create_success_output(
                message=f"Successfully retrieved document: {doc_response.name}",
                data={
                    "doc_id": doc_response.id,
                    "doc_name": doc_response.name,
                    "kb_id": doc_response.kb_id,
                    "file_size": doc_response.file_size,
                    "file_type": doc_response.file_type,
                    "chunk_count": doc_response.chunk_count,
                    "created_at": doc_response.created_at.isoformat()
                }
            )
            
        except ValueError as e:
            logger.warning(f"Document not found: {doc_id}")
            return self._create_error_output(
                message=f"Document not found: {doc_id}",
                error=str(e)
            )
        except Exception as e:
            self._log_error("Getting document", e)
            return self._create_error_output(
                message=f"Failed to get document: {doc_id}",
                error=str(e)
            )


class UpdateDocumentTool(BaseRagDocManTool):
    """
    Tool for updating a document with re-embedding.
    
    This tool allows the Agent to update document content and automatically
    regenerate embeddings in response to commands like "Update document X with new content".
    
    **Validates: Requirements 7.5, 15.1, 15.2, 15.3**
    
    Example usage:
        User: "Update the product_manual.pdf with the new version"
        Agent calls: UpdateDocumentTool(kb_id="kb_123", doc_id="doc_456", file_path="...", file_name="...")
    """
    
    name: str = "update_document"
    description: str = (
        "Update a document with new content and regenerate embeddings. Use this tool "
        "when the user wants to replace or update an existing document. The old content "
        "will be deleted and new content will be processed and embedded. Requires "
        "knowledge base ID, document ID, new file path, and file name."
    )
    args_schema: Type[BaseModel] = UpdateDocumentInput
    db_session: Any = Field(description="Database session")
    vector_store: Any = Field(description="Vector store instance")
    embedding_provider: Any = Field(default=None, description="Embedding provider")
    
    def __init__(
        self,
        db_session: Session,
        vector_store: VectorStore,
        embedding_provider=None
    ):
        """Initialize the tool with required services.
        
        Args:
            db_session: SQLAlchemy database session
            vector_store: Vector store instance
            embedding_provider: Embedding provider for generating embeddings
        """
        super().__init__(
            db_session=db_session,
            vector_store=vector_store,
            embedding_provider=embedding_provider
        )
    
    async def _aexecute(
        self,
        kb_id: str,
        doc_id: str,
        file_path: str,
        file_name: str
    ) -> ToolOutput:
        """
        Asynchronously update a document.
        
        **Validates: Requirements 7.5, 15.1, 15.2, 15.3**
        
        Args:
            kb_id: Knowledge base ID
            doc_id: Document ID
            file_path: Path to the new file
            file_name: Name of the new file
            
        Returns:
            ToolOutput with updated document details
        """
        try:
            self._log_execution_start(f"Updating document: {doc_id} in KB: {kb_id}")
            
            # Create document service
            doc_service = DocumentService(
                db=self.db_session,
                vector_store=self.vector_store,
                embedding_provider=self.embedding_provider
            )
            
            # Delete old document (this will clean up vectors)
            await doc_service.delete_document(kb_id=kb_id, doc_id=doc_id)
            
            # Upload new document with the same ID would be ideal, but since
            # upload_document generates a new ID, we'll upload as new and return that
            # Note: This is a simplified implementation. A more sophisticated approach
            # would preserve the document ID and update in place.
            doc_response = await doc_service.upload_document(
                kb_id=kb_id,
                file_path=file_path,
                file_name=file_name
            )
            
            return self._create_success_output(
                message=f"Successfully updated document: {file_name}",
                data={
                    "doc_id": doc_response.id,
                    "doc_name": doc_response.name,
                    "kb_id": doc_response.kb_id,
                    "file_size": doc_response.file_size,
                    "file_type": doc_response.file_type,
                    "chunk_count": doc_response.chunk_count,
                    "created_at": doc_response.created_at.isoformat(),
                    "note": "Document was replaced with new content and re-embedded"
                }
            )
            
        except ValueError as e:
            logger.warning(f"Document not found or validation error: {str(e)}")
            return self._create_error_output(
                message=f"Failed to update document: validation error",
                error=str(e)
            )
        except Exception as e:
            self._log_error("Updating document", e)
            return self._create_error_output(
                message=f"Failed to update document: {doc_id}",
                error=str(e)
            )


class DeleteDocumentTool(BaseRagDocManTool):
    """
    Tool for deleting a document and cleaning up vectors.
    
    This tool allows the Agent to delete documents and automatically clean up
    associated vectors in response to commands like "Delete document X".
    
    **Validates: Requirements 7.2, 15.1, 15.2, 15.3**
    
    Example usage:
        User: "Delete the old_manual.pdf from Product Docs"
        Agent calls: DeleteDocumentTool(kb_id="kb_123", doc_id="doc_456")
    """
    
    name: str = "delete_document"
    description: str = (
        "Delete a document and clean up all associated vectors and chunks. "
        "Use this tool when the user wants to remove or delete a document from "
        "a knowledge base. This operation is irreversible. Requires knowledge base ID "
        "and document ID."
    )
    args_schema: Type[BaseModel] = DeleteDocumentInput
    db_session: Any = Field(description="Database session")
    vector_store: Any = Field(description="Vector store instance")
    
    def __init__(self, db_session: Session, vector_store: VectorStore):
        """Initialize the tool with required services.
        
        Args:
            db_session: SQLAlchemy database session
            vector_store: Vector store instance
        """
        super().__init__(db_session=db_session, vector_store=vector_store)
    
    async def _aexecute(self, kb_id: str, doc_id: str) -> ToolOutput:
        """
        Asynchronously delete a document.
        
        **Validates: Requirements 7.2, 15.1, 15.2, 15.3**
        
        Args:
            kb_id: Knowledge base ID
            doc_id: Document ID
            
        Returns:
            ToolOutput with deletion confirmation
        """
        try:
            self._log_execution_start(f"Deleting document: {doc_id} from KB: {kb_id}")
            
            # Create document service
            doc_service = DocumentService(
                db=self.db_session,
                vector_store=self.vector_store
            )
            
            # Delete document
            await doc_service.delete_document(kb_id=kb_id, doc_id=doc_id)
            
            return self._create_success_output(
                message=f"Successfully deleted document: {doc_id}",
                data={
                    "doc_id": doc_id,
                    "kb_id": kb_id,
                    "deleted": True
                }
            )
            
        except ValueError as e:
            logger.warning(f"Document not found: {doc_id}")
            return self._create_error_output(
                message=f"Document not found: {doc_id}",
                error=str(e)
            )
        except Exception as e:
            self._log_error("Deleting document", e)
            return self._create_error_output(
                message=f"Failed to delete document: {doc_id}",
                error=str(e)
            )
