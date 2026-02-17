"""Embedding provider factory for managing different embedding models."""

import logging
from typing import List, Optional
from abc import ABC, abstractmethod
import httpx
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text."""
        pass

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validate connection to embedding service."""
        pass

    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings."""
        pass


class SiliconFlowEmbeddingProvider(EmbeddingProvider):
    """Silicon Flow embedding provider implementation."""

    BASE_URL = "https://api.siliconflow.cn/v1"
    DEFAULT_MODEL = "BAAI/bge-large-zh-v1.5"
    EMBEDDING_DIMENSIONS = {
        "BAAI/bge-large-zh-v1.5": 1024,
        "BAAI/bge-base-zh-v1.5": 768,
        "BAAI/bge-small-zh-v1.5": 512,
    }

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        timeout: int = 30,
    ):
        """
        Initialize Silicon Flow embedding provider.

        Args:
            api_key: API key for Silicon Flow
            model: Model name to use
            timeout: Request timeout in seconds

        Raises:
            ValueError: If API key is empty or model is not supported
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")

        if model not in self.EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Unsupported model: {model}. "
                f"Supported models: {list(self.EMBEDDING_DIMENSIONS.keys())}"
            )

        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector

        Raises:
            ValueError: If text is empty
            Exception: If API call fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        embeddings = await self.embed_texts([text])
        return embeddings[0]

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            ValueError: If texts list is empty
            Exception: If API call fails
        """
        if not texts or len(texts) == 0:
            raise ValueError("Texts list cannot be empty")

        # Filter out empty texts
        texts = [t for t in texts if t and t.strip()]
        if not texts:
            raise ValueError("All texts are empty")

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model,
                "input": texts,
            }

            response = await self.client.post(
                f"{self.BASE_URL}/embeddings",
                headers=headers,
                json=payload,
            )

            if response.status_code != 200:
                error_msg = f"API error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", error_msg)
                except Exception:
                    pass
                raise Exception(error_msg)

            data = response.json()
            if "data" not in data:
                raise Exception("No embeddings in response")

            # Sort by index to maintain order
            embeddings = sorted(data["data"], key=lambda x: x.get("index", 0))
            return [e["embedding"] for e in embeddings]

        except httpx.TimeoutException:
            logger.error("Embedding API request timeout")
            raise Exception("Request timeout")
        except Exception as e:
            logger.error(f"Error calling embedding API: {str(e)}")
            raise

    async def validate_connection(self) -> bool:
        """
        Validate connection to embedding service.

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            embedding = await self.embed_text("test")
            if embedding and len(embedding) == self.get_embedding_dimension():
                logger.info("Embedding provider connection validated successfully")
                return True
            else:
                logger.warning("Embedding provider validation failed: invalid dimension")
                return False
        except Exception as e:
            logger.error(f"Error validating embedding provider connection: {str(e)}")
            return False

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings for the current model."""
        return self.EMBEDDING_DIMENSIONS.get(self.model, 1024)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class EmbeddingProviderFactory:
    """Factory for creating and managing embedding providers."""

    PROVIDERS = {
        "siliconflow": SiliconFlowEmbeddingProvider,
    }

    @staticmethod
    def create_provider(
        provider_type: str, api_key: str, **kwargs
    ) -> EmbeddingProvider:
        """
        Create an embedding provider instance.

        Args:
            provider_type: Type of provider (e.g., 'siliconflow')
            api_key: API key for the provider
            **kwargs: Additional configuration parameters

        Returns:
            EmbeddingProvider instance

        Raises:
            ValueError: If provider type is not supported
            ValueError: If API key is empty
        """
        provider_type = provider_type.lower()

        if provider_type not in EmbeddingProviderFactory.PROVIDERS:
            raise ValueError(
                f"Unsupported provider type: {provider_type}. "
                f"Supported types: {list(EmbeddingProviderFactory.PROVIDERS.keys())}"
            )

        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")

        provider_class = EmbeddingProviderFactory.PROVIDERS[provider_type]
        return provider_class(api_key, **kwargs)

    @staticmethod
    def get_supported_providers() -> list:
        """Get list of supported provider types."""
        return list(EmbeddingProviderFactory.PROVIDERS.keys())
