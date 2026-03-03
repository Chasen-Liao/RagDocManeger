"""
Unit tests for document management tools.

Tests the document tools implementation including:
- UploadDocumentTool
- ListDocumentsTool
- GetDocumentTool
- UpdateDocumentTool
- DeleteDocumentTool

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 15.1, 15.2, 15.3
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from tools.document_tools import (
    UploadDocumentTool,
    ListDocumentsTool,
    GetDocumentTool,
    UpdateDocumentTool,
    DeleteDocumentTool,
)
from models.schemas import DocumentResponse, PaginatedResponse


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return Mock()


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    mock_store = Mock()
    mock_store.add_vector = AsyncMock()
    mock_store.delete_vector = AsyncMock()
    return mock_store


@pytest.fixture
def mock_embedding_provider():
    """Create a mock embedding provider."""
    mock_provider = Mock()
    mock_provider.embed_text = AsyncMock(return_value=[0.1] * 768)
    return mock_provider


@pytest.fixture
def sample_document_response():
    """Create a sample document response."""
    return DocumentResponse(
        id="doc_123",
        kb_id="kb_456",
        name="test_document.pdf",
        file_size=1024,
        file_type=".pdf",
        chunk_count=5,
        created_at=datetime.now()
    )


# ============================================================================
# UploadDocumentTool Tests
# ============================================================================

class TestUploadDocumentTool:
    """Tests for UploadDocumentTool.
    
    **Validates: Requirements 7.1, 15.1, 15.2, 15.3**
    """
    
    @pytest.mark.asyncio
    async def test_upload_document_success(
        self,
        mock_db_session,
        mock_vector_store,
        mock_embedding_provider,
        sample_document_response
    ):
        """Test successful document upload."""
        # Arrange
        tool = UploadDocumentTool(
            db_session=mock_db_session,
            vector_store=mock_vector_store,
            embedding_provider=mock_embedding_provider
        )
        
        with patch('tools.document_tools.DocumentService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.upload_document = AsyncMock(return_value=sample_document_response)
            
            # Act
            result = await tool._aexecute(
                kb_id="kb_456",
                file_path="/path/to/test.pdf",
                file_name="test_document.pdf"
            )
        
        # Assert
        assert result.success is True
        assert "Successfully uploaded document" in result.message
        assert result.data is not None
        assert result.data["doc_id"] == "doc_123"
        assert result.data["doc_name"] == "test_document.pdf"
        assert result.data["chunk_count"] == 5
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_upload_document_kb_not_found(
        self,
        mock_db_session,
        mock_vector_store,
        mock_embedding_provider
    ):
        """Test upload document when knowledge base doesn't exist."""
        # Arrange
        tool = UploadDocumentTool(
            db_session=mock_db_session,
            vector_store=mock_vector_store,
            embedding_provider=mock_embedding_provider
        )
        
        with patch('tools.document_tools.DocumentService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.upload_document = AsyncMock(
                side_effect=ValueError("Knowledge base not found: kb_999")
            )
            
            # Act
            result = await tool._aexecute(
                kb_id="kb_999",
                file_path="/path/to/test.pdf",
                file_name="test_document.pdf"
            )
        
        # Assert
        assert result.success is False
        assert "validation error" in result.message
        assert result.error is not None
        assert "Knowledge base not found" in result.error
    
    @pytest.mark.asyncio
    async def test_upload_document_invalid_file(
        self,
        mock_db_session,
        mock_vector_store,
        mock_embedding_provider
    ):
        """Test upload document with invalid file."""
        # Arrange
        tool = UploadDocumentTool(
            db_session=mock_db_session,
            vector_store=mock_vector_store,
            embedding_provider=mock_embedding_provider
        )
        
        with patch('tools.document_tools.DocumentService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.upload_document = AsyncMock(
                side_effect=ValueError("Invalid file format")
            )
            
            # Act
            result = await tool._aexecute(
                kb_id="kb_456",
                file_path="/path/to/invalid.xyz",
                file_name="invalid.xyz"
            )
        
        # Assert
        assert result.success is False
        assert "validation error" in result.message
        assert result.error is not None


# ============================================================================
# ListDocumentsTool Tests
# ============================================================================

class TestListDocumentsTool:
    """Tests for ListDocumentsTool.
    
    **Validates: Requirements 7.3, 15.1, 15.2, 15.3**
    """
    
    @pytest.mark.asyncio
    async def test_list_documents_success(
        self,
        mock_db_session,
        mock_vector_store,
        sample_document_response
    ):
        """Test successful document listing."""
        # Arrange
        tool = ListDocumentsTool(
            db_session=mock_db_session,
            vector_store=mock_vector_store
        )
        
        doc2 = DocumentResponse(
            id="doc_789",
            kb_id="kb_456",
            name="another_doc.txt",
            file_size=512,
            file_type=".txt",
            chunk_count=3,
            created_at=datetime.now()
        )
        
        paginated_response = PaginatedResponse(
            items=[sample_document_response, doc2],
            meta={"total": 2, "page": 1, "limit": 20, "pages": 1}
        )
        
        with patch('tools.document_tools.DocumentService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_documents = AsyncMock(return_value=paginated_response)
            
            # Act
            result = await tool._aexecute(kb_id="kb_456", skip=0, limit=20)
        
        # Assert
        assert result.success is True
        assert "Found 2 document(s)" in result.message
        assert result.data is not None
        assert len(result.data["documents"]) == 2
        assert result.data["total"] == 2
        assert result.data["documents"][0]["doc_id"] == "doc_123"
        assert result.data["documents"][1]["doc_id"] == "doc_789"
    
    @pytest.mark.asyncio
    async def test_list_documents_empty(
        self,
        mock_db_session,
        mock_vector_store
    ):
        """Test listing documents when knowledge base is empty."""
        # Arrange
        tool = ListDocumentsTool(
            db_session=mock_db_session,
            vector_store=mock_vector_store
        )
        
        paginated_response = PaginatedResponse(
            items=[],
            meta={"total": 0, "page": 1, "limit": 20, "pages": 0}
        )
        
        with patch('tools.document_tools.DocumentService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_documents = AsyncMock(return_value=paginated_response)
            
            # Act
            result = await tool._aexecute(kb_id="kb_456", skip=0, limit=20)
        
        # Assert
        assert result.success is True
        assert "No documents found" in result.message
        assert result.data["total"] == 0
        assert len(result.data["documents"]) == 0
    
    @pytest.mark.asyncio
    async def test_list_documents_kb_not_found(
        self,
        mock_db_session,
        mock_vector_store
    ):
        """Test listing documents when knowledge base doesn't exist."""
        # Arrange
        tool = ListDocumentsTool(
            db_session=mock_db_session,
            vector_store=mock_vector_store
        )
        
        with patch('tools.document_tools.DocumentService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_documents = AsyncMock(
                side_effect=ValueError("Knowledge base not found: kb_999")
            )
            
            # Act
            result = await tool._aexecute(kb_id="kb_999", skip=0, limit=20)
        
        # Assert
        assert result.success is False
        assert "Knowledge base not found" in result.message
        assert result.error is not None
    
    @pytest.mark.asyncio
    async def test_list_documents_pagination(
        self,
        mock_db_session,
        mock_vector_store,
        sample_document_response
    ):
        """Test document listing with pagination."""
        # Arrange
        tool = ListDocumentsTool(
            db_session=mock_db_session,
            vector_store=mock_vector_store
        )
        
        paginated_response = PaginatedResponse(
            items=[sample_document_response],
            meta={"total": 10, "page": 2, "limit": 5, "pages": 2}
        )
        
        with patch('tools.document_tools.DocumentService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_documents = AsyncMock(return_value=paginated_response)
            
            # Act
            result = await tool._aexecute(kb_id="kb_456", skip=5, limit=5)
        
        # Assert
        assert result.success is True
        assert result.data["total"] == 10
        assert result.data["page"] == 2
        assert result.data["limit"] == 5


# ============================================================================
# GetDocumentTool Tests
# ============================================================================

class TestGetDocumentTool:
    """Tests for GetDocumentTool.
    
    **Validates: Requirements 7.4, 15.1, 15.2, 15.3**
    """
    
    @pytest.mark.asyncio
    async def test_get_document_success(
        self,
        mock_db_session,
        mock_vector_store,
        sample_document_response
    ):
        """Test successful document retrieval."""
        # Arrange
        tool = GetDocumentTool(
            db_session=mock_db_session,
            vector_store=mock_vector_store
        )
        
        with patch('tools.document_tools.DocumentService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_document = AsyncMock(return_value=sample_document_response)
            
            # Act
            result = await tool._aexecute(kb_id="kb_456", doc_id="doc_123")
        
        # Assert
        assert result.success is True
        assert "Successfully retrieved document" in result.message
        assert result.data is not None
        assert result.data["doc_id"] == "doc_123"
        assert result.data["doc_name"] == "test_document.pdf"
        assert result.data["file_size"] == 1024
        assert result.data["chunk_count"] == 5
    
    @pytest.mark.asyncio
    async def test_get_document_not_found(
        self,
        mock_db_session,
        mock_vector_store
    ):
        """Test getting document that doesn't exist."""
        # Arrange
        tool = GetDocumentTool(
            db_session=mock_db_session,
            vector_store=mock_vector_store
        )
        
        with patch('tools.document_tools.DocumentService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_document = AsyncMock(
                side_effect=ValueError("Document not found: doc_999")
            )
            
            # Act
            result = await tool._aexecute(kb_id="kb_456", doc_id="doc_999")
        
        # Assert
        assert result.success is False
        assert "Document not found" in result.message
        assert result.error is not None


# ============================================================================
# UpdateDocumentTool Tests
# ============================================================================

class TestUpdateDocumentTool:
    """Tests for UpdateDocumentTool.
    
    **Validates: Requirements 7.5, 15.1, 15.2, 15.3**
    """
    
    @pytest.mark.asyncio
    async def test_update_document_success(
        self,
        mock_db_session,
        mock_vector_store,
        mock_embedding_provider,
        sample_document_response
    ):
        """Test successful document update."""
        # Arrange
        tool = UpdateDocumentTool(
            db_session=mock_db_session,
            vector_store=mock_vector_store,
            embedding_provider=mock_embedding_provider
        )
        
        updated_response = DocumentResponse(
            id="doc_new",
            kb_id="kb_456",
            name="updated_document.pdf",
            file_size=2048,
            file_type=".pdf",
            chunk_count=8,
            created_at=datetime.now()
        )
        
        with patch('tools.document_tools.DocumentService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.delete_document = AsyncMock()
            mock_service.upload_document = AsyncMock(return_value=updated_response)
            
            # Act
            result = await tool._aexecute(
                kb_id="kb_456",
                doc_id="doc_123",
                file_path="/path/to/updated.pdf",
                file_name="updated_document.pdf"
            )
        
        # Assert
        assert result.success is True
        assert "Successfully updated document" in result.message
        assert result.data is not None
        assert result.data["doc_name"] == "updated_document.pdf"
        assert result.data["chunk_count"] == 8
        assert "re-embedded" in result.data["note"]
        
        # Verify delete was called
        mock_service.delete_document.assert_called_once_with(
            kb_id="kb_456",
            doc_id="doc_123"
        )
    
    @pytest.mark.asyncio
    async def test_update_document_not_found(
        self,
        mock_db_session,
        mock_vector_store,
        mock_embedding_provider
    ):
        """Test updating document that doesn't exist."""
        # Arrange
        tool = UpdateDocumentTool(
            db_session=mock_db_session,
            vector_store=mock_vector_store,
            embedding_provider=mock_embedding_provider
        )
        
        with patch('tools.document_tools.DocumentService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.delete_document = AsyncMock(
                side_effect=ValueError("Document not found: doc_999")
            )
            
            # Act
            result = await tool._aexecute(
                kb_id="kb_456",
                doc_id="doc_999",
                file_path="/path/to/updated.pdf",
                file_name="updated_document.pdf"
            )
        
        # Assert
        assert result.success is False
        assert "validation error" in result.message
        assert result.error is not None


# ============================================================================
# DeleteDocumentTool Tests
# ============================================================================

class TestDeleteDocumentTool:
    """Tests for DeleteDocumentTool.
    
    **Validates: Requirements 7.2, 15.1, 15.2, 15.3**
    """
    
    @pytest.mark.asyncio
    async def test_delete_document_success(
        self,
        mock_db_session,
        mock_vector_store
    ):
        """Test successful document deletion."""
        # Arrange
        tool = DeleteDocumentTool(
            db_session=mock_db_session,
            vector_store=mock_vector_store
        )
        
        with patch('tools.document_tools.DocumentService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.delete_document = AsyncMock()
            
            # Act
            result = await tool._aexecute(kb_id="kb_456", doc_id="doc_123")
        
        # Assert
        assert result.success is True
        assert "Successfully deleted document" in result.message
        assert result.data is not None
        assert result.data["doc_id"] == "doc_123"
        assert result.data["deleted"] is True
        
        # Verify delete was called
        mock_service.delete_document.assert_called_once_with(
            kb_id="kb_456",
            doc_id="doc_123"
        )
    
    @pytest.mark.asyncio
    async def test_delete_document_not_found(
        self,
        mock_db_session,
        mock_vector_store
    ):
        """Test deleting document that doesn't exist."""
        # Arrange
        tool = DeleteDocumentTool(
            db_session=mock_db_session,
            vector_store=mock_vector_store
        )
        
        with patch('tools.document_tools.DocumentService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.delete_document = AsyncMock(
                side_effect=ValueError("Document not found: doc_999")
            )
            
            # Act
            result = await tool._aexecute(kb_id="kb_456", doc_id="doc_999")
        
        # Assert
        assert result.success is False
        assert "Document not found" in result.message
        assert result.error is not None
    
    @pytest.mark.asyncio
    async def test_delete_document_cleans_vectors(
        self,
        mock_db_session,
        mock_vector_store
    ):
        """Test that document deletion cleans up vectors."""
        # Arrange
        tool = DeleteDocumentTool(
            db_session=mock_db_session,
            vector_store=mock_vector_store
        )
        
        with patch('tools.document_tools.DocumentService') as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.delete_document = AsyncMock()
            
            # Act
            result = await tool._aexecute(kb_id="kb_456", doc_id="doc_123")
        
        # Assert
        assert result.success is True
        # The actual vector cleanup is handled by DocumentService,
        # so we just verify the service method was called
        mock_service.delete_document.assert_called_once()


# ============================================================================
# Tool Schema Validation Tests
# ============================================================================

class TestDocumentToolSchemas:
    """Tests for document tool input schemas.
    
    **Validates: Requirements 10.2, 10.5**
    """
    
    def test_upload_document_input_validation(self):
        """Test UploadDocumentInput validation."""
        from tools.document_tools import UploadDocumentInput
        
        # Valid input
        valid_input = UploadDocumentInput(
            kb_id="kb_123",
            file_path="/path/to/file.pdf",
            file_name="file.pdf"
        )
        assert valid_input.kb_id == "kb_123"
        
        # Invalid input - empty kb_id
        with pytest.raises(Exception):
            UploadDocumentInput(
                kb_id="",
                file_path="/path/to/file.pdf",
                file_name="file.pdf"
            )
    
    def test_list_documents_input_validation(self):
        """Test ListDocumentsInput validation."""
        from tools.document_tools import ListDocumentsInput
        
        # Valid input
        valid_input = ListDocumentsInput(kb_id="kb_123", skip=0, limit=20)
        assert valid_input.skip == 0
        assert valid_input.limit == 20
        
        # Invalid input - negative skip
        with pytest.raises(Exception):
            ListDocumentsInput(kb_id="kb_123", skip=-1, limit=20)
        
        # Invalid input - limit too large
        with pytest.raises(Exception):
            ListDocumentsInput(kb_id="kb_123", skip=0, limit=200)
    
    def test_delete_document_input_validation(self):
        """Test DeleteDocumentInput validation."""
        from tools.document_tools import DeleteDocumentInput
        
        # Valid input
        valid_input = DeleteDocumentInput(kb_id="kb_123", doc_id="doc_456")
        assert valid_input.kb_id == "kb_123"
        assert valid_input.doc_id == "doc_456"
        
        # Invalid input - empty doc_id
        with pytest.raises(Exception):
            DeleteDocumentInput(kb_id="kb_123", doc_id="")
