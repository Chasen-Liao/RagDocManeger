"""Reranking module for improving retrieval results."""

import logging
from typing import List, Optional
from rag.retriever import RetrievalResult

logger = logging.getLogger(__name__)


class Reranker:
    """Reranker for improving retrieval results using cross-encoder models."""

    def __init__(self, reranker_provider=None):
        """
        Initialize reranker.

        Args:
            reranker_provider: Provider for reranking
        """
        self.reranker_provider = reranker_provider

    async def rerank(
        self, query: str, candidates: List[RetrievalResult], top_k: int = 5
    ) -> List[RetrievalResult]:
        """
        Rerank candidates based on query.

        Args:
            query: Query string
            candidates: List of RetrievalResult objects to rerank
            top_k: Number of top results to return

        Returns:
            Reranked list of RetrievalResult objects

        Raises:
            ValueError: If query or candidates are empty
            ValueError: If reranker provider is not set
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if not candidates or len(candidates) == 0:
            raise ValueError("Candidates list cannot be empty")

        if self.reranker_provider is None:
            logger.warning("Reranker provider not set, returning original results")
            return candidates[:top_k]

        try:
            # Extract candidate texts
            candidate_texts = [c.content for c in candidates]

            # Get reranking scores
            ranked_indices = await self.reranker_provider.rerank(
                query, candidate_texts, top_k=top_k
            )

            # Create reranked results
            reranked_results = []
            for idx, score in ranked_indices:
                if idx < len(candidates):
                    result = candidates[idx]
                    # Create new result with reranked score
                    reranked_result = RetrievalResult(
                        chunk_id=result.chunk_id,
                        doc_id=result.doc_id,
                        content=result.content,
                        score=score,
                        doc_name=result.doc_name,
                    )
                    reranked_results.append(reranked_result)

            logger.info(f"Reranked {len(reranked_results)} results")
            return reranked_results

        except Exception as e:
            logger.error(f"Error reranking results: {str(e)}")
            # Return original results on error
            return candidates[:top_k]

    async def rerank_with_fallback(
        self, query: str, candidates: List[RetrievalResult], top_k: int = 5
    ) -> List[RetrievalResult]:
        """
        Rerank with fallback to original results if reranker fails.

        Args:
            query: Query string
            candidates: List of RetrievalResult objects to rerank
            top_k: Number of top results to return

        Returns:
            Reranked or original list of RetrievalResult objects
        """
        try:
            return await self.rerank(query, candidates, top_k)
        except Exception as e:
            logger.warning(f"Reranking failed, using original results: {str(e)}")
            return candidates[:top_k]
