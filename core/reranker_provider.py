"""Reranker provider factory for managing different reranking models."""

import logging
from typing import List, Tuple, Optional
from abc import ABC, abstractmethod
import httpx

logger = logging.getLogger(__name__)


class RerankerProvider(ABC):
    """Abstract base class for reranker providers."""

    @abstractmethod
    async def rerank(
        self, query: str, candidates: List[str], top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """Rerank candidates based on query."""
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validate connection to reranker service."""
        pass


class SiliconFlowRerankerProvider(RerankerProvider):
    """Silicon Flow reranker provider implementation."""

    BASE_URL = "https://api.siliconflow.cn/v1"
    DEFAULT_MODEL = "BAAI/bge-reranker-large"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        timeout: int = 30,
    ):
        """
        Initialize Silicon Flow reranker provider.

        Args:
            api_key: API key for Silicon Flow
            model: Model name to use
            timeout: Request timeout in seconds

        Raises:
            ValueError: If API key is empty
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")

        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def rerank(
        self, query: str, candidates: List[str], top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """
        Rerank candidates based on query.

        Args:
            query: Query text
            candidates: List of candidate texts to rerank
            top_k: Number of top results to return

        Returns:
            List of (index, score) tuples sorted by score descending

        Raises:
            ValueError: If query or candidates are empty
            Exception: If API call fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if not candidates or len(candidates) == 0:
            raise ValueError("Candidates list cannot be empty")

        # Filter out empty candidates
        candidates = [c for c in candidates if c and c.strip()]
        if not candidates:
            raise ValueError("All candidates are empty")

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # Prepare pairs for reranking
            pairs = [[query, candidate] for candidate in candidates]

            payload = {
                "model": self.model,
                "input": pairs,
            }

            response = await self.client.post(
                f"{self.BASE_URL}/rerank",
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
            if "results" not in data:
                raise Exception("No results in response")

            # Sort by score descending and return top_k
            results = sorted(
                data["results"], key=lambda x: x.get("score", 0), reverse=True
            )
            return [
                (r.get("index", 0), r.get("score", 0.0)) for r in results[:top_k]
            ]

        except httpx.TimeoutException:
            logger.error("Reranker API request timeout")
            raise Exception("Request timeout")
        except Exception as e:
            logger.error(f"Error calling reranker API: {str(e)}")
            raise

    async def validate_connection(self) -> bool:
        """
        Validate connection to reranker service.

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            results = await self.rerank("test", ["test candidate"], top_k=1)
            if results and len(results) > 0:
                logger.info("Reranker provider connection validated successfully")
                return True
            else:
                logger.warning("Reranker provider validation failed: no results")
                return False
        except Exception as e:
            logger.error(f"Error validating reranker provider connection: {str(e)}")
            return False

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class RerankerProviderFactory:
    """Factory for creating and managing reranker providers."""

    PROVIDERS = {
        "siliconflow": SiliconFlowRerankerProvider,
    }

    @staticmethod
    def create_provider(
        provider_type: str, api_key: str, **kwargs
    ) -> RerankerProvider:
        """
        Create a reranker provider instance.

        Args:
            provider_type: Type of provider (e.g., 'siliconflow')
            api_key: API key for the provider
            **kwargs: Additional configuration parameters

        Returns:
            RerankerProvider instance

        Raises:
            ValueError: If provider type is not supported
            ValueError: If API key is empty
        """
        provider_type = provider_type.lower()

        if provider_type not in RerankerProviderFactory.PROVIDERS:
            raise ValueError(
                f"Unsupported provider type: {provider_type}. "
                f"Supported types: {list(RerankerProviderFactory.PROVIDERS.keys())}"
            )

        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")

        provider_class = RerankerProviderFactory.PROVIDERS[provider_type]
        return provider_class(api_key, **kwargs)

    @staticmethod
    def get_supported_providers() -> list:
        """Get list of supported provider types."""
        return list(RerankerProviderFactory.PROVIDERS.keys())
