"""Tests for LangChain Embedding Wrapper."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from RagDocMan.core.langchain_embedding_wrapper import LangChainEmbeddingWrapper
from RagDocMan.core.embedding_provider import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider for testing."""

    def __init__(self, dimension: int = 1024):
        self.dimension = dimension
        self.embed_text_calls = []
        self.embed_texts_calls = []

    async def embed_text(self, text: str) -> list[float]:
        """Mock embed_text method."""
        self.embed_text_calls.append(text)
        return [0.1] * self.dimension

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Mock embed_texts method."""
        self.embed_texts_calls.append(texts)
        return [[0.1] * self.dimension for _ in texts]

    async def validate_connection(self) -> bool:
        """Mock validate_connection method."""
        return True

    def get_embedding_dimension(self) -> int:
        """Mock get_embedding_dimension method."""
        return self.dimension


class TestLangChainEmbeddingWrapper:
    """Test LangChain Embedding Wrapper."""

    def test_initialization(self):
        """Test wrapper initialization."""
        provider = MockEmbeddingProvider(dimension=768)
        wrapper = LangChainEmbeddingWrapper(
            embedding_provider=provider,
            model_name="test-model",
            batch_size=16
        )

        assert wrapper.embedding_provider == provider
        assert wrapper.model_name == "test-model"
        assert wrapper.batch_size == 16
        assert wrapper.get_embedding_dimension() == 768

    def test_embed_query_sync(self):
        """Test synchronous query embedding."""
        provider = MockEmbeddingProvider(dimension=1024)
        wrapper = LangChainEmbeddingWrapper(
            embedding_provider=provider,
            model_name="test-model"
        )

        result = wrapper.embed_query("test query")

        assert len(result) == 1024
        assert all(x == 0.1 for x in result)
        assert len(provider.embed_text_calls) == 1
        assert provider.embed_text_calls[0] == "test query"

    def test_embed_query_empty_text(self):
        """Test query embedding with empty text."""
        provider = MockEmbeddingProvider()
        wrapper = LangChainEmbeddingWrapper(embedding_provider=provider)

        with pytest.raises(ValueError, match="Text cannot be empty"):
            wrapper.embed_query("")

        with pytest.raises(ValueError, match="Text cannot be empty"):
            wrapper.embed_query("   ")

    def test_embed_documents_sync(self):
        """Test synchronous document embedding."""
        provider = MockEmbeddingProvider(dimension=512)
        wrapper = LangChainEmbeddingWrapper(
            embedding_provider=provider,
            model_name="test-model",
            batch_size=2
        )

        texts = ["doc1", "doc2", "doc3"]
        results = wrapper.embed_documents(texts)

        assert len(results) == 3
        assert all(len(emb) == 512 for emb in results)
        assert all(all(x == 0.1 for x in emb) for emb in results)
        # Should be called twice due to batch_size=2
        assert len(provider.embed_texts_calls) == 2

    def test_embed_documents_empty_list(self):
        """Test document embedding with empty list."""
        provider = MockEmbeddingProvider()
        wrapper = LangChainEmbeddingWrapper(embedding_provider=provider)

        with pytest.raises(ValueError, match="Texts list cannot be empty"):
            wrapper.embed_documents([])

    def test_embed_documents_batching(self):
        """Test document embedding with batching."""
        provider = MockEmbeddingProvider(dimension=768)
        wrapper = LangChainEmbeddingWrapper(
            embedding_provider=provider,
            batch_size=3
        )

        # 10 documents with batch_size=3 should result in 4 batches
        texts = [f"doc{i}" for i in range(10)]
        results = wrapper.embed_documents(texts)

        assert len(results) == 10
        assert len(provider.embed_texts_calls) == 4
        # Check batch sizes
        assert len(provider.embed_texts_calls[0]) == 3
        assert len(provider.embed_texts_calls[1]) == 3
        assert len(provider.embed_texts_calls[2]) == 3
        assert len(provider.embed_texts_calls[3]) == 1

    @pytest.mark.asyncio
    async def test_aembed_query(self):
        """Test asynchronous query embedding."""
        provider = MockEmbeddingProvider(dimension=1024)
        wrapper = LangChainEmbeddingWrapper(
            embedding_provider=provider,
            model_name="test-model"
        )

        result = await wrapper.aembed_query("async test query")

        assert len(result) == 1024
        assert all(x == 0.1 for x in result)
        assert len(provider.embed_text_calls) == 1
        assert provider.embed_text_calls[0] == "async test query"

    @pytest.mark.asyncio
    async def test_aembed_query_empty_text(self):
        """Test async query embedding with empty text."""
        provider = MockEmbeddingProvider()
        wrapper = LangChainEmbeddingWrapper(embedding_provider=provider)

        with pytest.raises(ValueError, match="Text cannot be empty"):
            await wrapper.aembed_query("")

        with pytest.raises(ValueError, match="Text cannot be empty"):
            await wrapper.aembed_query("   ")

    @pytest.mark.asyncio
    async def test_aembed_documents(self):
        """Test asynchronous document embedding."""
        provider = MockEmbeddingProvider(dimension=512)
        wrapper = LangChainEmbeddingWrapper(
            embedding_provider=provider,
            model_name="test-model",
            batch_size=2
        )

        texts = ["async doc1", "async doc2", "async doc3"]
        results = await wrapper.aembed_documents(texts)

        assert len(results) == 3
        assert all(len(emb) == 512 for emb in results)
        assert all(all(x == 0.1 for x in emb) for emb in results)
        # Should be called twice due to batch_size=2
        assert len(provider.embed_texts_calls) == 2

    @pytest.mark.asyncio
    async def test_aembed_documents_empty_list(self):
        """Test async document embedding with empty list."""
        provider = MockEmbeddingProvider()
        wrapper = LangChainEmbeddingWrapper(embedding_provider=provider)

        with pytest.raises(ValueError, match="Texts list cannot be empty"):
            await wrapper.aembed_documents([])

    @pytest.mark.asyncio
    async def test_aembed_documents_batching(self):
        """Test async document embedding with batching."""
        provider = MockEmbeddingProvider(dimension=768)
        wrapper = LangChainEmbeddingWrapper(
            embedding_provider=provider,
            batch_size=4
        )

        # 9 documents with batch_size=4 should result in 3 batches
        texts = [f"async doc{i}" for i in range(9)]
        results = await wrapper.aembed_documents(texts)

        assert len(results) == 9
        assert len(provider.embed_texts_calls) == 3
        # Check batch sizes
        assert len(provider.embed_texts_calls[0]) == 4
        assert len(provider.embed_texts_calls[1]) == 4
        assert len(provider.embed_texts_calls[2]) == 1

    def test_get_embedding_dimension(self):
        """Test getting embedding dimension."""
        provider = MockEmbeddingProvider(dimension=2048)
        wrapper = LangChainEmbeddingWrapper(embedding_provider=provider)

        assert wrapper.get_embedding_dimension() == 2048

    def test_identifying_params(self):
        """Test identifying parameters."""
        provider = MockEmbeddingProvider(dimension=1024)
        wrapper = LangChainEmbeddingWrapper(
            embedding_provider=provider,
            model_name="test-model-v1",
            batch_size=64
        )

        params = wrapper._identifying_params

        assert params["model_name"] == "test-model-v1"
        assert params["batch_size"] == 64
        assert params["embedding_dimension"] == 1024

    def test_default_batch_size(self):
        """Test default batch size."""
        provider = MockEmbeddingProvider()
        wrapper = LangChainEmbeddingWrapper(embedding_provider=provider)

        assert wrapper.batch_size == 32

    def test_custom_batch_size(self):
        """Test custom batch size."""
        provider = MockEmbeddingProvider()
        wrapper = LangChainEmbeddingWrapper(
            embedding_provider=provider,
            batch_size=128
        )

        assert wrapper.batch_size == 128


class TestLangChainEmbeddingWrapperWithRealProvider:
    """Test wrapper with real embedding provider (requires API key)."""

    @pytest.mark.skip(reason="Requires API key and network access")
    async def test_with_siliconflow_provider(self):
        """Test with real SiliconFlow provider."""
        from RagDocMan.core.embedding_provider import SiliconFlowEmbeddingProvider
        import os

        api_key = os.getenv("SILICONFLOW_API_KEY")
        if not api_key:
            pytest.skip("SILICONFLOW_API_KEY not set")

        provider = SiliconFlowEmbeddingProvider(
            api_key=api_key,
            model="BAAI/bge-large-zh-v1.5"
        )
        wrapper = LangChainEmbeddingWrapper(
            embedding_provider=provider,
            model_name="BAAI/bge-large-zh-v1.5"
        )

        # Test query embedding
        query_embedding = await wrapper.aembed_query("测试查询")
        assert len(query_embedding) == 1024

        # Test document embedding
        docs = ["文档1", "文档2", "文档3"]
        doc_embeddings = await wrapper.aembed_documents(docs)
        assert len(doc_embeddings) == 3
        assert all(len(emb) == 1024 for emb in doc_embeddings)


class TestLangChainEmbeddingWrapperErrorHandling:
    """Test error handling in the wrapper."""

    @pytest.mark.asyncio
    async def test_provider_error_propagation(self):
        """Test that provider errors are properly propagated."""
        provider = MockEmbeddingProvider()
        
        # Make the provider raise an error
        async def failing_embed_text(text: str):
            raise Exception("Provider error")
        
        provider.embed_text = failing_embed_text
        
        wrapper = LangChainEmbeddingWrapper(embedding_provider=provider)

        with pytest.raises(Exception, match="Provider error"):
            await wrapper.aembed_query("test")

    @pytest.mark.asyncio
    async def test_batch_error_propagation(self):
        """Test that batch processing errors are properly propagated."""
        provider = MockEmbeddingProvider()
        
        # Make the provider raise an error
        async def failing_embed_texts(texts: list[str]):
            raise Exception("Batch processing error")
        
        provider.embed_texts = failing_embed_texts
        
        wrapper = LangChainEmbeddingWrapper(embedding_provider=provider)

        with pytest.raises(Exception, match="Batch processing error"):
            await wrapper.aembed_documents(["doc1", "doc2"])
