"""Tests for embedding provider factory."""

import pytest
from RagDocMan.core.embedding_provider import (
    EmbeddingProviderFactory,
    SiliconFlowEmbeddingProvider,
)


class TestEmbeddingProviderFactory:
    """Test embedding provider factory."""

    def test_create_siliconflow_provider(self):
        """Test creating Silicon Flow embedding provider."""
        provider = EmbeddingProviderFactory.create_provider(
            "siliconflow", "test-api-key"
        )
        assert isinstance(provider, SiliconFlowEmbeddingProvider)
        assert provider.api_key == "test-api-key"

    def test_create_provider_with_custom_model(self):
        """Test creating provider with custom model."""
        provider = EmbeddingProviderFactory.create_provider(
            "siliconflow", "test-api-key", model="BAAI/bge-base-zh-v1.5"
        )
        assert provider.model == "BAAI/bge-base-zh-v1.5"

    def test_create_provider_unsupported_type(self):
        """Test creating provider with unsupported type."""
        with pytest.raises(ValueError, match="Unsupported provider type"):
            EmbeddingProviderFactory.create_provider("unsupported", "test-api-key")

    def test_create_provider_empty_api_key(self):
        """Test creating provider with empty API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            EmbeddingProviderFactory.create_provider("siliconflow", "")

    def test_get_supported_providers(self):
        """Test getting supported providers."""
        providers = EmbeddingProviderFactory.get_supported_providers()
        assert "siliconflow" in providers
        assert isinstance(providers, list)


class TestSiliconFlowEmbeddingProvider:
    """Test Silicon Flow embedding provider."""

    def test_init_with_valid_api_key(self):
        """Test initialization with valid API key."""
        provider = SiliconFlowEmbeddingProvider("test-api-key")
        assert provider.api_key == "test-api-key"
        assert provider.model == SiliconFlowEmbeddingProvider.DEFAULT_MODEL

    def test_init_with_empty_api_key(self):
        """Test initialization with empty API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            SiliconFlowEmbeddingProvider("")

    def test_init_with_unsupported_model(self):
        """Test initialization with unsupported model."""
        with pytest.raises(ValueError, match="Unsupported model"):
            SiliconFlowEmbeddingProvider("test-api-key", model="unsupported-model")

    def test_init_with_supported_models(self):
        """Test initialization with supported models."""
        for model in SiliconFlowEmbeddingProvider.EMBEDDING_DIMENSIONS.keys():
            provider = SiliconFlowEmbeddingProvider("test-api-key", model=model)
            assert provider.model == model

    def test_get_embedding_dimension(self):
        """Test getting embedding dimension."""
        provider = SiliconFlowEmbeddingProvider("test-api-key")
        dim = provider.get_embedding_dimension()
        assert dim == 1024  # Default model dimension

    def test_get_embedding_dimension_for_different_models(self):
        """Test getting embedding dimension for different models."""
        dimensions = {
            "BAAI/bge-large-zh-v1.5": 1024,
            "BAAI/bge-base-zh-v1.5": 768,
            "BAAI/bge-small-zh-v1.5": 512,
        }
        for model, expected_dim in dimensions.items():
            provider = SiliconFlowEmbeddingProvider("test-api-key", model=model)
            assert provider.get_embedding_dimension() == expected_dim


class TestSiliconFlowEmbeddingProviderValidation:
    """Test Silicon Flow embedding provider validation."""

    @pytest.mark.asyncio
    async def test_embed_text_with_empty_text(self):
        """Test embed text with empty text."""
        provider = SiliconFlowEmbeddingProvider("test-api-key")
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await provider.embed_text("")

    @pytest.mark.asyncio
    async def test_embed_text_with_whitespace(self):
        """Test embed text with whitespace."""
        provider = SiliconFlowEmbeddingProvider("test-api-key")
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await provider.embed_text("   ")

    @pytest.mark.asyncio
    async def test_embed_texts_with_empty_list(self):
        """Test embed texts with empty list."""
        provider = SiliconFlowEmbeddingProvider("test-api-key")
        with pytest.raises(ValueError, match="Texts list cannot be empty"):
            await provider.embed_texts([])

    @pytest.mark.asyncio
    async def test_embed_texts_with_all_empty_texts(self):
        """Test embed texts with all empty texts."""
        provider = SiliconFlowEmbeddingProvider("test-api-key")
        with pytest.raises(ValueError, match="All texts are empty"):
            await provider.embed_texts(["", "   ", "\n"])

    @pytest.mark.asyncio
    async def test_embed_text_with_valid_text(self):
        """Test embed text with valid text (will fail due to invalid API key)."""
        provider = SiliconFlowEmbeddingProvider("test-api-key")
        try:
            await provider.embed_text("test text")
        except Exception as e:
            # Expected to fail with API error
            assert "API error" in str(e) or "Request" in str(e)
        finally:
            await provider.close()

    @pytest.mark.asyncio
    async def test_embed_texts_with_valid_texts(self):
        """Test embed texts with valid texts (will fail due to invalid API key)."""
        provider = SiliconFlowEmbeddingProvider("test-api-key")
        try:
            await provider.embed_texts(["text 1", "text 2"])
        except Exception as e:
            # Expected to fail with API error
            assert "API error" in str(e) or "Request" in str(e)
        finally:
            await provider.close()

    @pytest.mark.asyncio
    async def test_validate_connection_with_invalid_key(self):
        """Test validate connection with invalid API key."""
        provider = SiliconFlowEmbeddingProvider("invalid-api-key")
        result = await provider.validate_connection()
        assert result is False
        await provider.close()

    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test closing the client."""
        provider = SiliconFlowEmbeddingProvider("test-api-key")
        await provider.close()
        # Should not raise any error
        assert True
