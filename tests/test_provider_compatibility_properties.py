"""Property-based tests for provider compatibility.

This module contains property-based tests using Hypothesis to verify that
the LangChain 1.x provider wrappers maintain correctness properties across
different inputs.

**Validates: Requirements 2.2, 2.3, 3.4, 4.3**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import AsyncMock
from RagDocMan.core.langchain_llm_wrapper import LangChainLLMWrapper
from RagDocMan.core.langchain_embedding_wrapper import LangChainEmbeddingWrapper
from RagDocMan.core.langchain_reranker_wrapper import LangChainRerankerWrapper


# Mock providers for testing
class MockLLMProvider:
    """Mock LLM provider for property testing."""

    def __init__(self, response: str = "test response"):
        self.response = response
        self.call_count = 0

    async def generate(self, prompt: str, **kwargs) -> str:
        """Mock generate method that returns consistent output."""
        self.call_count += 1
        # Simulate deterministic behavior for same prompt
        return f"{self.response} (prompt: {prompt[:20]}...)"


class MockEmbeddingProvider:
    """Mock embedding provider for property testing."""

    def __init__(self, dimension: int = 1024):
        self.dimension = dimension

    async def embed_text(self, text: str) -> list[float]:
        """Mock embed_text method."""
        return [0.1] * self.dimension

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Mock embed_texts method."""
        return [[0.1] * self.dimension for _ in texts]

    async def validate_connection(self) -> bool:
        """Mock validate_connection method."""
        return True

    def get_embedding_dimension(self) -> int:
        """Mock get_embedding_dimension method."""
        return self.dimension


class MockRerankerProvider:
    """Mock reranker provider for property testing."""

    def __init__(self):
        pass

    async def rerank(
        self, query: str, candidates: list[str], top_k: int = 5
    ) -> list[tuple[int, float]]:
        """Mock rerank method that returns scores in valid range."""
        # Return results with scores that need normalization
        num_results = min(top_k, len(candidates))
        # Simulate various score ranges to test normalization
        results = [(i, 10.0 - i * 0.5) for i in range(num_results)]
        return results

    async def validate_connection(self) -> bool:
        """Mock validate connection method."""
        return True


# Hypothesis strategies for generating test data
text_strategy = st.text(min_size=1, max_size=100)
prompt_strategy = st.text(min_size=1, max_size=200)
dimension_strategy = st.integers(min_value=128, max_value=2048)
score_strategy = st.floats(min_value=-100.0, max_value=100.0)


class TestLLMOutputConsistency:
    """
    Property 1: LLM Output Consistency
    
    **Validates: Requirements 2.2, 2.3**
    
    Tests that the same prompt produces consistent outputs when called multiple times.
    This verifies that the wrapper correctly handles LLM calls and maintains
    deterministic behavior when the underlying provider is deterministic.
    """

    @pytest.mark.asyncio
    @given(prompt=prompt_strategy)
    @settings(max_examples=50, deadline=None)
    async def test_same_prompt_produces_consistent_output(self, prompt):
        """
        Property: Same prompt should produce semantically similar outputs.
        
        This test verifies that calling the LLM wrapper multiple times with
        the same prompt produces consistent results, assuming a deterministic
        provider.
        """
        assume(len(prompt.strip()) > 0)  # Ensure non-empty prompt
        
        provider = MockLLMProvider(response="consistent response")
        wrapper = LangChainLLMWrapper(provider, model_name="test-model")
        
        # Call the wrapper multiple times with the same prompt
        result1 = await wrapper._acall(prompt)
        result2 = await wrapper._acall(prompt)
        
        # With a deterministic mock provider, results should be identical
        assert result1 == result2, "Same prompt should produce identical output"
        assert provider.call_count == 2, "Provider should be called twice"

    @pytest.mark.asyncio
    @given(prompt=prompt_strategy)
    @settings(max_examples=50, deadline=None)
    async def test_llm_output_is_non_empty(self, prompt):
        """
        Property: LLM output should always be non-empty for non-empty prompts.
        
        This verifies that the wrapper always returns a valid response.
        """
        assume(len(prompt.strip()) > 0)
        
        provider = MockLLMProvider(response="valid response")
        wrapper = LangChainLLMWrapper(provider, model_name="test-model")
        
        result = await wrapper._acall(prompt)
        
        assert result is not None, "Output should not be None"
        assert len(result) > 0, "Output should not be empty"
        assert isinstance(result, str), "Output should be a string"

    @pytest.mark.asyncio
    @given(
        prompt=prompt_strategy,
        temperature=st.floats(min_value=0.0, max_value=2.0, allow_nan=False)
    )
    @settings(max_examples=30, deadline=None)
    async def test_llm_accepts_various_parameters(self, prompt, temperature):
        """
        Property: LLM wrapper should accept and pass through various parameters.
        
        This verifies that the wrapper correctly handles different parameter values.
        """
        assume(len(prompt.strip()) > 0)
        
        provider = MockLLMProvider(response="response with params")
        wrapper = LangChainLLMWrapper(provider, model_name="test-model")
        
        # Should not raise an exception
        result = await wrapper._acall(prompt, temperature=temperature)
        
        assert result is not None
        assert isinstance(result, str)


class TestEmbeddingDimensionConsistency:
    """
    Property 2: Embedding Dimension Consistency
    
    **Validates: Requirement 3.4**
    
    Tests that the same model always produces embeddings with the same dimension.
    This is critical for vector store compatibility and ensures that embeddings
    can be consistently stored and retrieved.
    """

    @pytest.mark.asyncio
    @given(
        text=text_strategy,
        dimension=dimension_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_embedding_dimension_is_consistent(self, text, dimension):
        """
        Property: Same model always produces same dimension.
        
        This test verifies that embeddings from the same model always have
        the same dimensionality, regardless of input text.
        """
        assume(len(text.strip()) > 0)
        
        provider = MockEmbeddingProvider(dimension=dimension)
        wrapper = LangChainEmbeddingWrapper(
            embedding_provider=provider,
            model_name="test-model"
        )
        
        # Get embedding
        embedding = await wrapper.aembed_query(text)
        
        # Verify dimension matches expected
        assert len(embedding) == dimension, \
            f"Embedding dimension {len(embedding)} should match model dimension {dimension}"
        
        # Verify dimension is consistent with wrapper's reported dimension
        assert len(embedding) == wrapper.get_embedding_dimension(), \
            "Embedding dimension should match wrapper's reported dimension"

    @pytest.mark.asyncio
    @given(
        texts=st.lists(text_strategy, min_size=1, max_size=10),
        dimension=dimension_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_all_document_embeddings_have_same_dimension(self, texts, dimension):
        """
        Property: All embeddings in a batch have the same dimension.
        
        This verifies that batch embedding maintains dimension consistency
        across all documents.
        """
        # Filter out empty texts
        texts = [t for t in texts if len(t.strip()) > 0]
        assume(len(texts) > 0)
        
        provider = MockEmbeddingProvider(dimension=dimension)
        wrapper = LangChainEmbeddingWrapper(
            embedding_provider=provider,
            model_name="test-model"
        )
        
        # Get embeddings for multiple documents
        embeddings = await wrapper.aembed_documents(texts)
        
        # Verify all embeddings have the same dimension
        assert len(embeddings) == len(texts), \
            "Should have one embedding per document"
        
        dimensions = [len(emb) for emb in embeddings]
        assert all(d == dimension for d in dimensions), \
            f"All embeddings should have dimension {dimension}"
        
        # Verify first and last have same dimension
        assert len(embeddings[0]) == len(embeddings[-1]), \
            "First and last embeddings should have same dimension"

    @pytest.mark.asyncio
    @given(
        text=text_strategy,
        dimension=dimension_strategy
    )
    @settings(max_examples=30, deadline=None)
    async def test_query_and_document_embeddings_have_same_dimension(self, text, dimension):
        """
        Property: Query and document embeddings have the same dimension.
        
        This is important for similarity search to work correctly.
        """
        assume(len(text.strip()) > 0)
        
        provider = MockEmbeddingProvider(dimension=dimension)
        wrapper = LangChainEmbeddingWrapper(
            embedding_provider=provider,
            model_name="test-model"
        )
        
        # Get query embedding
        query_embedding = await wrapper.aembed_query(text)
        
        # Get document embedding for the same text
        doc_embeddings = await wrapper.aembed_documents([text])
        
        # Both should have the same dimension
        assert len(query_embedding) == len(doc_embeddings[0]), \
            "Query and document embeddings should have same dimension"
        assert len(query_embedding) == dimension, \
            f"Both should have dimension {dimension}"


class TestRerankerScoreRange:
    """
    Property 3: Reranker Score Range
    
    **Validates: Requirement 4.3**
    
    Tests that reranker scores are always normalized to the 0-1 range.
    This ensures consistent score interpretation across different reranker models
    and makes it easier to set thresholds for filtering results.
    """

    @pytest.mark.asyncio
    @given(
        query=text_strategy,
        candidates=st.lists(text_strategy, min_size=1, max_size=20)
    )
    @settings(max_examples=50, deadline=None)
    async def test_reranker_scores_are_in_valid_range(self, query, candidates):
        """
        Property: Reranker scores are always between 0 and 1.
        
        This test verifies that the wrapper correctly normalizes scores
        to the 0-1 range, regardless of the raw scores from the provider.
        """
        assume(len(query.strip()) > 0)
        candidates = [c for c in candidates if len(c.strip()) > 0]
        assume(len(candidates) > 0)
        
        provider = MockRerankerProvider()
        wrapper = LangChainRerankerWrapper(
            reranker_provider=provider,
            model_name="test-model",
            normalize_scores=True  # Enable normalization
        )
        
        # Get reranked results
        results = await wrapper.rerank(query, candidates, top_k=len(candidates))
        
        # Verify all scores are in [0, 1] range
        for idx, score in results:
            assert 0.0 <= score <= 1.0, \
                f"Score {score} should be in range [0, 1]"
            assert isinstance(score, float), \
                "Score should be a float"
            assert isinstance(idx, int), \
                "Index should be an integer"

    @pytest.mark.asyncio
    @given(
        query=text_strategy,
        candidates=st.lists(text_strategy, min_size=2, max_size=10)
    )
    @settings(max_examples=50, deadline=None)
    async def test_reranker_scores_are_sorted_descending(self, query, candidates):
        """
        Property: Reranker results are sorted by score in descending order.
        
        This verifies that the highest scoring results come first.
        """
        assume(len(query.strip()) > 0)
        candidates = [c for c in candidates if len(c.strip()) > 0]
        assume(len(candidates) >= 2)
        
        provider = MockRerankerProvider()
        wrapper = LangChainRerankerWrapper(
            reranker_provider=provider,
            model_name="test-model",
            normalize_scores=True
        )
        
        # Get reranked results
        results = await wrapper.rerank(query, candidates, top_k=len(candidates))
        
        # Verify scores are in descending order
        scores = [score for _, score in results]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], \
                f"Scores should be in descending order: {scores}"

    @pytest.mark.asyncio
    @given(
        query=text_strategy,
        candidates=st.lists(text_strategy, min_size=1, max_size=10),
        top_k=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50, deadline=None)
    async def test_reranker_respects_top_k_limit(self, query, candidates, top_k):
        """
        Property: Reranker returns at most top_k results.
        
        This verifies that the top_k parameter is respected.
        """
        assume(len(query.strip()) > 0)
        candidates = [c for c in candidates if len(c.strip()) > 0]
        assume(len(candidates) > 0)
        
        provider = MockRerankerProvider()
        wrapper = LangChainRerankerWrapper(
            reranker_provider=provider,
            model_name="test-model",
            normalize_scores=True
        )
        
        # Get reranked results
        results = await wrapper.rerank(query, candidates, top_k=top_k)
        
        # Verify result count
        expected_count = min(top_k, len(candidates))
        assert len(results) == expected_count, \
            f"Should return at most {expected_count} results"

    @pytest.mark.asyncio
    @given(
        query=text_strategy,
        candidates=st.lists(text_strategy, min_size=1, max_size=5)
    )
    @settings(max_examples=30, deadline=None)
    async def test_reranker_without_normalization_may_exceed_range(self, query, candidates):
        """
        Property: Without normalization, scores may be outside [0, 1].
        
        This verifies that normalization is actually doing something.
        """
        assume(len(query.strip()) > 0)
        candidates = [c for c in candidates if len(c.strip()) > 0]
        assume(len(candidates) > 0)
        
        provider = MockRerankerProvider()
        wrapper = LangChainRerankerWrapper(
            reranker_provider=provider,
            model_name="test-model",
            normalize_scores=False  # Disable normalization
        )
        
        # Get reranked results
        results = await wrapper.rerank(query, candidates, top_k=len(candidates))
        
        # Without normalization, scores from mock provider will be > 1
        # (MockRerankerProvider returns scores starting from 10.0)
        scores = [score for _, score in results]
        
        # At least one score should be outside [0, 1] range
        # (unless we only have 1 candidate)
        if len(candidates) > 1:
            assert any(score > 1.0 or score < 0.0 for score in scores), \
                "Without normalization, some scores should be outside [0, 1]"


class TestCrossProviderConsistency:
    """
    Additional property tests for cross-provider consistency.
    
    These tests verify that the wrappers maintain consistent behavior
    across different scenarios and edge cases.
    """

    @pytest.mark.asyncio
    @given(
        texts=st.lists(text_strategy, min_size=1, max_size=5),
        batch_size=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=30, deadline=None)
    async def test_embedding_batching_produces_same_results(self, texts, batch_size):
        """
        Property: Batching should not affect embedding results.
        
        This verifies that different batch sizes produce the same embeddings.
        """
        texts = [t for t in texts if len(t.strip()) > 0]
        assume(len(texts) > 0)
        
        dimension = 768
        provider = MockEmbeddingProvider(dimension=dimension)
        
        # Create two wrappers with different batch sizes
        wrapper1 = LangChainEmbeddingWrapper(
            embedding_provider=provider,
            batch_size=1
        )
        wrapper2 = LangChainEmbeddingWrapper(
            embedding_provider=provider,
            batch_size=batch_size
        )
        
        # Get embeddings with both wrappers
        embeddings1 = await wrapper1.aembed_documents(texts)
        embeddings2 = await wrapper2.aembed_documents(texts)
        
        # Results should be identical
        assert len(embeddings1) == len(embeddings2)
        for emb1, emb2 in zip(embeddings1, embeddings2):
            assert emb1 == emb2, \
                "Different batch sizes should produce same embeddings"

    @pytest.mark.asyncio
    @given(
        query=text_strategy,
        candidates=st.lists(text_strategy, min_size=1, max_size=10)
    )
    @settings(max_examples=30, deadline=None)
    async def test_reranker_fallback_maintains_score_range(self, query, candidates):
        """
        Property: Fallback reranking also maintains [0, 1] score range.
        
        This verifies that even without a provider, scores are valid.
        """
        assume(len(query.strip()) > 0)
        candidates = [c for c in candidates if len(c.strip()) > 0]
        assume(len(candidates) > 0)
        
        # Create wrapper without provider (will use fallback)
        wrapper = LangChainRerankerWrapper(
            reranker_provider=None,
            fallback_enabled=True,
            normalize_scores=True
        )
        
        # Get reranked results (will use fallback)
        results = await wrapper.rerank(query, candidates, top_k=len(candidates))
        
        # Verify all scores are in [0, 1] range
        for idx, score in results:
            assert 0.0 <= score <= 1.0, \
                f"Fallback score {score} should be in range [0, 1]"
