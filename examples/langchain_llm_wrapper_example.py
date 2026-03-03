"""Example demonstrating LangChain LLM wrapper usage."""

import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.llm_provider import SiliconFlowProvider
from core.langchain_llm_wrapper import LangChainLLMWrapper
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser


async def example_basic_usage():
    """Example of basic wrapper usage."""
    print("=== Basic Usage Example ===\n")
    
    # Create LLM provider (using mock for demo)
    class MockProvider:
        async def generate(self, prompt: str, **kwargs) -> str:
            return f"Response to: {prompt[:50]}..."
    
    provider = MockProvider()
    wrapper = LangChainLLMWrapper(provider, model_name="mock-model")
    
    # Asynchronous call (recommended in async contexts)
    print("Asynchronous call:")
    result = await wrapper._acall("What is the capital of France?")
    print(f"Result: {result}\n")
    
    print("Another async call:")
    result = await wrapper._acall("What is the capital of Germany?")
    print(f"Result: {result}\n")


async def example_with_chain():
    """Example of using wrapper in a LangChain chain."""
    print("=== Chain Usage Example ===\n")
    
    class MockProvider:
        async def generate(self, prompt: str, **kwargs) -> str:
            return f"Generated response for: {prompt}"
    
    provider = MockProvider()
    wrapper = LangChainLLMWrapper(provider)
    
    # Create a simple chain
    prompt = PromptTemplate.from_template("Translate '{text}' to French")
    chain = prompt | wrapper | StrOutputParser()
    
    # Invoke chain
    result = await chain.ainvoke({"text": "Hello world"})
    print(f"Chain result: {result}\n")


async def example_streaming():
    """Example of streaming usage."""
    print("=== Streaming Example ===\n")
    
    class MockStreamProvider:
        async def generate(self, prompt: str, **kwargs) -> str:
            return "Full response"
        
        async def generate_stream(self, prompt: str, **kwargs):
            words = ["Hello", "streaming", "world"]
            for word in words:
                yield word + " "
    
    provider = MockStreamProvider()
    wrapper = LangChainLLMWrapper(provider)
    
    print("Streaming output:")
    async for chunk in wrapper._astream("Tell me a story"):
        print(chunk.text, end="", flush=True)
    print("\n")


async def example_with_real_provider():
    """Example with real SiliconFlow provider (requires API key)."""
    print("=== Real Provider Example ===\n")
    
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        print("Skipping: SILICONFLOW_API_KEY not set\n")
        return
    
    # Create real provider
    provider = SiliconFlowProvider(api_key, model="Qwen/Qwen2-7B-Instruct")
    wrapper = LangChainLLMWrapper(provider, model_name="siliconflow")
    
    try:
        # Test with real API
        result = await wrapper._acall("Say hello in 3 words")
        print(f"Real API result: {result}\n")
    except Exception as e:
        print(f"Error: {e}\n")
    finally:
        await provider.close()


async def example_error_handling():
    """Example of error handling."""
    print("=== Error Handling Example ===\n")
    
    class FailingProvider:
        async def generate(self, prompt: str, **kwargs) -> str:
            raise Exception("API connection failed")
    
    provider = FailingProvider()
    wrapper = LangChainLLMWrapper(provider)
    
    try:
        result = await wrapper._acall("This will fail")
    except Exception as e:
        print(f"Caught expected error: {e}\n")


async def main():
    """Run all examples."""
    print("LangChain LLM Wrapper Examples")
    print("=" * 50 + "\n")
    
    await example_basic_usage()
    await example_with_chain()
    await example_streaming()
    await example_with_real_provider()
    await example_error_handling()
    
    print("=" * 50)
    print("All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
