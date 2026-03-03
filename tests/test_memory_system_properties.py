"""Property-based tests for conversation memory system.

This module contains property-based tests using Hypothesis to verify that
the conversation memory system maintains correctness properties across
different inputs and scenarios.

**Validates: Requirements 11.4, 11.5, 13.1, 13.2, 13.3**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import MagicMock, patch
from datetime import datetime
import uuid
from sqlalchemy.orm import Session

from core.persistent_conversation_memory import PersistentConversationMemory
from core.conversation_memory import ConversationMemory
from models.orm import ConversationHistory, Base
from langchain_core.messages import HumanMessage, AIMessage


# Hypothesis strategies for generating test data
session_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pd")),
    min_size=5,
    max_size=50
).map(lambda x: f"session_{x}" if x else f"session_{uuid.uuid4().hex[:10]}")

message_content_strategy = st.text(
    min_size=1,
    max_size=500
).filter(lambda x: len(x.strip()) > 0)

max_history_strategy = st.integers(min_value=1, max_value=50)

message_count_strategy = st.integers(min_value=1, max_value=100)


def create_mock_db_session():
    """Create a mock database session for testing."""
    mock_session = MagicMock(spec=Session)
    mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    mock_session.query.return_value.filter.return_value.delete.return_value = 0
    return mock_session


class TestSaveLoadConsistency:
    """
    Property 12: Save-then-Load Consistency
    
    **Validates: Requirements 13.1, 13.2, 13.3**
    
    Tests that messages saved to the database can be retrieved consistently.
    This verifies the persistence layer works correctly and messages are
    not lost or corrupted during save/load operations.
    """

    @pytest.mark.asyncio
    @given(
        session_id=session_id_strategy,
        messages=st.lists(
            st.tuples(
                st.sampled_from(["user", "assistant"]),
                message_content_strategy
            ),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=50, deadline=None)
    async def test_saved_messages_are_retrievable(self, session_id, messages):
        """
        Property: Saved messages should be retrievable with same content and order.
        
        This test verifies that after saving messages to the database,
        we can create a new memory instance and retrieve the same messages
        in the same order with the same content.
        """
        assume(len(session_id.strip()) > 0)
        assume(len(messages) > 0)
        
        # Create mock database session
        mock_db = create_mock_db_session()
        
        # Create database records that will be returned by the query
        db_messages = []
        for idx, (role, content) in enumerate(messages):
            db_msg = MagicMock(spec=ConversationHistory)
            db_msg.id = str(uuid.uuid4())
            db_msg.session_id = session_id
            db_msg.role = role
            db_msg.content = content
            db_msg.created_at = datetime.utcnow()
            db_messages.append(db_msg)
        
        # Configure mock to return these messages
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = db_messages
        
        # Create memory instance - should load from database
        memory = PersistentConversationMemory(
            session_id=session_id,
            max_history=100,  # Large enough to hold all messages
            db_session=mock_db
        )
        
        # Verify messages were loaded
        loaded_messages = memory.get_all_messages()
        
        # Property: Number of loaded messages should match saved messages
        assert len(loaded_messages) == len(messages), \
            f"Expected {len(messages)} messages, got {len(loaded_messages)}"
        
        # Property: Content and order should be preserved
        for idx, (role, content) in enumerate(messages):
            loaded_msg = loaded_messages[idx]
            
            # Verify message type
            if role == "user":
                assert isinstance(loaded_msg, HumanMessage), \
                    f"Message {idx} should be HumanMessage, got {type(loaded_msg)}"
            else:
                assert isinstance(loaded_msg, AIMessage), \
                    f"Message {idx} should be AIMessage, got {type(loaded_msg)}"
            
            # Verify content
            assert loaded_msg.content == content, \
                f"Message {idx} content mismatch: expected '{content}', got '{loaded_msg.content}'"

    @pytest.mark.asyncio
    @given(
        session_id=session_id_strategy,
        user_messages=st.lists(message_content_strategy, min_size=1, max_size=10),
        ai_messages=st.lists(message_content_strategy, min_size=1, max_size=10)
    )
    @settings(max_examples=50, deadline=None)
    async def test_persistence_across_instances(self, session_id, user_messages, ai_messages):
        """
        Property: Messages persist across different memory instances.
        
        This test verifies that messages saved by one memory instance
        can be retrieved by another instance with the same session_id.
        """
        assume(len(session_id.strip()) > 0)
        assume(len(user_messages) > 0 and len(ai_messages) > 0)
        
        # Create mock database session
        mock_db = create_mock_db_session()
        
        # Track saved messages
        saved_messages = []
        
        def mock_add(msg):
            saved_messages.append(msg)
        
        def mock_query_all():
            return saved_messages
        
        mock_db.add.side_effect = mock_add
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.side_effect = lambda: list(saved_messages)
        
        # First instance - add messages
        memory1 = PersistentConversationMemory(
            session_id=session_id,
            max_history=100,
            db_session=mock_db
        )
        
        # Add alternating user and AI messages
        min_len = min(len(user_messages), len(ai_messages))
        for i in range(min_len):
            memory1.add_user_message(user_messages[i])
            memory1.add_ai_message(ai_messages[i])
        
        # Verify messages were saved
        assert mock_db.add.call_count >= min_len * 2, \
            "Messages should be saved to database"
        
        # Second instance - should load previous messages
        memory2 = PersistentConversationMemory(
            session_id=session_id,
            max_history=100,
            db_session=mock_db
        )
        
        # Property: Second instance should have the same messages
        loaded_messages = memory2.get_all_messages()
        assert len(loaded_messages) >= min_len * 2, \
            f"Expected at least {min_len * 2} messages, got {len(loaded_messages)}"


class TestMaxHistoryEnforcement:
    """
    Property 13: Max History Enforcement
    
    **Validates: Requirements 11.4**
    
    Tests that the retrieved messages never exceed the max_history limit.
    This verifies that the memory system correctly enforces the maximum
    history constraint to prevent unbounded memory growth.
    """

    @pytest.mark.asyncio
    @given(
        session_id=session_id_strategy,
        max_history=max_history_strategy,
        message_count=message_count_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_retrieved_messages_do_not_exceed_max_history(
        self,
        session_id,
        max_history,
        message_count
    ):
        """
        Property: Retrieved messages should never exceed max_history.
        
        This test verifies that regardless of how many messages are added,
        get_messages() never returns more than max_history messages.
        """
        assume(len(session_id.strip()) > 0)
        assume(max_history > 0)
        assume(message_count > 0)
        
        # Create memory without database (in-memory only for this test)
        memory = ConversationMemory(
            session_id=session_id,
            max_history=max_history
        )
        
        # Add messages (alternating user and AI)
        for i in range(message_count):
            if i % 2 == 0:
                memory.add_user_message(f"User message {i}")
            else:
                memory.add_ai_message(f"AI message {i}")
        
        # Get messages with limit applied
        retrieved_messages = memory.get_messages()
        
        # Property: Retrieved messages should not exceed max_history
        assert len(retrieved_messages) <= max_history, \
            f"Retrieved {len(retrieved_messages)} messages, but max_history is {max_history}"
        
        # Property: If we added more than max_history, we should get exactly max_history
        if message_count > max_history:
            assert len(retrieved_messages) == max_history, \
                f"Expected exactly {max_history} messages when {message_count} were added"
        else:
            # If we added fewer than max_history, we should get all of them
            assert len(retrieved_messages) == message_count, \
                f"Expected {message_count} messages when fewer than max_history were added"

    @pytest.mark.asyncio
    @given(
        session_id=session_id_strategy,
        max_history=st.integers(min_value=1, max_value=10),
        message_count=st.integers(min_value=20, max_value=50)
    )
    @settings(max_examples=50, deadline=None)
    async def test_most_recent_messages_are_kept(
        self,
        session_id,
        max_history,
        message_count
    ):
        """
        Property: When exceeding max_history, most recent messages are kept.
        
        This test verifies that when the message count exceeds max_history,
        the system keeps the most recent messages and discards older ones.
        """
        assume(len(session_id.strip()) > 0)
        assume(message_count > max_history)
        
        # Create memory without database
        memory = ConversationMemory(
            session_id=session_id,
            max_history=max_history
        )
        
        # Add numbered messages to track order
        for i in range(message_count):
            memory.add_user_message(f"Message {i}")
        
        # Get messages with limit applied
        retrieved_messages = memory.get_messages()
        
        # Property: Should have exactly max_history messages
        assert len(retrieved_messages) == max_history, \
            f"Expected {max_history} messages, got {len(retrieved_messages)}"
        
        # Property: Messages should be the most recent ones
        # The first message should be from index (message_count - max_history)
        expected_first_index = message_count - max_history
        first_message_content = retrieved_messages[0].content
        
        assert first_message_content == f"Message {expected_first_index}", \
            f"Expected first message to be 'Message {expected_first_index}', got '{first_message_content}'"
        
        # Property: Last message should be the most recent
        last_message_content = retrieved_messages[-1].content
        assert last_message_content == f"Message {message_count - 1}", \
            f"Expected last message to be 'Message {message_count - 1}', got '{last_message_content}'"

    @pytest.mark.asyncio
    @given(
        session_id=session_id_strategy,
        max_history=max_history_strategy,
        message_count=message_count_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_max_history_with_persistence(
        self,
        session_id,
        max_history,
        message_count
    ):
        """
        Property: Max history enforcement works with database persistence.
        
        This test verifies that max_history is enforced even when using
        persistent storage.
        """
        assume(len(session_id.strip()) > 0)
        assume(max_history > 0)
        assume(message_count > 0)
        
        # Create mock database session
        mock_db = create_mock_db_session()
        
        # Create memory with persistence
        memory = PersistentConversationMemory(
            session_id=session_id,
            max_history=max_history,
            db_session=mock_db
        )
        
        # Add messages
        for i in range(message_count):
            memory.add_user_message(f"Message {i}")
        
        # Get messages with limit applied
        retrieved_messages = memory.get_messages()
        
        # Property: Retrieved messages should not exceed max_history
        assert len(retrieved_messages) <= max_history, \
            f"Retrieved {len(retrieved_messages)} messages, but max_history is {max_history}"


class TestClearIntegrity:
    """
    Property 14: Clear Integrity
    
    **Validates: Requirements 11.5**
    
    Tests that after clearing a session, it should have no messages.
    This verifies that the clear operation completely removes all
    conversation history from both memory and database.
    """

    @pytest.mark.asyncio
    @given(
        session_id=session_id_strategy,
        messages=st.lists(message_content_strategy, min_size=1, max_size=20)
    )
    @settings(max_examples=50, deadline=None)
    async def test_cleared_session_has_no_messages(self, session_id, messages):
        """
        Property: Cleared session should have no messages in memory.
        
        This test verifies that after calling clear(), the memory
        contains no messages.
        """
        assume(len(session_id.strip()) > 0)
        assume(len(messages) > 0)
        
        # Create memory without database
        memory = ConversationMemory(
            session_id=session_id,
            max_history=100
        )
        
        # Add messages
        for msg in messages:
            memory.add_user_message(msg)
        
        # Verify messages were added
        assert len(memory.get_all_messages()) == len(messages), \
            "Messages should be added before clearing"
        
        # Clear the memory
        memory.clear()
        
        # Property: After clear, should have no messages
        assert len(memory.get_all_messages()) == 0, \
            "Memory should be empty after clear()"
        
        # Property: get_messages should also return empty
        assert len(memory.get_messages()) == 0, \
            "get_messages() should return empty list after clear()"

    @pytest.mark.asyncio
    @given(
        session_id=session_id_strategy,
        messages=st.lists(message_content_strategy, min_size=1, max_size=20)
    )
    @settings(max_examples=50, deadline=None)
    async def test_clear_removes_from_database(self, session_id, messages):
        """
        Property: Clear should remove messages from database.
        
        This test verifies that clear() removes messages from both
        memory and the database.
        """
        assume(len(session_id.strip()) > 0)
        assume(len(messages) > 0)
        
        # Create mock database session
        mock_db = create_mock_db_session()
        
        # Track delete calls
        delete_called = False
        
        def mock_delete():
            nonlocal delete_called
            delete_called = True
            return len(messages)
        
        mock_db.query.return_value.filter.return_value.delete.side_effect = mock_delete
        
        # Create memory with persistence
        memory = PersistentConversationMemory(
            session_id=session_id,
            max_history=100,
            db_session=mock_db
        )
        
        # Add messages
        for msg in messages:
            memory.add_user_message(msg)
        
        # Clear the memory
        memory.clear()
        
        # Property: Database delete should be called
        assert delete_called, \
            "Database delete should be called when clearing persistent memory"
        
        # Property: Memory should be empty
        assert len(memory.get_all_messages()) == 0, \
            "Memory should be empty after clear()"

    @pytest.mark.asyncio
    @given(
        session_id=session_id_strategy,
        initial_messages=st.lists(message_content_strategy, min_size=1, max_size=10),
        new_messages=st.lists(message_content_strategy, min_size=1, max_size=10)
    )
    @settings(max_examples=50, deadline=None)
    async def test_clear_allows_fresh_start(
        self,
        session_id,
        initial_messages,
        new_messages
    ):
        """
        Property: After clear, new messages can be added independently.
        
        This test verifies that after clearing, the memory can be used
        again with new messages, and the old messages don't interfere.
        """
        assume(len(session_id.strip()) > 0)
        assume(len(initial_messages) > 0)
        assume(len(new_messages) > 0)
        
        # Create memory without database
        memory = ConversationMemory(
            session_id=session_id,
            max_history=100
        )
        
        # Add initial messages
        for msg in initial_messages:
            memory.add_user_message(msg)
        
        # Verify initial messages
        assert len(memory.get_all_messages()) == len(initial_messages)
        
        # Clear the memory
        memory.clear()
        
        # Add new messages
        for msg in new_messages:
            memory.add_ai_message(msg)
        
        # Property: Should only have new messages
        all_messages = memory.get_all_messages()
        assert len(all_messages) == len(new_messages), \
            f"Expected {len(new_messages)} messages after clear and re-add, got {len(all_messages)}"
        
        # Property: All messages should be AI messages (the new ones)
        for msg in all_messages:
            assert isinstance(msg, AIMessage), \
                "All messages should be AIMessage after clearing and adding AI messages"
        
        # Property: Content should match new messages
        for idx, msg in enumerate(all_messages):
            assert msg.content == new_messages[idx], \
                f"Message {idx} content should match new messages"

    @pytest.mark.asyncio
    @given(
        session_id=session_id_strategy,
        message_count=st.integers(min_value=0, max_value=50)
    )
    @settings(max_examples=50, deadline=None)
    async def test_clear_is_idempotent(self, session_id, message_count):
        """
        Property: Calling clear multiple times is safe (idempotent).
        
        This test verifies that calling clear() multiple times doesn't
        cause errors and maintains the empty state.
        """
        assume(len(session_id.strip()) > 0)
        
        # Create memory without database
        memory = ConversationMemory(
            session_id=session_id,
            max_history=100
        )
        
        # Add messages (if any)
        for i in range(message_count):
            memory.add_user_message(f"Message {i}")
        
        # Clear multiple times
        memory.clear()
        memory.clear()
        memory.clear()
        
        # Property: Should still be empty
        assert len(memory.get_all_messages()) == 0, \
            "Memory should remain empty after multiple clear() calls"
        
        # Property: Should not raise any exceptions
        # (if we got here, no exceptions were raised)
