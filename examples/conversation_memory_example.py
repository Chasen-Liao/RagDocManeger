"""Example usage of ConversationMemory and PersistentConversationMemory.

This example demonstrates how to use the conversation memory system
for managing chat history in the RagDocMan Agent.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.conversation_memory import ConversationMemory
from core.persistent_conversation_memory import PersistentConversationMemory
from database import SessionLocal, init_db


def example_basic_memory():
    """Example 1: Basic in-memory conversation storage."""
    print("=" * 60)
    print("Example 1: Basic ConversationMemory")
    print("=" * 60)
    
    # Create a memory instance for a session
    memory = ConversationMemory(
        session_id="user-123",
        max_history=5
    )
    
    # Simulate a conversation
    print("\n1. Adding messages to conversation:")
    memory.add_user_message("Hello! What is RAG?")
    memory.add_ai_message("RAG stands for Retrieval-Augmented Generation. It's a technique that combines retrieval of relevant documents with language model generation.")
    
    memory.add_user_message("Can you give me an example?")
    memory.add_ai_message("Sure! When you ask a question, RAG first searches a knowledge base for relevant information, then uses that information to generate a more accurate and informed response.")
    
    memory.add_user_message("That's helpful, thanks!")
    memory.add_ai_message("You're welcome! Feel free to ask if you have more questions.")
    
    # Get conversation history
    print("\n2. Retrieving conversation history:")
    messages = memory.get_messages()
    for i, msg in enumerate(messages):
        role = "User" if msg.__class__.__name__ == "HumanMessage" else "AI"
        print(f"   {i+1}. {role}: {msg.content[:60]}...")
    
    # Get context summary
    print("\n3. Context summary:")
    summary = memory.get_context_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    
    # Load memory variables (for use with LangChain)
    print("\n4. Memory variables (for LangChain integration):")
    variables = memory.load_memory_variables({})
    print(f"   Memory key: {memory.memory_key}")
    print(f"   Number of messages: {len(variables[memory.memory_key])}")
    
    print("\n")


def example_max_history_limit():
    """Example 2: Demonstrating max_history limit."""
    print("=" * 60)
    print("Example 2: Max History Limit")
    print("=" * 60)
    
    # Create memory with small max_history
    memory = ConversationMemory(
        session_id="user-456",
        max_history=3
    )
    
    # Add many messages
    print("\n1. Adding 10 messages:")
    for i in range(5):
        memory.add_user_message(f"User message {i+1}")
        memory.add_ai_message(f"AI response {i+1}")
    
    print(f"   Total messages added: 10")
    print(f"   Total messages in memory: {memory.get_message_count()}")
    
    # Get visible messages (limited by max_history)
    print("\n2. Visible messages (limited by max_history=3):")
    messages = memory.get_messages()
    print(f"   Number of visible messages: {len(messages)}")
    for msg in messages:
        role = "User" if msg.__class__.__name__ == "HumanMessage" else "AI"
        print(f"   - {role}: {msg.content}")
    
    # Get all messages (including truncated ones)
    print("\n3. All messages in memory:")
    all_messages = memory.get_all_messages()
    print(f"   Total messages: {len(all_messages)}")
    
    print("\n")


def example_save_context():
    """Example 3: Using save_context for LangChain integration."""
    print("=" * 60)
    print("Example 3: LangChain Integration with save_context")
    print("=" * 60)
    
    memory = ConversationMemory(
        session_id="user-789",
        max_history=10
    )
    
    # Simulate LangChain conversation turns
    print("\n1. Simulating LangChain conversation turns:")
    
    # Turn 1
    inputs = {"input": "What is the capital of France?"}
    outputs = {"output": "The capital of France is Paris."}
    memory.save_context(inputs, outputs)
    print(f"   Turn 1: User asked about France's capital")
    
    # Turn 2
    inputs = {"input": "What about Germany?"}
    outputs = {"output": "The capital of Germany is Berlin."}
    memory.save_context(inputs, outputs)
    print(f"   Turn 2: User asked about Germany's capital")
    
    # Turn 3
    inputs = {"input": "Tell me more about Paris."}
    outputs = {"output": "Paris is known as the City of Light and is famous for the Eiffel Tower, Louvre Museum, and its rich cultural heritage."}
    memory.save_context(inputs, outputs)
    print(f"   Turn 3: User asked about Paris")
    
    # Display conversation
    print("\n2. Full conversation:")
    messages = memory.get_messages()
    for i, msg in enumerate(messages):
        role = "User" if msg.__class__.__name__ == "HumanMessage" else "AI"
        print(f"   {i+1}. {role}: {msg.content}")
    
    print("\n")


def example_persistent_memory():
    """Example 4: Persistent memory with database storage."""
    print("=" * 60)
    print("Example 4: PersistentConversationMemory")
    print("=" * 60)
    
    # Initialize database
    print("\n1. Initializing database...")
    init_db()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Create persistent memory
        print("\n2. Creating persistent memory:")
        memory = PersistentConversationMemory(
            session_id="persistent-session-001",
            max_history=10,
            db_session=db,
            auto_save=True
        )
        
        # Add messages (automatically saved to database)
        print("\n3. Adding messages (auto-saved to database):")
        memory.add_user_message("Hello! I want to learn about vector databases.")
        memory.add_ai_message("Vector databases are specialized databases designed to store and query high-dimensional vectors efficiently.")
        
        memory.add_user_message("What are some examples?")
        memory.add_ai_message("Popular vector databases include ChromaDB, Pinecone, Weaviate, and FAISS.")
        
        print(f"   Added {memory.get_message_count()} messages")
        
        # Simulate application restart by creating new memory instance
        print("\n4. Simulating application restart...")
        print("   Creating new memory instance with same session_id...")
        
        memory2 = PersistentConversationMemory(
            session_id="persistent-session-001",
            max_history=10,
            db_session=db,
            auto_save=True
        )
        
        # Messages should be loaded from database
        print(f"\n5. Messages loaded from database:")
        messages = memory2.get_messages()
        print(f"   Loaded {len(messages)} messages:")
        for i, msg in enumerate(messages):
            role = "User" if msg.__class__.__name__ == "HumanMessage" else "AI"
            print(f"   {i+1}. {role}: {msg.content[:60]}...")
        
        # Clear conversation
        print("\n6. Clearing conversation history:")
        memory2.clear()
        print(f"   Messages after clear: {memory2.get_message_count()}")
        
    finally:
        db.close()
    
    print("\n")


def example_memory_string_format():
    """Example 5: Getting memory as string format."""
    print("=" * 60)
    print("Example 5: Memory as String Format")
    print("=" * 60)
    
    # Create memory that returns strings instead of message objects
    memory = ConversationMemory(
        session_id="user-string",
        max_history=10,
        return_messages=False  # Return as string
    )
    
    # Add conversation
    print("\n1. Adding conversation:")
    memory.add_user_message("What is machine learning?")
    memory.add_ai_message("Machine learning is a subset of AI that enables systems to learn from data.")
    memory.add_user_message("Can you give an example?")
    memory.add_ai_message("Sure! Email spam filters use machine learning to classify emails.")
    
    # Get as string format
    print("\n2. Memory as string format:")
    variables = memory.load_memory_variables({})
    history_string = variables[memory.memory_key]
    print(f"   {history_string}")
    
    print("\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ConversationMemory Examples")
    print("=" * 60 + "\n")
    
    # Run examples
    example_basic_memory()
    example_max_history_limit()
    example_save_context()
    example_memory_string_format()
    
    # Note: Persistent memory example requires database setup
    print("\nNote: To run the persistent memory example, uncomment the line below:")
    print("# example_persistent_memory()")
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60 + "\n")
