"""Unit tests for PersistentConversationMemory class."""
import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from langchain_core.messages import HumanMessage, AIMessage

from core.persistent_conversation_memory import PersistentConversationMemory
from models.orm import Base, ConversationHistory


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    # Create session
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    # Cleanup
    session.close()
    engine.dispose()


@pytest.fixture
def session_id():
    """Generate a unique session ID for testing."""
    return f"test-session-{uuid.uuid4()}"


class TestPersistentConversationMemory:
    """Test suite for PersistentConversationMemory."""
    
    def test_initialization_with_database(self, db_session, session_id):
        """Test memory initialization with database session."""
        memory = PersistentConversationMemory(
            session_id=session_id,
            db_session=db_session
        )
        
        assert memory.session_id == session_id
        assert memory.db_session is db_session
        assert memory.auto_save is True
        assert memory._loaded is True
        assert len(memory.messages) == 0
    
    def test_initialization_without_database(self, session_id):
        """Test memory initialization without database session."""
        memory = PersistentConversationMemory(
            session_id=session_id,
            db_session=None
        )
        
        assert memory.session_id == session_id
        assert memory.db_session is None
        assert memory._loaded is False
    
    def test_add_user_message_saves_to_database(self, db_session, session_id):
        """Test that adding user message saves to database."""
        memory = PersistentConversationMemory(
            session_id=session_id,
            db_session=db_session
        )
        
        memory.add_user_message("Hello, AI!")
        
        # Check in-memory
        assert len(memory.messages) == 1
        assert isinstance(memory.messages[0], HumanMessage)
        
        # Check database
        db_messages = db_session.query(ConversationHistory).filter(
            ConversationHistory.session_id == session_id
        ).all()
        
        assert len(db_messages) == 1
        assert db_messages[0].role == "user"
        assert db_messages[0].content == "Hello, AI!"
    
    def test_add_ai_message_saves_to_database(self, db_session, session_id):
        """Test that adding AI message saves to database."""
        memory = PersistentConversationMemory(
            session_id=session_id,
            db_session=db_session
        )
        
        memory.add_ai_message("Hello, human!")
        
        # Check in-memory
        assert len(memory.messages) == 1
        assert isinstance(memory.messages[0], AIMessage)
        
        # Check database
        db_messages = db_session.query(ConversationHistory).filter(
            ConversationHistory.session_id == session_id
        ).all()
        
        assert len(db_messages) == 1
        assert db_messages[0].role == "assistant"
        assert db_messages[0].content == "Hello, human!"

    
    def test_load_history_from_database(self, db_session, session_id):
        """Test loading conversation history from database."""
        # Pre-populate database with messages
        messages_data = [
            ("user", "What is AI?"),
            ("assistant", "AI stands for Artificial Intelligence."),
            ("user", "Tell me more."),
            ("assistant", "AI is a broad field of computer science.")
        ]
        
        for role, content in messages_data:
            db_msg = ConversationHistory(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role=role,
                content=content,
                created_at=datetime.utcnow()
            )
            db_session.add(db_msg)
        db_session.commit()
        
        # Create memory instance - should load from database
        memory = PersistentConversationMemory(
            session_id=session_id,
            db_session=db_session
        )
        
        # Verify messages were loaded
        assert len(memory.messages) == 4
        assert isinstance(memory.messages[0], HumanMessage)
        assert memory.messages[0].content == "What is AI?"
        assert isinstance(memory.messages[1], AIMessage)
        assert memory.messages[1].content == "AI stands for Artificial Intelligence."
    
    def test_persistence_across_instances(self, db_session, session_id):
        """Test that messages persist across different memory instances."""
        # First instance - add messages
        memory1 = PersistentConversationMemory(
            session_id=session_id,
            db_session=db_session
        )
        memory1.add_user_message("First message")
        memory1.add_ai_message("First response")
        
        # Second instance - should load previous messages
        memory2 = PersistentConversationMemory(
            session_id=session_id,
            db_session=db_session
        )
        
        assert len(memory2.messages) == 2
        assert memory2.messages[0].content == "First message"
        assert memory2.messages[1].content == "First response"
        
        # Add more messages
        memory2.add_user_message("Second message")
        
        # Third instance - should have all messages
        memory3 = PersistentConversationMemory(
            session_id=session_id,
            db_session=db_session
        )
        
        assert len(memory3.messages) == 3
        assert memory3.messages[2].content == "Second message"
    
    def test_clear_removes_from_database(self, db_session, session_id):
        """Test that clear removes messages from database."""
        memory = PersistentConversationMemory(
            session_id=session_id,
            db_session=db_session
        )
        
        memory.add_user_message("Message 1")
        memory.add_ai_message("Response 1")
        
        # Verify messages exist
        assert len(memory.messages) == 2
        db_count = db_session.query(ConversationHistory).filter(
            ConversationHistory.session_id == session_id
        ).count()
        assert db_count == 2
        
        # Clear
        memory.clear()
        
        # Verify cleared from memory
        assert len(memory.messages) == 0
        
        # Verify cleared from database
        db_count = db_session.query(ConversationHistory).filter(
            ConversationHistory.session_id == session_id
        ).count()
        assert db_count == 0
    
    def test_auto_save_disabled(self, db_session, session_id):
        """Test that auto_save=False prevents database writes."""
        memory = PersistentConversationMemory(
            session_id=session_id,
            db_session=db_session,
            auto_save=False
        )
        
        memory.add_user_message("Test message")
        
        # Check in-memory
        assert len(memory.messages) == 1
        
        # Check database - should be empty
        db_count = db_session.query(ConversationHistory).filter(
            ConversationHistory.session_id == session_id
        ).count()
        assert db_count == 0
    
    def test_session_isolation(self, db_session):
        """Test that different sessions are isolated in database."""
        session1_id = "session-1"
        session2_id = "session-2"
        
        memory1 = PersistentConversationMemory(
            session_id=session1_id,
            db_session=db_session
        )
        memory2 = PersistentConversationMemory(
            session_id=session2_id,
            db_session=db_session
        )
        
        memory1.add_user_message("Message in session 1")
        memory2.add_user_message("Message in session 2")
        
        # Verify in-memory isolation
        assert len(memory1.messages) == 1
        assert len(memory2.messages) == 1
        
        # Verify database isolation
        db_messages1 = db_session.query(ConversationHistory).filter(
            ConversationHistory.session_id == session1_id
        ).all()
        db_messages2 = db_session.query(ConversationHistory).filter(
            ConversationHistory.session_id == session2_id
        ).all()
        
        assert len(db_messages1) == 1
        assert len(db_messages2) == 1
        assert db_messages1[0].content == "Message in session 1"
        assert db_messages2[0].content == "Message in session 2"
    
    def test_reload_from_database(self, db_session, session_id):
        """Test reloading messages from database."""
        memory = PersistentConversationMemory(
            session_id=session_id,
            db_session=db_session
        )
        
        memory.add_user_message("Original message")
        
        # Manually add a message to database (simulating external change)
        db_msg = ConversationHistory(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="assistant",
            content="External message",
            created_at=datetime.utcnow()
        )
        db_session.add(db_msg)
        db_session.commit()
        
        # Before reload - should only have original message
        assert len(memory.messages) == 1
        
        # Reload
        memory.reload_from_database()
        
        # After reload - should have both messages
        assert len(memory.messages) == 2
        assert memory.messages[1].content == "External message"
    
    def test_max_history_with_persistence(self, db_session, session_id):
        """Test that max_history works correctly with persistence."""
        memory = PersistentConversationMemory(
            session_id=session_id,
            db_session=db_session,
            max_history=3
        )
        
        # Add 5 messages
        for i in range(5):
            memory.add_user_message(f"Message {i}")
        
        # get_messages should only return last 3
        messages = memory.get_messages()
        assert len(messages) == 3
        assert messages[0].content == "Message 2"
        assert messages[2].content == "Message 4"
        
        # But all 5 should be in database
        db_count = db_session.query(ConversationHistory).filter(
            ConversationHistory.session_id == session_id
        ).count()
        assert db_count == 5
    
    def test_error_handling_on_load(self, session_id):
        """Test error handling when database load fails."""
        # Create memory with invalid database session
        # This should not raise an exception due to degradation strategy
        memory = PersistentConversationMemory(
            session_id=session_id,
            db_session=None  # No database session
        )
        
        # Should still work with in-memory storage
        memory.add_user_message("Test message")
        assert len(memory.messages) == 1
    
    def test_retention_policy_cleanup(self, db_session, session_id):
        """Test automatic cleanup of expired records based on retention policy."""
        # Add old messages (older than retention period)
        old_date = datetime.utcnow() - timedelta(days=10)
        for i in range(3):
            db_msg = ConversationHistory(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role="user",
                content=f"Old message {i}",
                created_at=old_date
            )
            db_session.add(db_msg)
        
        # Add recent messages
        recent_date = datetime.utcnow() - timedelta(days=2)
        for i in range(2):
            db_msg = ConversationHistory(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role="user",
                content=f"Recent message {i}",
                created_at=recent_date
            )
            db_session.add(db_msg)
        
        db_session.commit()
        
        # Create memory with 7-day retention policy
        # Should delete old messages (10 days old) but keep recent ones (2 days old)
        memory = PersistentConversationMemory(
            session_id=session_id,
            db_session=db_session,
            retention_days=7
        )
        
        # Should only have recent messages
        assert len(memory.messages) == 2
        assert "Recent message" in memory.messages[0].content
        
        # Verify database
        db_count = db_session.query(ConversationHistory).filter(
            ConversationHistory.session_id == session_id
        ).count()
        assert db_count == 2
    
    def test_retention_policy_none(self, db_session, session_id):
        """Test that retention_days=None keeps all records."""
        # Add old messages
        old_date = datetime.utcnow() - timedelta(days=100)
        for i in range(3):
            db_msg = ConversationHistory(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role="user",
                content=f"Old message {i}",
                created_at=old_date
            )
            db_session.add(db_msg)
        db_session.commit()
        
        # Create memory without retention policy
        memory = PersistentConversationMemory(
            session_id=session_id,
            db_session=db_session,
            retention_days=None
        )
        
        # Should keep all messages
        assert len(memory.messages) == 3
    
    def test_batch_cleanup_expired_records(self, db_session):
        """Test batch cleanup of expired records across all sessions."""
        # Create messages in multiple sessions with different ages
        sessions = ["session-1", "session-2", "session-3"]
        
        # Old messages (should be deleted)
        old_date = datetime.utcnow() - timedelta(days=40)
        for session_id in sessions:
            for i in range(2):
                db_msg = ConversationHistory(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    role="user",
                    content=f"Old message {i}",
                    created_at=old_date
                )
                db_session.add(db_msg)
        
        # Recent messages (should be kept)
        recent_date = datetime.utcnow() - timedelta(days=10)
        for session_id in sessions:
            db_msg = ConversationHistory(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role="user",
                content="Recent message",
                created_at=recent_date
            )
            db_session.add(db_msg)
        
        db_session.commit()
        
        # Total: 6 old + 3 recent = 9 messages
        total_count = db_session.query(ConversationHistory).count()
        assert total_count == 9
        
        # Batch cleanup with 30-day retention
        deleted_count = PersistentConversationMemory.cleanup_all_expired_records(
            db_session=db_session,
            retention_days=30
        )
        
        # Should delete 6 old messages
        assert deleted_count == 6
        
        # Should have 3 recent messages remaining
        remaining_count = db_session.query(ConversationHistory).count()
        assert remaining_count == 3
    
    def test_message_ordering_preserved(self, db_session, session_id):
        """Test that message ordering is preserved when loading from database."""
        # Add messages with specific order
        messages = [
            ("user", "First"),
            ("assistant", "Second"),
            ("user", "Third"),
            ("assistant", "Fourth"),
            ("user", "Fifth")
        ]
        
        for role, content in messages:
            db_msg = ConversationHistory(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role=role,
                content=content,
                created_at=datetime.utcnow()
            )
            db_session.add(db_msg)
            db_session.commit()
            # Small delay to ensure different timestamps
            import time
            time.sleep(0.01)
        
        # Load messages
        memory = PersistentConversationMemory(
            session_id=session_id,
            db_session=db_session
        )
        
        # Verify order
        assert len(memory.messages) == 5
        assert memory.messages[0].content == "First"
        assert memory.messages[1].content == "Second"
        assert memory.messages[2].content == "Third"
        assert memory.messages[3].content == "Fourth"
        assert memory.messages[4].content == "Fifth"
    
    def test_add_message_generic_with_persistence(self, db_session, session_id):
        """Test adding generic message with database persistence."""
        memory = PersistentConversationMemory(
            session_id=session_id,
            db_session=db_session
        )
        
        message = HumanMessage(content="Generic message")
        memory.add_message(message)
        
        # Check in-memory
        assert len(memory.messages) == 1
        
        # Check database
        db_messages = db_session.query(ConversationHistory).filter(
            ConversationHistory.session_id == session_id
        ).all()
        
        assert len(db_messages) == 1
        assert db_messages[0].content == "Generic message"
    
    def test_async_clear(self, db_session, session_id):
        """Test async clear method."""
        import asyncio
        
        memory = PersistentConversationMemory(
            session_id=session_id,
            db_session=db_session
        )
        
        memory.add_user_message("Test message")
        assert len(memory.messages) == 1
        
        # Call async clear
        asyncio.run(memory.aclear())
        
        # Verify cleared
        assert len(memory.messages) == 0
        db_count = db_session.query(ConversationHistory).filter(
            ConversationHistory.session_id == session_id
        ).count()
        assert db_count == 0
