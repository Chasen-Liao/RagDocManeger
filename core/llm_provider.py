"""LLM provider factory for managing different LLM services."""

import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
import httpx
import json

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt."""
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validate connection to LLM service."""
        pass


class SiliconFlowProvider(LLMProvider):
    """Silicon Flow LLM provider implementation."""

    BASE_URL = "https://api.siliconflow.cn/v1"
    DEFAULT_MODEL = "Qwen/Qwen2-7B-Instruct"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 30,
    ):
        """
        Initialize Silicon Flow provider.

        Args:
            api_key: API key for Silicon Flow
            model: Model name to use
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds

        Raises:
            ValueError: If API key is empty
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")

        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text using Silicon Flow API.

        Args:
            prompt: Input prompt
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Generated text

        Raises:
            Exception: If API call fails
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        try:
            temperature = kwargs.get("temperature", self.temperature)
            max_tokens = kwargs.get("max_tokens", self.max_tokens)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            response = await self.client.post(
                f"{self.BASE_URL}/chat/completions",
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
            if "choices" not in data or len(data["choices"]) == 0:
                raise Exception("No choices in response")

            return data["choices"][0]["message"]["content"]

        except httpx.TimeoutException:
            logger.error("Silicon Flow API request timeout")
            raise Exception("Request timeout")
        except Exception as e:
            logger.error(f"Error calling Silicon Flow API: {str(e)}")
            raise

    async def validate_connection(self) -> bool:
        """
        Validate connection to Silicon Flow API.

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "test"}],
                "temperature": 0.7,
                "max_tokens": 10,
            }

            response = await self.client.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )

            if response.status_code == 200:
                logger.info("Silicon Flow connection validated successfully")
                return True
            else:
                logger.warning(f"Silicon Flow validation failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error validating Silicon Flow connection: {str(e)}")
            return False

    async def generate_stream(self, prompt: str, **kwargs):
        """
        Generate text using Silicon Flow API with streaming.

        Args:
            prompt: Input prompt
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Yields:
            Chunks of generated text

        Raises:
            Exception: If API call fails
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        try:
            temperature = kwargs.get("temperature", self.temperature)
            max_tokens = kwargs.get("max_tokens", self.max_tokens)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            }

            async with self.client.stream(
                "POST",
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=httpx.Timeout(self.timeout * 10),
            ) as response:
                if response.status_code != 200:
                    error_msg = f"API error: {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", error_msg)
                    except Exception:
                        pass
                    raise Exception(error_msg)

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

        except httpx.TimeoutException:
            logger.error("Silicon Flow API request timeout")
            raise Exception("Request timeout")
        except Exception as e:
            logger.error(f"Error calling Silicon Flow API: {str(e)}")
            raise

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class LLMProviderFactory:
    """Factory for creating and managing LLM providers."""

    PROVIDERS = {
        "siliconflow": SiliconFlowProvider,
    }

    @staticmethod
    def create_provider(
        provider_type: str, api_key: str, **kwargs
    ) -> LLMProvider:
        """
        Create an LLM provider instance.

        Args:
            provider_type: Type of provider (e.g., 'siliconflow')
            api_key: API key for the provider
            **kwargs: Additional configuration parameters

        Returns:
            LLMProvider instance

        Raises:
            ValueError: If provider type is not supported
            ValueError: If API key is empty
        """
        provider_type = provider_type.lower()

        if provider_type not in LLMProviderFactory.PROVIDERS:
            raise ValueError(
                f"Unsupported provider type: {provider_type}. "
                f"Supported types: {list(LLMProviderFactory.PROVIDERS.keys())}"
            )

        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")

        provider_class = LLMProviderFactory.PROVIDERS[provider_type]
        return provider_class(api_key, **kwargs)

    @staticmethod
    def get_supported_providers() -> list:
        """Get list of supported provider types."""
        return list(LLMProviderFactory.PROVIDERS.keys())
