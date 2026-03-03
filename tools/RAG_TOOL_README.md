# RAG Generation Tool

## Overview

The `RAGGenerateTool` is a powerful tool that combines document retrieval with Large Language Model (LLM) generation to produce contextual answers based on knowledge base content. It implements the Retrieval-Augmented Generation (RAG) pattern.

**Requirements Validated:** 9.1, 9.2, 9.3, 9.4, 9.5

## Features

### Core Capabilities

1. **Document Retrieval** (Requirement 9.1)
   - Retrieves relevant documents from knowledge base using hybrid search
   - Supports configurable top-k parameter (1-20 documents)
   - Integrates with SearchService for optimal retrieval

2. **Context Building** (Requirement 9.2)
   - Constructs structured context from retrieved documents
   - Includes document source information
   - Formats context for optimal LLM comprehension

3. **Prompt Construction** (Requirement 9.3)
   - Uses template-based prompt generation
   - Includes context and question in structured format
   - Handles cases with and without available context

4. **Source Citations** (Requirement 9.4)
   - Returns answer with source document references
   - Includes content previews and relevance scores
   - Provides document metadata (doc_id, doc_name, chunk_id)

5. **Streaming Support** (Requirement 9.5)
   - Enables real-time answer generation
   - Supports both streaming and non-streaming modes
   - Provides immediate feedback to users

## Usage

### Basic Usage

```python
from tools.search_tools import RAGGenerateTool
from services.search_service import SearchService
from core.llm_provider import LLMProviderFactory

# Initialize services
search_service = SearchService(...)
llm_provider = LLMProviderFactory.create_provider(
    provider_type="siliconflow",
    api_key="your-api-key"
)

# Create RAG tool
rag_tool = RAGGenerateTool(
    search_service=search_service,
    llm_provider=llm_provider
)

# Generate answer
result = await rag_tool._aexecute(
    question="What is Python?",
    kb_id="kb123",
    top_k=5,
    stream=False
)

# Process result
if result.success:
    print(f"Answer: {result.data['answer']}")
    print(f"Sources: {len(result.data['sources'])}")
    for source in result.data['sources']:
        print(f"  - {source['doc_name']} (score: {source['score']:.2f})")
else:
    print(f"Error: {result.error}")
```

### Streaming Usage

```python
# Stream answer generation
async for chunk in rag_tool.generate_stream(
    question="What is Python?",
    kb_id="kb123",
    top_k=5
):
    print(chunk, end="", flush=True)
```

### Synchronous Usage

```python
# Use synchronous wrapper
result = rag_tool._execute(
    question="What is Python?",
    kb_id="kb123",
    top_k=5
)
```

## Input Schema

### RAGGenerateInput

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| question | str | Yes | - | User's question |
| kb_id | str | Yes | - | Knowledge base ID |
| top_k | int | No | 5 | Number of documents to retrieve (1-20) |
| stream | bool | No | False | Enable streaming output |

### Validation Rules

- `question`: Cannot be empty or whitespace-only
- `kb_id`: Cannot be empty or whitespace-only
- `top_k`: Must be between 1 and 20 (inclusive)
- `stream`: Boolean flag for streaming mode

## Output Schema

### ToolOutput Structure

```python
{
    "success": bool,           # Whether generation succeeded
    "message": str,            # Human-readable status message
    "data": {
        "question": str,       # Original question
        "answer": str,         # Generated answer
        "sources": [           # Source citations
            {
                "content_preview": str,  # First 200 chars of content
                "score": float,          # Relevance score (0-1)
                "doc_id": str,           # Document ID
                "doc_name": str,         # Document name
                "chunk_id": str          # Chunk ID
            }
        ],
        "context_used": bool   # Whether context was available
    },
    "error": str | None        # Error message if failed
}
```

### Streaming Mode Output

When `stream=True`, the output includes:

```python
{
    "success": True,
    "message": "RAG 生成已启动（流式模式）",
    "data": {
        "question": str,
        "answer": "[STREAMING]",  # Placeholder
        "sources": [...],         # Source citations
        "context_used": bool,
        "stream": True,
        "prompt": str            # Prompt for streaming
    }
}
```

## RAG Pipeline

The tool executes the following pipeline:

```
1. Input Validation
   ↓
2. Document Retrieval (SearchService)
   ↓
3. Context Building (format documents)
   ↓
4. Prompt Construction (template + context + question)
   ↓
5. Answer Generation (LLM)
   ↓
6. Source Extraction (citations)
   ↓
7. Output Formatting
```

## Error Handling

### Input Validation Errors

```python
# Empty question
result = await rag_tool._aexecute(question="", kb_id="kb123")
# Returns: ToolOutput(success=False, error="问题不能为空")

# Empty kb_id
result = await rag_tool._aexecute(question="What?", kb_id="")
# Returns: ToolOutput(success=False, error="知识库 ID 不能为空")
```

### Service Errors

```python
# Search service failure
# Returns: ToolOutput(success=False, error="<service error message>")

# LLM generation failure
# Returns: ToolOutput(success=False, error="<llm error message>")
```

### Empty Search Results

When no documents are found:
- Tool still generates an answer
- LLM is informed about lack of context
- Returns empty sources list
- Sets `context_used=False`

```python
{
    "success": True,
    "message": "已生成答案（未找到相关文档）",
    "data": {
        "question": "...",
        "answer": "...",
        "sources": [],
        "context_used": False
    }
}
```

## Context Building

The tool formats retrieved documents as:

```
[文档 1: Document Name]
Document content here...

[文档 2: Another Document]
More content here...
```

This format:
- Clearly separates documents
- Includes source identification
- Maintains readability for LLM

## Prompt Template

### With Context

```
请基于以下上下文信息回答问题。

上下文信息：
[formatted context]

问题：[user question]

请基于上下文提供准确的答案。如果上下文中没有足够的信息来回答问题，请明确说明。在回答时，请引用相关的文档来源。
```

### Without Context

```
请回答以下问题。注意：当前没有找到相关的上下文信息。

问题：[user question]

请明确说明没有找到相关信息，并建议用户提供更多细节或尝试不同的问题。
```

## Performance Considerations

### Optimization Tips

1. **Adjust top_k**: Use fewer documents (3-5) for faster responses
2. **Use streaming**: Enable streaming for better user experience
3. **Cache results**: Consider caching for frequently asked questions
4. **Batch processing**: Process multiple questions in parallel

### Resource Usage

- **Memory**: Proportional to top_k and document size
- **Network**: Two API calls (search + LLM)
- **Latency**: ~2-5 seconds for typical queries

## Integration with Agent

The RAG tool is designed to be used by the Agent framework:

```python
from langchain_core.agents import AgentExecutor

# Register tool with agent
tools = [rag_tool]
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True
)

# Agent can now call RAG tool
result = await agent_executor.ainvoke({
    "input": "What is Python?"
})
```

## Testing

Comprehensive tests are available in `tests/test_rag_tools.py`:

```bash
# Run all RAG tool tests
pytest tests/test_rag_tools.py -v

# Run specific test class
pytest tests/test_rag_tools.py::TestRAGGenerateTool -v

# Run with coverage
pytest tests/test_rag_tools.py --cov=tools.search_tools
```

## Examples

See `examples/rag_tool_example.py` for detailed usage examples:

```bash
python examples/rag_tool_example.py
```

## Requirements Mapping

| Requirement | Description | Implementation |
|-------------|-------------|----------------|
| 9.1 | Retrieve documents from KB | `search_service.search()` |
| 9.2 | Build context from documents | `_build_context()` method |
| 9.3 | Construct prompt template | `_build_prompt()` method |
| 9.4 | Return answer with sources | `_extract_sources()` method |
| 9.5 | Support streaming | `generate_stream()` method |

## Troubleshooting

### Common Issues

1. **No results returned**
   - Check if knowledge base exists
   - Verify documents are indexed
   - Try different search query

2. **LLM timeout**
   - Increase LLM provider timeout
   - Reduce context size (lower top_k)
   - Check network connectivity

3. **Poor answer quality**
   - Increase top_k for more context
   - Improve document quality
   - Adjust prompt template

4. **Streaming not working**
   - Verify LLM provider supports streaming
   - Check `generate_stream()` implementation
   - Use `generate_stream()` method directly

## Future Enhancements

Potential improvements:

1. **Query rewriting**: Automatically improve queries
2. **Multi-turn context**: Maintain conversation history
3. **Answer validation**: Verify answer against sources
4. **Custom prompts**: Allow user-defined templates
5. **Caching**: Cache frequent queries
6. **Metrics**: Track answer quality and latency

## License

Part of the RagDocMan project.
