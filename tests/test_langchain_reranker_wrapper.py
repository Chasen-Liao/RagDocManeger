"""Tests for LangChain Reranker wrapper."""

import pytest
from unittest.mock import AsyncMock, Mock
from RagDocMan.core.langchain_reranker_wrapper import LangChainRerankerWrapper
from RagDocMan.core.reranker_provider import SiliconFlowRerankerProvider


class MockRerankerProvider:
    """Mock reranker provider for testing."""

    def __init__(self, results=None):
        """
        Initialize mock provider.
        
        Args:
            results: List of (index, score) tuples to return
        """
        self.results = results or [(0, 0.9), (1, 0.7), (2, 0.5)]
        self.rerank_called = False
        self.validate_called = False

    async def rerank(
        self, query: str, candidates: list[str], top_k: int = 5
    ) -> list[tuple[int, float]]:
        """Mock rerank method."""
        self.rerank_called = True
        return self.results[:top_k]

    async def validate_connection(self) -> bool:
        """Mock validate connection method."""
        self.validate_called = True
        return True


class TestLangChainRerankerWrapperInit:
    """Test reranker wrapper initialization."""

    def test_init_with_provider(self):
        """Test wrapper initialization with provider."""
        provider = MockRerankerProvider()
        wrapper = LangChainRerankerWrapper(
            reranker_provider=provider,
            model_name="test-model"
        )
        
        assert wrapper.reranker_provider == provider
        assert wrapper.model_name == "test-model"
        assert wrapper.normalize_scores is True
        assert wrapper.fallback_enabled is True

    def test_init_without_provider(self):
        """Test wrapper initialization without provider."""
        wrapper = LangChainRerankerWrapper()
        
        assert wrapper.reranker_provider is None
        assert wrapper.model_name == "custom"
        assert wrapper.normalize_scores is True
        assert wrapper.fallback_enabled is True

    def test_init_with_custom_settings(self):
        """Test wrapper initialization with custom settings."""
        provider = MockRerankerProvider()
        wrapper = LangChainRerankerWrapper(
            reranker_provider=provider,
            model_name="custom-model",
            normalize_scores=False,
            fallback_enabled=False
        )
        
        assert wrapper.normalize_scores is False
        assert wrapper.fallback_enabled is False

    def test_identifying_params(self):
        """Test _identifying_params property."""
        provider = MockRerankerProvider()
        wrapper = LangChainRerankerWrapper(
            reranker_provider=provider,
            model_name="test-model"
        )
        
        params = wrapper._identifying_params
        assert params["model_name"] == "test-model"
        assert params["normalize_scores"] is True
        assert params["fallback_enabled"] is True
        assert params["has_provider"] is True

    def test_identifying_params_without_provider(self):
        """Test _identifying_params without provider."""
        wrapper = LangChainRerankerWrapper()
        
        params = wrapper._identifying_params
        assert params["has_provider"] is False


class TestLangChainRerankerWrapperNormalization:
    """Test score normalization functionality."""

    def test_normalize_scores_basic(self):
        """Test basic score normalization."""
        wrapper = LangChainRerankerWrapper()
        
        results = [(0, 10.0), (1, 5.0), (2, 0.0)]
        normalized = wrapper._normalize_scores(results)
        
        assert normalized[0] == (0, 1.0)  # Max score -> 1.0
        assert normalized[1] == (1, 0.5)  # Mid score -> 0.5
        assert normalized[2] == (2, 0.0)  # Min score -> 0.0

    def test_normalize_scores_negative(self):
        """Test normalization with negative scores."""
        wrapper = LangChainRerankerWrapper()
        
        results = [(0, 5.0), (1, 0.0), (2, -5.0)]
        normalized = wrapper._normalize_scores(results)
        
        assert normalized[0] == (0, 1.0)
        assert normalized[1] == (1, 0.5)
        assert normalized[2] == (2, 0.0)

    def test_normalize_scores_same_values(self):
        """Test normalization when all scores are the same."""
        wrapper = LangChainRerankerWrapper()
        
        results = [(0, 5.0), (1, 5.0), (2, 5.0)]
        normalized = wrapper._normalize_scores(results)
        
        # All scores should be 0.5 when they're identical
        assert all(score == 0.5 for _, score in normalized)

    def test_normalize_scores_empty(self):
        """Test normalization with empty results."""
        wrapper = LangChainRerankerWrapper()
        
        results = []
        normalized = wrapper._normalize_scores(results)
        
        assert normalized == []

    def test_normalize_scores_single_result(self):
        """Test normalization with single result."""
        wrapper = LangChainRerankerWrapper()
        
        results = [(0, 10.0)]
        normalized = wrapper._normalize_scores(results)
        
        assert normalized[0] == (0, 0.5)


class TestLangChainRerankerWrapperAsyncRerank:
    """Test asynchronous reranking functionality."""

    @pytest.mark.asyncio
    async def test_rerank_basic(self):
        """Test basic asynchronous reranking."""
        provider = MockRerankerProvider(
            results=[(2, 0.9), (0, 0.7), (1, 0.5)]
        )
        wrapper = LangChainRerankerWrapper(reranker_provider=provider)
        
        query = "test query"
        candidates = ["doc1", "doc2", "doc3"]
        results = await wrapper.rerank(query, candidates, top_k=3)
        
        assert provider.rerank_called
        assert len(results) == 3
        # Scores should be normalized to 0-1 range
        assert all(0.0 <= score <= 1.0 for _, score in results)

    @pytest.mark.asyncio
    async def test_rerank_with_normalization(self):
        """Test reranking with score normalization."""
        provider = MockRerankerProvider(
            results=[(0, 100.0), (1, 50.0), (2, 0.0)]
        )
        wrapper = LangChainRerankerWrapper(
            reranker_provider=provider,
            normalize_scores=True
        )
        
        results = await wrapper.rerank("query", ["doc1", "doc2", "doc3"], top_k=3)
        
        # Check normalization
        assert results[0][1] == 1.0  # Max score
        assert results[1][1] == 0.5  # Mid score
        assert results[2][1] == 0.0  # Min score

    @pytest.mark.asyncio
    async def test_rerank_without_normalization(self):
        """Test reranking without score normalization."""
        provider = MockRerankerProvider(
            results=[(0, 100.0), (1, 50.0), (2, 0.0)]
        )
        wrapper = LangChainRerankerWrapper(
            reranker_provider=provider,
            normalize_scores=False
        )
        
        results = await wrapper.rerank("query", ["doc1", "doc2", "doc3"], top_k=3)
        
        # Scores should not be normalized
        assert results[0][1] == 100.0
        assert results[1][1] == 50.0
        assert results[2][1] == 0.0

    @pytest.mark.asyncio
    async def test_rerank_top_k_limit(self):
        """Test reranking with top_k limit."""
        provider = MockRerankerProvider(
            results=[(0, 0.9), (1, 0.8), (2, 0.7), (3, 0.6), (4, 0.5)]
        )
        wrapper = LangChainRerankerWrapper(reranker_provider=provider)
        
        results = await wrapper.rerank("query", ["doc1", "doc2", "doc3", "doc4", "doc5"], top_k=3)
        
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_rerank_empty_query_error(self):
        """Test reranking with empty query raises error."""
        provider = MockRerankerProvider()
        wrapper = LangChainRerankerWrapper(reranker_provider=provider)
        
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await wrapper.rerank("", ["doc1", "doc2"])

    @pytest.mark.asyncio
    async def test_rerank_empty_candidates_error(self):
        """Test reranking with empty candidates raises error."""
        provider = MockRerankerProvider()
        wrapper = LangChainRerankerWrapper(reranker_provider=provider)
        
        with pytest.raises(ValueError, match="Candidates list cannot be empty"):
            await wrapper.rerank("query", [])


class TestLangChainRerankerWrapperFallback:
    """Test fallback mechanism."""

    @pytest.mark.asyncio
    async def test_fallback_no_provider(self):
        """Test fallback when no provider is set."""
        wrapper = LangChainRerankerWrapper(
            reranker_provider=None,
            fallback_enabled=True
        )
        
        results = await wrapper.rerank("query", ["doc1", "doc2", "doc3"], top_k=3)
        
        # Should return original order with decreasing scores
        assert len(results) == 3
        assert results[0][0] == 0
        assert results[1][0] == 1
        assert results[2][0] == 2
        # Scores should be in decreasing order
        assert results[0][1] > results[1][1] > results[2][1]

    @pytest.mark.asyncio
    async def test_fallback_provider_error(self):
        """Test fallback when provider raises error."""
        provider = MockRerankerProvider()
        provider.rerank = AsyncMock(side_effect=Exception("API error"))
        
        wrapper = LangChainRerankerWrapper(
            reranker_provider=provider,
            fallback_enabled=True
        )
        
        results = await wrapper.rerank("query", ["doc1", "doc2", "doc3"], top_k=3)
        
        # Should return fallback results
        assert len(results) == 3
        assert results[0][0] == 0

    @pytest.mark.asyncio
    async def test_no_fallback_no_provider_error(self):
        """Test error when no provider and fallback disabled."""
        wrapper = LangChainRerankerWrapper(
            reranker_provider=None,
            fallback_enabled=False
        )
        
        with pytest.raises(ValueError, match="Reranker provider is not set"):
            await wrapper.rerank("query", ["doc1", "doc2"])

    @pytest.mark.asyncio
    async def test_no_fallback_provider_error(self):
        """Test error propagation when fallback disabled."""
        provider = MockRerankerProvider()
        provider.rerank = AsyncMock(side_effect=Exception("API error"))
        
        wrapper = LangChainRerankerWrapper(
            reranker_provider=provider,
            fallback_enabled=False
        )
        
        with pytest.raises(Exception, match="API error"):
            await wrapper.rerank("query", ["doc1", "doc2"])

    def test_fallback_ranking_basic(self):
        """Test fallback ranking method."""
        wrapper = LangChainRerankerWrapper()
        
        results = wrapper._fallback_ranking(["doc1", "doc2", "doc3"], top_k=3)
        
        assert len(results) == 3
        assert results[0] == (0, 1.0)
        assert results[1] == (1, 0.5)
        assert results[2] == (2, 0.0)

    def test_fallback_ranking_single_result(self):
        """Test fallback ranking with single result."""
        wrapper = LangChainRerankerWrapper()
        
        results = wrapper._fallback_ranking(["doc1"], top_k=1)
        
        assert len(results) == 1
        assert results[0] == (0, 1.0)

    def test_fallback_ranking_top_k_limit(self):
        """Test fallback ranking respects top_k."""
        wrapper = LangChainRerankerWrapper()
        
        results = wrapper._fallback_ranking(["doc1", "doc2", "doc3", "doc4", "doc5"], top_k=3)
        
        assert len(results) == 3


class TestLangChainRerankerWrapperSyncRerank:
    """Test synchronous reranking functionality."""

    def test_rerank_sync_basic(self):
        """Test basic synchronous reranking."""
        provider = MockRerankerProvider(
            results=[(2, 0.9), (0, 0.7), (1, 0.5)]
        )
        wrapper = LangChainRerankerWrapper(reranker_provider=provider)
        
        results = wrapper.rerank_sync("query", ["doc1", "doc2", "doc3"], top_k=3)
        
        assert provider.rerank_called
        assert len(results) == 3

    def test_rerank_sync_with_fallback(self):
        """Test synchronous reranking with fallback."""
        wrapper = LangChainRerankerWrapper(
            reranker_provider=None,
            fallback_enabled=True
        )
        
        results = wrapper.rerank_sync("query", ["doc1", "doc2", "doc3"], top_k=3)
        
        assert len(results) == 3
        assert results[0][0] == 0

    def test_rerank_sync_error(self):
        """Test synchronous reranking error handling."""
        provider = MockRerankerProvider()
        provider.rerank = AsyncMock(side_effect=Exception("API error"))
        
        wrapper = LangChainRerankerWrapper(
            reranker_provider=provider,
            fallback_enabled=False
        )
        
        with pytest.raises(Exception, match="API error"):
            wrapper.rerank_sync("query", ["doc1", "doc2"])


class TestLangChainRerankerWrapperValidation:
    """Test connection validation functionality."""

    @pytest.mark.asyncio
    async def test_validate_connection_with_provider(self):
        """Test connection validation with provider."""
        provider = MockRerankerProvider()
        wrapper = LangChainRerankerWrapper(reranker_provider=provider)
        
        is_valid = await wrapper.validate_connection()
        
        assert is_valid is True
        assert provider.validate_called

    @pytest.mark.asyncio
    async def test_validate_connection_no_provider_with_fallback(self):
        """Test validation without provider but with fallback."""
        wrapper = LangChainRerankerWrapper(
            reranker_provider=None,
            fallback_enabled=True
        )
        
        is_valid = await wrapper.validate_connection()
        
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_connection_no_provider_no_fallback(self):
        """Test validation without provider and without fallback."""
        wrapper = LangChainRerankerWrapper(
            reranker_provider=None,
            fallback_enabled=False
        )
        
        is_valid = await wrapper.validate_connection()
        
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_connection_provider_fails(self):
        """Test validation when provider validation fails."""
        provider = MockRerankerProvider()
        provider.validate_connection = AsyncMock(return_value=False)
        
        wrapper = LangChainRerankerWrapper(reranker_provider=provider)
        
        is_valid = await wrapper.validate_connection()
        
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_connection_provider_error_with_fallback(self):
        """Test validation when provider raises error with fallback."""
        provider = MockRerankerProvider()
        provider.validate_connection = AsyncMock(side_effect=Exception("Connection error"))
        
        wrapper = LangChainRerankerWrapper(
            reranker_provider=provider,
            fallback_enabled=True
        )
        
        is_valid = await wrapper.validate_connection()
        
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_connection_provider_error_no_fallback(self):
        """Test validation when provider raises error without fallback."""
        provider = MockRerankerProvider()
        provider.validate_connection = AsyncMock(side_effect=Exception("Connection error"))
        
        wrapper = LangChainRerankerWrapper(
            reranker_provider=provider,
            fallback_enabled=False
        )
        
        is_valid = await wrapper.validate_connection()
        
        assert is_valid is False


class TestLangChainRerankerWrapperWithRealProvider:
    """Test wrapper with real reranker providers."""

    def test_with_siliconflow_provider(self):
        """Test wrapper with SiliconFlow provider."""
        provider = SiliconFlowRerankerProvider(
            api_key="test-api-key",
            model="BAAI/bge-reranker-base"
        )
        wrapper = LangChainRerankerWrapper(
            reranker_provider=provider,
            model_name="siliconflow"
        )
        
        assert wrapper.reranker_provider == provider
        assert wrapper.model_name == "siliconflow"

    @pytest.mark.asyncio
    async def test_rerank_with_siliconflow_invalid_key(self):
        """Test reranking with SiliconFlow provider (will fail with invalid key)."""
        provider = SiliconFlowRerankerProvider(
            api_key="invalid-key",
            model="BAAI/bge-reranker-base"
        )
        wrapper = LangChainRerankerWrapper(
            reranker_provider=provider,
            fallback_enabled=True
        )
        
        # Should fall back to original order
        results = await wrapper.rerank("query", ["doc1", "doc2", "doc3"], top_k=3)
        
        assert len(results) == 3
        # Should be fallback results
        assert results[0][0] == 0
        
        # Clean up
        await provider.close()


class TestLangChainRerankerWrapperEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_rerank_with_whitespace_query(self):
        """Test reranking with whitespace-only query."""
        provider = MockRerankerProvider()
        wrapper = LangChainRerankerWrapper(reranker_provider=provider)
        
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await wrapper.rerank("   ", ["doc1", "doc2"])

    @pytest.mark.asyncio
    async def test_rerank_with_special_characters(self):
        """Test reranking with special characters."""
        provider = MockRerankerProvider()
        wrapper = LangChainRerankerWrapper(reranker_provider=provider)
        
        query = "Test with 特殊字符 and émojis 🎉"
        candidates = ["文档1", "Document 2", "Doc 🚀"]
        results = await wrapper.rerank(query, candidates, top_k=3)
        
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_rerank_with_very_long_candidates(self):
        """Test reranking with very long candidate texts."""
        provider = MockRerankerProvider()
        wrapper = LangChainRerankerWrapper(reranker_provider=provider)
        
        long_text = "test " * 1000
        candidates = [long_text, long_text, long_text]
        results = await wrapper.rerank("query", candidates, top_k=3)
        
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_rerank_with_many_candidates(self):
        """Test reranking with many candidates."""
        provider = MockRerankerProvider(
            results=[(i, 1.0 - i * 0.01) for i in range(100)]
        )
        wrapper = LangChainRerankerWrapper(reranker_provider=provider)
        
        candidates = [f"doc{i}" for i in range(100)]
        results = await wrapper.rerank("query", candidates, top_k=10)
        
        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_rerank_top_k_larger_than_candidates(self):
        """Test reranking when top_k is larger than number of candidates."""
        provider = MockRerankerProvider(
            results=[(0, 0.9), (1, 0.7)]
        )
        wrapper = LangChainRerankerWrapper(reranker_provider=provider)
        
        results = await wrapper.rerank("query", ["doc1", "doc2"], top_k=10)
        
        # Should return only available results
        assert len(results) == 2
