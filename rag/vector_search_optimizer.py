"""Vector search optimization for Agent."""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import asyncio


@dataclass
class SearchQuery:
    """Represents a search query."""
    query_text: str
    kb_id: str
    top_k: int = 5


@dataclass
class SearchResult:
    """Represents a search result."""
    chunk_id: str
    content: str
    score: float
    metadata: Dict[str, Any]


class BatchEmbeddingProcessor:
    """Processes embeddings in batches."""
    
    def __init__(self, batch_size: int = 32):
        self.batch_size = batch_size
    
    async def embed_batch(self, texts: List[str], provider: Any) -> List[List[float]]:
        """Embed texts in batches."""
        embeddings = []
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = await provider.embed_documents(batch)
            embeddings.extend(batch_embeddings)
        
        return embeddings


class VectorSearchOptimizer:
    """Optimizes vector search performance."""
    
    def __init__(self, batch_size: int = 32, cache_size: int = 100):
        self.batch_size = batch_size
        self.cache_size = cache_size
        self.search_cache = {}
    
    async def search_optimized(self, query: SearchQuery, vector_store: Any,
                              embedding_provider: Any, 
                              use_cache: bool = True) -> List[SearchResult]:
        """Perform optimized search with caching."""
        cache_key = f"{query.kb_id}_{query.query_text}"
        
        if use_cache and cache_key in self.search_cache:
            return self.search_cache[cache_key]
        
        # Embed query
        query_embedding = await embedding_provider.embed_query(query.query_text)
        
        # Search
        results = await vector_store.search(
            query_embedding, 
            kb_id=query.kb_id,
            top_k=query.top_k
        )
        
        # Convert to SearchResult objects
        search_results = [
            SearchResult(
                chunk_id=r.get("chunk_id"),
                content=r.get("content"),
                score=r.get("score"),
                metadata=r.get("metadata", {})
            )
            for r in results
        ]
        
        # Cache results
        if use_cache:
            self.search_cache[cache_key] = search_results
            if len(self.search_cache) > self.cache_size:
                # Remove oldest entry
                oldest_key = next(iter(self.search_cache))
                del self.search_cache[oldest_key]
        
        return search_results
    
    async def batch_search(self, queries: List[SearchQuery], 
                          vector_store: Any,
                          embedding_provider: Any,
                          use_cache: bool = True) -> Dict[str, List[SearchResult]]:
        """Perform batch searches."""
        results = {}
        
        for query in queries:
            result = await self.search_optimized(
                query, vector_store, embedding_provider, use_cache
            )
            results[query.query_text] = result
        
        return results
