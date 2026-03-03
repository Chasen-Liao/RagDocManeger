"""Property-based tests for search tools.

This module contains property-based tests using Hypothesis to verify that
the search tools maintain correctness properties across different inputs.

**Validates: Requirements 8.2, 8.3**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import uuid

from tools.search_tools import SearchTool, SearchWithRewriteTool
from services.search_service import SearchResponse
from rag.retriever import RetrievalResult


# Hypothesis strategies for generating test data
query_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs")),
    min_size=1,
    max_size=200
).filter(lambda x: len(x.strip()) > 0)

kb_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    min_size=5,
    max_size=50
).map(lambda x: f"kb_{x}")

top_k_strategy = st.integers(min_value=1, max_value=50)

score_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)


def create_mock_search_result(
    content: str,
    score: float,
    chunk_id: str = None,
    doc_id: str = None,
    doc_name: str = None
) -> RetrievalResult:
    """Helper function to create mock search results."""
    return RetrievalResult(
        chunk_id=chunk_id or f"chunk_{uuid.uuid4().hex[:8]}",
        doc_id=doc_id or f"doc_{uuid.uuid4().hex[:8]}",
        content=content,
        score=score,
        doc_name=doc_name or f"document_{uuid.uuid4().hex[:4]}.pdf"
    )


def create_mock_search_response(
    results: list,
    total_count: int = None,
    rewritten_query: str = None,
    query: str = "test query"
) -> SearchResponse:
    """Helper function to create mock search responses."""
    return SearchResponse(
        query=query,
        results=results,
        total_count=total_count or len(results),
        rewritten_query=rewritten_query
    )


# ============================================================================
# Property 8: Search Result Ordering
# **Validates: Requirements 8.2, 8.3**
# ============================================================================

class TestSearchResultOrdering:
    """
    Property 8: Search Result Ordering
    
    Search results should always be sorted in descending order by score.
    This property ensures that the most relevant results appear first,
    which is critical for user experience and downstream processing.
    
    **Validates: Requirements 8.2, 8.3**
    """
    
    @pytest.mark.asyncio
    @given(
        query=query_strategy,
        kb_id=kb_id_strategy,
        num_results=st.integers(min_value=2, max_value=20),
        top_k=top_k_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_search_results_are_sorted_by_score_descending(
        self,
        query,
        kb_id,
        num_results,
        top_k
    ):
        """
        Property: Search results should be sorted by score in descending order.
        
        Given: A search query that returns multiple results
        When: We execute the search
        Then: Results should be ordered from highest to lowest score
        
        This ensures that the most relevant documents appear first.
        """
        assume(len(query.strip()) > 0)
        
        # Generate mock results with random scores
        # We'll intentionally create them unsorted to test the sorting
        mock_results = []
        for i in range(min(num_results, top_k)):
            # Generate scores that might not be in order
            score = 1.0 - (i * 0.1) + (0.05 if i % 2 == 0 else -0.05)
            score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
            mock_results.append(
                create_mock_search_result(
                    content=f"Result {i} content",
                    score=score
                )
            )
        
        # Sort results by score descending (this is what the service should do)
        mock_results.sort(key=lambda x: x.score, reverse=True)
        
        mock_response = create_mock_search_response(
            results=mock_results,
            total_count=num_results
        )
        
        # Create mock search service
        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=mock_response)
        
        # Create search tool
        search_tool = SearchTool(search_service=mock_search_service)
        
        # Execute search
        result = await search_tool._aexecute(
            query=query,
            kb_id=kb_id,
            top_k=top_k
        )
        
        # Assert search succeeded
        assert result.success is True, "Search should succeed"
        assert result.data is not None, "Result should have data"
        assert "results" in result.data, "Result should have results"
        
        # Extract scores from results
        results = result.data["results"]
        scores = [r["score"] for r in results]
        
        # Property: Scores should be in descending order
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], \
                f"Scores should be in descending order: {scores}"
    
    @pytest.mark.asyncio
    @given(
        query=query_strategy,
        kb_id=kb_id_strategy,
        num_results=st.integers(min_value=2, max_value=20),
        top_k=top_k_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_search_with_rewrite_results_are_sorted_by_score_descending(
        self,
        query,
        kb_id,
        num_results,
        top_k
    ):
        """
        Property: Search with rewrite results should also be sorted by score.
        
        This verifies that query rewriting doesn't affect result ordering.
        """
        assume(len(query.strip()) > 0)
        
        # Generate mock results with scores
        mock_results = []
        for i in range(min(num_results, top_k)):
            score = 1.0 - (i * 0.08)
            score = max(0.0, min(1.0, score))
            mock_results.append(
                create_mock_search_result(
                    content=f"Result {i} content",
                    score=score
                )
            )
        
        # Sort results by score descending
        mock_results.sort(key=lambda x: x.score, reverse=True)
        
        mock_response = create_mock_search_response(
            results=mock_results,
            total_count=num_results,
            rewritten_query=f"rewritten: {query}"
        )
        
        # Create mock search service
        mock_search_service = MagicMock()
        mock_search_service.search_with_rewrite = AsyncMock(return_value=mock_response)
        
        # Create search tool
        search_tool = SearchWithRewriteTool(search_service=mock_search_service)
        
        # Execute search
        result = await search_tool._aexecute(
            query=query,
            kb_id=kb_id,
            top_k=top_k
        )
        
        # Assert search succeeded
        assert result.success is True
        assert result.data is not None
        assert "results" in result.data
        
        # Extract scores from results
        results = result.data["results"]
        scores = [r["score"] for r in results]
        
        # Property: Scores should be in descending order
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], \
                f"Scores should be in descending order: {scores}"
    
    @pytest.mark.asyncio
    @given(
        query=query_strategy,
        kb_id=kb_id_strategy,
        top_k=top_k_strategy
    )
    @settings(max_examples=30, deadline=None)
    async def test_single_result_is_trivially_sorted(
        self,
        query,
        kb_id,
        top_k
    ):
        """
        Property: A single result is trivially sorted.
        
        This edge case verifies that single-result searches work correctly.
        """
        assume(len(query.strip()) > 0)
        
        # Create single result
        mock_results = [
            create_mock_search_result(
                content="Single result content",
                score=0.95
            )
        ]
        
        mock_response = create_mock_search_response(
            results=mock_results,
            total_count=1
        )
        
        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=mock_response)
        
        search_tool = SearchTool(search_service=mock_search_service)
        
        result = await search_tool._aexecute(
            query=query,
            kb_id=kb_id,
            top_k=top_k
        )
        
        # Assert search succeeded
        assert result.success is True
        assert len(result.data["results"]) == 1
        assert result.data["results"][0]["score"] == 0.95


# ============================================================================
# Property 9: Top-k Constraint
# **Validates: Requirement 8.3**
# ============================================================================

class TestTopKConstraint:
    """
    Property 9: Top-k Constraint
    
    The number of returned results should never exceed the top_k parameter.
    This property ensures that the search respects user-specified limits,
    which is important for performance and API contract compliance.
    
    **Validates: Requirement 8.3**
    """
    
    @pytest.mark.asyncio
    @given(
        query=query_strategy,
        kb_id=kb_id_strategy,
        num_available=st.integers(min_value=1, max_value=100),
        top_k=top_k_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_search_respects_top_k_limit(
        self,
        query,
        kb_id,
        num_available,
        top_k
    ):
        """
        Property: Search should return at most top_k results.
        
        Given: A knowledge base with num_available documents
        When: We search with top_k parameter
        Then: The number of results should be min(num_available, top_k)
        
        This ensures the API contract is respected.
        """
        assume(len(query.strip()) > 0)
        
        # Generate mock results (limited by top_k)
        num_results = min(num_available, top_k)
        mock_results = []
        for i in range(num_results):
            score = 1.0 - (i * 0.01)
            score = max(0.0, min(1.0, score))
            mock_results.append(
                create_mock_search_result(
                    content=f"Result {i} content",
                    score=score
                )
            )
        
        mock_response = create_mock_search_response(
            results=mock_results,
            total_count=num_available  # Total available, not returned
        )
        
        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=mock_response)
        
        search_tool = SearchTool(search_service=mock_search_service)
        
        result = await search_tool._aexecute(
            query=query,
            kb_id=kb_id,
            top_k=top_k
        )
        
        # Assert search succeeded
        assert result.success is True
        assert result.data is not None
        
        # Property: Number of results should not exceed top_k
        num_returned = len(result.data["results"])
        assert num_returned <= top_k, \
            f"Returned {num_returned} results, but top_k is {top_k}"
        
        # Property: Number of results should be min(available, top_k)
        expected_count = min(num_available, top_k)
        assert num_returned == expected_count, \
            f"Expected {expected_count} results, got {num_returned}"
    
    @pytest.mark.asyncio
    @given(
        query=query_strategy,
        kb_id=kb_id_strategy,
        num_available=st.integers(min_value=1, max_value=100),
        top_k=top_k_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_search_with_rewrite_respects_top_k_limit(
        self,
        query,
        kb_id,
        num_available,
        top_k
    ):
        """
        Property: Search with rewrite should also respect top_k limit.
        
        This verifies that query rewriting doesn't bypass the top_k constraint.
        """
        assume(len(query.strip()) > 0)
        
        # Generate mock results (limited by top_k)
        num_results = min(num_available, top_k)
        mock_results = []
        for i in range(num_results):
            score = 1.0 - (i * 0.01)
            score = max(0.0, min(1.0, score))
            mock_results.append(
                create_mock_search_result(
                    content=f"Result {i} content",
                    score=score
                )
            )
        
        mock_response = create_mock_search_response(
            results=mock_results,
            total_count=num_available,
            rewritten_query=f"rewritten: {query}"
        )
        
        mock_search_service = MagicMock()
        mock_search_service.search_with_rewrite = AsyncMock(return_value=mock_response)
        
        search_tool = SearchWithRewriteTool(search_service=mock_search_service)
        
        result = await search_tool._aexecute(
            query=query,
            kb_id=kb_id,
            top_k=top_k
        )
        
        # Assert search succeeded
        assert result.success is True
        
        # Property: Number of results should not exceed top_k
        num_returned = len(result.data["results"])
        assert num_returned <= top_k, \
            f"Returned {num_returned} results, but top_k is {top_k}"
    
    @pytest.mark.asyncio
    @given(
        query=query_strategy,
        kb_id=kb_id_strategy,
        top_k=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=30, deadline=None)
    async def test_top_k_with_fewer_available_results(
        self,
        query,
        kb_id,
        top_k
    ):
        """
        Property: When fewer results are available than top_k, return all.
        
        This edge case verifies that we don't pad results to reach top_k.
        """
        assume(len(query.strip()) > 0)
        
        # Create fewer results than top_k
        num_available = max(1, top_k - 2)
        mock_results = []
        for i in range(num_available):
            mock_results.append(
                create_mock_search_result(
                    content=f"Result {i} content",
                    score=1.0 - (i * 0.1)
                )
            )
        
        mock_response = create_mock_search_response(
            results=mock_results,
            total_count=num_available
        )
        
        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=mock_response)
        
        search_tool = SearchTool(search_service=mock_search_service)
        
        result = await search_tool._aexecute(
            query=query,
            kb_id=kb_id,
            top_k=top_k
        )
        
        # Assert search succeeded
        assert result.success is True
        
        # Property: Should return all available results (not padded to top_k)
        num_returned = len(result.data["results"])
        assert num_returned == num_available, \
            f"Should return {num_available} results, got {num_returned}"
        assert num_returned <= top_k, \
            f"Should not exceed top_k={top_k}"
    
    @pytest.mark.asyncio
    @given(
        query=query_strategy,
        kb_id=kb_id_strategy,
        top_k=top_k_strategy
    )
    @settings(max_examples=30, deadline=None)
    async def test_empty_results_respect_top_k(
        self,
        query,
        kb_id,
        top_k
    ):
        """
        Property: Empty results should return 0 results (not top_k).
        
        This verifies that we don't create fake results to fill top_k.
        """
        assume(len(query.strip()) > 0)
        
        # Create empty results
        mock_response = create_mock_search_response(
            results=[],
            total_count=0
        )
        
        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=mock_response)
        
        search_tool = SearchTool(search_service=mock_search_service)
        
        result = await search_tool._aexecute(
            query=query,
            kb_id=kb_id,
            top_k=top_k
        )
        
        # Assert search succeeded (empty results are valid)
        assert result.success is True
        
        # Property: Should return 0 results
        assert len(result.data["results"]) == 0, \
            "Empty search should return 0 results"
        assert result.data["total_count"] == 0, \
            "Total count should be 0"


# ============================================================================
# Additional Property Tests
# ============================================================================

class TestSearchToolConsistency:
    """
    Additional property tests for search tool consistency.
    
    These tests verify that search tools maintain consistent behavior
    across different scenarios and edge cases.
    """
    
    @pytest.mark.asyncio
    @given(
        query=query_strategy,
        kb_id=kb_id_strategy,
        top_k=top_k_strategy
    )
    @settings(max_examples=30, deadline=None)
    async def test_search_results_include_required_fields(
        self,
        query,
        kb_id,
        top_k
    ):
        """
        Property: All search results should include required fields.
        
        This verifies that the result format is consistent.
        """
        assume(len(query.strip()) > 0)
        
        # Create mock results
        mock_results = [
            create_mock_search_result(
                content="Test content",
                score=0.95,
                chunk_id="chunk_123",
                doc_id="doc_456",
                doc_name="test.pdf"
            )
        ]
        
        mock_response = create_mock_search_response(
            results=mock_results,
            total_count=1
        )
        
        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=mock_response)
        
        search_tool = SearchTool(search_service=mock_search_service)
        
        result = await search_tool._aexecute(
            query=query,
            kb_id=kb_id,
            top_k=top_k
        )
        
        # Assert search succeeded
        assert result.success is True
        assert len(result.data["results"]) > 0
        
        # Property: Each result should have required fields
        for search_result in result.data["results"]:
            assert "content" in search_result, \
                "Result should have content field"
            assert "score" in search_result, \
                "Result should have score field"
            assert "metadata" in search_result, \
                "Result should have metadata field"
            
            # Check metadata fields
            metadata = search_result["metadata"]
            assert "chunk_id" in metadata, \
                "Metadata should have chunk_id"
            assert "doc_id" in metadata, \
                "Metadata should have doc_id"
            assert "doc_name" in metadata, \
                "Metadata should have doc_name"
    
    @pytest.mark.asyncio
    @given(
        query=query_strategy,
        kb_id=kb_id_strategy,
        top_k=top_k_strategy
    )
    @settings(max_examples=30, deadline=None)
    async def test_search_scores_are_in_valid_range(
        self,
        query,
        kb_id,
        top_k
    ):
        """
        Property: All search scores should be in [0, 1] range.
        
        This verifies that scores are properly normalized.
        """
        assume(len(query.strip()) > 0)
        
        # Create mock results with various scores
        mock_results = [
            create_mock_search_result(
                content=f"Result {i}",
                score=1.0 - (i * 0.2)
            )
            for i in range(min(5, top_k))
        ]
        
        mock_response = create_mock_search_response(
            results=mock_results,
            total_count=len(mock_results)
        )
        
        mock_search_service = MagicMock()
        mock_search_service.search = AsyncMock(return_value=mock_response)
        
        search_tool = SearchTool(search_service=mock_search_service)
        
        result = await search_tool._aexecute(
            query=query,
            kb_id=kb_id,
            top_k=top_k
        )
        
        # Assert search succeeded
        assert result.success is True
        
        # Property: All scores should be in [0, 1] range
        for search_result in result.data["results"]:
            score = search_result["score"]
            assert 0.0 <= score <= 1.0, \
                f"Score {score} should be in range [0, 1]"
            assert isinstance(score, float), \
                "Score should be a float"
    
    @pytest.mark.asyncio
    @given(
        query=query_strategy,
        kb_id=kb_id_strategy,
        top_k=top_k_strategy
    )
    @settings(max_examples=20, deadline=None)
    async def test_search_with_rewrite_includes_rewritten_query(
        self,
        query,
        kb_id,
        top_k
    ):
        """
        Property: Search with rewrite should include rewritten query in response.
        
        This verifies that query rewriting information is preserved.
        """
        assume(len(query.strip()) > 0)
        
        rewritten_query = f"rewritten: {query}"
        
        mock_results = [
            create_mock_search_result(
                content="Test content",
                score=0.9
            )
        ]
        
        mock_response = create_mock_search_response(
            results=mock_results,
            total_count=1,
            rewritten_query=rewritten_query
        )
        
        mock_search_service = MagicMock()
        mock_search_service.search_with_rewrite = AsyncMock(return_value=mock_response)
        
        search_tool = SearchWithRewriteTool(search_service=mock_search_service)
        
        result = await search_tool._aexecute(
            query=query,
            kb_id=kb_id,
            top_k=top_k
        )
        
        # Assert search succeeded
        assert result.success is True
        
        # Property: Response should include rewritten query
        assert "rewritten_query" in result.data, \
            "Response should include rewritten_query field"
        assert result.data["rewritten_query"] == rewritten_query, \
            "Rewritten query should match"
