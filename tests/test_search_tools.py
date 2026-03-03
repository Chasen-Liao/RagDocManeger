"""
Unit tests for search tools.

Tests the search tools implementation including:
- SearchTool
- SearchWithRewriteTool

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 15.1, 15.2, 15.3
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from tools.search_tools import SearchTool, SearchWithRewriteTool
from services.search_service import SearchResponse
from rag.retriever import RetrievalResult


@pytest.fixture
def mock_search_service():
    """Create a mock search service."""
    return Mock()


@pytest.fixture
def sample_retrieval_results():
    """Create sample retrieval results."""
    return [
        RetrievalResult(
            chunk_id="chunk_1",
            doc_id="doc_123",
            content="This is the first relevant document chunk about Python programming.",
            score=0.95,
            doc_name="python_guide.pdf"
        ),
        RetrievalResult(
            chunk_id="chunk_2",
            doc_id="doc_456",
            content="This is the second relevant document chunk about machine learning.",
            score=0.87,
            doc_name="ml_basics.pdf"
        ),
        RetrievalResult(
            chunk_id="chunk_3",
            doc_id="doc_123",
            content="Another chunk from the Python guide about data structures.",
            score=0.82,
            doc_name="python_guide.pdf"
        ),
    ]


@pytest.fixture
def sample_search_response(sample_retrieval_results):
    """Create a sample search response."""
    return SearchResponse(
        query="Python programming",
        results=sample_retrieval_results,
        total_count=3
    )


# ============================================================================
# SearchTool Tests
# ============================================================================

class TestSearchTool:
    """Tests for SearchTool.
    
    **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 15.1, 15.2, 15.3**
    """
    
    @pytest.mark.asyncio
    async def test_search_success(
        self,
        mock_search_service,
        sample_search_response
    ):
        """Test successful search operation.
        
        **Validates: Requirements 8.1, 8.2, 8.3, 8.4**
        """
        # Arrange
        mock_search_service.search = AsyncMock(return_value=sample_search_response)
        tool = SearchTool(search_service=mock_search_service)
        
        # Act
        result = await tool._aexecute(
            query="Python programming",
            kb_id="kb_123",
            top_k=5
        )
        
        # Assert
        assert result.success is True
        assert "找到 3 个相关结果" in result.message
        assert result.data is not None
        assert result.data["query"] == "Python programming"
        assert result.data["total_count"] == 3
        assert len(result.data["results"]) == 3
        assert result.error is None
        
        # Verify search service was called correctly
        mock_search_service.search.assert_called_once_with(
            kb_id="kb_123",
            query="Python programming",
            top_k=5
        )
    
    @pytest.mark.asyncio
    async def test_search_with_scores_and_metadata(
        self,
        mock_search_service,
        sample_search_response
    ):
        """Test that search returns results with scores and metadata.
        
        **Validates: Requirement 8.4**
        """
        # Arrange
        mock_search_service.search = AsyncMock(return_value=sample_search_response)
        tool = SearchTool(search_service=mock_search_service)
        
        # Act
        result = await tool._aexecute(
            query="Python programming",
            kb_id="kb_123",
            top_k=5
        )
        
        # Assert
        assert result.success is True
        results = result.data["results"]
        
        # Check first result has all required fields
        first_result = results[0]
        assert "content" in first_result
        assert "score" in first_result
        assert "metadata" in first_result
        
        # Check metadata structure
        metadata = first_result["metadata"]
        assert "chunk_id" in metadata
        assert "doc_id" in metadata
        assert "doc_name" in metadata
        
        # Verify values
        assert first_result["score"] == 0.95
        assert metadata["chunk_id"] == "chunk_1"
        assert metadata["doc_id"] == "doc_123"
        assert metadata["doc_name"] == "python_guide.pdf"
    
    @pytest.mark.asyncio
    async def test_search_empty_results(
        self,
        mock_search_service
    ):
        """Test search with no results (graceful handling).
        
        **Validates: Requirement 8.5**
        """
        # Arrange
        empty_response = SearchResponse(
            query="nonexistent topic",
            results=[],
            total_count=0
        )
        mock_search_service.search = AsyncMock(return_value=empty_response)
        tool = SearchTool(search_service=mock_search_service)
        
        # Act
        result = await tool._aexecute(
            query="nonexistent topic",
            kb_id="kb_123",
            top_k=5
        )
        
        # Assert
        assert result.success is True
        assert "未找到与查询" in result.message
        assert result.data is not None
        assert result.data["total_count"] == 0
        assert len(result.data["results"]) == 0
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_search_empty_query(
        self,
        mock_search_service
    ):
        """Test search with empty query string."""
        # Arrange
        tool = SearchTool(search_service=mock_search_service)
        
        # Act
        result = await tool._aexecute(
            query="",
            kb_id="kb_123",
            top_k=5
        )
        
        # Assert
        assert result.success is False
        assert "查询文本不能为空" in result.error
        assert result.data is None
    
    @pytest.mark.asyncio
    async def test_search_whitespace_query(
        self,
        mock_search_service
    ):
        """Test search with whitespace-only query."""
        # Arrange
        tool = SearchTool(search_service=mock_search_service)
        
        # Act
        result = await tool._aexecute(
            query="   ",
            kb_id="kb_123",
            top_k=5
        )
        
        # Assert
        assert result.success is False
        assert "查询文本不能为空" in result.error
    
    @pytest.mark.asyncio
    async def test_search_empty_kb_id(
        self,
        mock_search_service
    ):
        """Test search with empty knowledge base ID."""
        # Arrange
        tool = SearchTool(search_service=mock_search_service)
        
        # Act
        result = await tool._aexecute(
            query="Python programming",
            kb_id="",
            top_k=5
        )
        
        # Assert
        assert result.success is False
        assert "知识库 ID 不能为空" in result.error
    
    @pytest.mark.asyncio
    async def test_search_kb_not_found(
        self,
        mock_search_service
    ):
        """Test search when knowledge base doesn't exist."""
        # Arrange
        mock_search_service.search = AsyncMock(
            side_effect=ValueError("Knowledge base not found: kb_999")
        )
        tool = SearchTool(search_service=mock_search_service)
        
        # Act
        result = await tool._aexecute(
            query="Python programming",
            kb_id="kb_999",
            top_k=5
        )
        
        # Assert
        assert result.success is False
        assert "搜索失败" in result.message
        assert "Knowledge base not found" in result.error
    
    @pytest.mark.asyncio
    async def test_search_with_custom_top_k(
        self,
        mock_search_service,
        sample_retrieval_results
    ):
        """Test search with custom top_k parameter.
        
        **Validates: Requirement 8.3**
        """
        # Arrange
        limited_response = SearchResponse(
            query="Python programming",
            results=sample_retrieval_results[:2],
            total_count=2
        )
        mock_search_service.search = AsyncMock(return_value=limited_response)
        tool = SearchTool(search_service=mock_search_service)
        
        # Act
        result = await tool._aexecute(
            query="Python programming",
            kb_id="kb_123",
            top_k=2
        )
        
        # Assert
        assert result.success is True
        assert len(result.data["results"]) == 2
        
        # Verify top_k was passed correctly
        mock_search_service.search.assert_called_once_with(
            kb_id="kb_123",
            query="Python programming",
            top_k=2
        )
    
    @pytest.mark.asyncio
    async def test_search_service_exception(
        self,
        mock_search_service
    ):
        """Test search when service raises unexpected exception."""
        # Arrange
        mock_search_service.search = AsyncMock(
            side_effect=Exception("Database connection error")
        )
        tool = SearchTool(search_service=mock_search_service)
        
        # Act
        result = await tool._aexecute(
            query="Python programming",
            kb_id="kb_123",
            top_k=5
        )
        
        # Assert
        assert result.success is False
        assert "搜索过程中发生错误" in result.message
        assert "Database connection error" in result.error
    
    def test_search_synchronous_execution(
        self,
        mock_search_service,
        sample_search_response
    ):
        """Test synchronous search execution."""
        # Arrange
        mock_search_service.search = AsyncMock(return_value=sample_search_response)
        tool = SearchTool(search_service=mock_search_service)
        
        # Act
        result = tool._execute(
            query="Python programming",
            kb_id="kb_123",
            top_k=5
        )
        
        # Assert
        assert result.success is True
        assert "找到 3 个相关结果" in result.message


# ============================================================================
# SearchWithRewriteTool Tests
# ============================================================================

class TestSearchWithRewriteTool:
    """Tests for SearchWithRewriteTool.
    
    **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 15.1, 15.2, 15.3**
    """
    
    @pytest.mark.asyncio
    async def test_search_with_rewrite_success(
        self,
        mock_search_service,
        sample_retrieval_results
    ):
        """Test successful search with query rewriting."""
        # Arrange
        rewrite_response = SearchResponse(
            query="Python programming",
            results=sample_retrieval_results,
            total_count=3,
            rewritten_query="Python programming | Python coding | Python development"
        )
        mock_search_service.search_with_rewrite = AsyncMock(return_value=rewrite_response)
        tool = SearchWithRewriteTool(search_service=mock_search_service)
        
        # Act
        result = await tool._aexecute(
            query="Python programming",
            kb_id="kb_123",
            top_k=5
        )
        
        # Assert
        assert result.success is True
        assert "找到 3 个相关结果" in result.message
        assert result.data is not None
        assert result.data["query"] == "Python programming"
        assert result.data["rewritten_query"] is not None
        assert "Python coding" in result.data["rewritten_query"]
        assert len(result.data["results"]) == 3
        
        # Verify service was called correctly
        mock_search_service.search_with_rewrite.assert_called_once_with(
            kb_id="kb_123",
            query="Python programming",
            top_k=5
        )
    
    @pytest.mark.asyncio
    async def test_search_with_rewrite_empty_results(
        self,
        mock_search_service
    ):
        """Test search with rewrite returning no results."""
        # Arrange
        empty_response = SearchResponse(
            query="nonexistent topic",
            results=[],
            total_count=0,
            rewritten_query="nonexistent topic | unknown subject"
        )
        mock_search_service.search_with_rewrite = AsyncMock(return_value=empty_response)
        tool = SearchWithRewriteTool(search_service=mock_search_service)
        
        # Act
        result = await tool._aexecute(
            query="nonexistent topic",
            kb_id="kb_123",
            top_k=5
        )
        
        # Assert
        assert result.success is True
        assert "未找到与查询" in result.message
        assert result.data["total_count"] == 0
        assert len(result.data["results"]) == 0
        assert result.data["rewritten_query"] is not None
    
    @pytest.mark.asyncio
    async def test_search_with_rewrite_empty_query(
        self,
        mock_search_service
    ):
        """Test search with rewrite using empty query."""
        # Arrange
        tool = SearchWithRewriteTool(search_service=mock_search_service)
        
        # Act
        result = await tool._aexecute(
            query="",
            kb_id="kb_123",
            top_k=5
        )
        
        # Assert
        assert result.success is False
        assert "查询文本不能为空" in result.error
    
    @pytest.mark.asyncio
    async def test_search_with_rewrite_kb_not_found(
        self,
        mock_search_service
    ):
        """Test search with rewrite when knowledge base doesn't exist."""
        # Arrange
        mock_search_service.search_with_rewrite = AsyncMock(
            side_effect=ValueError("Knowledge base not found: kb_999")
        )
        tool = SearchWithRewriteTool(search_service=mock_search_service)
        
        # Act
        result = await tool._aexecute(
            query="Python programming",
            kb_id="kb_999",
            top_k=5
        )
        
        # Assert
        assert result.success is False
        assert "搜索失败" in result.message
        assert "Knowledge base not found" in result.error
    
    @pytest.mark.asyncio
    async def test_search_with_rewrite_service_exception(
        self,
        mock_search_service
    ):
        """Test search with rewrite when service raises exception."""
        # Arrange
        mock_search_service.search_with_rewrite = AsyncMock(
            side_effect=Exception("LLM service unavailable")
        )
        tool = SearchWithRewriteTool(search_service=mock_search_service)
        
        # Act
        result = await tool._aexecute(
            query="Python programming",
            kb_id="kb_123",
            top_k=5
        )
        
        # Assert
        assert result.success is False
        assert "搜索过程中发生错误" in result.message
        assert "LLM service unavailable" in result.error
    
    def test_search_with_rewrite_synchronous_execution(
        self,
        mock_search_service,
        sample_retrieval_results
    ):
        """Test synchronous execution of search with rewrite."""
        # Arrange
        rewrite_response = SearchResponse(
            query="Python programming",
            results=sample_retrieval_results,
            total_count=3,
            rewritten_query="Python programming | Python coding"
        )
        mock_search_service.search_with_rewrite = AsyncMock(return_value=rewrite_response)
        tool = SearchWithRewriteTool(search_service=mock_search_service)
        
        # Act
        result = tool._execute(
            query="Python programming",
            kb_id="kb_123",
            top_k=5
        )
        
        # Assert
        assert result.success is True
        assert "找到 3 个相关结果" in result.message


# ============================================================================
# Tool Schema Validation Tests
# ============================================================================

class TestSearchToolSchemas:
    """Tests for search tool input schemas.
    
    **Validates: Requirements 10.2, 10.5**
    """
    
    def test_search_input_validation(self):
        """Test SearchInput validation."""
        from tools.search_tools import SearchInput
        
        # Valid input
        valid_input = SearchInput(
            query="Python programming",
            kb_id="kb_123",
            top_k=5
        )
        assert valid_input.query == "Python programming"
        assert valid_input.kb_id == "kb_123"
        assert valid_input.top_k == 5
    
    def test_search_input_default_top_k(self):
        """Test SearchInput with default top_k."""
        from tools.search_tools import SearchInput
        
        # Input without top_k should use default
        input_with_default = SearchInput(
            query="Python programming",
            kb_id="kb_123"
        )
        assert input_with_default.top_k == 5
    
    def test_search_input_top_k_validation(self):
        """Test SearchInput top_k validation."""
        from tools.search_tools import SearchInput
        from pydantic import ValidationError
        
        # Valid top_k values
        valid_input = SearchInput(
            query="test",
            kb_id="kb_123",
            top_k=10
        )
        assert valid_input.top_k == 10
        
        # Invalid top_k - too small
        with pytest.raises(ValidationError):
            SearchInput(
                query="test",
                kb_id="kb_123",
                top_k=0
            )
        
        # Invalid top_k - too large
        with pytest.raises(ValidationError):
            SearchInput(
                query="test",
                kb_id="kb_123",
                top_k=100
            )
    
    def test_search_input_extra_fields_forbidden(self):
        """Test that SearchInput forbids extra fields."""
        from tools.search_tools import SearchInput
        from pydantic import ValidationError
        
        # Extra fields should be rejected
        with pytest.raises(ValidationError):
            SearchInput(
                query="test",
                kb_id="kb_123",
                top_k=5,
                extra_field="not allowed"
            )


# ============================================================================
# Integration Tests
# ============================================================================

class TestSearchToolIntegration:
    """Integration tests for search tools.
    
    **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**
    """
    
    @pytest.mark.asyncio
    async def test_search_tool_langchain_compatibility(
        self,
        mock_search_service,
        sample_search_response
    ):
        """Test that SearchTool is compatible with LangChain."""
        # Arrange
        mock_search_service.search = AsyncMock(return_value=sample_search_response)
        tool = SearchTool(search_service=mock_search_service)
        
        # Verify LangChain tool attributes
        assert hasattr(tool, 'name')
        assert hasattr(tool, 'description')
        assert hasattr(tool, 'args_schema')
        assert tool.name == "search"
        assert "混合检索" in tool.description
        
        # Verify tool can be invoked
        result = await tool._arun(
            query="Python programming",
            kb_id="kb_123",
            top_k=5
        )
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_search_with_rewrite_tool_langchain_compatibility(
        self,
        mock_search_service,
        sample_retrieval_results
    ):
        """Test that SearchWithRewriteTool is compatible with LangChain."""
        # Arrange
        rewrite_response = SearchResponse(
            query="Python",
            results=sample_retrieval_results,
            total_count=3,
            rewritten_query="Python | Python programming"
        )
        mock_search_service.search_with_rewrite = AsyncMock(return_value=rewrite_response)
        tool = SearchWithRewriteTool(search_service=mock_search_service)
        
        # Verify LangChain tool attributes
        assert hasattr(tool, 'name')
        assert hasattr(tool, 'description')
        assert hasattr(tool, 'args_schema')
        assert tool.name == "search_with_rewrite"
        assert "查询重写" in tool.description
        
        # Verify tool can be invoked
        result = await tool._arun(
            query="Python",
            kb_id="kb_123",
            top_k=5
        )
        assert result.success is True
