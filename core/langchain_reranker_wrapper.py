"""LangChain 1.x Reranker wrapper for Reranker Provider."""

import logging
from typing import List, Tuple, Optional
from .reranker_provider import RerankerProvider

logger = logging.getLogger(__name__)


class LangChainRerankerWrapper:
    """
    LangChain 1.x compatible wrapper for Reranker Provider.
    
    This wrapper adapts our custom Reranker Provider to work seamlessly with
    LangChain 1.x, providing reranking functionality with score normalization
    and fallback mechanisms.
    
    Attributes:
        reranker_provider: The underlying reranker provider instance
        model_name: Name of the model for identification
        normalize_scores: Whether to normalize scores to 0-1 range
        fallback_enabled: Whether to enable fallback when reranker is unavailable
    """

    def __init__(
        self,
        reranker_provider: Optional[RerankerProvider] = None,
        model_name: str = "custom",
        normalize_scores: bool = True,
        fallback_enabled: bool = True
    ):
        """
        Initialize LangChain Reranker wrapper.

        Args:
            reranker_provider: Our custom reranker provider instance (optional)
            model_name: Name of the model for identification
            normalize_scores: Whether to normalize scores to 0-1 range
            fallback_enabled: Whether to enable fallback when reranker is unavailable
        """
        self.reranker_provider = reranker_provider
        self.model_name = model_name
        self.normalize_scores = normalize_scores
        self.fallback_enabled = fallback_enabled

    def _normalize_scores(
        self, results: List[Tuple[int, float]]
    ) -> List[Tuple[int, float]]:
        """
        Normalize scores to 0-1 range.
        
        Uses min-max normalization to ensure all scores are between 0 and 1.

        Args:
            results: List of (index, score) tuples

        Returns:
            List of (index, normalized_score) tuples
        """
        if not results:
            return results

        scores = [score for _, score in results]
        min_score = min(scores)
        max_score = max(scores)
        
        # Avoid division by zero
        if max_score == min_score:
            # All scores are the same, normalize to 0.5
            return [(idx, 0.5) for idx, _ in results]
        
        # Min-max normalization
        normalized_results = [
            (idx, (score - min_score) / (max_score - min_score))
            for idx, score in results
        ]
        
        logger.debug(f"Normalized {len(results)} scores to 0-1 range")
        return normalized_results

    async def rerank(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """
        Rerank candidates based on query asynchronously.
        
        This method provides native async execution with score normalization
        and fallback support.

        Args:
            query: Query text
            candidates: List of candidate texts to rerank
            top_k: Number of top results to return

        Returns:
            List of (index, score) tuples sorted by score descending,
            with scores normalized to 0-1 range if normalize_scores is True
            
        Raises:
            ValueError: If query or candidates are empty and fallback is disabled
            Exception: If reranking fails and fallback is disabled
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if not candidates or len(candidates) == 0:
            raise ValueError("Candidates list cannot be empty")

        # Check if reranker provider is available
        if self.reranker_provider is None:
            if self.fallback_enabled:
                logger.warning("Reranker provider not set, returning original order")
                return self._fallback_ranking(candidates, top_k)
            else:
                raise ValueError("Reranker provider is not set and fallback is disabled")

        try:
            # Call the reranker provider
            results = await self.reranker_provider.rerank(query, candidates, top_k)
            
            # Normalize scores if enabled
            if self.normalize_scores:
                results = self._normalize_scores(results)
            
            logger.info(f"Reranked {len(candidates)} candidates, returning top {len(results)}")
            return results

        except Exception as e:
            logger.error(f"Error in reranking: {str(e)}")
            
            if self.fallback_enabled:
                logger.warning("Reranking failed, falling back to original order")
                return self._fallback_ranking(candidates, top_k)
            else:
                raise

    def rerank_sync(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """
        Rerank candidates based on query synchronously.
        
        This method wraps the async rerank method to provide synchronous execution.

        Args:
            query: Query text
            candidates: List of candidate texts to rerank
            top_k: Number of top results to return

        Returns:
            List of (index, score) tuples sorted by score descending
            
        Raises:
            ValueError: If query or candidates are empty and fallback is disabled
            Exception: If reranking fails and fallback is disabled
        """
        import asyncio

        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run async reranking in sync context
            result = loop.run_until_complete(
                self.rerank(query, candidates, top_k)
            )
            
            return result

        except Exception as e:
            logger.error(f"Error in synchronous reranking: {str(e)}")
            raise

    def _fallback_ranking(
        self, candidates: List[str], top_k: int
    ) -> List[Tuple[int, float]]:
        """
        Fallback ranking that returns original order with uniform scores.
        
        Used when reranker is unavailable or fails.

        Args:
            candidates: List of candidate texts
            top_k: Number of top results to return

        Returns:
            List of (index, score) tuples in original order with decreasing scores
        """
        # Return original order with linearly decreasing scores from 1.0 to 0.0
        num_results = min(top_k, len(candidates))
        
        if num_results == 1:
            return [(0, 1.0)]
        
        results = [
            (i, 1.0 - (i / (num_results - 1)))
            for i in range(num_results)
        ]
        
        logger.debug(f"Fallback ranking: returning top {num_results} in original order")
        return results

    async def validate_connection(self) -> bool:
        """
        Validate connection to reranker service.
        
        Returns:
            True if connection is valid or fallback is enabled, False otherwise
        """
        if self.reranker_provider is None:
            if self.fallback_enabled:
                logger.info("Reranker provider not set, but fallback is enabled")
                return True
            else:
                logger.warning("Reranker provider not set and fallback is disabled")
                return False

        try:
            is_valid = await self.reranker_provider.validate_connection()
            if is_valid:
                logger.info("Reranker provider connection validated successfully")
            else:
                logger.warning("Reranker provider connection validation failed")
            return is_valid

        except Exception as e:
            logger.error(f"Error validating reranker connection: {str(e)}")
            return self.fallback_enabled

    @property
    def _identifying_params(self) -> dict:
        """
        Get identifying parameters for the reranker.
        
        Returns:
            Dictionary of identifying parameters
        """
        return {
            "model_name": self.model_name,
            "normalize_scores": self.normalize_scores,
            "fallback_enabled": self.fallback_enabled,
            "has_provider": self.reranker_provider is not None,
        }
