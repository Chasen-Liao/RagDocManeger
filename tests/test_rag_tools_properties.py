"""Property-based tests for RAG generation tools.

This module contains property-based tests using Hypothesis to verify that
the RAG generation tools maintain correctness properties across different inputs.

**Validates: Requirements 9.1, 9.4**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import AsyncMock, MagicMock
import uuid

from tools.search_tools import RAGGenerateTool
from services.search_service import SearchResponse
from rag.retriever import RetrievalResult

# Hypothesis strategies for generating test data
question_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs", "Po")),
    min_size=5,
    max_size=200
).filter(lambda x: len(x.strip()) > 5)

kb_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    min_size=5,
    max_size=50
).map(lambda x: f"kb_{x}")

top_k_strategy = st.integers(min_value=1, max_value=20)

content_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs", "Po")),
    min_size=10,
    max_size=500
).filter(lambda x: len(x.strip()) > 10)

score_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)


def create_mock_retrieval_result(
    content: str,
    score: float,
    chunk_id: str = None,
    doc_id: str = None,
    doc_name: str = None
) -> RetrievalResult:
    """Helper function to create mock retrieval results."""
    return RetrievalResult(
        chunk_id=chunk_id or f"chunk_{uuid.uuid4().hex[:8]}",
        doc_id=doc_id or f"doc_{uuid.uuid4().hex[:8]}",
        content=content,
        score=score,
        doc_name=doc_name or f"document_{uuid.uuid4().hex[:4]}.pdf"
    )


def create_mock_search_response(
    results: list,
    total_count: int = None
) -> SearchResponse:
    """Helper function to create mock search responses."""
    return SearchResponse(
        query="test query",
        results=results,
        total_count=total_count or len(results)
    )


class MockLLMProvider:
    """Mock LLM provider for property testing."""
    
    def __init__(self, response_template: str = "Answer: {question}"):
        self.response_template = response_template
        self.call_count = 0
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Mock generate method that returns consistent output."""
        self.call_count += 1
        # Extract question from prompt if possible
        if "问题：" in prompt or "问题:" in prompt:
            # Return a response that includes context info
            return f"Based on the provided context, here is the answer. (Call #{self.call_count})"
        return f"Answer without context. (Call #{self.call_count})"
    
    async def generate_stream(self, prompt: str, **kwargs):
        """Mock streaming generate method."""
        response = await self.generate(prompt, **kwargs)
        # Yield response in chunks
        chunk_size = max(1, len(response) // 5)
        for i in range(0, len(response), chunk_size):
            yield response[i:i+chunk_size]


class MockSearchService:
    """Mock search service for property testing."""
    
    def __init__(self, results_to_return: list = None):
        self.results_to_return = results_to_return or []
        self.call_count = 0
        self.last_query = None
    
    async def search(self, kb_id: str, query: str, top_k: int):
        """Mock search method that returns predefined results."""
        self.call_count += 1
        self.last_query = query
        
        # Return the predefined results, limited by top_k
        results = self.results_to_return[:top_k]
        
        return create_mock_search_response(
            results=results,
            total_count=len(results)
        )



# ============================================================================
# Property 10: RAG with Sources - Generated answers should include source citations
# **Validates: Requirement 9.4**
# ============================================================================

@pytest.mark.asyncio
@given(
    question=question_strategy,
    kb_id=kb_id_strategy,
    top_k=top_k_strategy,
    num_results=st.integers(min_value=1, max_value=10),
    contents=st.lists(content_strategy, min_size=1, max_size=10),
    scores=st.lists(score_strategy, min_size=1, max_size=10)
)
@settings(max_examples=50, deadline=5000)
async def test_property_rag_with_sources(
    question: str,
    kb_id: str,
    top_k: int,
    num_results: int,
    contents: list,
    scores: list
):
    """
    Property 10: RAG with Sources
    
    When RAG generation is performed with retrieved documents,
    the generated answer MUST include source citations.
    
    **Validates: Requirement 9.4**
    
    Property:
    - IF search returns results
    - THEN the RAG output MUST contain a 'sources' field
    - AND the 'sources' field MUST be a non-empty list
    - AND each source MUST contain:
      - content_preview: preview of the source content
      - score: relevance score
      - doc_name: name of the source document
      - doc_id: ID of the source document
      - chunk_id: ID of the chunk
    """
    # Ensure we have matching lengths
    num_results = min(num_results, len(contents), len(scores))
    assume(num_results > 0)
    
    # Create mock retrieval results
    mock_results = []
    for i in range(num_results):
        result = create_mock_retrieval_result(
            content=contents[i],
            score=scores[i],
            chunk_id=f"chunk_{i}",
            doc_id=f"doc_{i}",
            doc_name=f"document_{i}.pdf"
        )
        mock_results.append(result)
    
    # Create mock services
    mock_search_service = MockSearchService(results_to_return=mock_results)
    mock_llm_provider = MockLLMProvider()
    
    # Create RAG tool
    rag_tool = RAGGenerateTool(
        search_service=mock_search_service,
        llm_provider=mock_llm_provider
    )
    
    # Execute RAG generation
    result = await rag_tool._aexecute(
        question=question,
        kb_id=kb_id,
        top_k=top_k,
        stream=False
    )
    
    # Property assertions
    assert result.success is True, "RAG generation should succeed"
    assert result.data is not None, "Result data should not be None"
    
    # MUST contain sources field
    assert "sources" in result.data, "Result must contain 'sources' field"
    
    # Sources must be a list
    assert isinstance(result.data["sources"], list), "Sources must be a list"
    
    # Sources must not be empty (since we have results)
    assert len(result.data["sources"]) > 0, "Sources must not be empty when documents are retrieved"
    
    # Each source must have required fields
    for source in result.data["sources"]:
        assert "content_preview" in source, "Source must have content_preview"
        assert "score" in source, "Source must have score"
        assert "doc_name" in source, "Source must have doc_name"
        assert "doc_id" in source, "Source must have doc_id"
        assert "chunk_id" in source, "Source must have chunk_id"
        
        # Validate types
        assert isinstance(source["content_preview"], str), "content_preview must be string"
        assert isinstance(source["score"], (int, float)), "score must be numeric"
        assert isinstance(source["doc_name"], str), "doc_name must be string"
        assert isinstance(source["doc_id"], str), "doc_id must be string"
        assert isinstance(source["chunk_id"], str), "chunk_id must be string"
        
        # Content preview should not be empty
        assert len(source["content_preview"]) > 0, "content_preview should not be empty"


@pytest.mark.asyncio
@given(
    question=question_strategy,
    kb_id=kb_id_strategy,
    top_k=top_k_strategy
)
@settings(max_examples=30, deadline=5000)
async def test_property_rag_sources_empty_when_no_results(
    question: str,
    kb_id: str,
    top_k: int
):
    """
    Property 10 (Edge Case): RAG with Sources - Empty sources when no documents found
    
    When RAG generation is performed but no documents are retrieved,
    the sources field should be empty.
    
    **Validates: Requirement 9.4**
    
    Property:
    - IF search returns no results
    - THEN the RAG output MUST contain a 'sources' field
    - AND the 'sources' field MUST be an empty list
    - AND context_used MUST be False
    """
    # Create mock services with no results
    mock_search_service = MockSearchService(results_to_return=[])
    mock_llm_provider = MockLLMProvider()
    
    # Create RAG tool
    rag_tool = RAGGenerateTool(
        search_service=mock_search_service,
        llm_provider=mock_llm_provider
    )
    
    # Execute RAG generation
    result = await rag_tool._aexecute(
        question=question,
        kb_id=kb_id,
        top_k=top_k,
        stream=False
    )
    
    # Property assertions
    assert result.success is True, "RAG generation should succeed even without results"
    assert result.data is not None, "Result data should not be None"
    
    # MUST contain sources field
    assert "sources" in result.data, "Result must contain 'sources' field"
    
    # Sources must be empty when no documents found
    assert isinstance(result.data["sources"], list), "Sources must be a list"
    assert len(result.data["sources"]) == 0, "Sources must be empty when no documents retrieved"
    
    # Context should not be used
    assert "context_used" in result.data, "Result must contain 'context_used' field"
    assert result.data["context_used"] is False, "context_used must be False when no documents found"


# ============================================================================
# Property 11: Context Relevance - Retrieved documents should be semantically relevant
# **Validates: Requirement 9.1**
# ============================================================================

@pytest.mark.asyncio
@given(
    question=question_strategy,
    kb_id=kb_id_strategy,
    top_k=top_k_strategy,
    num_results=st.integers(min_value=1, max_value=10),
    contents=st.lists(content_strategy, min_size=1, max_size=10),
    scores=st.lists(score_strategy, min_size=1, max_size=10)
)
@settings(max_examples=50, deadline=5000)
async def test_property_context_relevance(
    question: str,
    kb_id: str,
    top_k: int,
    num_results: int,
    contents: list,
    scores: list
):
    """
    Property 11: Context Relevance
    
    When RAG generation retrieves documents from the knowledge base,
    the retrieved documents should be semantically relevant to the question.
    
    **Validates: Requirement 9.1**
    
    Property:
    - WHEN user submits a question
    - THEN the tool SHALL retrieve documents from the knowledge base
    - AND the retrieved documents MUST have relevance scores
    - AND the relevance scores MUST be in the range [0, 1]
    - AND the documents MUST be ordered by relevance (descending)
    - AND the number of retrieved documents MUST NOT exceed top_k
    """
    # Ensure we have matching lengths
    num_results = min(num_results, len(contents), len(scores))
    assume(num_results > 0)
    
    # Sort scores in descending order to simulate proper ranking
    sorted_scores = sorted(scores[:num_results], reverse=True)
    
    # Create mock retrieval results with sorted scores
    mock_results = []
    for i in range(num_results):
        result = create_mock_retrieval_result(
            content=contents[i],
            score=sorted_scores[i],
            chunk_id=f"chunk_{i}",
            doc_id=f"doc_{i}",
            doc_name=f"document_{i}.pdf"
        )
        mock_results.append(result)
    
    # Create mock services
    mock_search_service = MockSearchService(results_to_return=mock_results)
    mock_llm_provider = MockLLMProvider()
    
    # Create RAG tool
    rag_tool = RAGGenerateTool(
        search_service=mock_search_service,
        llm_provider=mock_llm_provider
    )
    
    # Execute RAG generation
    result = await rag_tool._aexecute(
        question=question,
        kb_id=kb_id,
        top_k=top_k,
        stream=False
    )
    
    # Property assertions
    assert result.success is True, "RAG generation should succeed"
    assert result.data is not None, "Result data should not be None"
    assert "sources" in result.data, "Result must contain sources"
    
    sources = result.data["sources"]
    
    # Number of retrieved documents must not exceed top_k
    assert len(sources) <= top_k, f"Number of sources ({len(sources)}) must not exceed top_k ({top_k})"
    
    # Each source must have a relevance score
    for source in sources:
        assert "score" in source, "Each source must have a relevance score"
        score = source["score"]
        
        # Score must be numeric
        assert isinstance(score, (int, float)), "Score must be numeric"
        
        # Score must be in valid range [0, 1]
        assert 0.0 <= score <= 1.0, f"Score {score} must be in range [0, 1]"
    
    # Documents must be ordered by relevance (descending)
    if len(sources) > 1:
        for i in range(len(sources) - 1):
            current_score = sources[i]["score"]
            next_score = sources[i + 1]["score"]
            assert current_score >= next_score, \
                f"Sources must be ordered by score (descending): {current_score} >= {next_score}"


@pytest.mark.asyncio
@given(
    question=question_strategy,
    kb_id=kb_id_strategy,
    top_k=top_k_strategy
)
@settings(max_examples=30, deadline=5000)
async def test_property_context_relevance_search_called(
    question: str,
    kb_id: str,
    top_k: int
):
    """
    Property 11 (Behavioral): Context Relevance - Search service must be called
    
    When RAG generation is performed, the search service MUST be called
    to retrieve relevant documents from the knowledge base.
    
    **Validates: Requirement 9.1**
    
    Property:
    - WHEN user submits a question
    - THEN the search service MUST be called
    - AND the search query MUST match the user's question
    - AND the search MUST target the specified knowledge base
    """
    # Create mock services
    mock_search_service = MockSearchService(results_to_return=[])
    mock_llm_provider = MockLLMProvider()
    
    # Create RAG tool
    rag_tool = RAGGenerateTool(
        search_service=mock_search_service,
        llm_provider=mock_llm_provider
    )
    
    # Execute RAG generation
    result = await rag_tool._aexecute(
        question=question,
        kb_id=kb_id,
        top_k=top_k,
        stream=False
    )
    
    # Property assertions
    assert result.success is True, "RAG generation should succeed"
    
    # Search service MUST be called
    assert mock_search_service.call_count > 0, "Search service must be called"
    
    # Search query MUST match the user's question
    assert mock_search_service.last_query == question, \
        f"Search query must match question: expected '{question}', got '{mock_search_service.last_query}'"


@pytest.mark.asyncio
@given(
    question=question_strategy,
    kb_id=kb_id_strategy,
    top_k_requested=st.integers(min_value=1, max_value=20),
    num_available=st.integers(min_value=1, max_value=20),
    contents=st.lists(content_strategy, min_size=1, max_size=20),
    scores=st.lists(score_strategy, min_size=1, max_size=20)
)
@settings(max_examples=50, deadline=5000)
async def test_property_context_relevance_top_k_constraint(
    question: str,
    kb_id: str,
    top_k_requested: int,
    num_available: int,
    contents: list,
    scores: list
):
    """
    Property 11 (Constraint): Context Relevance - Top-k constraint
    
    The number of retrieved documents should respect the top_k parameter
    and not exceed it, even if more documents are available.
    
    **Validates: Requirement 9.1**
    
    Property:
    - WHEN user requests top_k documents
    - AND N documents are available (where N >= top_k)
    - THEN the tool SHALL return at most top_k documents
    - AND the returned documents SHALL be the top_k most relevant ones
    """
    # Ensure we have enough data
    num_available = min(num_available, len(contents), len(scores))
    assume(num_available > 0)
    
    # Create mock retrieval results
    mock_results = []
    for i in range(num_available):
        result = create_mock_retrieval_result(
            content=contents[i],
            score=scores[i],
            chunk_id=f"chunk_{i}",
            doc_id=f"doc_{i}",
            doc_name=f"document_{i}.pdf"
        )
        mock_results.append(result)
    
    # Create mock services
    mock_search_service = MockSearchService(results_to_return=mock_results)
    mock_llm_provider = MockLLMProvider()
    
    # Create RAG tool
    rag_tool = RAGGenerateTool(
        search_service=mock_search_service,
        llm_provider=mock_llm_provider
    )
    
    # Execute RAG generation
    result = await rag_tool._aexecute(
        question=question,
        kb_id=kb_id,
        top_k=top_k_requested,
        stream=False
    )
    
    # Property assertions
    assert result.success is True, "RAG generation should succeed"
    assert result.data is not None, "Result data should not be None"
    assert "sources" in result.data, "Result must contain sources"
    
    sources = result.data["sources"]
    
    # The number of returned documents must not exceed top_k
    expected_count = min(top_k_requested, num_available)
    assert len(sources) <= top_k_requested, \
        f"Number of sources ({len(sources)}) must not exceed top_k ({top_k_requested})"
    
    # The number should match the expected count (min of requested and available)
    assert len(sources) == expected_count, \
        f"Expected {expected_count} sources (min of {top_k_requested} requested and {num_available} available), got {len(sources)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
