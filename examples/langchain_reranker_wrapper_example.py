"""Example usage of LangChain Reranker wrapper."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.reranker_provider import SiliconFlowRerankerProvider
from core.langchain_reranker_wrapper import LangChainRerankerWrapper


async def example_basic_usage():
    """Example: Basic reranking with SiliconFlow provider."""
    print("\n=== Example 1: Basic Reranking ===")
    
    # Get API key from environment
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        print("⚠️  SILICONFLOW_API_KEY not set, skipping real API example")
        return
    
    # Create provider
    provider = SiliconFlowRerankerProvider(
        api_key=api_key,
        model="BAAI/bge-reranker-large"
    )
    
    # Create wrapper
    reranker = LangChainRerankerWrapper(
        reranker_provider=provider,
        model_name="BAAI/bge-reranker-large",
        normalize_scores=True
    )
    
    # Rerank candidates
    query = "What is artificial intelligence?"
    candidates = [
        "Deep learning uses neural networks with multiple layers",
        "Artificial intelligence is the simulation of human intelligence by machines",
        "Machine learning is a subset of AI that learns from data",
        "Python is a popular programming language",
        "Neural networks are inspired by biological neurons"
    ]
    
    print(f"Query: {query}")
    print(f"Candidates: {len(candidates)}")
    
    # Rerank
    results = await reranker.rerank(query, candidates, top_k=3)
    
    print("\nTop 3 reranked results:")
    for idx, score in results:
        print(f"  [{idx}] Score: {score:.4f} - {candidates[idx][:60]}...")
    
    # Clean up
    await provider.close()


async def example_score_normalization():
    """Example: Score normalization demonstration."""
    print("\n=== Example 2: Score Normalization ===")
    
    # Mock provider for demonstration
    class MockProvider:
        async def rerank(self, query, candidates, top_k=5):
            # Return raw scores (not normalized)
            return [(0, 100.0), (1, 75.0), (2, 50.0), (3, 25.0), (4, 0.0)]
        
        async def validate_connection(self):
            return True
    
    provider = MockProvider()
    
    # With normalization
    reranker_normalized = LangChainRerankerWrapper(
        reranker_provider=provider,
        normalize_scores=True
    )
    
    # Without normalization
    reranker_raw = LangChainRerankerWrapper(
        reranker_provider=provider,
        normalize_scores=False
    )
    
    candidates = [f"Document {i}" for i in range(5)]
    
    # Compare results
    results_normalized = await reranker_normalized.rerank("query", candidates, top_k=5)
    results_raw = await reranker_raw.rerank("query", candidates, top_k=5)
    
    print("With normalization (0-1 range):")
    for idx, score in results_normalized:
        print(f"  [{idx}] Score: {score:.4f}")
    
    print("\nWithout normalization (raw scores):")
    for idx, score in results_raw:
        print(f"  [{idx}] Score: {score:.4f}")


async def example_fallback_mechanism():
    """Example: Fallback mechanism when reranker is unavailable."""
    print("\n=== Example 3: Fallback Mechanism ===")
    
    # Create wrapper without provider
    reranker = LangChainRerankerWrapper(
        reranker_provider=None,
        fallback_enabled=True
    )
    
    candidates = [
        "First document",
        "Second document",
        "Third document",
        "Fourth document",
        "Fifth document"
    ]
    
    print("Reranking without provider (fallback mode):")
    results = await reranker.rerank("query", candidates, top_k=5)
    
    print("Results (original order with decreasing scores):")
    for idx, score in results:
        print(f"  [{idx}] Score: {score:.4f} - {candidates[idx]}")


async def example_error_handling():
    """Example: Error handling with and without fallback."""
    print("\n=== Example 4: Error Handling ===")
    
    # Mock provider that always fails
    class FailingProvider:
        async def rerank(self, query, candidates, top_k=5):
            raise Exception("API connection failed")
        
        async def validate_connection(self):
            return False
    
    provider = FailingProvider()
    
    # With fallback enabled
    reranker_with_fallback = LangChainRerankerWrapper(
        reranker_provider=provider,
        fallback_enabled=True
    )
    
    # Without fallback
    reranker_no_fallback = LangChainRerankerWrapper(
        reranker_provider=provider,
        fallback_enabled=False
    )
    
    candidates = ["Doc 1", "Doc 2", "Doc 3"]
    
    # Test with fallback
    print("With fallback enabled:")
    try:
        results = await reranker_with_fallback.rerank("query", candidates, top_k=3)
        print(f"  ✓ Fallback successful, got {len(results)} results")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    # Test without fallback
    print("\nWithout fallback:")
    try:
        results = await reranker_no_fallback.rerank("query", candidates, top_k=3)
        print(f"  ✓ Got {len(results)} results")
    except Exception as e:
        print(f"  ✗ Error raised as expected: {type(e).__name__}")


async def example_connection_validation():
    """Example: Connection validation."""
    print("\n=== Example 5: Connection Validation ===")
    
    # Mock providers
    class WorkingProvider:
        async def rerank(self, query, candidates, top_k=5):
            return [(0, 0.9), (1, 0.7)]
        
        async def validate_connection(self):
            return True
    
    class BrokenProvider:
        async def rerank(self, query, candidates, top_k=5):
            raise Exception("Connection failed")
        
        async def validate_connection(self):
            return False
    
    # Test working provider
    reranker_working = LangChainRerankerWrapper(
        reranker_provider=WorkingProvider(),
        model_name="working"
    )
    
    is_valid = await reranker_working.validate_connection()
    print(f"Working provider validation: {'✓ Valid' if is_valid else '✗ Invalid'}")
    
    # Test broken provider with fallback
    reranker_broken = LangChainRerankerWrapper(
        reranker_provider=BrokenProvider(),
        fallback_enabled=True
    )
    
    is_valid = await reranker_broken.validate_connection()
    print(f"Broken provider with fallback: {'✓ Valid' if is_valid else '✗ Invalid'}")
    
    # Test no provider with fallback
    reranker_no_provider = LangChainRerankerWrapper(
        reranker_provider=None,
        fallback_enabled=True
    )
    
    is_valid = await reranker_no_provider.validate_connection()
    print(f"No provider with fallback: {'✓ Valid' if is_valid else '✗ Invalid'}")


async def example_rag_integration():
    """Example: Integration with RAG pipeline."""
    print("\n=== Example 6: RAG Pipeline Integration ===")
    
    # Mock search results
    class SearchResult:
        def __init__(self, content, score):
            self.content = content
            self.score = score
    
    # Simulate initial retrieval
    initial_results = [
        SearchResult("AI is artificial intelligence", 0.8),
        SearchResult("Python is a programming language", 0.75),
        SearchResult("Machine learning is a subset of AI", 0.85),
        SearchResult("Deep learning uses neural networks", 0.82),
        SearchResult("Data science involves statistics", 0.70),
    ]
    
    print(f"Initial retrieval: {len(initial_results)} results")
    
    # Create reranker (fallback mode for demo)
    reranker = LangChainRerankerWrapper(
        reranker_provider=None,
        fallback_enabled=True
    )
    
    # Rerank
    query = "What is artificial intelligence?"
    candidates = [r.content for r in initial_results]
    reranked_indices = await reranker.rerank(query, candidates, top_k=3)
    
    print(f"\nReranked top 3 results:")
    for idx, score in reranked_indices:
        result = initial_results[idx]
        print(f"  [{idx}] Score: {score:.4f} - {result.content}")


async def example_sync_vs_async():
    """Example: Synchronous vs asynchronous usage."""
    print("\n=== Example 7: Sync vs Async ===")
    
    # Create reranker
    reranker = LangChainRerankerWrapper(
        reranker_provider=None,
        fallback_enabled=True
    )
    
    candidates = ["Doc 1", "Doc 2", "Doc 3"]
    
    # Async usage (recommended)
    print("Async usage (recommended in async contexts):")
    results_async = await reranker.rerank("query", candidates, top_k=3)
    print(f"  ✓ Got {len(results_async)} results")
    
    # Note: Sync usage should be called from non-async contexts
    print("\nSync usage:")
    print("  ℹ️  rerank_sync() should be called from non-async contexts")
    print("  ℹ️  In async contexts, always use await rerank()")
    
    # Show the results
    print(f"\nAsync results:")
    for idx, score in results_async:
        print(f"  [{idx}] Score: {score:.4f}")


async def main():
    """Run all examples."""
    print("=" * 60)
    print("LangChain Reranker Wrapper Examples")
    print("=" * 60)
    
    try:
        await example_basic_usage()
        await example_score_normalization()
        await example_fallback_mechanism()
        await example_error_handling()
        await example_connection_validation()
        await example_rag_integration()
        await example_sync_vs_async()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
