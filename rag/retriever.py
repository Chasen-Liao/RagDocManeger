"""Retrieval components for hybrid search."""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Result from retrieval."""

    chunk_id: str
    doc_id: str
    content: str
    score: float
    doc_name: str = ""


class BM25Retriever:
    """BM25 keyword-based retriever."""

    def __init__(self):
        """Initialize BM25 retriever."""
        self.bm25 = None
        self.chunks = []
        self.chunk_ids = []

    def build_index(self, chunks: List[Dict]) -> None:
        """
        Build BM25 index from chunks.

        Args:
            chunks: List of chunk dicts with 'id', 'content', 'doc_id', 'doc_name'

        Raises:
            ValueError: If chunks list is empty
        """
        if not chunks or len(chunks) == 0:
            raise ValueError("Chunks list cannot be empty")

        # Tokenize chunks
        tokenized_chunks = []
        self.chunks = chunks
        self.chunk_ids = []

        for chunk in chunks:
            content = chunk.get("content", "")
            if not content or not content.strip():
                continue

            # Simple tokenization: split by whitespace and lowercase
            tokens = content.lower().split()
            tokenized_chunks.append(tokens)
            self.chunk_ids.append(chunk.get("id", ""))

        if not tokenized_chunks:
            raise ValueError("No valid chunks to index")

        self.bm25 = BM25Okapi(tokenized_chunks)
        logger.info(f"BM25 index built with {len(tokenized_chunks)} chunks")

    def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """
        Retrieve chunks using BM25.

        Args:
            query: Query string
            top_k: Number of top results to return

        Returns:
            List of RetrievalResult objects

        Raises:
            ValueError: If query is empty or index not built
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if self.bm25 is None:
            raise ValueError("Index not built. Call build_index first.")

        # Tokenize query
        tokens = query.lower().split()
        if not tokens:
            raise ValueError("Query has no valid tokens")

        # Get scores
        scores = self.bm25.get_scores(tokens)

        # Get top-k results
        top_indices = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[:top_k]

        results = []
        for idx in top_indices:
            if idx < len(self.chunks):
                chunk = self.chunks[idx]
                results.append(
                    RetrievalResult(
                        chunk_id=chunk.get("id", ""),
                        doc_id=chunk.get("doc_id", ""),
                        content=chunk.get("content", ""),
                        score=float(scores[idx]),
                        doc_name=chunk.get("doc_name", ""),
                    )
                )

        logger.info(f"BM25 retrieved {len(results)} results for query: {query}")
        return results


class VectorRetriever:
    """Vector-based retriever using embeddings."""

    def __init__(self, embedding_provider=None):
        """
        Initialize vector retriever.

        Args:
            embedding_provider: Provider for generating embeddings
        """
        self.embedding_provider = embedding_provider
        self.chunks = []
        self.embeddings = []

    async def build_index(self, chunks: List[Dict]) -> None:
        """
        Build vector index from chunks.

        Args:
            chunks: List of chunk dicts with 'id', 'content', 'doc_id', 'doc_name'

        Raises:
            ValueError: If chunks list is empty
            Exception: If embedding generation fails
        """
        if not chunks or len(chunks) == 0:
            raise ValueError("Chunks list cannot be empty")

        if self.embedding_provider is None:
            raise ValueError("Embedding provider not set")

        self.chunks = chunks
        self.embeddings = []

        # Generate embeddings for all chunks
        contents = [chunk.get("content", "") for chunk in chunks]
        try:
            embeddings = await self.embedding_provider.embed_texts(contents)
            self.embeddings = embeddings
            logger.info(f"Vector index built with {len(embeddings)} embeddings")
        except Exception as e:
            logger.error(f"Error building vector index: {str(e)}")
            raise

    async def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """
        Retrieve chunks using vector similarity.

        Args:
            query: Query string
            top_k: Number of top results to return

        Returns:
            List of RetrievalResult objects

        Raises:
            ValueError: If query is empty or index not built
            Exception: If embedding generation fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if not self.embeddings or len(self.embeddings) == 0:
            raise ValueError("Index not built. Call build_index first.")

        if self.embedding_provider is None:
            raise ValueError("Embedding provider not set")

        try:
            # Generate query embedding
            query_embedding = await self.embedding_provider.embed_text(query)

            # Calculate similarity scores
            import numpy as np

            query_vec = np.array(query_embedding)
            scores = []

            for embedding in self.embeddings:
                emb_vec = np.array(embedding)
                # Cosine similarity
                similarity = np.dot(query_vec, emb_vec) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(emb_vec) + 1e-8
                )
                scores.append(similarity)

            # Get top-k results
            top_indices = sorted(
                range(len(scores)), key=lambda i: scores[i], reverse=True
            )[:top_k]

            results = []
            for idx in top_indices:
                if idx < len(self.chunks):
                    chunk = self.chunks[idx]
                    results.append(
                        RetrievalResult(
                            chunk_id=chunk.get("id", ""),
                            doc_id=chunk.get("doc_id", ""),
                            content=chunk.get("content", ""),
                            score=float(scores[idx]),
                            doc_name=chunk.get("doc_name", ""),
                        )
                    )

            logger.info(f"Vector retriever retrieved {len(results)} results for query: {query}")
            return results

        except Exception as e:
            logger.error(f"Error retrieving with vector similarity: {str(e)}")
            raise


class ResultFuser:
    """Fuses results from multiple retrieval methods using RRF."""

    @staticmethod
    def fuse_results(
        bm25_results: List[RetrievalResult],
        vector_results: List[RetrievalResult],
        k: int = 60,
    ) -> List[RetrievalResult]:
        """
        Fuse results using Reciprocal Rank Fusion (RRF).

        Args:
            bm25_results: Results from BM25 retrieval
            vector_results: Results from vector retrieval
            k: RRF parameter (default 60)

        Returns:
            Fused results sorted by RRF score

        Raises:
            ValueError: If both result lists are empty
        """
        if not bm25_results and not vector_results:
            raise ValueError("Both result lists cannot be empty")

        # Create RRF scores
        rrf_scores = {}

        # Process BM25 results
        for rank, result in enumerate(bm25_results, 1):
            chunk_id = result.chunk_id
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (k + rank)

        # Process vector results
        for rank, result in enumerate(vector_results, 1):
            chunk_id = result.chunk_id
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (k + rank)

        # Create result map for quick lookup
        result_map = {}
        for result in bm25_results + vector_results:
            if result.chunk_id not in result_map:
                result_map[result.chunk_id] = result

        # Sort by RRF score
        sorted_chunks = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        # Create fused results
        fused_results = []
        for chunk_id, rrf_score in sorted_chunks:
            if chunk_id in result_map:
                result = result_map[chunk_id]
                # Update score to RRF score
                fused_result = RetrievalResult(
                    chunk_id=result.chunk_id,
                    doc_id=result.doc_id,
                    content=result.content,
                    score=rrf_score,
                    doc_name=result.doc_name,
                )
                fused_results.append(fused_result)

        logger.info(f"Fused {len(fused_results)} results using RRF")
        return fused_results


class HybridRetriever:
    """Hybrid retriever combining BM25 and vector search."""

    def __init__(self, embedding_provider=None):
        """
        Initialize hybrid retriever.

        Args:
            embedding_provider: Provider for generating embeddings
        """
        self.bm25_retriever = BM25Retriever()
        self.vector_retriever = VectorRetriever(embedding_provider)
        self.embedding_provider = embedding_provider

    async def build_index(self, chunks: List[Dict]) -> None:
        """
        Build indices for both BM25 and vector retrieval.

        Args:
            chunks: List of chunk dicts

        Raises:
            ValueError: If chunks list is empty
        """
        if not chunks or len(chunks) == 0:
            raise ValueError("Chunks list cannot be empty")

        # Build BM25 index
        self.bm25_retriever.build_index(chunks)

        # Build vector index if embedding provider is available
        if self.embedding_provider:
            await self.vector_retriever.build_index(chunks)

    async def retrieve(
        self, query: str, top_k: int = 10, use_vector: bool = True
    ) -> List[RetrievalResult]:
        """
        Retrieve using hybrid search.

        Args:
            query: Query string
            top_k: Number of top results to return
            use_vector: Whether to use vector retrieval

        Returns:
            List of fused RetrievalResult objects

        Raises:
            ValueError: If query is empty
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        # Get BM25 results
        bm25_results = self.bm25_retriever.retrieve(query, top_k=top_k)

        # Get vector results if enabled
        vector_results = []
        if use_vector and self.embedding_provider:
            try:
                vector_results = await self.vector_retriever.retrieve(
                    query, top_k=top_k
                )
            except Exception as e:
                logger.warning(f"Vector retrieval failed, using BM25 only: {str(e)}")

        # Fuse results
        if vector_results:
            fused_results = ResultFuser.fuse_results(bm25_results, vector_results)
            return fused_results[:top_k]
        else:
            return bm25_results[:top_k]
