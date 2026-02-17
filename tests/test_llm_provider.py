"""Tests for LLM provider factory."""

import pytest
from RagDocMan.core.llm_provider import LLMProviderFactory, SiliconFlowProvider


class TestLLMProviderFactory:
    """Test LLM provider factory."""

    def test_create_siliconflow_provider(self):
        """Test creating Silicon Flow provider."""
        provider = LLMProviderFactory.create_provider(
            "siliconflow", "test-api-key"
        )
        assert isinstance(provider, SiliconFlowProvider)
        assert provider.api_key == "test-api-key"

    def test_create_provider_with_custom_model(self):
        """Test creating provider with custom model."""
        provider = LLMProviderFactory.create_provider(
            "siliconflow", "test-api-key", model="custom-model"
        )
        assert provider.model == "custom-model"

    def test_create_provider_with_custom_temperature(self):
        """Test creating provider with custom temperature."""
        provider = LLMProviderFactory.create_provider(
            "siliconflow", "test-api-key", temperature=0.5
        )
        assert provider.temperature == 0.5

    def test_create_provider_unsupported_type(self):
        """Test creating provider with unsupported type."""
        with pytest.raises(ValueError, match="Unsupported provider type"):
            LLMProviderFactory.create_provider("unsupported", "test-api-key")

    def test_create_provider_empty_api_key(self):
        """Test creating provider with empty API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            LLMProviderFactory.create_provider("siliconflow", "")

    def test_create_provider_whitespace_api_key(self):
        """Test creating provider with whitespace API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            LLMProviderFactory.create_provider("siliconflow", "   ")

    def test_get_supported_providers(self):
        """Test getting supported providers."""
        providers = LLMProviderFactory.get_supported_providers()
        assert "siliconflow" in providers
        assert isinstance(providers, list)


class TestSiliconFlowProvider:
    """Test Silicon Flow provider."""

    def test_init_with_valid_api_key(self):
        """Test initialization with valid API key."""
        provider = SiliconFlowProvider("test-api-key")
        assert provider.api_key == "test-api-key"
        assert provider.model == SiliconFlowProvider.DEFAULT_MODEL

    def test_init_with_empty_api_key(self):
        """Test initialization with empty API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            SiliconFlowProvider("")

    def test_init_with_whitespace_api_key(self):
        """Test initialization with whitespace API key."""
        with pytest.raises(ValueError, match="API key cannot be empty"):
            SiliconFlowProvider("   ")

    def test_init_with_custom_parameters(self):
        """Test initialization with custom parameters."""
        provider = SiliconFlowProvider(
            "test-api-key",
            model="custom-model",
            temperature=0.5,
            max_tokens=1024,
            timeout=60,
        )
        assert provider.model == "custom-model"
        assert provider.temperature == 0.5
        assert provider.max_tokens == 1024
        assert provider.timeout == 60

    def test_default_model(self):
        """Test default model is set."""
        provider = SiliconFlowProvider("test-api-key")
        assert provider.model == "Qwen/Qwen2-7B-Instruct"

    def test_default_temperature(self):
        """Test default temperature is set."""
        provider = SiliconFlowProvider("test-api-key")
        assert provider.temperature == 0.7

    def test_default_max_tokens(self):
        """Test default max tokens is set."""
        provider = SiliconFlowProvider("test-api-key")
        assert provider.max_tokens == 2048

    def test_default_timeout(self):
        """Test default timeout is set."""
        provider = SiliconFlowProvider("test-api-key")
        assert provider.timeout == 30


class TestSiliconFlowProviderValidation:
    """Test Silicon Flow provider validation."""

    @pytest.mark.asyncio
    async def test_generate_with_empty_prompt(self):
        """Test generate with empty prompt."""
        provider = SiliconFlowProvider("test-api-key")
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            await provider.generate("")

    @pytest.mark.asyncio
    async def test_generate_with_whitespace_prompt(self):
        """Test generate with whitespace prompt."""
        provider = SiliconFlowProvider("test-api-key")
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            await provider.generate("   ")

    @pytest.mark.asyncio
    async def test_generate_with_valid_prompt(self):
        """Test generate with valid prompt (will fail due to invalid API key)."""
        provider = SiliconFlowProvider("test-api-key")
        try:
            # This will fail due to invalid API key, but we're testing the prompt validation
            await provider.generate("test prompt")
        except Exception as e:
            # Expected to fail with API error
            assert "API error" in str(e) or "Request" in str(e)
        finally:
            await provider.close()

    @pytest.mark.asyncio
    async def test_validate_connection_with_invalid_key(self):
        """Test validate connection with invalid API key."""
        provider = SiliconFlowProvider("invalid-api-key")
        result = await provider.validate_connection()
        assert result is False
        await provider.close()

    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test closing the client."""
        provider = SiliconFlowProvider("test-api-key")
        await provider.close()
        # Should not raise any error
        assert True
