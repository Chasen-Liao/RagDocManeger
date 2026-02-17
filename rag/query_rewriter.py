"""Query rewriting module for improving search quality."""

import logging
import json
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class QueryRewriteResult:
    """Result from query rewriting."""

    original_query: str
    rewritten_queries: List[str]
    hypothetical_docs: List[str]


class QueryRewriter:
    """Query rewriter using HyDE and query expansion."""

    def __init__(self, llm_provider=None):
        """
        Initialize query rewriter.

        Args:
            llm_provider: Provider for LLM calls
        """
        self.llm_provider = llm_provider

    async def rewrite_query(self, query: str) -> QueryRewriteResult:
        """
        Rewrite query using HyDE and expansion.

        Args:
            query: Original query string

        Returns:
            QueryRewriteResult with rewritten queries and hypothetical docs

        Raises:
            ValueError: If query is empty
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        rewritten_queries = [query]  # Include original query
        hypothetical_docs = []

        # Try HyDE rewriting if LLM provider is available
        if self.llm_provider:
            try:
                hyde_docs = await self._hyde_rewrite(query)
                hypothetical_docs.extend(hyde_docs)
            except Exception as e:
                logger.warning(f"HyDE rewriting failed: {str(e)}")

            # Try query expansion
            try:
                expanded_queries = await self._query_expansion(query)
                rewritten_queries.extend(expanded_queries)
            except Exception as e:
                logger.warning(f"Query expansion failed: {str(e)}")

        logger.info(
            f"Query rewritten: {len(rewritten_queries)} queries, "
            f"{len(hypothetical_docs)} hypothetical docs"
        )

        return QueryRewriteResult(
            original_query=query,
            rewritten_queries=rewritten_queries,
            hypothetical_docs=hypothetical_docs,
        )

    async def _hyde_rewrite(self, query: str) -> List[str]:
        """
        Generate hypothetical documents using HyDE method.

        Args:
            query: Query string

        Returns:
            List of hypothetical documents

        Raises:
            ValueError: If LLM provider is not set
            Exception: If LLM call fails
        """
        if self.llm_provider is None:
            raise ValueError("LLM provider not set")

        prompt = f"""Please write a short, informative document that would answer the following question. 
The document should be concise and directly address the question.

Question: {query}

Document:"""

        try:
            response = await self.llm_provider.generate(prompt, max_tokens=500)
            if response and response.strip():
                return [response.strip()]
            return []
        except Exception as e:
            logger.error(f"Error generating hypothetical document: {str(e)}")
            raise

    async def _query_expansion(self, query: str) -> List[str]:
        """
        Expand query with related queries.

        Args:
            query: Query string

        Returns:
            List of expanded queries

        Raises:
            ValueError: If LLM provider is not set
            Exception: If LLM call fails
        """
        if self.llm_provider is None:
            raise ValueError("LLM provider not set")

        prompt = f"""Generate 2-3 alternative phrasings or related queries for the following question. 
Return only the queries, one per line, without numbering or additional text.

Original question: {query}

Alternative queries:"""

        try:
            response = await self.llm_provider.generate(prompt, max_tokens=300)
            if response and response.strip():
                # Parse response into individual queries
                queries = [q.strip() for q in response.strip().split("\n") if q.strip()]
                return queries[:3]  # Limit to 3 queries
            return []
        except Exception as e:
            logger.error(f"Error expanding query: {str(e)}")
            raise

    async def rewrite_with_fallback(self, query: str) -> QueryRewriteResult:
        """
        Rewrite query with fallback to original if rewriting fails.

        Args:
            query: Query string

        Returns:
            QueryRewriteResult with at least the original query
        """
        try:
            return await self.rewrite_query(query)
        except Exception as e:
            logger.warning(f"Query rewriting failed, using original query: {str(e)}")
            return QueryRewriteResult(
                original_query=query,
                rewritten_queries=[query],
                hypothetical_docs=[],
            )
