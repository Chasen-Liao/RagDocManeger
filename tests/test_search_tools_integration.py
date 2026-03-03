"""
Integration tests for search tools with real services.

These tests verify that the search tools work correctly with actual
SearchService instances (though still using mocked dependencies).

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime

from tools.search_tools import SearchTool, SearchWithRewriteTool
from services.search_service import SearchService, SearchResponse
from rag.retriever import RetrievalResult


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return Mock()


@pytest.fixture
def mock_embedding_provider():
    """Create a mock embedding provider."""
    mock_provider = Mock()
    mock_provider.embed_text = AsyncMock(return_value=[0.1] * 768)
    mock_provider.embed_texts = AsyncMock(return_value=[[0.1] * 768] * 3)
    return mock_provider


@pytest.fixture
def mock_reranker_provider():
    """Create a mock reranker provider."""
    return Mock()


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    return Mock()


@pytest.fixture
def search_service(
    mock_db_session,
    mock_embedding_provider,
    mock_reranker_provider,
    mock_llm_provider
):
    """Create a SearchService instance with mocked dependencies."""
    return SearchService(
        db=mock_db_session,
        embedding_provider=mock_embedding_provider,
        reranker_provider=mock_reranker_provider,
        llm_provider=mock_llm_provider
    )


@pytest.fixture
def sample_retrieval_results():
    """Create sample retrieval results."""
    return [
        RetrievalResult(
            chunk_id="chunk_1",
            doc_id="doc_123",
            content="Python is a high-level programming language.",
            score=0.95,
            doc_name="python_guide.pdf"
        ),
        RetrievalResult(
            chunk_id="chunk_2",
            doc_id="doc_456",
            content="Machine learning is a subset of artificial intelligence.",
            score=0.87,
            doc_name="ml_basics.pdf"
        ),
    ]


class TestSearchToolWithService:
    """Integration tests for SearchTool with SearchService.
    
    **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**
    """
    
    @pytest.mark.asyncio
    async def test_search_tool_with_mocked_service_search(
        self,
        search_service,
        sample_retrieval_results
    ):
        """Test SearchTool with mocked SearchService.search method."""
        # Arrange
        search_response = SearchResponse(
            query="Python programming",
            results=sample_retrieval_results,
            total_count=2
        )
        search_service.search = AsyncMock(return_value=search_response)
        
        tool = SearchTool(search_service=search_service)
        
        # Act
        result = await tool._aexecute(
            query="Python programming",
            kb_id="kb_123",
            top_k=5
        )
        
        # Assert
        assert result.success is True
        assert "找到 2 个相关结果" in result.message
        assert len(result.data["results"]) == 2
        
        # Verify service was called
        search_service.search.assert_called_once_with(
            kb_id="kb_123",
            query="Python programming",
            top_k=5
        )
    
    @pytest.mark.asyncio
    async def test_search_tool_result_format(
        self,
        search_service,
        sample_retrieval_results
    ):
        """Test that SearchTool formats results correctly.
        
        **Validates: Requirement 8.4**
        """
        # Arrange
        search_response = SearchResponse(
            query="Python",
            results=sample_retrieval_results,
            total_count=2
        )
        search_service.search = AsyncMock(return_value=search_response)
        
        tool = SearchTool(search_service=search_service)
        
        # Act
        result = await tool._aexecute(
            query="Python",
            kb_id="kb_123",
            top_k=5
        )
        
        # Assert
        assert result.success is True
        results = result.data["results"]
        
        # Verify each result has required fields
        for res in results:
            assert "content" in res
            assert "score" in res
            assert "metadata" in res
            assert "chunk_id" in res["metadata"]
            assert "doc_id" in res["metadata"]
            assert "doc_name" in res["metadata"]
        
        # Verify first result values
        first = results[0]
        assert first["content"] == "Python is a high-level programming language."
        assert first["score"] == 0.95
        assert first["metadata"]["chunk_id"] == "chunk_1"
        assert first["metadata"]["doc_id"] == "doc_123"
        assert first["metadata"]["doc_name"] == "python_guide.pdf"


class TestSearchWithRewriteToolWithService:
    """Integration tests for SearchWithRewriteTool with SearchService.
    
    **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**
    """
    
    @pytest.mark.asyncio
    async def test_search_with_rewrite_tool_with_mocked_service(
        self,
        search_service,
        sample_retrieval_results
    ):
        """Test SearchWithRewriteTool with mocked SearchService."""
        # Arrange
        search_response = SearchResponse(
            query="Python",
            results=sample_retrieval_results,
            total_count=2,
            rewritten_query="Python | Python programming | Python language"
        )
        search_service.search_with_rewrite = AsyncMock(return_value=search_response)
        
        tool = SearchWithRewriteTool(search_service=search_service)
        
        # Act
        result = await tool._aexecute(
            query="Python",
            kb_id="kb_123",
            top_k=5
        )
        
        # Assert
        assert result.success is True
        assert "找到 2 个相关结果" in result.message
        assert result.data["rewritten_query"] is not None
        assert "Python programming" in result.data["rewritten_query"]
        
        # Verify service was called
        search_service.search_with_rewrite.assert_called_once_with(
            kb_id="kb_123",
            query="Python",
            top_k=5
        )
    
    @pytest.mark.asyncio
    async def test_search_with_rewrite_includes_rewritten_query(
        self,
        search_service,
        sample_retrieval_results
    ):
        """Test that SearchWithRewriteTool includes rewritten query in output."""
        # Arrange
        search_response = SearchResponse(
            query="ML",
            results=sample_retrieval_results,
            total_count=2,
            rewritten_query="ML | machine learning | artificial intelligence"
        )
        search_service.search_with_rewrite = AsyncMock(return_value=search_response)
        
        tool = SearchWithRewriteTool(search_service=search_service)
        
        # Act
        result = await tool._aexecute(
            query="ML",
            kb_id="kb_123",
            top_k=5
        )
        
        # Assert
        assert result.success is True
        assert result.data["query"] == "ML"
        assert result.data["rewritten_query"] == "ML | machine learning | artificial intelligence"


class TestSearchToolErrorHandling:
    """Test error handling in search tools.
    
    **Validates: Requirements 8.5, 16.1, 16.2, 16.3**
    """
    
    @pytest.mark.asyncio
    async def test_search_tool_handles_service_errors_gracefully(
        self,
        search_service
    ):
        """Test that SearchTool handles service errors gracefully."""
        # Arrange
        search_service.search = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        tool = SearchTool(search_service=search_service)
        
        # Act
        result = await tool._aexecute(
            query="Python",
            kb_id="kb_123",
            top_k=5
        )
        
        # Assert
        assert result.success is False
        assert "搜索过程中发生错误" in result.message
        assert "Database connection failed" in result.error
    
    @pytest.mark.asyncio
    async def test_search_with_rewrite_handles_service_errors_gracefully(
        self,
        search_service
    ):
        """Test that SearchWithRewriteTool handles service errors gracefully."""
        # Arrange
        search_service.search_with_rewrite = AsyncMock(
            side_effect=Exception("LLM service unavailable")
        )
        tool = SearchWithRewriteTool(search_service=search_service)
        
        # Act
        result = await tool._aexecute(
            query="Python",
            kb_id="kb_123",
            top_k=5
        )
        
        # Assert
        assert result.success is False
        assert "搜索过程中发生错误" in result.message
        assert "LLM service unavailable" in result.error
