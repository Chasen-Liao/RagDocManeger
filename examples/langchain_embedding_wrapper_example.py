"""Example usage of LangChain Embedding Wrapper."""

import asyncio
import os
from RagDocMan.core.embedding_provider import SiliconFlowEmbeddingProvider
from RagDocMan.core.langchain_embedding_wrapper import LangChainEmbeddingWrapper


async def basic_usage_example():
    """Basic usage example with SiliconFlow provider."""
    print("=== Basic Usage Example ===\n")
    
    # Get API key from environment
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        print("Error: SILICONFLOW_API_KEY environment variable not set")
        return
    
    # Create embedding provider
    provider = SiliconFlowEmbeddingProvider(
        api_key=api_key,
        model="BAAI/bge-large-zh-v1.5"
    )
    
    # Create LangChain wrapper
    wrapper = LangChainEmbeddingWrapper(
        embedding_provider=provider,
        model_name="BAAI/bge-large-zh-v1.5",
        batch_size=32
    )
    
    # Embed a single query
    print("Embedding a single query...")
    query = "什么是人工智能？"
    query_embedding = await wrapper.aembed_query(query)
    print(f"Query: {query}")
    print(f"Embedding dimension: {len(query_embedding)}")
    print(f"First 5 values: {query_embedding[:5]}\n")
    
    # Embed multiple documents
    print("Embedding multiple documents...")
    documents = [
        "人工智能是计算机科学的一个分支。",
        "机器学习是人工智能的核心技术。",
        "深度学习使用神经网络进行学习。"
    ]
    doc_embeddings = await wrapper.aembed_documents(documents)
    print(f"Number of documents: {len(documents)}")
    print(f"Number of embeddings: {len(doc_embeddings)}")
    print(f"Each embedding dimension: {len(doc_embeddings[0])}\n")
    
    # Clean up
    await provider.close()


async def batch_processing_example():
    """Example demonstrating batch processing."""
    print("=== Batch Processing Example ===\n")
    
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        print("Error: SILICONFLOW_API_KEY environment variable not set")
        return
    
    provider = SiliconFlowEmbeddingProvider(
        api_key=api_key,
        model="BAAI/bge-large-zh-v1.5"
    )
    
    # Create wrapper with small batch size to demonstrate batching
    wrapper = LangChainEmbeddingWrapper(
        embedding_provider=provider,
        model_name="BAAI/bge-large-zh-v1.5",
        batch_size=3  # Small batch size for demonstration
    )
    
    # Create a larger set of documents
    documents = [f"这是第 {i+1} 个文档的内容。" for i in range(10)]
    
    print(f"Processing {len(documents)} documents with batch_size={wrapper.batch_size}")
    print(f"Expected number of batches: {(len(documents) + wrapper.batch_size - 1) // wrapper.batch_size}\n")
    
    # Embed all documents (will be processed in batches)
    embeddings = await wrapper.aembed_documents(documents)
    
    print(f"Successfully embedded {len(embeddings)} documents")
    print(f"Each embedding has {len(embeddings[0])} dimensions\n")
    
    await provider.close()


async def multiple_models_example():
    """Example using different embedding models."""
    print("=== Multiple Models Example ===\n")
    
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        print("Error: SILICONFLOW_API_KEY environment variable not set")
        return
    
    models = [
        ("BAAI/bge-large-zh-v1.5", 1024),
        ("BAAI/bge-base-zh-v1.5", 768),
        ("BAAI/bge-small-zh-v1.5", 512),
    ]
    
    query = "测试查询"
    
    for model_name, expected_dim in models:
        print(f"Testing model: {model_name}")
        
        provider = SiliconFlowEmbeddingProvider(
            api_key=api_key,
            model=model_name
        )
        
        wrapper = LangChainEmbeddingWrapper(
            embedding_provider=provider,
            model_name=model_name
        )
        
        embedding = await wrapper.aembed_query(query)
        actual_dim = len(embedding)
        
        print(f"  Expected dimension: {expected_dim}")
        print(f"  Actual dimension: {actual_dim}")
        print(f"  Match: {'✓' if actual_dim == expected_dim else '✗'}\n")
        
        await provider.close()


async def langchain_integration_example():
    """Example showing integration with LangChain components."""
    print("=== LangChain Integration Example ===\n")
    
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        print("Error: SILICONFLOW_API_KEY environment variable not set")
        return
    
    provider = SiliconFlowEmbeddingProvider(
        api_key=api_key,
        model="BAAI/bge-large-zh-v1.5"
    )
    
    wrapper = LangChainEmbeddingWrapper(
        embedding_provider=provider,
        model_name="BAAI/bge-large-zh-v1.5"
    )
    
    # The wrapper can now be used with any LangChain component that expects Embeddings
    print("Wrapper is compatible with LangChain 1.x Embeddings interface")
    print(f"Model name: {wrapper.model_name}")
    print(f"Batch size: {wrapper.batch_size}")
    print(f"Embedding dimension: {wrapper.get_embedding_dimension()}")
    print(f"Identifying params: {wrapper._identifying_params}\n")
    
    # Example: Use with vector store (pseudo-code)
    print("The wrapper can be used with LangChain vector stores:")
    print("  from langchain_community.vectorstores import FAISS")
    print("  vector_store = FAISS.from_documents(documents, wrapper)")
    print()
    
    await provider.close()


async def error_handling_example():
    """Example demonstrating error handling."""
    print("=== Error Handling Example ===\n")
    
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        print("Error: SILICONFLOW_API_KEY environment variable not set")
        return
    
    provider = SiliconFlowEmbeddingProvider(
        api_key=api_key,
        model="BAAI/bge-large-zh-v1.5"
    )
    
    wrapper = LangChainEmbeddingWrapper(
        embedding_provider=provider,
        model_name="BAAI/bge-large-zh-v1.5"
    )
    
    # Test empty text handling
    print("Testing empty text handling...")
    try:
        await wrapper.aembed_query("")
    except ValueError as e:
        print(f"  Caught expected error: {e}\n")
    
    # Test empty list handling
    print("Testing empty list handling...")
    try:
        await wrapper.aembed_documents([])
    except ValueError as e:
        print(f"  Caught expected error: {e}\n")
    
    # Test with valid input
    print("Testing with valid input...")
    try:
        result = await wrapper.aembed_query("有效的查询")
        print(f"  Success! Embedding dimension: {len(result)}\n")
    except Exception as e:
        print(f"  Error: {e}\n")
    
    await provider.close()


async def synchronous_usage_example():
    """Example showing synchronous usage (for non-async contexts)."""
    print("=== Synchronous Usage Example ===\n")
    
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        print("Error: SILICONFLOW_API_KEY environment variable not set")
        return
    
    provider = SiliconFlowEmbeddingProvider(
        api_key=api_key,
        model="BAAI/bge-large-zh-v1.5"
    )
    
    wrapper = LangChainEmbeddingWrapper(
        embedding_provider=provider,
        model_name="BAAI/bge-large-zh-v1.5"
    )
    
    print("Using synchronous methods (embed_query and embed_documents)...")
    
    # Synchronous query embedding
    query = "同步查询示例"
    query_embedding = wrapper.embed_query(query)
    print(f"Query embedding dimension: {len(query_embedding)}")
    
    # Synchronous document embedding
    documents = ["文档1", "文档2", "文档3"]
    doc_embeddings = wrapper.embed_documents(documents)
    print(f"Document embeddings count: {len(doc_embeddings)}")
    print(f"Each embedding dimension: {len(doc_embeddings[0])}\n")
    
    await provider.close()


async def main():
    """Run all examples."""
    examples = [
        ("Basic Usage", basic_usage_example),
        ("Batch Processing", batch_processing_example),
        ("Multiple Models", multiple_models_example),
        ("LangChain Integration", langchain_integration_example),
        ("Error Handling", error_handling_example),
        ("Synchronous Usage", synchronous_usage_example),
    ]
    
    print("LangChain Embedding Wrapper Examples")
    print("=" * 50)
    print()
    
    for name, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            print(f"Error in {name} example: {e}\n")
        
        print("-" * 50)
        print()


if __name__ == "__main__":
    asyncio.run(main())
