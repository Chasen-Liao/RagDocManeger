# RagDocMan Agent Tools

This directory contains the tool system for the RagDocMan Agent, providing a standardized framework for implementing tools that can be used by LangChain agents.

## Architecture

The tool system is built on three foundational classes:

1. **ToolInput**: Base model for tool inputs with validation
2. **ToolOutput**: Standardized output format for all tools
3. **BaseRagDocManTool**: Base class extending LangChain's BaseTool with error handling and logging

## Features

- **Standardized Interface**: All tools follow the same input/output pattern
- **Error Handling**: Automatic error catching and graceful degradation
- **Logging**: Built-in logging for execution tracking and debugging
- **Async Support**: Both synchronous and asynchronous execution
- **Performance Monitoring**: Automatic execution time tracking
- **Type Safety**: Full Pydantic validation for inputs and outputs

## Quick Start

### Creating a Simple Tool

```python
from typing import Type
from pydantic import BaseModel, Field
from tools.base import ToolInput, ToolOutput, BaseRagDocManTool

# 1. Define the input schema
class GreetingInput(ToolInput):
    name: str = Field(description="Name of the person to greet")
    language: str = Field(default="en", description="Language code (en, zh, etc.)")

# 2. Implement the tool
class GreetingTool(BaseRagDocManTool):
    name: str = "greeting"
    description: str = "Generate a greeting message in different languages"
    args_schema: Type[BaseModel] = GreetingInput
    
    def _execute(self, name: str, language: str = "en") -> ToolOutput:
        greetings = {
            "en": f"Hello, {name}!",
            "zh": f"你好，{name}！",
            "es": f"¡Hola, {name}!",
        }
        
        greeting = greetings.get(language, greetings["en"])
        
        return self._create_success_output(
            message=f"Generated greeting in {language}",
            data={"greeting": greeting}
        )

# 3. Use the tool
tool = GreetingTool()
result = tool._run(name="Alice", language="zh")
print(result.data["greeting"])  # Output: 你好，Alice！
```

### Creating an Async Tool

```python
import asyncio
from typing import Type
from pydantic import BaseModel, Field
from tools.base import ToolInput, ToolOutput, BaseRagDocManTool

class SearchInput(ToolInput):
    query: str = Field(description="Search query")
    limit: int = Field(default=10, description="Maximum results")

class AsyncSearchTool(BaseRagDocManTool):
    name: str = "async_search"
    description: str = "Search documents asynchronously"
    args_schema: Type[BaseModel] = SearchInput
    
    async def _aexecute(self, query: str, limit: int = 10) -> ToolOutput:
        # Simulate async operation
        await asyncio.sleep(0.1)
        
        results = [f"Result {i} for '{query}'" for i in range(limit)]
        
        return self._create_success_output(
            message=f"Found {len(results)} results",
            data={"results": results}
        )

# Use the async tool
async def main():
    tool = AsyncSearchTool()
    result = await tool._arun(query="test", limit=5)
    print(result.data["results"])

asyncio.run(main())
```

## Tool Output Format

All tools return a `ToolOutput` object with the following structure:

```python
{
    "success": bool,      # Whether execution was successful
    "message": str,       # Human-readable message
    "data": dict | None,  # Result data (if successful)
    "error": str | None   # Error message (if failed)
}
```

### Success Example

```python
ToolOutput(
    success=True,
    message="Operation completed successfully",
    data={"result": "example data"},
    error=None
)
```

### Error Example

```python
ToolOutput(
    success=False,
    message="Operation failed",
    data=None,
    error="ValueError: Invalid input parameter"
)
```

## Error Handling

The base tool class provides automatic error handling:

```python
class RiskyTool(BaseRagDocManTool):
    name: str = "risky_tool"
    description: str = "A tool that might fail"
    args_schema: Type[BaseModel] = ToolInput
    
    def _execute(self) -> ToolOutput:
        # This error will be caught automatically
        raise ValueError("Something went wrong")

tool = RiskyTool()
result = tool._run()
# Returns: ToolOutput(success=False, error="Tool execution failed: Something went wrong")
```

To disable automatic error handling:

```python
class StrictTool(BaseRagDocManTool):
    name: str = "strict_tool"
    description: str = "A tool with strict error handling"
    args_schema: Type[BaseModel] = ToolInput
    handle_tool_error: bool = False  # Disable error handling
    
    def _execute(self) -> ToolOutput:
        raise ValueError("This will propagate")

tool = StrictTool()
tool._run()  # Raises ValueError
```

## Logging

The base tool class includes built-in logging:

```python
class VerboseTool(BaseRagDocManTool):
    name: str = "verbose_tool"
    description: str = "A tool with verbose logging"
    args_schema: Type[BaseModel] = ToolInput
    verbose: bool = True  # Enable verbose logging
    
    def _execute(self) -> ToolOutput:
        self._log_execution_start("Processing data")
        # ... do work ...
        return self._create_success_output("Done")
```

Logs include:
- Execution start/end times
- Input parameters (in verbose mode)
- Execution duration
- Error stack traces

## Helper Methods

The base class provides several helper methods:

### Creating Outputs

```python
# Success output
output = self._create_success_output(
    message="Operation successful",
    data={"key": "value"}
)

# Error output
output = self._create_error_output(
    message="Operation failed",
    error="Detailed error message"
)
```

### Logging

```python
# Log operation start
self._log_execution_start("Starting operation")

# Log operation end
self._log_execution_end("Operation", execution_time=1.5)

# Log error
self._log_error("Operation", exception)
```

## Integration with LangChain Agents

Tools can be used directly with LangChain agents:

```python
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI

# Create tools
tools = [
    GreetingTool(),
    AsyncSearchTool(),
]

# Create agent
llm = ChatOpenAI(model="gpt-4")
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)

# Use agent
result = agent_executor.invoke({
    "input": "Greet Alice in Chinese"
})
```

## Requirements Validation

This tool system validates the following requirements:

- **Requirement 10.1**: Uses LangChain 1.x's BaseTool class
- **Requirement 10.2**: Validates input parameters using Pydantic schemas
- **Requirement 10.3**: Returns structured output with status, data, and errors
- **Requirement 10.4**: Auto-generates tool documentation from metadata
- **Requirement 10.5**: Returns detailed validation errors for invalid inputs

## Testing

See `tests/test_base_tool.py` for comprehensive test examples covering:
- Input validation
- Output format
- Error handling
- Async execution
- Helper methods

## Next Steps

The following tool implementations are built on this foundation:

### Knowledge Base Management Tools (✓ Implemented)
- `CreateKnowledgeBaseTool`: Create new knowledge bases
- `ListKnowledgeBasesTool`: List all knowledge bases with pagination
- `GetKnowledgeBaseTool`: Get knowledge base details
- `UpdateKnowledgeBaseTool`: Update knowledge base metadata
- `DeleteKnowledgeBaseTool`: Delete knowledge bases

See `tools/knowledge_base_tools.py` for implementation details.

### Document Management Tools (✓ Implemented)
- `UploadDocumentTool`: Upload documents with automatic processing and embedding
- `ListDocumentsTool`: List documents in a knowledge base with pagination
- `GetDocumentTool`: Get document details and metadata
- `UpdateDocumentTool`: Update documents with automatic re-embedding
- `DeleteDocumentTool`: Delete documents and clean up vectors

See `tools/document_tools.py` for implementation details.

### Upcoming Tools
- Search Tools: Hybrid retrieval with vector and keyword search
- RAG Generation Tools: Generate answers based on knowledge base content

## Document Management Tools

The document management tools provide comprehensive document lifecycle management:

### UploadDocumentTool

Upload and process documents into a knowledge base:

```python
from tools.document_tools import UploadDocumentTool

tool = UploadDocumentTool(
    db_session=db,
    vector_store=vector_store,
    embedding_provider=embedding_provider
)

result = await tool._arun(
    kb_id="kb_123",
    file_path="/path/to/document.pdf",
    file_name="document.pdf"
)

# Returns document details including chunk count and embeddings
print(result.data["doc_id"])
print(result.data["chunk_count"])
```

**Features:**
- Automatic file validation
- Document chunking based on file type
- Embedding generation for all chunks
- Vector storage integration

### ListDocumentsTool

List documents with pagination support:

```python
from tools.document_tools import ListDocumentsTool

tool = ListDocumentsTool(
    db_session=db,
    vector_store=vector_store
)

result = await tool._arun(
    kb_id="kb_123",
    skip=0,
    limit=20
)

# Returns paginated document list
for doc in result.data["documents"]:
    print(f"{doc['doc_name']}: {doc['chunk_count']} chunks")
```

**Features:**
- Pagination support (skip/limit)
- Document metadata (size, type, chunk count)
- Total count and page information

### GetDocumentTool

Retrieve detailed information about a specific document:

```python
from tools.document_tools import GetDocumentTool

tool = GetDocumentTool(
    db_session=db,
    vector_store=vector_store
)

result = await tool._arun(
    kb_id="kb_123",
    doc_id="doc_456"
)

# Returns complete document metadata
print(result.data["doc_name"])
print(result.data["file_size"])
print(result.data["created_at"])
```

### UpdateDocumentTool

Update document content with automatic re-embedding:

```python
from tools.document_tools import UpdateDocumentTool

tool = UpdateDocumentTool(
    db_session=db,
    vector_store=vector_store,
    embedding_provider=embedding_provider
)

result = await tool._arun(
    kb_id="kb_123",
    doc_id="doc_456",
    file_path="/path/to/updated_document.pdf",
    file_name="updated_document.pdf"
)

# Old content is deleted, new content is processed and embedded
print(result.data["chunk_count"])  # New chunk count
```

**Features:**
- Automatic cleanup of old vectors
- Re-processing and re-embedding of new content
- Preserves document metadata

### DeleteDocumentTool

Delete documents and clean up all associated data:

```python
from tools.document_tools import DeleteDocumentTool

tool = DeleteDocumentTool(
    db_session=db,
    vector_store=vector_store
)

result = await tool._arun(
    kb_id="kb_123",
    doc_id="doc_456"
)

# Document, chunks, and vectors are all deleted
print(result.data["deleted"])  # True
```

**Features:**
- Cascading deletion of chunks
- Vector cleanup from vector store
- File deletion from storage

## Usage with Agent

All document tools can be used with LangChain agents for natural language interaction:

```python
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from tools.document_tools import (
    UploadDocumentTool,
    ListDocumentsTool,
    GetDocumentTool,
    UpdateDocumentTool,
    DeleteDocumentTool,
)

# Create tools
tools = [
    UploadDocumentTool(db, vector_store, embedding_provider),
    ListDocumentsTool(db, vector_store),
    GetDocumentTool(db, vector_store),
    UpdateDocumentTool(db, vector_store, embedding_provider),
    DeleteDocumentTool(db, vector_store),
]

# Create agent
llm = ChatOpenAI(model="gpt-4")
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)

# Natural language commands
result = agent_executor.invoke({
    "input": "Upload the product_manual.pdf to the Product Docs knowledge base"
})

result = agent_executor.invoke({
    "input": "Show me all documents in the Product Docs knowledge base"
})

result = agent_executor.invoke({
    "input": "Delete the old_manual.pdf from Product Docs"
})
```
