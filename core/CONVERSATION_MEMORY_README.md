# Conversation Memory System

## Overview

The Conversation Memory System provides a robust solution for managing chat history in the RagDocMan Agent. It supports both in-memory and persistent storage, with features like automatic message truncation, context retention, and seamless LangChain integration.

## Features

- **Message Storage**: Store user and AI messages with proper typing
- **Max History Limit**: Automatically limit visible messages to prevent context overflow
- **Message Truncation**: Intelligent truncation for long conversations
- **LangChain Integration**: Compatible with LangChain's memory interface
- **Persistent Storage**: Optional database persistence for conversation history
- **Session Management**: Isolated conversations per session ID
- **Context Summary**: Get statistics about conversation state

## Components

### 1. ConversationMemory

Basic in-memory conversation storage.

**Key Features:**
- Stores messages in memory
- Enforces max_history limit
- Automatic truncation for long conversations
- LangChain-compatible interface

**Usage:**

```python
from core.conversation_memory import ConversationMemory

# Create memory instance
memory = ConversationMemory(
    session_id="user-123",
    max_history=10
)

# Add messages
memory.add_user_message("Hello!")
memory.add_ai_message("Hi there! How can I help?")

# Get messages
messages = memory.get_messages()

# Get context summary
summary = memory.get_context_summary()
```

### 2. PersistentConversationMemory

Extends ConversationMemory with database persistence.

**Key Features:**
- All features of ConversationMemory
- Automatic database persistence
- Load history on initialization
- Survive application restarts
- Graceful degradation if database unavailable

**Usage:**

```python
from core.persistent_conversation_memory import PersistentConversationMemory
from database import SessionLocal

# Create database session
db = SessionLocal()

# Create persistent memory
memory = PersistentConversationMemory(
    session_id="user-123",
    max_history=10,
    db_session=db,
    auto_save=True
)

# Messages are automatically saved to database
memory.add_user_message("Hello!")
memory.add_ai_message("Hi there!")

# On next initialization, messages are loaded from database
memory2 = PersistentConversationMemory(
    session_id="user-123",
    max_history=10,
    db_session=db
)
# memory2 now has the previous messages loaded
```

## API Reference

### ConversationMemory

#### Constructor

```python
ConversationMemory(
    session_id: str,
    max_history: int = 10,
    memory_key: str = "history",
    return_messages: bool = True
)
```

**Parameters:**
- `session_id`: Unique identifier for the conversation session
- `max_history`: Maximum number of messages to retain (default: 10)
- `memory_key`: Key used to store memory in context (default: "history")
- `return_messages`: Whether to return messages as objects or strings (default: True)

#### Methods

##### add_user_message(content: str)
Add a user message to the conversation history.

```python
memory.add_user_message("What is RAG?")
```

##### add_ai_message(content: str)
Add an AI message to the conversation history.

```python
memory.add_ai_message("RAG stands for Retrieval-Augmented Generation.")
```

##### add_message(message: BaseMessage)
Add a generic message to the conversation history.

```python
from langchain_core.messages import HumanMessage
message = HumanMessage(content="Hello")
memory.add_message(message)
```

##### get_messages() -> List[BaseMessage]
Get conversation messages with max_history limit applied.

```python
messages = memory.get_messages()
# Returns only the most recent max_history messages
```

##### get_all_messages() -> List[BaseMessage]
Get all conversation messages without limit.

```python
all_messages = memory.get_all_messages()
# Returns all messages, including those beyond max_history
```

##### clear()
Clear all messages from memory.

```python
memory.clear()
```

##### get_message_count() -> int
Get the total number of messages in memory.

```python
count = memory.get_message_count()
```

##### get_context_summary() -> Dict[str, Any]
Get a summary of the current conversation context.

```python
summary = memory.get_context_summary()
# Returns: {
#     "session_id": "user-123",
#     "total_messages": 10,
#     "visible_messages": 10,
#     "max_history": 10,
#     "user_messages": 5,
#     "ai_messages": 5
# }
```

##### load_memory_variables(inputs: Dict[str, Any]) -> Dict[str, Any]
Load memory variables for LangChain integration.

```python
variables = memory.load_memory_variables({})
# Returns: {"history": [messages...]}
```

##### save_context(inputs: Dict[str, Any], outputs: Dict[str, str])
Save context from a conversation turn (LangChain integration).

```python
inputs = {"input": "What is AI?"}
outputs = {"output": "AI is Artificial Intelligence."}
memory.save_context(inputs, outputs)
```

### PersistentConversationMemory

Inherits all methods from ConversationMemory with additional features:

#### Constructor

```python
PersistentConversationMemory(
    session_id: str,
    max_history: int = 10,
    memory_key: str = "history",
    return_messages: bool = True,
    db_session: Optional[Session] = None,
    auto_save: bool = True
)
```

**Additional Parameters:**
- `db_session`: SQLAlchemy database session for persistence
- `auto_save`: Whether to automatically save messages to database (default: True)

#### Additional Methods

##### reload_from_database()
Reload conversation history from database.

```python
memory.reload_from_database()
```

##### aclear()
Async version of clear method.

```python
await memory.aclear()
```

## Database Schema

The conversation history is stored in the `conversation_history` table:

```sql
CREATE TABLE conversation_history (
    id VARCHAR PRIMARY KEY,
    session_id VARCHAR NOT NULL,
    role VARCHAR NOT NULL,  -- "user" or "assistant"
    content TEXT NOT NULL,
    message_metadata JSON,
    created_at DATETIME NOT NULL,
    INDEX idx_session_created (session_id, created_at)
);
```

## Message Truncation

The memory system implements intelligent truncation to prevent unlimited memory growth:

1. **Visible Messages**: Only the most recent `max_history` messages are returned by `get_messages()`
2. **Buffer**: The system maintains a buffer of `2 * max_history` messages in memory
3. **Automatic Truncation**: When messages exceed the buffer size, older messages are automatically removed

**Example:**

```python
memory = ConversationMemory(session_id="user-123", max_history=5)

# Add 15 messages
for i in range(15):
    memory.add_user_message(f"Message {i}")

# get_messages() returns only the last 5 messages
messages = memory.get_messages()
assert len(messages) == 5

# get_all_messages() returns up to 10 messages (buffer size)
all_messages = memory.get_all_messages()
assert len(all_messages) == 10
```

## LangChain Integration

The memory system is designed to work seamlessly with LangChain:

### Using with LangChain Agents

```python
from langchain.agents import AgentExecutor
from core.conversation_memory import ConversationMemory

# Create memory
memory = ConversationMemory(session_id="user-123")

# Use with agent (pseudo-code)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,  # Pass memory to agent
    verbose=True
)

# Agent will automatically use memory for context
response = agent_executor.invoke({"input": "Hello!"})
```

### Manual Context Management

```python
# Save conversation turn
inputs = {"input": "What is Python?"}
outputs = {"output": "Python is a programming language."}
memory.save_context(inputs, outputs)

# Load context for next turn
context = memory.load_memory_variables({})
# Use context in your prompt
```

## Best Practices

### 1. Choose Appropriate max_history

- **Short conversations**: `max_history=5-10`
- **Medium conversations**: `max_history=10-20`
- **Long conversations**: `max_history=20-50`

Consider your LLM's context window and the average message length.

### 2. Use Persistent Memory for Production

For production applications, use `PersistentConversationMemory` to ensure conversation history survives application restarts:

```python
memory = PersistentConversationMemory(
    session_id=user_id,
    max_history=20,
    db_session=db,
    auto_save=True
)
```

### 3. Session ID Management

Use meaningful session IDs that map to your application's user/conversation structure:

```python
# Per-user session
session_id = f"user-{user_id}"

# Per-conversation session
session_id = f"conversation-{conversation_id}"

# Per-user-per-topic session
session_id = f"user-{user_id}-topic-{topic_id}"
```

### 4. Clear Old Sessions

Periodically clear old conversation sessions to prevent database bloat:

```python
# Clear specific session
memory.clear()

# Or delete old records from database
db.query(ConversationHistory).filter(
    ConversationHistory.created_at < cutoff_date
).delete()
```

### 5. Error Handling

The persistent memory system implements graceful degradation:

```python
try:
    memory = PersistentConversationMemory(
        session_id="user-123",
        db_session=db
    )
except Exception as e:
    logger.error(f"Failed to load persistent memory: {e}")
    # Fall back to in-memory storage
    memory = ConversationMemory(session_id="user-123")
```

## Examples

See `examples/conversation_memory_example.py` for comprehensive usage examples:

```bash
python examples/conversation_memory_example.py
```

## Requirements

The conversation memory system validates the following requirements:

- **Requirement 11.1**: Store each message (user input, agent response, tool calls)
- **Requirement 11.2**: Retrieve previous conversation history
- **Requirement 11.3**: Use history as agent context
- **Requirement 11.4**: Retain most recent N messages when history exceeds limit
- **Requirement 11.5**: Delete all history when user requests
- **Requirement 12.1-12.5**: Context retention mechanism

## Testing

Run the test suite:

```bash
pytest tests/test_conversation_memory.py -v
```

## Future Enhancements

Potential future improvements:

1. **Message Summarization**: Automatically summarize old messages instead of truncating
2. **Semantic Compression**: Use embeddings to compress similar messages
3. **Topic Segmentation**: Automatically detect topic changes and segment conversations
4. **Multi-modal Support**: Support for images, files, and other media types
5. **Async Database Operations**: Full async support for database operations
6. **Redis Backend**: Optional Redis backend for distributed systems
7. **Message Search**: Search through conversation history by content or metadata

## License

This module is part of the RagDocMan project.
