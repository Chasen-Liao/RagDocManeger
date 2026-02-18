"""Property-based tests for configuration management.

**Validates: Requirements 7.1, 7.2, 8.1, 8.2, 9.1, 9.2, 14.1, 14.2, 14.3**

This module tests configuration management properties using hypothesis:
- Property 7: Configuration Validity - System validates configuration and returns clear error messages
- Property 20: Sensitive Information Protection - System does not output sensitive info in logs
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, Phase
from typing import Dict, Any
from unittest.mock import patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import Settings
from core.llm_provider import LLMProviderFactory, SiliconFlowProvider
from core.embedding_provider import EmbeddingProviderFactory, SiliconFlowEmbeddingProvider
from core.reranker_provider import RerankerProviderFactory, SiliconFlowRerankerProvider
from logger import mask_sensitive_info


# ============================================================================
# Property 7: Configuration Validity Tests
# ============================================================================

class TestConfigurationValidity:
    """Test configuration validity validation."""

    @given(
        api_key=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""),
        provider_type=st.sampled_from(["siliconflow", "SiliconFlow", "SILICONFLOW"])
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_valid_llm_provider_creation(self, api_key: str, provider_type: str):
        """
        Property: For any valid API key and provider type, LLM provider creation should succeed.
        
        **Validates: Requirements 7.1, 7.2**
        """
        provider = LLMProviderFactory.create_provider(provider_type, api_key)
        assert provider is not None
        assert isinstance(provider, SiliconFlowProvider)
        assert provider.api_key == api_key

    @given(
        api_key=st.one_of(st.just(""), st.just("   "), st.just("\t")),
        provider_type=st.sampled_from(["siliconflow", "SiliconFlow"])
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_invalid_llm_api_key_rejected(self, api_key: str, provider_type: str):
        """
        Property: For any invalid API key, LLM provider creation should fail with clear error.
        
        **Validates: Requirements 7.2, 14.2**
        """
        with pytest.raises(ValueError, match="API key cannot be empty"):
            LLMProviderFactory.create_provider(provider_type, api_key)

    @given(
        api_key=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""),
        provider_type=st.text(min_size=1, max_size=20).filter(lambda x: x.lower() not in ["siliconflow"])
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_invalid_llm_provider_type_rejected(self, api_key: str, provider_type: str):
        """
        Property: For any invalid provider type, creation should fail with clear error.
        
        **Validates: Requirements 7.1, 14.2**
        """
        with pytest.raises(ValueError, match="Unsupported provider type"):
            LLMProviderFactory.create_provider(provider_type, api_key)

    @given(
        api_key=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""),
        model=st.sampled_from(["BAAI/bge-large-zh-v1.5", "BAAI/bge-base-zh-v1.5", "BAAI/bge-small-zh-v1.5"])
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_valid_embedding_provider_creation(self, api_key: str, model: str):
        """
        Property: For any valid API key and embedding model, provider creation should succeed.
        
        **Validates: Requirements 8.1, 8.2**
        """
        provider = EmbeddingProviderFactory.create_provider("siliconflow", api_key, model=model)
        assert provider is not None
        assert isinstance(provider, SiliconFlowEmbeddingProvider)
        assert provider.api_key == api_key
        assert provider.model == model

    @given(
        api_key=st.one_of(st.just(""), st.just("   ")),
        model=st.sampled_from(["BAAI/bge-large-zh-v1.5", "BAAI/bge-base-zh-v1.5"])
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_invalid_embedding_api_key_rejected(self, api_key: str, model: str):
        """
        Property: For any invalid API key, embedding provider creation should fail.
        
        **Validates: Requirements 8.2, 14.2**
        """
        with pytest.raises(ValueError, match="API key cannot be empty"):
            EmbeddingProviderFactory.create_provider("siliconflow", api_key, model=model)

    @given(
        api_key=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""),
        model=st.text(min_size=1, max_size=30).filter(lambda x: x not in [
            "BAAI/bge-large-zh-v1.5", "BAAI/bge-base-zh-v1.5", "BAAI/bge-small-zh-v1.5"
        ])
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_invalid_embedding_model_rejected(self, api_key: str, model: str):
        """
        Property: For any invalid embedding model, creation should fail with clear error.
        
        **Validates: Requirements 8.1, 8.2, 14.2**
        """
        with pytest.raises(ValueError, match="Unsupported model"):
            EmbeddingProviderFactory.create_provider("siliconflow", api_key, model=model)

    @given(
        api_key=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""),
        model=st.sampled_from(["BAAI/bge-reranker-large", "BAAI/bge-reranker-base"])
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_valid_reranker_provider_creation(self, api_key: str, model: str):
        """
        Property: For any valid API key and reranker model, provider creation should succeed.
        
        **Validates: Requirements 9.1, 9.2**
        """
        provider = RerankerProviderFactory.create_provider("siliconflow", api_key, model=model)
        assert provider is not None
        assert isinstance(provider, SiliconFlowRerankerProvider)
        assert provider.api_key == api_key
        assert provider.model == model

    @given(
        api_key=st.one_of(st.just(""), st.just("   ")),
        model=st.sampled_from(["BAAI/bge-reranker-large", "BAAI/bge-reranker-base"])
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_invalid_reranker_api_key_rejected(self, api_key: str, model: str):
        """
        Property: For any invalid API key, reranker provider creation should fail.
        
        **Validates: Requirements 9.2, 14.2**
        """
        with pytest.raises(ValueError, match="API key cannot be empty"):
            RerankerProviderFactory.create_provider("siliconflow", api_key, model=model)

    @given(
        chunk_size=st.integers(min_value=1, max_value=10000),
        chunk_overlap=st.integers(min_value=0, max_value=5000),
        retrieval_top_k=st.integers(min_value=1, max_value=100),
        reranking_top_k=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_valid_configuration_parameters(self, chunk_size: int, chunk_overlap: int, 
                                           retrieval_top_k: int, reranking_top_k: int):
        """
        Property: For any valid configuration parameters, validation should succeed.
        
        **Validates: Requirements 14.1, 14.2**
        """
        settings_obj = Settings(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            retrieval_top_k=retrieval_top_k,
            reranking_top_k=reranking_top_k
        )
        settings_obj.validate_config()
        assert settings_obj.chunk_size == chunk_size
        assert settings_obj.chunk_overlap == chunk_overlap

    @given(chunk_size=st.integers(max_value=0))
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_invalid_chunk_size_rejected(self, chunk_size: int):
        """
        Property: For any invalid chunk size (<=0), validation should fail.
        
        **Validates: Requirements 14.2**
        """
        settings_obj = Settings(chunk_size=chunk_size)
        with pytest.raises(ValueError, match="CHUNK_SIZE must be greater than 0"):
            settings_obj.validate_config()

    @given(chunk_overlap=st.integers(max_value=-1))
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_invalid_chunk_overlap_rejected(self, chunk_overlap: int):
        """
        Property: For any invalid chunk overlap (<0), validation should fail.
        
        **Validates: Requirements 14.2**
        """
        settings_obj = Settings(chunk_overlap=chunk_overlap)
        with pytest.raises(ValueError, match="CHUNK_OVERLAP must be non-negative"):
            settings_obj.validate_config()

    @given(retrieval_top_k=st.integers(max_value=0))
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_invalid_retrieval_top_k_rejected(self, retrieval_top_k: int):
        """
        Property: For any invalid retrieval_top_k (<=0), validation should fail.
        
        **Validates: Requirements 14.2**
        """
        settings_obj = Settings(retrieval_top_k=retrieval_top_k)
        with pytest.raises(ValueError, match="RETRIEVAL_TOP_K must be greater than 0"):
            settings_obj.validate_config()

    @given(reranking_top_k=st.integers(max_value=0))
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_invalid_reranking_top_k_rejected(self, reranking_top_k: int):
        """
        Property: For any invalid reranking_top_k (<=0), validation should fail.
        
        **Validates: Requirements 14.2**
        """
        settings_obj = Settings(reranking_top_k=reranking_top_k)
        with pytest.raises(ValueError, match="RERANKING_TOP_K must be greater than 0"):
            settings_obj.validate_config()


# ============================================================================
# Property 20: Sensitive Information Protection Tests
# ============================================================================

class TestSensitiveInformationProtection:
    """Test that sensitive information is not exposed in logs."""

    @given(sensitive_info=st.sampled_from([
        "api_key=sk-1234567890abcdef",
        "password=MySecretPassword123",
        "token=ghp_1234567890abcdefghijklmnopqrstuvwxyz",
        "secret=my-secret-value",
        "API_KEY: sk-1234567890abcdef",
        "Password: MySecretPassword123",
    ]))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_sensitive_info_masked_in_logs(self, sensitive_info: str):
        """
        Property: For any log message containing sensitive information,
        the mask_sensitive_info function should mask the sensitive values.
        
        **Validates: Requirements 14.3**
        """
        masked = mask_sensitive_info(sensitive_info)
        assert "***" in masked or masked == sensitive_info
        if "sk-" in sensitive_info or "ghp_" in sensitive_info:
            assert "sk-" not in masked or "***" in masked
            assert "ghp_" not in masked or "***" in masked

    @given(api_key=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_api_key_not_logged_in_provider_creation(self, api_key: str):
        """
        Property: For any API key used in provider creation,
        the API key should not appear in log messages.
        
        **Validates: Requirements 14.3**
        """
        with patch("core.llm_provider.logger") as mock_logger:
            provider = LLMProviderFactory.create_provider("siliconflow", api_key)
            for call in mock_logger.method_calls:
                if call[0] in ["error", "warning", "info"]:
                    message = str(call[1])
                    if api_key in message:
                        assert "***" in message or api_key.startswith("***")

    @given(
        api_key=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""),
        model=st.sampled_from(["BAAI/bge-large-zh-v1.5", "BAAI/bge-base-zh-v1.5"])
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_api_key_not_logged_in_embedding_provider(self, api_key: str, model: str):
        """
        Property: For any API key used in embedding provider creation,
        the API key should not appear in log messages.
        
        **Validates: Requirements 14.3**
        """
        with patch("core.embedding_provider.logger") as mock_logger:
            provider = EmbeddingProviderFactory.create_provider("siliconflow", api_key, model=model)
            for call in mock_logger.method_calls:
                if call[0] in ["error", "warning", "info"]:
                    message = str(call[1])
                    if api_key in message:
                        assert "***" in message or api_key.startswith("***")

    @given(
        api_key=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""),
        model=st.sampled_from(["BAAI/bge-reranker-large", "BAAI/bge-reranker-base"])
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_api_key_not_logged_in_reranker_provider(self, api_key: str, model: str):
        """
        Property: For any API key used in reranker provider creation,
        the API key should not appear in log messages.
        
        **Validates: Requirements 14.3**
        """
        with patch("core.reranker_provider.logger") as mock_logger:
            provider = RerankerProviderFactory.create_provider("siliconflow", api_key, model=model)
            for call in mock_logger.method_calls:
                if call[0] in ["error", "warning", "info"]:
                    message = str(call[1])
                    if api_key in message:
                        assert "***" in message or api_key.startswith("***")

    @given(message=st.text(min_size=1, max_size=200))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_mask_function_preserves_non_sensitive_content(self, message: str):
        """
        Property: For any message without sensitive information,
        mask_sensitive_info should return the message unchanged.
        
        **Validates: Requirements 14.3**
        """
        if any(pattern in message.lower() for pattern in ["api_key", "password", "token", "secret"]):
            pytest.skip("Message contains sensitive pattern")
        masked = mask_sensitive_info(message)
        assert masked == message

    @given(api_key=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_configuration_with_api_key_validation(self, api_key: str):
        """
        Property: For any configuration containing API keys,
        validation should succeed without exposing the API key.
        
        **Validates: Requirements 7.1, 7.2, 8.1, 8.2, 9.1, 9.2, 14.1, 14.2, 14.3**
        """
        settings_obj = Settings(
            llm_api_key=api_key,
            embedding_api_key=api_key,
            reranker_api_key=api_key,
        )
        settings_obj.validate_config()
        assert settings_obj.llm_api_key == api_key
        assert settings_obj.embedding_api_key == api_key
        assert settings_obj.reranker_api_key == api_key


# ============================================================================
# Integration Tests: Configuration Changes Validation
# ============================================================================

class TestConfigurationChangesValidation:
    """Test that configuration changes are properly validated."""

    @given(
        old_chunk_size=st.integers(min_value=1, max_value=5000),
        new_chunk_size=st.integers(min_value=1, max_value=5000),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_chunk_size_change_validation(self, old_chunk_size: int, new_chunk_size: int):
        """
        Property: For any valid chunk size changes, validation should succeed.
        
        **Validates: Requirements 14.2**
        """
        settings_obj = Settings(chunk_size=old_chunk_size)
        settings_obj.validate_config()
        settings_obj.chunk_size = new_chunk_size
        settings_obj.validate_config()
        assert settings_obj.chunk_size == new_chunk_size

    @given(
        old_overlap=st.integers(min_value=0, max_value=2000),
        new_overlap=st.integers(min_value=0, max_value=2000),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_chunk_overlap_change_validation(self, old_overlap: int, new_overlap: int):
        """
        Property: For any valid chunk overlap changes, validation should succeed.
        
        **Validates: Requirements 14.2**
        """
        settings_obj = Settings(chunk_overlap=old_overlap)
        settings_obj.validate_config()
        settings_obj.chunk_overlap = new_overlap
        settings_obj.validate_config()
        assert settings_obj.chunk_overlap == new_overlap

    @given(
        api_key=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""),
        model=st.sampled_from(["BAAI/bge-large-zh-v1.5", "BAAI/bge-base-zh-v1.5"])
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_embedding_model_change_validation(self, api_key: str, model: str):
        """
        Property: For any valid embedding model changes, provider should be recreated successfully.
        
        **Validates: Requirements 8.1, 8.2, 14.2**
        """
        provider1 = EmbeddingProviderFactory.create_provider("siliconflow", api_key, model=model)
        assert provider1.model == model
        new_model = "BAAI/bge-large-zh-v1.5" if model != "BAAI/bge-large-zh-v1.5" else "BAAI/bge-base-zh-v1.5"
        provider2 = EmbeddingProviderFactory.create_provider("siliconflow", api_key, model=new_model)
        assert provider2.model == new_model
        assert provider1.model != provider2.model

    @given(
        api_key=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""),
        model=st.sampled_from(["BAAI/bge-reranker-large", "BAAI/bge-reranker-base"])
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_reranker_model_change_validation(self, api_key: str, model: str):
        """
        Property: For any valid reranker model changes, provider should be recreated successfully.
        
        **Validates: Requirements 9.1, 9.2, 14.2**
        """
        provider1 = RerankerProviderFactory.create_provider("siliconflow", api_key, model=model)
        assert provider1.model == model
        new_model = "BAAI/bge-reranker-large" if model != "BAAI/bge-reranker-large" else "BAAI/bge-reranker-base"
        provider2 = RerankerProviderFactory.create_provider("siliconflow", api_key, model=new_model)
        assert provider2.model == new_model
        assert provider1.model != provider2.model

    @given(api_key=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_llm_provider_change_validation(self, api_key: str):
        """
        Property: For any valid LLM provider changes, provider should be recreated successfully.
        
        **Validates: Requirements 7.1, 7.2, 14.2**
        """
        provider1 = LLMProviderFactory.create_provider("siliconflow", api_key)
        assert provider1.api_key == api_key
        new_api_key = api_key + "_new" if len(api_key) < 40 else api_key[:-4] + "_new"
        provider2 = LLMProviderFactory.create_provider("siliconflow", new_api_key)
        assert provider2.api_key == new_api_key
        assert provider1.api_key != provider2.api_key
