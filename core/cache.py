"""Caching mechanism for queries and models."""
import hashlib
import json
from typing import Any, Optional, Dict, Callable
from datetime import datetime, timedelta
from logger import logger


class CacheEntry:
    """Represents a cache entry with expiration."""
    
    def __init__(self, value: Any, ttl_seconds: Optional[int] = None):
        """
        Initialize cache entry.
        
        Args:
            value: Value to cache
            ttl_seconds: Time to live in seconds (None for no expiration)
        """
        self.value = value
        self.created_at = datetime.now()
        self.ttl_seconds = ttl_seconds
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds


class QueryCache:
    """Cache for search queries and results."""
    
    def __init__(self, max_size: int = 1000, default_ttl_seconds: int = 3600):
        """
        Initialize query cache.
        
        Args:
            max_size: Maximum number of cache entries
            default_ttl_seconds: Default time to live for cache entries
        """
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.default_ttl_seconds = default_ttl_seconds
        self.hits = 0
        self.misses = 0
    
    def _generate_key(self, kb_id: str, query: str, top_k: int) -> str:
        """Generate cache key from query parameters."""
        key_str = f"{kb_id}:{query}:{top_k}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, kb_id: str, query: str, top_k: int) -> Optional[Any]:
        """
        Get cached query result.
        
        Args:
            kb_id: Knowledge base ID
            query: Search query
            top_k: Number of top results
            
        Returns:
            Cached result or None if not found or expired
        """
        key = self._generate_key(kb_id, query, top_k)
        
        if key not in self.cache:
            self.misses += 1
            return None
        
        entry = self.cache[key]
        if entry.is_expired():
            del self.cache[key]
            self.misses += 1
            logger.debug(f"Cache entry expired: {key}")
            return None
        
        self.hits += 1
        logger.debug(f"Cache hit: {key}")
        return entry.value
    
    def set(
        self,
        kb_id: str,
        query: str,
        top_k: int,
        result: Any,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Set cached query result.
        
        Args:
            kb_id: Knowledge base ID
            query: Search query
            top_k: Number of top results
            result: Result to cache
            ttl_seconds: Time to live (uses default if None)
        """
        # Evict oldest entry if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k].created_at
            )
            del self.cache[oldest_key]
            logger.debug(f"Evicted oldest cache entry: {oldest_key}")
        
        key = self._generate_key(kb_id, query, top_k)
        ttl = ttl_seconds or self.default_ttl_seconds
        self.cache[key] = CacheEntry(result, ttl)
        logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Query cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate
        }


class ModelCache:
    """Cache for loaded models."""
    
    def __init__(self):
        """Initialize model cache."""
        self.cache: Dict[str, Any] = {}
    
    def get(self, model_key: str) -> Optional[Any]:
        """
        Get cached model.
        
        Args:
            model_key: Model identifier
            
        Returns:
            Cached model or None if not found
        """
        if model_key not in self.cache:
            logger.debug(f"Model not in cache: {model_key}")
            return None
        
        logger.debug(f"Model cache hit: {model_key}")
        return self.cache[model_key]
    
    def set(self, model_key: str, model: Any) -> None:
        """
        Set cached model.
        
        Args:
            model_key: Model identifier
            model: Model to cache
        """
        self.cache[model_key] = model
        logger.debug(f"Model cached: {model_key}")
    
    def clear(self, model_key: Optional[str] = None) -> None:
        """
        Clear model cache.
        
        Args:
            model_key: Specific model to clear (clears all if None)
        """
        if model_key:
            if model_key in self.cache:
                del self.cache[model_key]
                logger.debug(f"Model cache cleared: {model_key}")
        else:
            self.cache.clear()
            logger.info("Model cache cleared")
    
    def get_cached_models(self) -> list:
        """Get list of cached model keys."""
        return list(self.cache.keys())


class CacheManager:
    """Manager for all caching operations."""
    
    def __init__(self, query_cache_size: int = 1000, query_ttl_seconds: int = 3600):
        """
        Initialize cache manager.
        
        Args:
            query_cache_size: Maximum size of query cache
            query_ttl_seconds: Default TTL for query cache entries
        """
        self.query_cache = QueryCache(query_cache_size, query_ttl_seconds)
        self.model_cache = ModelCache()
    
    def get_query_result(
        self,
        kb_id: str,
        query: str,
        top_k: int
    ) -> Optional[Any]:
        """Get cached query result."""
        return self.query_cache.get(kb_id, query, top_k)
    
    def set_query_result(
        self,
        kb_id: str,
        query: str,
        top_k: int,
        result: Any,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Set cached query result."""
        self.query_cache.set(kb_id, query, top_k, result, ttl_seconds)
    
    def get_model(self, model_key: str) -> Optional[Any]:
        """Get cached model."""
        return self.model_cache.get(model_key)
    
    def set_model(self, model_key: str, model: Any) -> None:
        """Set cached model."""
        self.model_cache.set(model_key, model)
    
    def clear_query_cache(self) -> None:
        """Clear query cache."""
        self.query_cache.clear()
    
    def clear_model_cache(self, model_key: Optional[str] = None) -> None:
        """Clear model cache."""
        self.model_cache.clear(model_key)
    
    def clear_all(self) -> None:
        """Clear all caches."""
        self.query_cache.clear()
        self.model_cache.clear()
        logger.info("All caches cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "query_cache": self.query_cache.get_stats(),
            "model_cache": {
                "cached_models": self.model_cache.get_cached_models()
            }
        }


# Global cache manager instance
cache_manager = CacheManager()
