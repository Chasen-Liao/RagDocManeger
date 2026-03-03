"""Unit tests for ConversationMemory class."""
import pytest
from langchain_core.messages import HumanMessage, AIMessage
from core.conversation_memory import ConversationMemory


class TestConversationMemory:
    """Test suite for ConversationMemory."""
    
    def test_initialization(self):
        """Test memory initialization with default parameters."""
        memory = ConversationMemory(session_id="test-session")
        
        assert memory.session_id == "test-session"
        assert memory.max_history == 10
        assert memory.memory_key == "history"
        assert memory.return_messages is True
        assert len(memory.messages) == 0
    
    def test_initialization_with_custom_params(self):
        """Test memory initialization with custom parameters."""
        memory = ConversationMemory(
            session_id="custom-session",
            max_history=5,
            memory_key="chat_history",
            return_messages=False
        )
        
        assert memory.session_id == "custom-session"
        assert memory.max_history == 5
        assert memory.memory_key == "chat_history"
        assert memory.return_messages is False
    
    def test_add_user_message(self):
        """Test adding user messages."""
        memory = ConversationMemory(session_id="test-session")
        
        memory.add_user_message("Hello, AI!")
        
        assert len(memory.messages) == 1
        assert isinstance(memory.messages[0], HumanMessage)
        assert memory.messages[0].content == "Hello, AI!"
    
    def test_add_ai_message(self):
        """Test adding AI messages."""
        memory = ConversationMemory(session_id="test-session")
        
        memory.add_ai_message("Hello, human!")
        
        assert len(memory.messages) == 1
        assert isinstance(memory.messages[0], AIMessage)
        assert memory.messages[0].content == "Hello, human!"
    
    def test_add_multiple_messages(self):
        """Test adding multiple messages in sequence."""
        memory = ConversationMemory(session_id="test-session")
        
        memory.add_user_message("What is AI?")
        memory.add_ai_message("AI stands for Artificial Intelligence.")
        memory.add_user_message("Tell me more.")
        memory.add_ai_message("AI is a broad field of computer science.")
        
        assert len(memory.messages) == 4
        assert isinstance(memory.messages[0], HumanMessage)
        assert isinstance(memory.messages[1], AIMessage)
        assert isinstance(memory.messages[2], HumanMessage)
        assert isinstance(memory.messages[3], AIMessage)
    
    def test_get_messages_within_limit(self):
        """Test getting messages when count is within max_history."""
        memory = ConversationMemory(session_id="test-session", max_history=10)
        
        for i in range(5):
            memory.add_user_message(f"User message {i}")
            memory.add_ai_message(f"AI message {i}")
        
        messages = memory.get_messages()
        
        assert len(messages) == 10
        assert messages[0].content == "User message 0"
        assert messages[-1].content == "AI message 4"
    
    def test_get_messages_exceeds_limit(self):
        """Test getting messages when count exceeds max_history."""
        memory = ConversationMemory(session_id="test-session", max_history=5)
        
        for i in range(10):
            memory.add_user_message(f"Message {i}")
        
        messages = memory.get_messages()
        
        # Should only return the last 5 messages
        assert len(messages) == 5
        assert messages[0].content == "Message 5"
        assert messages[-1].content == "Message 9"
    
    def test_get_all_messages(self):
        """Test getting all messages without limit."""
        memory = ConversationMemory(session_id="test-session", max_history=5)
        
        for i in range(10):
            memory.add_user_message(f"Message {i}")
        
        all_messages = memory.get_all_messages()
        
        # Should return all 10 messages
        assert len(all_messages) == 10
        assert all_messages[0].content == "Message 0"
        assert all_messages[-1].content == "Message 9"
    
    def test_message_truncation(self):
        """Test automatic message truncation for long conversations."""
        memory = ConversationMemory(session_id="test-session", max_history=5)
        
        # Add more than 2x max_history messages to trigger truncation
        for i in range(15):
            memory.add_user_message(f"Message {i}")
        
        # Should have truncated to buffer_size (2 * max_history = 10)
        assert len(memory.messages) == 10
        assert memory.messages[0].content == "Message 5"
        assert memory.messages[-1].content == "Message 14"
    
    def test_clear(self):
        """Test clearing conversation history."""
        memory = ConversationMemory(session_id="test-session")
        
        memory.add_user_message("Message 1")
        memory.add_ai_message("Response 1")
        assert len(memory.messages) == 2
        
        memory.clear()
        
        assert len(memory.messages) == 0
    
    def test_get_message_count(self):
        """Test getting message count."""
        memory = ConversationMemory(session_id="test-session")
        
        assert memory.get_message_count() == 0
        
        memory.add_user_message("Message 1")
        assert memory.get_message_count() == 1
        
        memory.add_ai_message("Response 1")
        assert memory.get_message_count() == 2
    
    def test_get_context_summary(self):
        """Test getting context summary."""
        memory = ConversationMemory(session_id="test-session", max_history=10)
        
        for i in range(3):
            memory.add_user_message(f"User {i}")
            memory.add_ai_message(f"AI {i}")
        
        summary = memory.get_context_summary()
        
        assert summary["session_id"] == "test-session"
        assert summary["total_messages"] == 6
        assert summary["visible_messages"] == 6
        assert summary["max_history"] == 10
        assert summary["user_messages"] == 3
        assert summary["ai_messages"] == 3
    
    def test_memory_variables(self):
        """Test memory_variables property."""
        memory = ConversationMemory(session_id="test-session", memory_key="chat")
        
        assert memory.memory_variables == ["chat"]
    
    def test_load_memory_variables_with_messages(self):
        """Test loading memory variables returns messages."""
        memory = ConversationMemory(session_id="test-session", return_messages=True)
        
        memory.add_user_message("Hello")
        memory.add_ai_message("Hi there")
        
        variables = memory.load_memory_variables({})
        
        assert "history" in variables
        assert len(variables["history"]) == 2
        assert isinstance(variables["history"][0], HumanMessage)
        assert isinstance(variables["history"][1], AIMessage)
    
    def test_load_memory_variables_as_string(self):
        """Test loading memory variables returns string format."""
        memory = ConversationMemory(session_id="test-session", return_messages=False)
        
        memory.add_user_message("Hello")
        memory.add_ai_message("Hi there")
        
        variables = memory.load_memory_variables({})
        
        assert "history" in variables
        assert isinstance(variables["history"], str)
        assert "Hello" in variables["history"]
        assert "Hi there" in variables["history"]
    
    def test_save_context(self):
        """Test saving context from conversation turn."""
        memory = ConversationMemory(session_id="test-session")
        
        inputs = {"input": "What is Python?"}
        outputs = {"output": "Python is a programming language."}
        
        memory.save_context(inputs, outputs)
        
        assert len(memory.messages) == 2
        assert memory.messages[0].content == "What is Python?"
        assert memory.messages[1].content == "Python is a programming language."
    
    def test_save_context_empty_input(self):
        """Test saving context with empty input."""
        memory = ConversationMemory(session_id="test-session")
        
        inputs = {}
        outputs = {"output": "Response"}
        
        memory.save_context(inputs, outputs)
        
        # Should only add AI message
        assert len(memory.messages) == 1
        assert isinstance(memory.messages[0], AIMessage)
    
    def test_save_context_empty_output(self):
        """Test saving context with empty output."""
        memory = ConversationMemory(session_id="test-session")
        
        inputs = {"input": "Question"}
        outputs = {}
        
        memory.save_context(inputs, outputs)
        
        # Should only add user message
        assert len(memory.messages) == 1
        assert isinstance(memory.messages[0], HumanMessage)
    
    def test_add_message_generic(self):
        """Test adding generic message."""
        memory = ConversationMemory(session_id="test-session")
        
        message = HumanMessage(content="Generic message")
        memory.add_message(message)
        
        assert len(memory.messages) == 1
        assert memory.messages[0].content == "Generic message"
    
    def test_max_history_enforcement_in_get_messages(self):
        """Test that get_messages enforces max_history limit."""
        memory = ConversationMemory(session_id="test-session", max_history=3)
        
        for i in range(10):
            memory.add_user_message(f"Message {i}")
        
        messages = memory.get_messages()
        
        # Should only return last 3 messages
        assert len(messages) == 3
        assert messages[0].content == "Message 7"
        assert messages[1].content == "Message 8"
        assert messages[2].content == "Message 9"
    
    def test_multiple_sessions_isolated(self):
        """Test that different sessions are isolated."""
        memory1 = ConversationMemory(session_id="session-1")
        memory2 = ConversationMemory(session_id="session-2")
        
        memory1.add_user_message("Message in session 1")
        memory2.add_user_message("Message in session 2")
        
        assert len(memory1.messages) == 1
        assert len(memory2.messages) == 1
        assert memory1.messages[0].content == "Message in session 1"
        assert memory2.messages[0].content == "Message in session 2"
