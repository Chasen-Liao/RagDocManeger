"""Tests for retriever components."""

import pytest
from RagDocMan.rag.retriever import (
    BM25Retriever,
    VectorRetriever,
    ResultFuser,
    HybridRetriever,
    RetrievalResult,
)


class TestBM25Retriever:
    """Test BM25 retriever."""

    def test_build_index(self):
        """Test building BM25 index."""
        retriever = BM25Retriever()
        chunks = [
            {
                "id": "1",
                "content": "This is a test document",
                "doc_id": "doc1",
                "doc_name": "Test Doc",
            },
            {
                "id": "2",
                "content": "Another test document",
                "doc_id": "doc2",
                "doc_name": "Test Doc 2",
            },
        ]
        retriever.build_index(chunks)
        assert retriever.bm25 is not None
        assert len(retriever.chunks) == 2

    def test_build_index_empty_chunks(self):
        """Test building index with empty chunks."""
        retriever = BM25Retriever()
        with pytest.raises(ValueError, match="Chunks list cannot be empty"):
            retriever.build_index([])

    def test_retrieve_without_index(self):
        """Test retrieve without building index."""
        retriever = BM25Retriever()
        with pytest.raises(ValueError, match="Index not built"):
            retriever.retrieve("test query")

    def test_retrieve_with_empty_query(self):
        """Test retrieve with empty query."""
        retriever = BM25Retriever()
        chunks = [
            {
                "id": "1",
                "content": "This is a test document",
                "doc_id": "doc1",
                "doc_name": "Test Doc",
            }
        ]
        retriever.build_index(chunks)
        with pytest.raises(ValueError, match="Query cannot be empty"):
            retriever.retrieve("")

    def test_retrieve_basic(self):
        """Test basic retrieval."""
        retriever = BM25Retriever()
        chunks = [
            {
                "id": "1",
                "content": "This is a test document about Python",
                "doc_id": "doc1",
                "doc_name": "Test Doc",
            },
            {
                "id": "2",
                "content": "Another document about Java",
                "doc_id": "doc2",
                "doc_name": "Test Doc 2",
            },
        ]
        retriever.build_index(chunks)
        results = retriever.retrieve("Python", top_k=1)
        assert len(results) > 0
        assert results[0].chunk_id == "1"

    def test_retrieve_top_k(self):
        """Test retrieve with top_k."""
        retriever = BM25Retriever()
        chunks = [
            {
                "id": str(i),
                "content": f"Document {i} with test content",
                "doc_id": f"doc{i}",
                "doc_name": f"Doc {i}",
            }
            for i in range(5)
        ]
        retriever.build_index(chunks)
        results = retriever.retrieve("test", top_k=2)
        assert len(results) <= 2


class TestResultFuser:
    """Test result fuser."""

    def test_fuse_results_basic(self):
        """Test basic result fusion."""
        bm25_results = [
            RetrievalResult(
                chunk_id="1",
                doc_id="doc1",
                content="test",
                score=0.9,
                doc_name="Doc1",
            ),
            RetrievalResult(
                chunk_id="2",
                doc_id="doc2",
                content="test",
                score=0.7,
                doc_name="Doc2",
            ),
        ]
        vector_results = [
            RetrievalResult(
                chunk_id="2",
                doc_id="doc2",
                content="test",
                score=0.8,
                doc_name="Doc2",
            ),
            RetrievalResult(
                chunk_id="3",
                doc_id="doc3",
                content="test",
                score=0.6,
                doc_name="Doc3",
            ),
        ]
        fused = ResultFuser.fuse_results(bm25_results, vector_results)
        assert len(fused) > 0
        # Check that results are sorted by score
        for i in range(len(fused) - 1):
            assert fused[i].score >= fused[i + 1].score

    def test_fuse_results_empty_lists(self):
        """Test fusing with empty lists."""
        with pytest.raises(ValueError, match="Both result lists cannot be empty"):
            ResultFuser.fuse_results([], [])

    def test_fuse_results_only_bm25(self):
        """Test fusing with only BM25 results."""
        bm25_results = [
            RetrievalResult(
                chunk_id="1",
                doc_id="doc1",
                content="test",
                score=0.9,
                doc_name="Doc1",
            )
        ]
        fused = ResultFuser.fuse_results(bm25_results, [])
        assert len(fused) == 1

    def test_fuse_results_only_vector(self):
        """Test fusing with only vector results."""
        vector_results = [
            RetrievalResult(
                chunk_id="1",
                doc_id="doc1",
                content="test",
                score=0.9,
                doc_name="Doc1",
            )
        ]
        fused = ResultFuser.fuse_results([], vector_results)
        assert len(fused) == 1


class TestHybridRetriever:
    """Test hybrid retriever."""

    @pytest.mark.asyncio
    async def test_build_index(self):
        """Test building hybrid index."""
        retriever = HybridRetriever()
        chunks = [
            {
                "id": "1",
                "content": "This is a test document",
                "doc_id": "doc1",
                "doc_name": "Test Doc",
            }
        ]
        await retriever.build_index(chunks)
        assert retriever.bm25_retriever.bm25 is not None

    @pytest.mark.asyncio
    async def test_build_index_empty_chunks(self):
        """Test building index with empty chunks."""
        retriever = HybridRetriever()
        with pytest.raises(ValueError, match="Chunks list cannot be empty"):
            await retriever.build_index([])

    @pytest.mark.asyncio
    async def test_retrieve_without_index(self):
        """Test retrieve without building index."""
        retriever = HybridRetriever()
        with pytest.raises(ValueError, match="Index not built"):
            await retriever.retrieve("test query")

    @pytest.mark.asyncio
    async def test_retrieve_with_empty_query(self):
        """Test retrieve with empty query."""
        retriever = HybridRetriever()
        chunks = [
            {
                "id": "1",
                "content": "This is a test document",
                "doc_id": "doc1",
                "doc_name": "Test Doc",
            }
        ]
        await retriever.build_index(chunks)
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await retriever.retrieve("")

    @pytest.mark.asyncio
    async def test_retrieve_basic(self):
        """Test basic hybrid retrieval."""
        retriever = HybridRetriever()
        chunks = [
            {
                "id": "1",
                "content": "This is a test document about Python",
                "doc_id": "doc1",
                "doc_name": "Test Doc",
            },
            {
                "id": "2",
                "content": "Another document about Java",
                "doc_id": "doc2",
                "doc_name": "Test Doc 2",
            },
        ]
        await retriever.build_index(chunks)
        results = await retriever.retrieve("Python", top_k=1, use_vector=False)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_retrieve_top_k(self):
        """Test retrieve with top_k."""
        retriever = HybridRetriever()
        chunks = [
            {
                "id": str(i),
                "content": f"Document {i} with test content",
                "doc_id": f"doc{i}",
                "doc_name": f"Doc {i}",
            }
            for i in range(5)
        ]
        await retriever.build_index(chunks)
        results = await retriever.retrieve("test", top_k=2, use_vector=False)
        assert len(results) <= 2
