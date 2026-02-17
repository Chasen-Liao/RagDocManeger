"""Search service for RAG operations."""

import logging
from typing import List, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session
from models.orm import KnowledgeBase, Chunk
from rag.retriever import HybridRetriever, RetrievalResult
from rag.reranker import Reranker
from rag.query_rewriter import QueryRewriter

logger = logging.getLogger(__name__)


@dataclass
class SearchResponse:
    """Response from search."""

    query: str
    results: List[RetrievalResult]
    total_count: int
    rewritten_query: Optional[str] = None


class SearchService:
    """Service for searching documents."""

    def __init__(
        self,
        db: Session,
        embedding_provider=None,
        reranker_provider=None,
        llm_provider=None,
    ):
        """
        Initialize search service.

        Args:
            db: Database session
            embedding_provider: Provider for generating embeddings
            reranker_provider: Provider for reranking results
            llm_provider: Provider for LLM calls
        """
        self.db = db
        self.embedding_provider = embedding_provider
        self.reranker_provider = reranker_provider
        self.llm_provider = llm_provider

        self.hybrid_retriever = HybridRetriever(embedding_provider)
        self.reranker = Reranker(reranker_provider)
        self.query_rewriter = QueryRewriter(llm_provider)

    async def search(
        self, kb_id: str, query: str, top_k: int = 5
    ) -> SearchResponse:
        """
        Execute basic search.

        Args:
            kb_id: Knowledge base ID
            query: Query string
            top_k: Number of top results to return

        Returns:
            SearchResponse with results

        Raises:
            ValueError: If knowledge base doesn't exist or query is empty
            Exception: If search fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        # Verify knowledge base exists
        kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise ValueError(f"Knowledge base not found: {kb_id}")

        try:
            # Get chunks for this knowledge base
            chunks = self.db.query(Chunk).filter(Chunk.kb_id == kb_id).all()
            if not chunks:
                logger.warning(f"No chunks found in knowledge base {kb_id}")
                return SearchResponse(query=query, results=[], total_count=0)

            # Convert chunks to retrieval format
            chunk_dicts = [
                {
                    "id": chunk.id,
                    "content": chunk.content,
                    "doc_id": chunk.doc_id,
                    "doc_name": chunk.document.name if chunk.document else "",
                }
                for chunk in chunks
            ]

            # Build index
            await self.hybrid_retriever.build_index(chunk_dicts)

            # Retrieve results
            results = await self.hybrid_retriever.retrieve(
                query, top_k=top_k * 2, use_vector=bool(self.embedding_provider)
            )

            # Rerank results
            reranked_results = await self.reranker.rerank_with_fallback(
                query, results, top_k=top_k
            )

            logger.info(f"Search completed: {len(reranked_results)} results")

            return SearchResponse(
                query=query,
                results=reranked_results,
                total_count=len(reranked_results),
            )

        except Exception as e:
            logger.error(f"Error searching: {str(e)}")
            raise

    async def search_with_rewrite(
        self, kb_id: str, query: str, top_k: int = 5
    ) -> SearchResponse:
        """
        Execute search with query rewriting.

        Args:
            kb_id: Knowledge base ID
            query: Query string
            top_k: Number of top results to return

        Returns:
            SearchResponse with results

        Raises:
            ValueError: If knowledge base doesn't exist or query is empty
            Exception: If search fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        # Verify knowledge base exists
        kb = self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise ValueError(f"Knowledge base not found: {kb_id}")

        try:
            # Rewrite query
            rewrite_result = await self.query_rewriter.rewrite_with_fallback(query)

            # Get chunks for this knowledge base
            chunks = self.db.query(Chunk).filter(Chunk.kb_id == kb_id).all()
            if not chunks:
                logger.warning(f"No chunks found in knowledge base {kb_id}")
                return SearchResponse(
                    query=query,
                    results=[],
                    total_count=0,
                    rewritten_query=query,
                )

            # Convert chunks to retrieval format
            chunk_dicts = [
                {
                    "id": chunk.id,
                    "content": chunk.content,
                    "doc_id": chunk.doc_id,
                    "doc_name": chunk.document.name if chunk.document else "",
                }
                for chunk in chunks
            ]

            # Build index
            await self.hybrid_retriever.build_index(chunk_dicts)

            # Search with all rewritten queries
            all_results = []
            for rewritten_query in rewrite_result.rewritten_queries:
                try:
                    results = await self.hybrid_retriever.retrieve(
                        rewritten_query,
                        top_k=top_k * 2,
                        use_vector=bool(self.embedding_provider),
                    )
                    all_results.extend(results)
                except Exception as e:
                    logger.warning(f"Error retrieving with query '{rewritten_query}': {e}")

            # Deduplicate results by chunk_id
            seen = set()
            unique_results = []
            for result in all_results:
                if result.chunk_id not in seen:
                    seen.add(result.chunk_id)
                    unique_results.append(result)

            # Rerank results
            reranked_results = await self.reranker.rerank_with_fallback(
                query, unique_results, top_k=top_k
            )

            logger.info(
                f"Search with rewrite completed: {len(reranked_results)} results"
            )

            return SearchResponse(
                query=query,
                results=reranked_results,
                total_count=len(reranked_results),
                rewritten_query=" | ".join(rewrite_result.rewritten_queries),
            )

        except Exception as e:
            logger.error(f"Error searching with rewrite: {str(e)}")
            raise
