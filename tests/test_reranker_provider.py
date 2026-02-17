"""Tests for reranker provider factory."""

import pytest
from RagDocMan.core.reranker_provider import (
    RerankerProviderFactory,
    SiliconFlowRerankerProvider,
)


class TestRerankerProviderFactory:
    """Test reranker provider factory."""

    def test_create_siliconflow_provider(self):
        """Test creating Silicon Flow reranker provider."""
        provider = RerankerProviderFactory.create_provider(
            "siliconflow", "test-api-key"
        )
        assert isinstance(provider, SiliconFlowRerankerProvider)
        assert provider.api_key == "test-api-key"

    def test_create_provider_with_custom_model(self):
        """Test creating provider with custom model."""
        provider = RerankerProviderFactory.create_provider(
            "siliconflow", "test-api-key", model="custom-model"
        )
        assert provider.model == "custom-model"

    def test_create_provider_unsupported_type(self):
        """Test creating provider with unsupported type."""
        with pytest.raises(ValueError, match="Unsupported provider type"):
            RerankerProviderFactory.create_provider("unsupported", "test-api-key")

    def test_create_provider_empty_api_key(self):
        """Test creating provider with empty API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            RerankerProviderFactory.create_provider("siliconflow", "")

    def test_get_supported_providers(self):
        """Test getting supported providers."""
        providers = RerankerProviderFactory.get_supported_providers()
        assert "siliconflow" in providers
        assert isinstance(providers, list)


class TestSiliconFlowRerankerProvider:
    """Test Silicon Flow reranker provider."""

    def test_init_with_valid_api_key(self):
        """Test initialization with valid API key."""
        provider = SiliconFlowRerankerProvider("test-api-key")
        assert provider.api_key == "test-api-key"
        assert provider.model == SiliconFlowRerankerProvider.DEFAULT_MODEL

    def test_init_with_empty_api_key(self):
        """Test initialization with empty API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            SiliconFlowRerankerProvider("")

    def test_init_with_custom_parameters(self):
        """Test initialization with custom parameters."""
        provider = SiliconFlowRerankerProvider(
            "test-api-key", model="custom-model", timeout=60
        )
        assert provider.model == "custom-model"
        assert provider.timeout == 60

    def test_default_model(self):
        """Test default model is set."""
        provider = SiliconFlowRerankerProvider("test-api-key")
        assert provider.model == "BAAI/bge-reranker-large"

    def test_default_timeout(self):
        """Test default timeout is set."""
        provider = SiliconFlowRerankerProvider("test-api-key")
        assert provider.timeout == 30


class TestSiliconFlowRerankerProviderValidation:
    """Test Silicon Flow reranker provider validation."""

    @pytest.mark.asyncio
    async def test_rerank_with_empty_query(self):
        """Test rerank with empty query."""
        provider = SiliconFlowRerankerProvider("test-api-key")
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await provider.rerank("", ["candidate 1", "candidate 2"])

    @pytest.mark.asyncio
    async def test_rerank_with_whitespace_query(self):
        """Test rerank with whitespace query."""
        provider = SiliconFlowRerankerProvider("test-api-key")
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await provider.rerank("   ", ["candidate 1", "candidate 2"])

    @pytest.mark.asyncio
    async def test_rerank_with_empty_candidates(self):
        """Test rerank with empty candidates list."""
        provider = SiliconFlowRerankerProvider("test-api-key")
        with pytest.raises(ValueError, match="Candidates list cannot be empty"):
            await provider.rerank("query", [])

    @pytest.mark.asyncio
    async def test_rerank_with_all_empty_candidates(self):
        """Test rerank with all empty candidates."""
        provider = SiliconFlowRerankerProvider("test-api-key")
        with pytest.raises(ValueError, match="All candidates are empty"):
            await provider.rerank("query", ["", "   ", "\n"])

    @pytest.mark.asyncio
    async def test_rerank_with_valid_inputs(self):
        """Test rerank with valid inputs (will fail due to invalid API key)."""
        provider = SiliconFlowRerankerProvider("test-api-key")
        try:
            await provider.rerank("query", ["candidate 1", "candidate 2"])
        except Exception as e:
            # Expected to fail with API error
            assert "API error" in str(e) or "Request" in str(e)
        finally:
            await provider.close()

    @pytest.mark.asyncio
    async def test_rerank_with_custom_top_k(self):
        """Test rerank with custom top_k (will fail due to invalid API key)."""
        provider = SiliconFlowRerankerProvider("test-api-key")
        try:
            await provider.rerank(
                "query", ["candidate 1", "candidate 2", "candidate 3"], top_k=2
            )
        except Exception as e:
            # Expected to fail with API error
            assert "API error" in str(e) or "Request" in str(e)
        finally:
            await provider.close()

    @pytest.mark.asyncio
    async def test_validate_connection_with_invalid_key(self):
        """Test validate connection with invalid API key."""
        provider = SiliconFlowRerankerProvider("invalid-api-key")
        result = await provider.validate_connection()
        assert result is False
        await provider.close()

    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test closing the client."""
        provider = SiliconFlowRerankerProvider("test-api-key")
        await provider.close()
        # Should not raise any error
        assert True
