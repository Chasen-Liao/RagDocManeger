"""
Example usage of RAG Generation Tool

This example demonstrates how to use the RAGGenerateTool to generate
answers based on knowledge base content.

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.search_tools import RAGGenerateTool
from services.search_service import SearchService
from core.llm_provider import LLMProviderFactory


async def example_basic_rag():
    """
    Example: Basic RAG generation.
    
    Demonstrates:
    - Document retrieval (Requirement 9.1)
    - Context building (Requirement 9.2)
    - Prompt construction (Requirement 9.3)
    - Answer generation with sources (Requirement 9.4)
    """
    print("=" * 60)
    print("Example 1: Basic RAG Generation")
    print("=" * 60)
    
    # Initialize services (replace with actual configuration)
    # search_service = SearchService(...)
    # llm_provider = LLMProviderFactory.create_provider(
    #     provider_type="siliconflow",
    #     api_key="your-api-key"
    # )
    
    # For demonstration, we'll use mock services
    print("\nNote: This is a demonstration. Replace with actual services.")
    print("\nInitializing RAG tool...")
    
    # rag_tool = RAGGenerateTool(
    #     search_service=search_service,
    #     llm_provider=llm_provider
    # )
    
    # Generate answer
    # result = await rag_tool._aexecute(
    #     question="What is Python?",
    #     kb_id="kb123",
    #     top_k=5,
    #     stream=False
    # )
    
    # Display results
    # if result.success:
    #     print(f"\nQuestion: {result.data['question']}")
    #     print(f"\nAnswer: {result.data['answer']}")
    #     print(f"\nSources ({len(result.data['sources'])}):")
    #     for idx, source in enumerate(result.data['sources'], 1):
    #         print(f"\n  [{idx}] {source['doc_name']} (score: {source['score']:.2f})")
    #         print(f"      {source['content_preview']}")
    # else:
    #     print(f"\nError: {result.error}")
    
    print("\nExample code structure shown above.")


async def example_streaming_rag():
    """
    Example: Streaming RAG generation.
    
    Demonstrates:
    - Real-time answer streaming (Requirement 9.5)
    """
    print("\n" + "=" * 60)
    print("Example 2: Streaming RAG Generation")
    print("=" * 60)
    
    print("\nNote: This is a demonstration. Replace with actual services.")
    print("\nInitializing RAG tool for streaming...")
    
    # Initialize services
    # search_service = SearchService(...)
    # llm_provider = LLMProviderFactory.create_provider(
    #     provider_type="siliconflow",
    #     api_key="your-api-key"
    # )
    
    # rag_tool = RAGGenerateTool(
    #     search_service=search_service,
    #     llm_provider=llm_provider
    # )
    
    # Stream answer generation
    # print("\nQuestion: What is Python?")
    # print("\nAnswer (streaming): ", end="", flush=True)
    
    # async for chunk in rag_tool.generate_stream(
    #     question="What is Python?",
    #     kb_id="kb123",
    #     top_k=5
    # ):
    #     print(chunk, end="", flush=True)
    
    # print("\n\nStreaming completed.")
    
    print("\nExample code structure shown above.")


async def example_no_context_rag():
    """
    Example: RAG generation when no documents are found.
    
    Demonstrates:
    - Graceful handling of empty search results
    - LLM fallback without context
    """
    print("\n" + "=" * 60)
    print("Example 3: RAG with No Context")
    print("=" * 60)
    
    print("\nNote: This is a demonstration. Replace with actual services.")
    print("\nWhen no relevant documents are found, the RAG tool:")
    print("1. Still generates an answer using the LLM")
    print("2. Informs the user that no context was available")
    print("3. Returns empty sources list")
    print("4. Sets context_used flag to False")
    
    # result = await rag_tool._aexecute(
    #     question="What is quantum computing?",
    #     kb_id="kb123",
    #     top_k=5
    # )
    
    # if result.success:
    #     print(f"\nContext used: {result.data['context_used']}")
    #     print(f"Sources found: {len(result.data['sources'])}")
    #     print(f"Answer: {result.data['answer']}")
    
    print("\nExample code structure shown above.")


async def example_error_handling():
    """
    Example: Error handling in RAG generation.
    
    Demonstrates:
    - Input validation
    - Service error handling
    - Graceful error responses
    """
    print("\n" + "=" * 60)
    print("Example 4: Error Handling")
    print("=" * 60)
    
    print("\nNote: This is a demonstration. Replace with actual services.")
    print("\nThe RAG tool handles various error scenarios:")
    
    # Test empty question
    # result = await rag_tool._aexecute(
    #     question="",
    #     kb_id="kb123",
    #     top_k=5
    # )
    # print(f"\n1. Empty question: {result.error}")
    
    # Test empty kb_id
    # result = await rag_tool._aexecute(
    #     question="What is Python?",
    #     kb_id="",
    #     top_k=5
    # )
    # print(f"2. Empty KB ID: {result.error}")
    
    # Test service errors
    # (Service errors are caught and returned as ToolOutput with error)
    
    print("\n1. Empty question validation")
    print("2. Empty knowledge base ID validation")
    print("3. Search service error handling")
    print("4. LLM generation error handling")
    print("\nAll errors return ToolOutput with success=False and error message.")


async def example_custom_parameters():
    """
    Example: Using custom parameters.
    
    Demonstrates:
    - Adjusting top_k for more/fewer documents
    - Enabling streaming mode
    """
    print("\n" + "=" * 60)
    print("Example 5: Custom Parameters")
    print("=" * 60)
    
    print("\nNote: This is a demonstration. Replace with actual services.")
    print("\nCustomizable parameters:")
    print("- question: User's question (required)")
    print("- kb_id: Knowledge base ID (required)")
    print("- top_k: Number of documents to retrieve (default: 5, range: 1-20)")
    print("- stream: Enable streaming output (default: False)")
    
    # Example with more documents
    # result = await rag_tool._aexecute(
    #     question="What is Python?",
    #     kb_id="kb123",
    #     top_k=10,  # Retrieve more documents for better context
    #     stream=False
    # )
    
    # Example with streaming
    # result = await rag_tool._aexecute(
    #     question="What is Python?",
    #     kb_id="kb123",
    #     top_k=5,
    #     stream=True  # Enable streaming
    # )
    
    print("\nExample code structure shown above.")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("RAG Generation Tool Examples")
    print("=" * 60)
    print("\nThese examples demonstrate the RAGGenerateTool capabilities:")
    print("- Basic RAG generation with sources")
    print("- Streaming answer generation")
    print("- Handling empty search results")
    print("- Error handling and validation")
    print("- Custom parameter usage")
    
    await example_basic_rag()
    await example_streaming_rag()
    await example_no_context_rag()
    await example_error_handling()
    await example_custom_parameters()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
    print("\nTo use the RAG tool in your application:")
    print("1. Initialize SearchService with your vector store")
    print("2. Create LLM provider using LLMProviderFactory")
    print("3. Create RAGGenerateTool with both services")
    print("4. Call _aexecute() or generate_stream() methods")
    print("5. Process the ToolOutput results")
    print("\nFor more details, see the test file: tests/test_rag_tools.py")


if __name__ == "__main__":
    asyncio.run(main())
