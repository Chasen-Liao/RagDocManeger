"""
Unit tests for RAG generation tool.

This module tests the RAGGenerateTool implementation including:
- Context building from search results
- Prompt template construction
- Answer generation with LLM
- Source citation extraction
- Streaming support

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from tools.search_tools import RAGGenerateTool, RAGGenerateInput
from tools.base import ToolOutput


class MockSearchResult:
    """Mock search result for testing."""
    
    def __init__(self, content, score, chunk_id, doc_id, doc_name):
        self.content = content
        self.score = score
        self.chunk_id = chunk_id
        self.doc_id = doc_id
        self.doc_name = doc_name


class MockSearchResponse:
    """Mock search response for testing."""
    
    def __init__(self, results, total_count):
        self.results = results
        self.total_count = total_count


class MockSearchService:
    """Mock search service for testing."""
    
    async def search(self, kb_id, query, top_k):
        """Mock search method."""
        # Return mock results
        results = [
            MockSearchResult(
                content="Python is a high-level programming language.",
                score=0.95,
                chunk_id="chunk1",
                doc_id="doc1",
                doc_name="Python Guide"
            ),
            MockSearchResult(
                content="Python supports multiple programming paradigms.",
                score=0.85,
                chunk_id="chunk2",
                doc_id="doc1",
                doc_name="Python Guide"
            )
        ]
        return MockSearchResponse(results=results, total_count=2)


class MockLLMProvider:
    """Mock LLM provider for testing."""
    
    async def generate(self, prompt, **kwargs):
        """Mock generate method."""
        return "Python is a versatile programming language that supports multiple paradigms."
    
    async def generate_stream(self, prompt, **kwargs):
        """Mock streaming generate method."""
        chunks = ["Python ", "is ", "a ", "versatile ", "language."]
        for chunk in chunks:
            yield chunk


@pytest.fixture
def mock_search_service():
    """Fixture for mock search service."""
    return MockSearchService()


@pytest.fixture
def mock_llm_provider():
    """Fixture for mock LLM provider."""
    return MockLLMProvider()


@pytest.fixture
def rag_tool(mock_search_service, mock_llm_provider):
    """Fixture for RAG generation tool."""
    return RAGGenerateTool(
        search_service=mock_search_service,
        llm_provider=mock_llm_provider
    )


class TestRAGGenerateInput:
    """Test RAG generate input schema."""
    
    def test_valid_input(self):
        """Test valid input creation."""
        input_data = RAGGenerateInput(
            question="What is Python?",
            kb_id="kb123",
            top_k=5,
            stream=False
        )
        
        assert input_data.question == "What is Python?"
        assert input_data.kb_id == "kb123"
        assert input_data.top_k == 5
        assert input_data.stream is False
    
    def test_default_values(self):
        """Test default values."""
        input_data = RAGGenerateInput(
            question="What is Python?",
            kb_id="kb123"
        )
        
        assert input_data.top_k == 5
        assert input_data.stream is False
    
    def test_top_k_validation(self):
        """Test top_k validation."""
        # Valid range
        input_data = RAGGenerateInput(
            question="What is Python?",
            kb_id="kb123",
            top_k=10
        )
        assert input_data.top_k == 10
        
        # Test boundary values
        with pytest.raises(Exception):
            RAGGenerateInput(
                question="What is Python?",
                kb_id="kb123",
                top_k=0  # Below minimum
            )
        
        with pytest.raises(Exception):
            RAGGenerateInput(
                question="What is Python?",
                kb_id="kb123",
                top_k=100  # Above maximum
            )


class TestRAGGenerateTool:
    """Test RAG generation tool."""
    
    @pytest.mark.asyncio
    async def test_successful_generation(self, rag_tool):
        """
        Test successful RAG generation.
        
        **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
        """
        result = await rag_tool._aexecute(
            question="What is Python?",
            kb_id="kb123",
            top_k=5,
            stream=False
        )
        
        assert isinstance(result, ToolOutput)
        assert result.success is True
        assert result.data is not None
        assert "answer" in result.data
        assert "sources" in result.data
        assert "question" in result.data
        assert result.data["context_used"] is True
        
        # Check answer content
        assert len(result.data["answer"]) > 0
        
        # Check sources
        assert len(result.data["sources"]) > 0
        assert "content_preview" in result.data["sources"][0]
        assert "score" in result.data["sources"][0]
        assert "doc_name" in result.data["sources"][0]
    
    @pytest.mark.asyncio
    async def test_empty_question(self, rag_tool):
        """Test handling of empty question."""
        result = await rag_tool._aexecute(
            question="",
            kb_id="kb123",
            top_k=5
        )
        
        assert result.success is False
        assert "不能为空" in result.error
    
    @pytest.mark.asyncio
    async def test_empty_kb_id(self, rag_tool):
        """Test handling of empty knowledge base ID."""
        result = await rag_tool._aexecute(
            question="What is Python?",
            kb_id="",
            top_k=5
        )
        
        assert result.success is False
        assert "不能为空" in result.error
    
    @pytest.mark.asyncio
    async def test_no_search_results(self, mock_llm_provider):
        """
        Test RAG generation when no documents are found.
        
        **Validates: Requirement 9.1**
        """
        # Create mock search service that returns empty results
        empty_search_service = AsyncMock()
        empty_search_service.search = AsyncMock(
            return_value=MockSearchResponse(results=[], total_count=0)
        )
        
        tool = RAGGenerateTool(
            search_service=empty_search_service,
            llm_provider=mock_llm_provider
        )
        
        result = await tool._aexecute(
            question="What is Python?",
            kb_id="kb123",
            top_k=5
        )
        
        assert result.success is True
        assert result.data["context_used"] is False
        assert len(result.data["sources"]) == 0
        assert "answer" in result.data
    
    def test_build_context(self, rag_tool):
        """
        Test context building from search results.
        
        **Validates: Requirement 9.2**
        """
        search_results = [
            {
                "content": "Python is a programming language.",
                "score": 0.95,
                "metadata": {
                    "doc_name": "Python Guide",
                    "doc_id": "doc1",
                    "chunk_id": "chunk1"
                }
            },
            {
                "content": "Python supports OOP.",
                "score": 0.85,
                "metadata": {
                    "doc_name": "Python OOP",
                    "doc_id": "doc2",
                    "chunk_id": "chunk2"
                }
            }
        ]
        
        context = rag_tool._build_context(search_results)
        
        assert len(context) > 0
        assert "Python is a programming language." in context
        assert "Python supports OOP." in context
        assert "Python Guide" in context
        assert "Python OOP" in context
        assert "[文档 1:" in context
        assert "[文档 2:" in context
    
    def test_build_context_empty(self, rag_tool):
        """Test context building with empty results."""
        context = rag_tool._build_context([])
        assert context == ""
    
    def test_build_prompt_with_context(self, rag_tool):
        """
        Test prompt building with context.
        
        **Validates: Requirement 9.3**
        """
        question = "What is Python?"
        context = "Python is a high-level programming language."
        
        prompt = rag_tool._build_prompt(question, context)
        
        assert len(prompt) > 0
        assert question in prompt
        assert context in prompt
        assert "上下文" in prompt
        assert "问题" in prompt
    
    def test_build_prompt_without_context(self, rag_tool):
        """
        Test prompt building without context.
        
        **Validates: Requirement 9.3**
        """
        question = "What is Python?"
        context = ""
        
        prompt = rag_tool._build_prompt(question, context)
        
        assert len(prompt) > 0
        assert question in prompt
        assert "没有找到相关" in prompt
    
    def test_extract_sources(self, rag_tool):
        """
        Test source citation extraction.
        
        **Validates: Requirement 9.4**
        """
        search_results = [
            {
                "content": "Python is a high-level programming language with dynamic typing.",
                "score": 0.95,
                "metadata": {
                    "doc_name": "Python Guide",
                    "doc_id": "doc1",
                    "chunk_id": "chunk1"
                }
            }
        ]
        
        sources = rag_tool._extract_sources(search_results)
        
        assert len(sources) == 1
        assert "content_preview" in sources[0]
        assert "score" in sources[0]
        assert "doc_name" in sources[0]
        assert "doc_id" in sources[0]
        assert "chunk_id" in sources[0]
        assert sources[0]["score"] == 0.95
        assert sources[0]["doc_name"] == "Python Guide"
    
    def test_extract_sources_long_content(self, rag_tool):
        """Test source extraction with long content (should be truncated)."""
        long_content = "A" * 300  # Content longer than 200 chars
        
        search_results = [
            {
                "content": long_content,
                "score": 0.95,
                "metadata": {
                    "doc_name": "Long Doc",
                    "doc_id": "doc1",
                    "chunk_id": "chunk1"
                }
            }
        ]
        
        sources = rag_tool._extract_sources(search_results)
        
        assert len(sources[0]["content_preview"]) <= 203  # 200 + "..."
        assert sources[0]["content_preview"].endswith("...")
    
    @pytest.mark.asyncio
    async def test_streaming_mode(self, rag_tool):
        """
        Test streaming mode flag.
        
        **Validates: Requirement 9.5**
        """
        result = await rag_tool._aexecute(
            question="What is Python?",
            kb_id="kb123",
            top_k=5,
            stream=True
        )
        
        assert result.success is True
        assert result.data["stream"] is True
        assert "prompt" in result.data
        assert "sources" in result.data
    
    @pytest.mark.asyncio
    async def test_generate_stream(self, rag_tool):
        """
        Test streaming generation method.
        
        **Validates: Requirement 9.5**
        """
        chunks = []
        async for chunk in rag_tool.generate_stream(
            question="What is Python?",
            kb_id="kb123",
            top_k=5
        ):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        full_text = "".join(chunks)
        assert len(full_text) > 0
    
    @pytest.mark.asyncio
    async def test_generate_stream_empty_question(self, rag_tool):
        """Test streaming with empty question."""
        with pytest.raises(ValueError, match="不能为空"):
            async for _ in rag_tool.generate_stream(
                question="",
                kb_id="kb123",
                top_k=5
            ):
                pass
    
    def test_synchronous_execution(self, rag_tool):
        """Test synchronous wrapper method."""
        result = rag_tool._execute(
            question="What is Python?",
            kb_id="kb123",
            top_k=5,
            stream=False
        )
        
        assert isinstance(result, ToolOutput)
        assert result.success is True
        assert result.data is not None


class TestRAGToolIntegration:
    """Integration tests for RAG tool."""
    
    @pytest.mark.asyncio
    async def test_full_rag_pipeline(self, rag_tool):
        """
        Test complete RAG pipeline from question to answer.
        
        **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
        """
        # Execute full pipeline
        result = await rag_tool._aexecute(
            question="What is Python?",
            kb_id="kb123",
            top_k=5,
            stream=False
        )
        
        # Verify all components
        assert result.success is True
        
        # Check question is preserved
        assert result.data["question"] == "What is Python?"
        
        # Check answer is generated
        assert "answer" in result.data
        assert len(result.data["answer"]) > 0
        
        # Check sources are included
        assert "sources" in result.data
        assert len(result.data["sources"]) > 0
        
        # Check context was used
        assert result.data["context_used"] is True
        
        # Verify source structure
        for source in result.data["sources"]:
            assert "content_preview" in source
            assert "score" in source
            assert "doc_name" in source
            assert isinstance(source["score"], (int, float))
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_llm_provider):
        """Test error handling in RAG pipeline."""
        # Create search service that raises exception
        error_search_service = AsyncMock()
        error_search_service.search = AsyncMock(
            side_effect=Exception("Search service error")
        )
        
        tool = RAGGenerateTool(
            search_service=error_search_service,
            llm_provider=mock_llm_provider
        )
        
        result = await tool._aexecute(
            question="What is Python?",
            kb_id="kb123",
            top_k=5
        )
        
        assert result.success is False
        assert result.error is not None
        assert "Search service error" in result.error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
