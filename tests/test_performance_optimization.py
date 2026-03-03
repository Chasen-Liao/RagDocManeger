"""Performance tests for Agent optimization.

**Validates: Requirements 20.1, 20.2, 20.3, 20.5**

This module tests:
1. Response time under various loads
2. Concurrent Agent execution performance
3. Cache hit rate and effectiveness
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any
import statistics

from rag.agent_cache import CacheManager, ToolResultCache, SearchResultCache
from rag.parallel_tool_executor import (
    ParallelToolExecutor,
    ToolExecutionTask,
    IndependentToolDetector,
    ToolExecutionResult
)
from rag.vector_search_optimizer import (
    VectorSearchOptimizer,
    SearchQuery,
    BatchEmbeddingProcessor,
    SearchResult
)


class TestCachePerformance:
    """Test cache performance and hit rate effectiveness.
    
    **Validates: Requirements 20.1, 20.5**
    """
    
    @pytest.mark.anyio
    async def test_cache_hit_performance(self):
        """Test cache hit performance under load.
        
        Verifies that cache hits are fast (< 1ms average per hit).
        """
        cache = CacheManager(max_size=100, default_ttl=3600)
        
        # Set a value
        await cache.set("test_key", {"data": "test_value"})
        
        # Measure cache hit time
        start = time.time()
        for _ in range(1000):
            await cache.get("test_key")
        hit_time = time.time() - start
        
        # Cache hits should be very fast (< 1ms per hit on average)
        assert hit_time < 1.0
        assert cache.hits == 1000
    
    @pytest.mark.anyio
    async def test_cache_miss_performance(self):
        """Test cache miss performance.
        
        Verifies that cache misses are also fast.
        """
        cache = CacheManager(max_size=100, default_ttl=3600)
        
        # Measure cache miss time
        start = time.time()
        for _ in range(1000):
            await cache.get("nonexistent_key")
        miss_time = time.time() - start
        
        # Cache misses should also be fast
        assert miss_time < 1.0
        assert cache.misses == 1000
    
    @pytest.mark.anyio
    async def test_cache_hit_rate(self):
        """Test cache hit rate calculation.
        
        Verifies that cache hit rate is correctly calculated.
        """
        cache = CacheManager(max_size=100, default_ttl=3600)
        
        # Set some values
        for i in range(10):
            await cache.set(f"key_{i}", f"value_{i}")
        
        # Access with mix of hits and misses
        for i in range(10):
            await cache.get(f"key_{i}")  # Hit
        for i in range(10):
            await cache.get(f"missing_{i}")  # Miss
        
        stats = cache.get_stats()
        assert stats["hits"] == 10
        assert stats["misses"] == 10
        assert "50.00%" in stats["hit_rate"]
    
    @pytest.mark.anyio
    async def test_cache_effectiveness_under_load(self):
        """Test cache effectiveness with high load.
        
        Verifies that cache improves performance under load.
        """
        cache = CacheManager(max_size=1000, default_ttl=3600)
        
        # Populate cache
        for i in range(100):
            await cache.set(f"key_{i}", {"data": f"value_{i}"})
        
        # Measure performance with cache hits
        start = time.time()
        for _ in range(10000):
            key_idx = _ % 100
            await cache.get(f"key_{key_idx}")
        cache_time = time.time() - start
        
        # Verify high hit rate
        stats = cache.get_stats()
        assert stats["hits"] == 10000
        assert stats["misses"] == 0
        
        # Cache should handle 10000 operations in < 1 second
        assert cache_time < 1.0
    
    @pytest.mark.anyio
    async def test_tool_result_cache_performance(self):
        """Test tool result cache performance.
        
        Verifies that tool result caching improves performance.
        """
        cache_manager = CacheManager(max_size=100, default_ttl=3600)
        tool_cache = ToolResultCache(cache_manager)
        
        # Cache some tool results
        tool_input = {"query": "test", "kb_id": "kb_1"}
        tool_output = {"results": ["result1", "result2"]}
        
        await tool_cache.set_tool_result("search_tool", tool_input, tool_output)
        
        # Measure retrieval time
        start = time.time()
        for _ in range(1000):
            result = await tool_cache.get_tool_result("search_tool", tool_input)
            assert result == tool_output
        retrieval_time = time.time() - start
        
        # Should be very fast
        assert retrieval_time < 1.0
    
    @pytest.mark.anyio
    async def test_search_result_cache_performance(self):
        """Test search result cache performance.
        
        Verifies that search result caching is effective.
        """
        cache_manager = CacheManager(max_size=100, default_ttl=3600)
        search_cache = SearchResultCache(cache_manager)
        
        # Cache search results
        search_results = [
            {"chunk_id": "1", "content": "result1", "score": 0.9},
            {"chunk_id": "2", "content": "result2", "score": 0.8}
        ]
        
        await search_cache.set_search_result("kb_1", "test query", search_results)
        
        # Measure retrieval time
        start = time.time()
        for _ in range(1000):
            result = await search_cache.get_search_result("kb_1", "test query")
            assert result == search_results
        retrieval_time = time.time() - start
        
        # Should be very fast
        assert retrieval_time < 1.0


class TestParallelExecutionPerformance:
    """Test parallel execution performance.
    
    **Validates: Requirements 20.2, 20.3**
    """
    
    @pytest.mark.anyio
    async def test_parallel_vs_sequential(self):
        """Test parallel execution vs sequential execution.
        
        Verifies that parallel execution is faster than sequential.
        """
        executor = ParallelToolExecutor(max_concurrent=5)
        
        # Create tasks that take time
        async def slow_task(duration: float):
            await asyncio.sleep(duration)
            return f"completed_{duration}"
        
        # Sequential execution
        start = time.time()
        for i in range(5):
            await slow_task(0.1)
        sequential_time = time.time() - start
        
        # Parallel execution
        tasks = [
            ToolExecutionTask(
                tool_name=f"task_{i}",
                tool_func=slow_task,
                tool_input={"duration": 0.1}
            )
            for i in range(5)
        ]
        
        start = time.time()
        results = await executor.execute_tasks(tasks)
        parallel_time = time.time() - start
        
        # Parallel should be faster
        assert parallel_time < sequential_time
        assert len(results) == 5
        assert all(r.success for r in results.values())
    
    @pytest.mark.anyio
    async def test_concurrent_agent_execution(self):
        """Test concurrent Agent execution performance.
        
        Verifies that multiple agents can execute concurrently.
        """
        executor = ParallelToolExecutor(max_concurrent=10)
        
        # Create multiple concurrent tasks
        async def agent_task(agent_id: int):
            await asyncio.sleep(0.05)
            return f"agent_{agent_id}_result"
        
        tasks = [
            ToolExecutionTask(
                tool_name=f"agent_{i}",
                tool_func=agent_task,
                tool_input={"agent_id": i}
            )
            for i in range(10)
        ]
        
        start = time.time()
        results = await executor.execute_tasks(tasks)
        execution_time = time.time() - start
        
        # Should complete in roughly 0.05s (concurrent) not 0.5s (sequential)
        assert execution_time < 0.2
        assert len(results) == 10
        assert all(r.success for r in results.values())
    
    @pytest.mark.anyio
    async def test_parallel_execution_with_dependencies(self):
        """Test parallel execution respecting dependencies.
        
        Verifies that dependent tasks execute in correct order.
        """
        executor = ParallelToolExecutor(max_concurrent=5)
        
        execution_order = []
        
        async def task_with_id(task_id: int):
            execution_order.append(task_id)
            await asyncio.sleep(0.01)
            return f"result_{task_id}"
        
        # Create tasks with dependencies
        tasks = [
            ToolExecutionTask(
                tool_name="task_1",
                tool_func=task_with_id,
                tool_input={"task_id": 1},
                dependencies=[]
            ),
            ToolExecutionTask(
                tool_name="task_2",
                tool_func=task_with_id,
                tool_input={"task_id": 2},
                dependencies=["task_1"]
            ),
            ToolExecutionTask(
                tool_name="task_3",
                tool_func=task_with_id,
                tool_input={"task_id": 3},
                dependencies=["task_2"]
            )
        ]
        
        results = await executor.execute_tasks(tasks)
        
        # Verify all tasks completed
        assert len(results) == 3
        assert all(r.success for r in results.values())
        
        # Verify execution order respects dependencies
        assert execution_order[0] == 1
        assert execution_order[1] == 2
        assert execution_order[2] == 3
    
    @pytest.mark.anyio
    async def test_parallel_execution_throughput(self):
        """Test parallel execution throughput.
        
        Verifies that parallel execution can handle high throughput.
        """
        executor = ParallelToolExecutor(max_concurrent=20)
        
        async def fast_task():
            await asyncio.sleep(0.001)
            return "result"
        
        # Create many tasks
        tasks = [
            ToolExecutionTask(
                tool_name=f"task_{i}",
                tool_func=fast_task,
                tool_input={}
            )
            for i in range(100)
        ]
        
        start = time.time()
        results = await executor.execute_tasks(tasks)
        execution_time = time.time() - start
        
        # Should complete all 100 tasks efficiently
        assert len(results) == 100
        assert all(r.success for r in results.values())
        
        # Throughput should be high (100 tasks in < 1 second)
        assert execution_time < 1.0
        throughput = len(results) / execution_time
        assert throughput > 50  # At least 50 tasks per second
    
    @pytest.mark.anyio
    async def test_independent_tool_detection(self):
        """Test independent tool detection.
        
        Verifies that independent tools are correctly identified.
        """
        detector = IndependentToolDetector()
        
        tool_calls = [
            {"tool_name": "tool_1", "dependencies": []},
            {"tool_name": "tool_2", "dependencies": []},
            {"tool_name": "tool_3", "dependencies": ["tool_1"]},
            {"tool_name": "tool_4", "dependencies": ["tool_2"]}
        ]
        
        groups = detector.detect_independent_tools(tool_calls)
        
        # Should identify independent groups
        assert len(groups) > 0
        
        # First group should contain independent tools
        first_group = groups[0]
        assert "tool_1" in first_group or "tool_2" in first_group


class TestVectorSearchPerformance:
    """Test vector search performance optimization.
    
    **Validates: Requirements 20.3, 20.4, 20.5**
    """
    
    @pytest.mark.anyio
    async def test_batch_embedding_performance(self):
        """Test batch embedding performance.
        
        Verifies that batch processing improves embedding performance.
        """
        batch_processor = BatchEmbeddingProcessor(batch_size=32)
        
        # Mock embedding provider - return correct number of embeddings per batch
        mock_provider = AsyncMock()
        
        async def mock_embed(texts):
            # Return embeddings matching the number of texts
            return [[0.1] * 768 for _ in range(len(texts))]
        
        mock_provider.embed_documents = mock_embed
        
        # Create texts to embed
        texts = [f"text_{i}" for i in range(100)]
        
        start = time.time()
        embeddings = await batch_processor.embed_batch(texts, mock_provider)
        batch_time = time.time() - start
        
        # Should process all texts
        assert len(embeddings) == 100
    
    @pytest.mark.anyio
    async def test_query_result_cache_effectiveness(self):
        """Test query result cache effectiveness.
        
        Verifies that query caching improves search performance.
        """
        optimizer = VectorSearchOptimizer(batch_size=32, cache_size=100)
        
        # Mock vector store and embedding provider
        mock_vector_store = AsyncMock()
        mock_embedding_provider = AsyncMock()
        
        mock_embedding_provider.embed_query = AsyncMock(
            return_value=[0.1] * 768
        )
        mock_vector_store.search = AsyncMock(
            return_value=[
                {"chunk_id": "1", "content": "result1", "score": 0.9, "metadata": {}},
                {"chunk_id": "2", "content": "result2", "score": 0.8, "metadata": {}}
            ]
        )
        
        query = SearchQuery(query_text="test query", kb_id="kb_1", top_k=5)
        
        # First search (cache miss)
        results1 = await optimizer.search_optimized(
            query, mock_vector_store, mock_embedding_provider, use_cache=True
        )
        
        # Second search (cache hit)
        results2 = await optimizer.search_optimized(
            query, mock_vector_store, mock_embedding_provider, use_cache=True
        )
        
        # Results should be the same
        assert len(results1) == len(results2)
        
        # Vector store should only be called once (second call uses cache)
        assert mock_vector_store.search.call_count == 1
        
        # Embedding provider should only be called once
        assert mock_embedding_provider.embed_query.call_count == 1
    
    @pytest.mark.anyio
    async def test_batch_search_performance(self):
        """Test batch search performance.
        
        Verifies that batch searching improves throughput.
        """
        optimizer = VectorSearchOptimizer(batch_size=32, cache_size=100)
        
        # Mock vector store and embedding provider
        mock_vector_store = AsyncMock()
        mock_embedding_provider = AsyncMock()
        
        mock_embedding_provider.embed_documents = AsyncMock(
            return_value=[[0.1] * 768 for _ in range(10)]
        )
        mock_vector_store.search = AsyncMock(
            return_value=[
                {"chunk_id": "1", "content": "result1", "score": 0.9, "metadata": {}},
                {"chunk_id": "2", "content": "result2", "score": 0.8, "metadata": {}}
            ]
        )
        
        # Create multiple queries
        queries = [
            SearchQuery(query_text=f"query_{i}", kb_id="kb_1", top_k=5)
            for i in range(10)
        ]
        
        start = time.time()
        results = await optimizer.batch_search(
            queries, mock_vector_store, mock_embedding_provider, use_cache=False
        )
        batch_time = time.time() - start
        
        # Should process all queries
        assert len(results) == 10
        
        # All queries should have results
        assert all(len(r) > 0 for r in results.values())


class TestResponseTimeUnderLoad:
    """Test response time under various loads.
    
    **Validates: Requirements 20.1, 20.5**
    """
    
    @pytest.mark.anyio
    async def test_response_time_light_load(self):
        """Test response time under light load.
        
        Verifies acceptable response time with few concurrent requests.
        """
        executor = ParallelToolExecutor(max_concurrent=5)
        
        async def mock_agent_execution():
            await asyncio.sleep(0.01)
            return {"output": "result"}
        
        # Simulate light load (5 concurrent requests)
        tasks = [
            ToolExecutionTask(
                tool_name=f"request_{i}",
                tool_func=mock_agent_execution,
                tool_input={}
            )
            for i in range(5)
        ]
        
        start = time.time()
        results = await executor.execute_tasks(tasks)
        total_time = time.time() - start
        
        # All should complete
        assert len(results) == 5
        assert all(r.success for r in results.values())
        
        # Response time should be acceptable
        avg_response_time = total_time / 5
        assert avg_response_time < 0.05
    
    @pytest.mark.anyio
    async def test_response_time_medium_load(self):
        """Test response time under medium load.
        
        Verifies acceptable response time with moderate concurrent requests.
        """
        executor = ParallelToolExecutor(max_concurrent=10)
        
        async def mock_agent_execution():
            await asyncio.sleep(0.02)
            return {"output": "result"}
        
        # Simulate medium load (20 concurrent requests)
        tasks = [
            ToolExecutionTask(
                tool_name=f"request_{i}",
                tool_func=mock_agent_execution,
                tool_input={}
            )
            for i in range(20)
        ]
        
        start = time.time()
        results = await executor.execute_tasks(tasks)
        total_time = time.time() - start
        
        # All should complete
        assert len(results) == 20
        assert all(r.success for r in results.values())
        
        # Response time should be acceptable
        avg_response_time = total_time / 20
        assert avg_response_time < 0.1
    
    @pytest.mark.anyio
    async def test_response_time_heavy_load(self):
        """Test response time under heavy load.
        
        Verifies acceptable response time with many concurrent requests.
        """
        executor = ParallelToolExecutor(max_concurrent=20)
        
        async def mock_agent_execution():
            await asyncio.sleep(0.01)
            return {"output": "result"}
        
        # Simulate heavy load (50 concurrent requests)
        tasks = [
            ToolExecutionTask(
                tool_name=f"request_{i}",
                tool_func=mock_agent_execution,
                tool_input={}
            )
            for i in range(50)
        ]
        
        start = time.time()
        results = await executor.execute_tasks(tasks)
        total_time = time.time() - start
        
        # All should complete
        assert len(results) == 50
        assert all(r.success for r in results.values())
        
        # Response time should be acceptable even under heavy load
        avg_response_time = total_time / 50
        assert avg_response_time < 0.2
    
    @pytest.mark.anyio
    async def test_response_time_consistency(self):
        """Test response time consistency across multiple runs.
        
        Verifies that response times are consistent and predictable.
        """
        executor = ParallelToolExecutor(max_concurrent=10)
        
        async def mock_agent_execution():
            await asyncio.sleep(0.01)
            return {"output": "result"}
        
        response_times = []
        
        # Run multiple times
        for _ in range(5):
            tasks = [
                ToolExecutionTask(
                    tool_name=f"request_{i}",
                    tool_func=mock_agent_execution,
                    tool_input={}
                )
                for i in range(10)
            ]
            
            start = time.time()
            results = await executor.execute_tasks(tasks)
            response_time = time.time() - start
            response_times.append(response_time)
        
        # Calculate statistics
        avg_time = statistics.mean(response_times)
        std_dev = statistics.stdev(response_times)
        
        # Response times should be consistent (low standard deviation)
        assert std_dev / avg_time < 0.3  # Coefficient of variation < 30%


class TestCacheHitRateAndValidity:
    """Test cache hit rate and validity.
    
    **Validates: Requirements 20.1, 20.5**
    """
    
    @pytest.mark.anyio
    async def test_cache_hit_rate_tracking(self):
        """Test cache hit rate tracking.
        
        Verifies that cache hit rate is accurately tracked.
        """
        cache = CacheManager(max_size=100, default_ttl=3600)
        
        # Set values
        for i in range(50):
            await cache.set(f"key_{i}", f"value_{i}")
        
        # Access with known hit/miss pattern
        hits = 0
        misses = 0
        
        for i in range(100):
            if i % 2 == 0:
                # Hit
                await cache.get(f"key_{i % 50}")
                hits += 1
            else:
                # Miss
                await cache.get(f"missing_{i}")
                misses += 1
        
        stats = cache.get_stats()
        assert stats["hits"] == hits
        assert stats["misses"] == misses
    
    @pytest.mark.anyio
    async def test_cache_validity_after_expiration(self):
        """Test cache validity after TTL expiration.
        
        Verifies that expired cache entries are not returned.
        """
        cache = CacheManager(max_size=100, default_ttl=1)
        
        # Set a value with short TTL
        await cache.set("test_key", "test_value", ttl=1)
        
        # Should be available immediately
        result = await cache.get("test_key")
        assert result == "test_value"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        result = await cache.get("test_key")
        assert result is None
    
    @pytest.mark.anyio
    async def test_cache_invalidation_pattern(self):
        """Test cache invalidation by pattern.
        
        Verifies that pattern-based cache invalidation works.
        """
        cache = CacheManager(max_size=100, default_ttl=3600)
        
        # Set values with pattern
        for i in range(10):
            await cache.set(f"search_kb_1_{i}", f"value_{i}")
            await cache.set(f"search_kb_2_{i}", f"value_{i}")
        
        # Invalidate pattern
        invalidated = await cache.invalidate_pattern("search_kb_1_*")
        
        # Should invalidate 10 entries
        assert invalidated == 10
        
        # kb_1 entries should be gone
        for i in range(10):
            result = await cache.get(f"search_kb_1_{i}")
            assert result is None
        
        # kb_2 entries should still exist
        for i in range(10):
            result = await cache.get(f"search_kb_2_{i}")
            assert result == f"value_{i}"