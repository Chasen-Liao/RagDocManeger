"""Tests for query rewriter."""

import pytest
from RagDocMan.rag.query_rewriter import QueryRewriter, QueryRewriteResult


class TestQueryRewriter:
    """Test query rewriter."""

    def test_init_without_provider(self):
        """Test initialization without provider."""
        rewriter = QueryRewriter()
        assert rewriter.llm_provider is None

    @pytest.mark.asyncio
    async def test_rewrite_query_without_provider(self):
        """Test rewriting query without provider."""
        rewriter = QueryRewriter()
        result = await rewriter.rewrite_query("test query")
        assert isinstance(result, QueryRewriteResult)
        assert result.original_query == "test query"
        assert "test query" in result.rewritten_queries

    @pytest.mark.asyncio
    async def test_rewrite_query_with_empty_query(self):
        """Test rewriting with empty query."""
        rewriter = QueryRewriter()
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await rewriter.rewrite_query("")

    @pytest.mark.asyncio
    async def test_rewrite_query_with_whitespace(self):
        """Test rewriting with whitespace query."""
        rewriter = QueryRewriter()
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await rewriter.rewrite_query("   ")

    @pytest.mark.asyncio
    async def test_rewrite_with_fallback(self):
        """Test rewriting with fallback."""
        rewriter = QueryRewriter()
        result = await rewriter.rewrite_with_fallback("test query")
        assert isinstance(result, QueryRewriteResult)
        assert result.original_query == "test query"
        assert "test query" in result.rewritten_queries
