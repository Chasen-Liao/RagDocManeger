# LangChain 1.x LLM Wrapper

## Overview

The `LangChainLLMWrapper` is a LangChain 1.x compatible adapter that wraps our custom LLM providers to work seamlessly with the LangChain ecosystem. It implements the `LLM` interface from `langchain_core` and supports synchronous, asynchronous, and streaming execution.

## Features

- ✅ **Synchronous Execution**: `_call()` method for sync contexts
- ✅ **Asynchronous Execution**: `_acall()` method for async contexts  
- ✅ **Streaming Support**: `_stream()` and `_astream()` methods for real-time output
- ✅ **Multiple Providers**: Works with OpenAI, Anthropic, DeepSeek, SiliconFlow, and custom providers
- ✅ **LangChain Integration**: Compatible with chains, agents, and other LangChain components
- ✅ **Error Handling**: Graceful fallbacks and comprehensive error messages
- ✅ **Callback Support**: Integrates with LangChain's callback system

## Installation

The wrapper is part of the core module and requires:

```bash
pip install langchain>=1.0.0
pip install langchain-core>=1.0.0
```

## Basic Usage

### With Custom Provider

```python
from core.llm_provider import SiliconFlowProvider
from core.langchain_llm_wrapper import LangChainLLMWrapper

# Create your LLM provider
provider = SiliconFlowProvider(api_key="your-api-key")

# Wrap it for LangChain
llm = LangChainLLMWrapper(provider, model_name="siliconflow")

# Use synchronously
result = llm._call("What is the capital of France?")

# Use asynchronously (recommended)
result = await llm._acall("What is the capital of Germany?")
```

### With LangChain Chains

```python
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Create a chain
prompt = PromptTemplate.from_template("Translate '{text}' to French")
chain = prompt | llm | StrOutputParser()

# Invoke the chain
result = await chain.ainvoke({"text": "Hello world"})
```

### Streaming

```python
# Async streaming (recommended)
async for chunk in llm._astream("Tell me a story"):
    print(chunk.text, end="", flush=True)

# Sync streaming
for chunk in llm._stream("Tell me a story"):
    print(chunk.text, end="", flush=True)
```

## Supported Providers

The wrapper works with any provider that implements the `LLMProvider` interface:

### SiliconFlow
```python
from core.llm_provider import SiliconFlowProvider

provider = SiliconFlowProvider(
    api_key="your-key",
    model="Qwen/Qwen2-7B-Instruct",
    temperature=0.7,
    max_tokens=2048
)
llm = LangChainLLMWrapper(provider, model_name="siliconflow")
```

### OpenAI (via LangChain)
```python
from langchain_openai import ChatOpenAI

# Use LangChain's native OpenAI integration
llm = ChatOpenAI(model="gpt-4", temperature=0.7)
```

### Anthropic (via LangChain)
```python
from langchain_anthropic import ChatAnthropic

# Use LangChain's native Anthropic integration
llm = ChatAnthropic(model="claude-3-opus-20240229")
```

### Custom Provider
```python
class MyCustomProvider:
    async def generate(self, prompt: str, **kwargs) -> str:
        # Your implementation
        return "Generated response"
    
    async def generate_stream(self, prompt: str, **kwargs):
        # Optional: for streaming support
        for chunk in ["Hello", " ", "world"]:
            yield chunk

provider = MyCustomProvider()
llm = LangChainLLMWrapper(provider, model_name="custom")
```

## Advanced Usage

### With Agents

```python
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.tools import tool

# Define tools
@tool
def search(query: str) -> str:
    """Search for information."""
    return f"Results for: {query}"

tools = [search]

# Create agent
agent = create_react_agent(llm, tools, prompt_template)
agent_executor = AgentExecutor(agent=agent, tools=tools)

# Run agent
result = await agent_executor.ainvoke({"input": "Search for Python tutorials"})
```

### With Memory

```python
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain

memory = ConversationBufferMemory()
conversation = ConversationChain(llm=llm, memory=memory)

# Have a conversation
response1 = await conversation.ainvoke({"input": "Hi, my name is Alice"})
response2 = await conversation.ainvoke({"input": "What's my name?"})
```

### Error Handling

```python
try:
    result = await llm._acall("Your prompt")
except Exception as e:
    print(f"LLM call failed: {e}")
    # Handle error appropriately
```

## Implementation Details

### Synchronous vs Asynchronous

- **Synchronous (`_call`)**: Uses `asyncio.run_until_complete()` to wrap async providers. Not recommended in async contexts.
- **Asynchronous (`_acall`)**: Native async execution. Recommended for better performance.

### Streaming Fallback

If a provider doesn't implement `generate_stream()`, the wrapper automatically falls back to generating the full response and yielding it as a single chunk.

### Callback Integration

The wrapper integrates with LangChain's callback system:

```python
from langchain_core.callbacks import StdOutCallbackHandler

callbacks = [StdOutCallbackHandler()]
result = await llm._acall("Your prompt", callbacks=callbacks)
```

## Testing

Comprehensive tests are available in `tests/test_langchain_llm_wrapper.py`:

```bash
pytest tests/test_langchain_llm_wrapper.py -v
```

Test coverage includes:
- Basic initialization and properties
- Synchronous and asynchronous calls
- Streaming (with and without provider support)
- Integration with LangChain chains
- Error handling
- Edge cases (empty prompts, special characters, etc.)

## Requirements Validation

This implementation satisfies the following requirements from the design document:

- **Requirement 2.1**: Supports multiple LLM providers (OpenAI, Anthropic, DeepSeek, SiliconFlow)
- **Requirement 2.2**: Uses LangChain 1.x API for model calls
- **Requirement 2.3**: Supports streaming responses
- **Requirement 2.4**: Captures and handles LLM call failures with meaningful errors
- **Requirement 2.5**: Correctly passes model parameters (temperature, max_tokens, etc.)

## Migration from Old Wrapper

If you're using the old wrapper from `rag/agent_manager.py`, migrate to the new one:

```python
# Old (in agent_manager.py)
from rag.agent_manager import LangChainLLMWrapper

# New (centralized in core)
from core.langchain_llm_wrapper import LangChainLLMWrapper
```

The API is identical, so no code changes are needed beyond the import.

## Examples

See `examples/langchain_llm_wrapper_example.py` for complete working examples:

```bash
cd RagDocMan
python examples/langchain_llm_wrapper_example.py
```

## Troubleshooting

### "Event loop is already running" error

This occurs when calling `_call()` (synchronous) from an async context. Use `_acall()` instead:

```python
# ❌ Don't do this in async functions
result = llm._call("prompt")

# ✅ Do this instead
result = await llm._acall("prompt")
```

### Provider doesn't support streaming

The wrapper automatically falls back to non-streaming mode. No action needed.

### Import errors

Make sure you're importing from the correct location:

```python
from core.langchain_llm_wrapper import LangChainLLMWrapper
```

## Contributing

When adding new LLM providers:

1. Implement the `LLMProvider` interface with `generate()` method
2. Optionally implement `generate_stream()` for streaming support
3. Test with the wrapper to ensure compatibility
4. Add tests to `test_langchain_llm_wrapper.py`

## License

Same as the parent project.


---

# LangChain 1.x Embeddings Wrapper

## Overview

The `LangChainEmbeddingWrapper` is a LangChain 1.x compatible adapter that wraps our custom Embedding providers to work seamlessly with the LangChain ecosystem. It implements the `Embeddings` interface from `langchain_core` and supports both document and query embedding with batch processing.

## Features

- ✅ **Document Embedding**: `embed_documents()` method for embedding multiple texts
- ✅ **Query Embedding**: `embed_query()` method for embedding single queries
- ✅ **Asynchronous Support**: `aembed_documents()` and `aembed_query()` for async contexts
- ✅ **Batch Processing**: Automatic batching for efficient processing of large document sets
- ✅ **Multiple Models**: Works with BAAI/bge-m3, BAAI/bge-large-zh-v1.5, Jina, and custom models
- ✅ **LangChain Integration**: Compatible with vector stores and other LangChain components
- ✅ **Error Handling**: Comprehensive validation and error messages
- ✅ **Dimension Tracking**: Automatic embedding dimension detection

## Installation

The wrapper is part of the core module and requires:

```bash
pip install langchain>=1.0.0
pip install langchain-core>=1.0.0
```

## Basic Usage

### With SiliconFlow Provider

```python
from core.embedding_provider import SiliconFlowEmbeddingProvider
from core.langchain_embedding_wrapper import LangChainEmbeddingWrapper

# Create your embedding provider
provider = SiliconFlowEmbeddingProvider(
    api_key="your-api-key",
    model="BAAI/bge-large-zh-v1.5"
)

# Wrap it for LangChain
embeddings = LangChainEmbeddingWrapper(
    embedding_provider=provider,
    model_name="BAAI/bge-large-zh-v1.5",
    batch_size=32
)

# Embed a query
query_vector = await embeddings.aembed_query("What is AI?")

# Embed documents
documents = ["Doc 1", "Doc 2", "Doc 3"]
doc_vectors = await embeddings.aembed_documents(documents)
```

### With Vector Stores

```python
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# Create documents
docs = [
    Document(page_content="AI is artificial intelligence"),
    Document(page_content="ML is machine learning"),
]

# Create vector store with our embeddings
vector_store = FAISS.from_documents(docs, embeddings)

# Search
results = vector_store.similarity_search("What is AI?", k=2)
```

### Synchronous Usage

```python
# For non-async contexts
query_vector = embeddings.embed_query("What is AI?")
doc_vectors = embeddings.embed_documents(["Doc 1", "Doc 2"])
```

## Supported Models

The wrapper works with any provider that implements the `EmbeddingProvider` interface:

### BAAI/bge-large-zh-v1.5 (1024 dimensions)
```python
provider = SiliconFlowEmbeddingProvider(
    api_key="your-key",
    model="BAAI/bge-large-zh-v1.5"
)
embeddings = LangChainEmbeddingWrapper(
    embedding_provider=provider,
    model_name="BAAI/bge-large-zh-v1.5"
)
```

### BAAI/bge-base-zh-v1.5 (768 dimensions)
```python
provider = SiliconFlowEmbeddingProvider(
    api_key="your-key",
    model="BAAI/bge-base-zh-v1.5"
)
embeddings = LangChainEmbeddingWrapper(
    embedding_provider=provider,
    model_name="BAAI/bge-base-zh-v1.5"
)
```

### BAAI/bge-small-zh-v1.5 (512 dimensions)
```python
provider = SiliconFlowEmbeddingProvider(
    api_key="your-key",
    model="BAAI/bge-small-zh-v1.5"
)
embeddings = LangChainEmbeddingWrapper(
    embedding_provider=provider,
    model_name="BAAI/bge-small-zh-v1.5"
)
```

### Custom Provider
```python
class MyCustomEmbeddingProvider:
    async def embed_text(self, text: str) -> list[float]:
        # Your implementation
        return [0.1] * 768
    
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        # Your implementation
        return [[0.1] * 768 for _ in texts]
    
    def get_embedding_dimension(self) -> int:
        return 768

provider = MyCustomEmbeddingProvider()
embeddings = LangChainEmbeddingWrapper(
    embedding_provider=provider,
    model_name="custom"
)
```

## Advanced Usage

### Batch Processing

The wrapper automatically processes documents in batches for efficiency:

```python
# Create wrapper with custom batch size
embeddings = LangChainEmbeddingWrapper(
    embedding_provider=provider,
    batch_size=16  # Process 16 documents at a time
)

# Embed large document set
large_doc_set = [f"Document {i}" for i in range(1000)]
vectors = await embeddings.aembed_documents(large_doc_set)
# Automatically processed in 63 batches (1000 / 16)
```

### With Retrieval Chains

```python
from langchain.chains import RetrievalQA

# Create vector store
vector_store = FAISS.from_documents(documents, embeddings)

# Create retrieval chain
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vector_store.as_retriever()
)

# Ask questions
answer = await qa_chain.ainvoke({"query": "What is machine learning?"})
```

### With Hybrid Search

```python
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

# Vector retriever
vector_retriever = vector_store.as_retriever(search_kwargs={"k": 5})

# Keyword retriever
bm25_retriever = BM25Retriever.from_documents(documents)

# Combine both
ensemble_retriever = EnsembleRetriever(
    retrievers=[vector_retriever, bm25_retriever],
    weights=[0.7, 0.3]
)

results = ensemble_retriever.get_relevant_documents("query")
```

### Dimension Checking

```python
# Get embedding dimension
dimension = embeddings.get_embedding_dimension()
print(f"Embedding dimension: {dimension}")

# Verify embeddings
query_vec = await embeddings.aembed_query("test")
assert len(query_vec) == dimension
```

### Error Handling

```python
try:
    # Empty text validation
    vector = await embeddings.aembed_query("")
except ValueError as e:
    print(f"Validation error: {e}")

try:
    # Empty list validation
    vectors = await embeddings.aembed_documents([])
except ValueError as e:
    print(f"Validation error: {e}")

try:
    # Provider errors
    vectors = await embeddings.aembed_documents(documents)
except Exception as e:
    print(f"Embedding error: {e}")
```

## Implementation Details

### Synchronous vs Asynchronous

- **Synchronous (`embed_query`, `embed_documents`)**: Uses `asyncio.run_until_complete()` to wrap async providers. Not recommended in async contexts.
- **Asynchronous (`aembed_query`, `aembed_documents`)**: Native async execution. Recommended for better performance.

### Batch Processing Strategy

The wrapper automatically splits large document sets into batches:

1. Documents are divided into chunks of `batch_size`
2. Each batch is processed sequentially
3. Results are concatenated in order
4. This prevents memory issues and API rate limits

### Dimension Consistency

The wrapper ensures dimension consistency:

- All embeddings from the same model have the same dimension
- Dimension is retrieved from the provider's `get_embedding_dimension()` method
- Useful for validation and vector store configuration

## Testing

Comprehensive tests are available in `tests/test_langchain_embedding_wrapper.py`:

```bash
pytest tests/test_langchain_embedding_wrapper.py -v
```

Test coverage includes:
- Basic initialization and properties
- Synchronous and asynchronous embedding
- Batch processing with various sizes
- Query and document embedding
- Error handling and validation
- Integration with real providers (skipped by default)
- Edge cases (empty texts, empty lists, etc.)

## Requirements Validation

This implementation satisfies the following requirements from the design document:

- **Requirement 3.1**: Supports multiple embedding models (BAAI/bge-m3, BAAI/bge-large-zh-v1.5, Jina)
- **Requirement 3.2**: Uses LangChain 1.x Embeddings interface
- **Requirement 3.3**: Supports batch processing for efficiency
- **Requirement 3.4**: Correctly handles different model dimensions (1024, 768, 512)
- **Requirement 3.5**: Returns errors and allows retry when service unavailable

## Examples

See `examples/langchain_embedding_wrapper_example.py` for complete working examples:

```bash
cd RagDocMan
export SILICONFLOW_API_KEY="your-api-key"
python examples/langchain_embedding_wrapper_example.py
```

Examples include:
- Basic usage with query and document embedding
- Batch processing demonstration
- Multiple models comparison
- LangChain integration patterns
- Error handling scenarios
- Synchronous and asynchronous usage

## Performance Tips

### Optimize Batch Size

Choose batch size based on your use case:

```python
# Small batch size (16-32): Better for rate-limited APIs
embeddings = LangChainEmbeddingWrapper(provider, batch_size=16)

# Medium batch size (32-64): Balanced performance
embeddings = LangChainEmbeddingWrapper(provider, batch_size=32)

# Large batch size (64-128): Maximum throughput
embeddings = LangChainEmbeddingWrapper(provider, batch_size=128)
```

### Use Async Methods

Always prefer async methods in async contexts:

```python
# ✅ Good: Native async
vectors = await embeddings.aembed_documents(docs)

# ❌ Avoid: Sync wrapper in async context
vectors = embeddings.embed_documents(docs)
```

### Cache Embeddings

For frequently used queries, cache the embeddings:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_embedding(query: str) -> tuple:
    vector = embeddings.embed_query(query)
    return tuple(vector)  # Convert to tuple for hashing
```

## Troubleshooting

### "Event loop is already running" error

Use async methods in async contexts:

```python
# ❌ Don't do this in async functions
vector = embeddings.embed_query("query")

# ✅ Do this instead
vector = await embeddings.aembed_query("query")
```

### Dimension mismatch errors

Ensure you're using the correct model:

```python
# Check dimension
print(f"Expected dimension: {embeddings.get_embedding_dimension()}")

# Verify with test embedding
test_vec = await embeddings.aembed_query("test")
print(f"Actual dimension: {len(test_vec)}")
```

### Batch processing too slow

Adjust batch size based on your API limits:

```python
# Increase batch size for faster processing
embeddings = LangChainEmbeddingWrapper(
    embedding_provider=provider,
    batch_size=64  # Larger batches
)
```

### API rate limit errors

Reduce batch size and add delays:

```python
import asyncio

# Smaller batches
embeddings = LangChainEmbeddingWrapper(provider, batch_size=8)

# Add delay between batches (implement in provider)
async def embed_with_delay(texts):
    results = []
    for i in range(0, len(texts), 8):
        batch = texts[i:i+8]
        batch_results = await embeddings.aembed_documents(batch)
        results.extend(batch_results)
        await asyncio.sleep(1)  # 1 second delay
    return results
```

## Contributing

When adding new embedding providers:

1. Implement the `EmbeddingProvider` interface:
   - `embed_text(text: str) -> list[float]`
   - `embed_texts(texts: list[str]) -> list[list[float]]`
   - `get_embedding_dimension() -> int`
   - `validate_connection() -> bool`
2. Test with the wrapper to ensure compatibility
3. Add tests to `test_langchain_embedding_wrapper.py`
4. Document the model dimensions and characteristics

## License

Same as the parent project.


---

# LangChain 1.x Reranker Wrapper

## Overview

The `LangChainRerankerWrapper` is a LangChain 1.x compatible adapter that wraps our custom Reranker providers to work seamlessly with the LangChain ecosystem. It provides reranking functionality with score normalization (0-1 range) and fallback mechanisms when the reranker is unavailable.

## Features

- ✅ **Asynchronous Reranking**: `rerank()` method for async contexts
- ✅ **Synchronous Support**: `rerank_sync()` method for sync contexts
- ✅ **Score Normalization**: Automatic normalization of scores to 0-1 range
- ✅ **Fallback Mechanism**: Graceful degradation when reranker is unavailable
- ✅ **Multiple Models**: Works with BAAI/bge-reranker-base, BAAI/bge-reranker-large, and custom models
- ✅ **LangChain Integration**: Compatible with retrieval chains and other LangChain components
- ✅ **Error Handling**: Comprehensive validation and error messages
- ✅ **Connection Validation**: Built-in connection testing

## Installation

The wrapper is part of the core module and requires:

```bash
pip install langchain>=1.0.0
pip install langchain-core>=1.0.0
```

## Basic Usage

### With SiliconFlow Provider

```python
from core.reranker_provider import SiliconFlowRerankerProvider
from core.langchain_reranker_wrapper import LangChainRerankerWrapper

# Create your reranker provider
provider = SiliconFlowRerankerProvider(
    api_key="your-api-key",
    model="BAAI/bge-reranker-large"
)

# Wrap it for LangChain
reranker = LangChainRerankerWrapper(
    reranker_provider=provider,
    model_name="BAAI/bge-reranker-large",
    normalize_scores=True,
    fallback_enabled=True
)

# Rerank candidates
query = "What is artificial intelligence?"
candidates = [
    "AI is the simulation of human intelligence",
    "Machine learning is a subset of AI",
    "Deep learning uses neural networks"
]

# Async reranking (recommended)
results = await reranker.rerank(query, candidates, top_k=3)
# Returns: [(index, score), ...] sorted by relevance

# Sync reranking
results = reranker.rerank_sync(query, candidates, top_k=3)
```

### Without Provider (Fallback Mode)

```python
# Create wrapper without provider - uses fallback ranking
reranker = LangChainRerankerWrapper(
    reranker_provider=None,
    fallback_enabled=True
)

# Will return original order with decreasing scores
results = await reranker.rerank(query, candidates, top_k=3)
# Returns: [(0, 1.0), (1, 0.5), (2, 0.0)]
```

## Supported Models

The wrapper works with any provider that implements the `RerankerProvider` interface:

### BAAI/bge-reranker-large
```python
provider = SiliconFlowRerankerProvider(
    api_key="your-key",
    model="BAAI/bge-reranker-large"
)
reranker = LangChainRerankerWrapper(
    reranker_provider=provider,
    model_name="BAAI/bge-reranker-large"
)
```

### BAAI/bge-reranker-base
```python
provider = SiliconFlowRerankerProvider(
    api_key="your-key",
    model="BAAI/bge-reranker-base"
)
reranker = LangChainRerankerWrapper(
    reranker_provider=provider,
    model_name="BAAI/bge-reranker-base"
)
```

### Custom Provider
```python
class MyCustomRerankerProvider:
    async def rerank(
        self, query: str, candidates: list[str], top_k: int = 5
    ) -> list[tuple[int, float]]:
        # Your implementation
        return [(0, 0.9), (1, 0.7), (2, 0.5)]
    
    async def validate_connection(self) -> bool:
        return True

provider = MyCustomRerankerProvider()
reranker = LangChainRerankerWrapper(
    reranker_provider=provider,
    model_name="custom"
)
```

## Advanced Usage

### Score Normalization

The wrapper automatically normalizes scores to 0-1 range using min-max normalization:

```python
# With normalization (default)
reranker = LangChainRerankerWrapper(
    reranker_provider=provider,
    normalize_scores=True
)

results = await reranker.rerank(query, candidates, top_k=3)
# All scores will be between 0.0 and 1.0

# Without normalization
reranker = LangChainRerankerWrapper(
    reranker_provider=provider,
    normalize_scores=False
)

results = await reranker.rerank(query, candidates, top_k=3)
# Scores will be raw values from the provider
```

### Fallback Mechanism

Control fallback behavior when reranker is unavailable:

```python
# With fallback (default) - graceful degradation
reranker = LangChainRerankerWrapper(
    reranker_provider=provider,
    fallback_enabled=True
)

# If provider fails, returns original order
results = await reranker.rerank(query, candidates, top_k=3)

# Without fallback - raises errors
reranker = LangChainRerankerWrapper(
    reranker_provider=provider,
    fallback_enabled=False
)

# If provider fails, raises exception
try:
    results = await reranker.rerank(query, candidates, top_k=3)
except Exception as e:
    print(f"Reranking failed: {e}")
```

### With Retrieval Chains

```python
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS

# Create vector store
vector_store = FAISS.from_documents(documents, embeddings)

# Get initial retrieval results
retriever = vector_store.as_retriever(search_kwargs={"k": 20})
initial_docs = retriever.get_relevant_documents(query)

# Rerank the results
candidates = [doc.page_content for doc in initial_docs]
reranked_indices = await reranker.rerank(query, candidates, top_k=5)

# Get top reranked documents
top_docs = [initial_docs[idx] for idx, score in reranked_indices]
```

### Connection Validation

```python
# Validate reranker connection
is_valid = await reranker.validate_connection()

if is_valid:
    print("Reranker is ready")
    results = await reranker.rerank(query, candidates, top_k=5)
else:
    print("Reranker unavailable, using fallback")
```

### Integration with RAG Pipeline

```python
async def rag_with_reranking(query: str, kb_id: str):
    # 1. Initial retrieval
    initial_results = await search_service.search(
        query=query,
        kb_id=kb_id,
        top_k=20
    )
    
    # 2. Rerank results
    candidates = [r.content for r in initial_results]
    reranked_indices = await reranker.rerank(query, candidates, top_k=5)
    
    # 3. Get top reranked results
    top_results = [
        initial_results[idx] 
        for idx, score in reranked_indices
    ]
    
    # 4. Generate answer with top results
    context = "\n\n".join([r.content for r in top_results])
    answer = await llm.generate(f"Context: {context}\n\nQuestion: {query}")
    
    return answer, top_results
```

## Implementation Details

### Score Normalization Algorithm

The wrapper uses min-max normalization:

```
normalized_score = (score - min_score) / (max_score - min_score)
```

Special cases:
- If all scores are identical: normalized to 0.5
- If only one result: normalized to 0.5
- Empty results: returns empty list

### Fallback Ranking Strategy

When reranker is unavailable, the wrapper returns original order with linearly decreasing scores:

```
score = 1.0 - (index / (num_results - 1))
```

This ensures:
- First result gets score 1.0
- Last result gets score 0.0
- Intermediate results get evenly distributed scores

### Synchronous vs Asynchronous

- **Synchronous (`rerank_sync`)**: Uses `asyncio.run_until_complete()` to wrap async providers. Not recommended in async contexts.
- **Asynchronous (`rerank`)**: Native async execution. Recommended for better performance.

## Testing

Comprehensive tests are available in `tests/test_langchain_reranker_wrapper.py`:

```bash
pytest tests/test_langchain_reranker_wrapper.py -v
```

Test coverage includes:
- Basic initialization and properties
- Score normalization with various inputs
- Asynchronous and synchronous reranking
- Fallback mechanism with and without provider
- Connection validation
- Integration with real providers
- Edge cases (empty inputs, special characters, etc.)

## Requirements Validation

This implementation satisfies the following requirements from the design document:

- **Requirement 4.1**: Supports multiple reranking models (BAAI/bge-reranker-base, BAAI/bge-reranker-large)
- **Requirement 4.2**: Uses LangChain 1.x compatible API
- **Requirement 4.3**: Returns scores normalized to 0-1 range
- **Requirement 4.4**: Results are sorted by score descending
- **Requirement 4.5**: Returns original results when reranker is unavailable (fallback)

## Performance Tips

### Choose Appropriate Models

Different models have different trade-offs:

```python
# Base model: Faster, lower accuracy
provider = SiliconFlowRerankerProvider(
    api_key="your-key",
    model="BAAI/bge-reranker-base"
)

# Large model: Slower, higher accuracy
provider = SiliconFlowRerankerProvider(
    api_key="your-key",
    model="BAAI/bge-reranker-large"
)
```

### Use Async Methods

Always prefer async methods in async contexts:

```python
# ✅ Good: Native async
results = await reranker.rerank(query, candidates, top_k=5)

# ❌ Avoid: Sync wrapper in async context
results = reranker.rerank_sync(query, candidates, top_k=5)
```

### Enable Fallback for Production

For production systems, enable fallback to ensure availability:

```python
reranker = LangChainRerankerWrapper(
    reranker_provider=provider,
    fallback_enabled=True  # Graceful degradation
)
```

### Limit Reranking Candidates

Rerank only the most relevant candidates to reduce latency:

```python
# Initial retrieval: Get many candidates
initial_results = await search(query, top_k=50)

# Rerank: Only top 20 candidates
candidates = [r.content for r in initial_results[:20]]
reranked = await reranker.rerank(query, candidates, top_k=5)
```

## Troubleshooting

### "Event loop is already running" error

Use async methods in async contexts:

```python
# ❌ Don't do this in async functions
results = reranker.rerank_sync(query, candidates)

# ✅ Do this instead
results = await reranker.rerank(query, candidates)
```

### Reranker unavailable errors

Enable fallback for graceful degradation:

```python
reranker = LangChainRerankerWrapper(
    reranker_provider=provider,
    fallback_enabled=True
)
```

### Score normalization issues

Check if normalization is enabled:

```python
# Verify settings
params = reranker._identifying_params
print(f"Normalization enabled: {params['normalize_scores']}")

# Disable if needed
reranker = LangChainRerankerWrapper(
    reranker_provider=provider,
    normalize_scores=False
)
```

### API rate limit errors

Reduce the number of candidates or add delays:

```python
import asyncio

# Limit candidates
candidates = initial_results[:10]  # Fewer candidates

# Add delay between calls
await asyncio.sleep(1)
results = await reranker.rerank(query, candidates, top_k=5)
```

## Contributing

When adding new reranker providers:

1. Implement the `RerankerProvider` interface:
   - `rerank(query: str, candidates: list[str], top_k: int) -> list[tuple[int, float]]`
   - `validate_connection() -> bool`
2. Test with the wrapper to ensure compatibility
3. Add tests to `test_langchain_reranker_wrapper.py`
4. Document the model characteristics and performance

## License

Same as the parent project.
