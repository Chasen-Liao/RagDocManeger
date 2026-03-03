"""Cache management for Agent optimization."""

import time
from typing import Any, Dict, Optional
from datetime import datetime, timedelta


class CacheManager:
    """Manages caching with TTL support."""
    
    def __init__(self, max_size: int = 100, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, tuple] = {}  # (value, expiry_time)
        self.hits = 0
        self.misses = 0
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set a cache value with TTL."""
        if ttl is None:
            ttl = self.default_ttl
        expiry = time.time() + ttl
        self.cache[key] = (value, expiry)
        
        # Evict oldest if over capacity
        if len(self.cache) > self.max_size:
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a cache value."""
        if key not in self.cache:
            self.misses += 1
            return None
        
        value, expiry = self.cache[key]
        if time.time() > expiry:
            del self.cache[key]
            self.misses += 1
            return None
        
        self.hits += 1
        return value
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.2f}%"
        }
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        import fnmatch
        keys_to_delete = [k for k in self.cache.keys() 
                         if fnmatch.fnmatch(k, pattern)]
        for key in keys_to_delete:
            del self.cache[key]
        return len(keys_to_delete)


class ToolResultCache:
    """Cache for tool execution results."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    async def set_tool_result(self, tool_name: str, tool_input: Dict, 
                             tool_output: Any):
        """Cache tool result."""
        key = f"tool_{tool_name}_{hash(str(tool_input))}"
        await self.cache_manager.set(key, tool_output)
    
    async def get_tool_result(self, tool_name: str, 
                             tool_input: Dict) -> Optional[Any]:
        """Get cached tool result."""
        key = f"tool_{tool_name}_{hash(str(tool_input))}"
        return await self.cache_manager.get(key)


class SearchResultCache:
    """Cache for search results."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    async def set_search_result(self, kb_id: str, query: str, 
                               results: list):
        """Cache search results."""
        key = f"search_{kb_id}_{hash(query)}"
        await self.cache_manager.set(key, results)
    
    async def get_search_result(self, kb_id: str, 
                               query: str) -> Optional[list]:
        """Get cached search results."""
        key = f"search_{kb_id}_{hash(query)}"
        return await self.cache_manager.get(key)
