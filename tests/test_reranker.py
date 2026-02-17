"""Tests for reranker."""

import pytest
from RagDocMan.rag.reranker import Reranker
from RagDocMan.rag.retriever import RetrievalResult


class TestReranker:
    """Test reranker."""

    def test_init_without_provider(self):
        """Test initialization without provider."""
        reranker = Reranker()
        assert reranker.reranker_provider is None

    @pytest.mark.asyncio
    async def test_rerank_without_provider(self):
        """Test reranking without provider."""
        reranker = Reranker()
        candidates = [
            RetrievalResult(
                chunk_id="1",
                doc_id="doc1",
                content="test",
                score=0.9,
                doc_name="Doc1",
            )
        ]
        results = await reranker.rerank("query", candidates)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_rerank_with_empty_query(self):
        """Test reranking with empty query."""
        reranker = Reranker()
        candidates = [
            RetrievalResult(
                chunk_id="1",
                doc_id="doc1",
                content="test",
                score=0.9,
                doc_name="Doc1",
            )
        ]
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await reranker.rerank("", candidates)

    @pytest.mark.asyncio
    async def test_rerank_with_empty_candidates(self):
        """Test reranking with empty candidates."""
        reranker = Reranker()
        with pytest.raises(ValueError, match="Candidates list cannot be empty"):
            await reranker.rerank("query", [])

    @pytest.mark.asyncio
    async def test_rerank_with_fallback(self):
        """Test reranking with fallback."""
        reranker = Reranker()
        candidates = [
            RetrievalResult(
                chunk_id="1",
                doc_id="doc1",
                content="test",
                score=0.9,
                doc_name="Doc1",
            )
        ]
        results = await reranker.rerank_with_fallback("query", candidates)
        assert len(results) == 1
