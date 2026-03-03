"""Tests for LangChain LLM wrapper."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from RagDocMan.core.langchain_llm_wrapper import LangChainLLMWrapper
from RagDocMan.core.llm_provider import SiliconFlowProvider


class MockLLMProvider:
    """Mock LLM provider for testing."""

    def __init__(self, response: str = "test response"):
        self.response = response
        self.generate_called = False
        self.stream_called = False

    async def generate(self, prompt: str, **kwargs) -> str:
        """Mock generate method."""
        self.generate_called = True
        return self.response

    async def generate_stream(self, prompt: str, **kwargs):
        """Mock streaming generate method."""
        self.stream_called = True
        chunks = self.response.split()
        for chunk in chunks:
            yield chunk + " "


class TestLangChainLLMWrapper:
    """Test LangChain LLM wrapper basic functionality."""

    def test_init(self):
        """Test wrapper initialization."""
        provider = MockLLMProvider()
        wrapper = LangChainLLMWrapper(provider, model_name="test-model")
        
        assert wrapper.llm_provider == provider
        assert wrapper.model_name == "test-model"

    def test_init_default_model_name(self):
        """Test wrapper initialization with default model name."""
        provider = MockLLMProvider()
        wrapper = LangChainLLMWrapper(provider)
        
        assert wrapper.model_name == "custom"

    def test_llm_type_property(self):
        """Test _llm_type property."""
        provider = MockLLMProvider()
        wrapper = LangChainLLMWrapper(provider, model_name="test-model")
        
        assert wrapper._llm_type == "test-model"

    def test_identifying_params(self):
        """Test _identifying_params property."""
        provider = MockLLMProvider()
        wrapper = LangChainLLMWrapper(provider, model_name="test-model")
        
        params = wrapper._identifying_params
        assert params["model_name"] == "test-model"
        assert params["llm_type"] == "test-model"


class TestLangChainLLMWrapperSyncCall:
    """Test synchronous LLM calls."""

    def test_call_basic(self):
        """Test basic synchronous call."""
        provider = MockLLMProvider(response="Hello world")
        wrapper = LangChainLLMWrapper(provider)
        
        result = wrapper._call("test prompt")
        
        assert result == "Hello world"
        assert provider.generate_called

    def test_call_with_kwargs(self):
        """Test synchronous call with additional kwargs."""
        provider = MockLLMProvider(response="Response with params")
        wrapper = LangChainLLMWrapper(provider)
        
        result = wrapper._call("test prompt", temperature=0.5, max_tokens=100)
        
        assert result == "Response with params"
        assert provider.generate_called

    def test_call_with_stop_sequences(self):
        """Test synchronous call with stop sequences."""
        provider = MockLLMProvider(response="Test response")
        wrapper = LangChainLLMWrapper(provider)
        
        result = wrapper._call("test prompt", stop=["STOP", "END"])
        
        assert result == "Test response"

    def test_call_error_handling(self):
        """Test error handling in synchronous call."""
        provider = MockLLMProvider()
        provider.generate = AsyncMock(side_effect=Exception("API error"))
        wrapper = LangChainLLMWrapper(provider)
        
        with pytest.raises(Exception, match="API error"):
            wrapper._call("test prompt")


class TestLangChainLLMWrapperAsyncCall:
    """Test asynchronous LLM calls."""

    @pytest.mark.asyncio
    async def test_acall_basic(self):
        """Test basic asynchronous call."""
        provider = MockLLMProvider(response="Async hello world")
        wrapper = LangChainLLMWrapper(provider)
        
        result = await wrapper._acall("test prompt")
        
        assert result == "Async hello world"
        assert provider.generate_called

    @pytest.mark.asyncio
    async def test_acall_with_kwargs(self):
        """Test asynchronous call with additional kwargs."""
        provider = MockLLMProvider(response="Async response with params")
        wrapper = LangChainLLMWrapper(provider)
        
        result = await wrapper._acall("test prompt", temperature=0.7, max_tokens=200)
        
        assert result == "Async response with params"
        assert provider.generate_called

    @pytest.mark.asyncio
    async def test_acall_with_stop_sequences(self):
        """Test asynchronous call with stop sequences."""
        provider = MockLLMProvider(response="Async test response")
        wrapper = LangChainLLMWrapper(provider)
        
        result = await wrapper._acall("test prompt", stop=["STOP"])
        
        assert result == "Async test response"

    @pytest.mark.asyncio
    async def test_acall_error_handling(self):
        """Test error handling in asynchronous call."""
        provider = MockLLMProvider()
        provider.generate = AsyncMock(side_effect=Exception("Async API error"))
        wrapper = LangChainLLMWrapper(provider)
        
        with pytest.raises(Exception, match="Async API error"):
            await wrapper._acall("test prompt")


class TestLangChainLLMWrapperStreaming:
    """Test streaming functionality."""

    def test_stream_basic(self):
        """Test basic synchronous streaming."""
        provider = MockLLMProvider(response="Hello streaming world")
        wrapper = LangChainLLMWrapper(provider)
        
        chunks = list(wrapper._stream("test prompt"))
        
        assert provider.stream_called
        assert len(chunks) > 0
        # Chunks are GenerationChunk objects
        full_text = "".join([chunk.text for chunk in chunks]).strip()
        assert full_text == "Hello streaming world"

    def test_stream_without_support(self):
        """Test streaming fallback when provider doesn't support it."""
        # Create a provider without generate_stream method
        class MockProviderNoStream:
            async def generate(self, prompt: str, **kwargs) -> str:
                return "Fallback response"
        
        provider = MockProviderNoStream()
        wrapper = LangChainLLMWrapper(provider)
        
        chunks = list(wrapper._stream("test prompt"))
        
        assert len(chunks) == 1
        assert chunks[0].text == "Fallback response"

    @pytest.mark.asyncio
    async def test_astream_basic(self):
        """Test basic asynchronous streaming."""
        provider = MockLLMProvider(response="Async streaming test")
        wrapper = LangChainLLMWrapper(provider)
        
        chunks = []
        async for chunk in wrapper._astream("test prompt"):
            chunks.append(chunk)
        
        assert provider.stream_called
        assert len(chunks) > 0
        # Chunks are GenerationChunk objects
        full_text = "".join([chunk.text for chunk in chunks]).strip()
        assert full_text == "Async streaming test"

    @pytest.mark.asyncio
    async def test_astream_without_support(self):
        """Test async streaming fallback when provider doesn't support it."""
        # Create a provider without generate_stream method
        class MockProviderNoStream:
            async def generate(self, prompt: str, **kwargs) -> str:
                return "Async fallback response"
        
        provider = MockProviderNoStream()
        wrapper = LangChainLLMWrapper(provider)
        
        chunks = []
        async for chunk in wrapper._astream("test prompt"):
            chunks.append(chunk)
        
        assert len(chunks) == 1
        assert chunks[0].text == "Async fallback response"


class TestLangChainLLMWrapperWithRealProvider:
    """Test wrapper with real LLM providers."""

    def test_with_siliconflow_provider(self):
        """Test wrapper with SiliconFlow provider."""
        provider = SiliconFlowProvider("test-api-key", model="test-model")
        wrapper = LangChainLLMWrapper(provider, model_name="siliconflow")
        
        assert wrapper.llm_provider == provider
        assert wrapper.model_name == "siliconflow"
        assert wrapper._llm_type == "siliconflow"

    @pytest.mark.asyncio
    async def test_acall_with_siliconflow_invalid_key(self):
        """Test async call with SiliconFlow provider (will fail with invalid key)."""
        provider = SiliconFlowProvider("invalid-key")
        wrapper = LangChainLLMWrapper(provider, model_name="siliconflow")
        
        with pytest.raises(Exception):
            await wrapper._acall("test prompt")
        
        # Clean up
        await provider.close()


class TestLangChainLLMWrapperIntegration:
    """Integration tests for LangChain LLM wrapper."""

    def test_wrapper_can_be_used_in_langchain_chain(self):
        """Test that wrapper can be used in LangChain chains."""
        from langchain_core.prompts import PromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        
        provider = MockLLMProvider(response="Chain response")
        wrapper = LangChainLLMWrapper(provider)
        
        # Create a simple chain
        prompt = PromptTemplate.from_template("Say {text}")
        chain = prompt | wrapper | StrOutputParser()
        
        result = chain.invoke({"text": "hello"})
        
        assert result == "Chain response"
        assert provider.generate_called

    @pytest.mark.asyncio
    async def test_wrapper_can_be_used_in_async_chain(self):
        """Test that wrapper can be used in async LangChain chains."""
        from langchain_core.prompts import PromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        
        provider = MockLLMProvider(response="Async chain response")
        wrapper = LangChainLLMWrapper(provider)
        
        # Create a simple chain
        prompt = PromptTemplate.from_template("Say {text}")
        chain = prompt | wrapper | StrOutputParser()
        
        result = await chain.ainvoke({"text": "hello"})
        
        assert result == "Async chain response"
        assert provider.generate_called

    @pytest.mark.asyncio
    async def test_wrapper_streaming_in_chain(self):
        """Test that wrapper streaming works in LangChain chains."""
        from langchain_core.prompts import PromptTemplate
        
        provider = MockLLMProvider(response="Streaming chain response")
        wrapper = LangChainLLMWrapper(provider)
        
        # Create a simple chain
        prompt = PromptTemplate.from_template("Say {text}")
        chain = prompt | wrapper
        
        chunks = []
        async for chunk in chain.astream({"text": "hello"}):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        assert provider.stream_called


class TestLangChainLLMWrapperEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_prompt(self):
        """Test with empty prompt."""
        provider = MockLLMProvider(response="")
        wrapper = LangChainLLMWrapper(provider)
        
        result = wrapper._call("")
        
        assert result == ""

    @pytest.mark.asyncio
    async def test_async_empty_prompt(self):
        """Test async call with empty prompt."""
        provider = MockLLMProvider(response="")
        wrapper = LangChainLLMWrapper(provider)
        
        result = await wrapper._acall("")
        
        assert result == ""

    def test_very_long_prompt(self):
        """Test with very long prompt."""
        provider = MockLLMProvider(response="Long response")
        wrapper = LangChainLLMWrapper(provider)
        
        long_prompt = "test " * 1000
        result = wrapper._call(long_prompt)
        
        assert result == "Long response"

    def test_special_characters_in_prompt(self):
        """Test with special characters in prompt."""
        provider = MockLLMProvider(response="Special response")
        wrapper = LangChainLLMWrapper(provider)
        
        special_prompt = "Test with 特殊字符 and émojis 🎉"
        result = wrapper._call(special_prompt)
        
        assert result == "Special response"
