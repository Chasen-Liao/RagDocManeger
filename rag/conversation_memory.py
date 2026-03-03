"""Conversation memory system for managing chat history."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from models.orm import ConversationHistory


class Message:
    """Simple message class."""
    
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content


class ConversationMemory:
    """Memory system for managing conversation history."""
    
    def __init__(
        self,
        session_id: str,
        max_history: int = 10,
        db_session: Optional[Session] = None
    ):
        """Initialize conversation memory.
        
        Args:
            session_id: Unique session identifier
            max_history: Maximum number of messages to keep in memory
            db_session: Database session for persistence
        """
        self.session_id = session_id
        self.max_history = max_history
        self.db_session = db_session
        self.messages: List[Message] = []
    
    def add_user_message(self, content: str) -> None:
        """Add user message to memory.
        
        Args:
            content: Message content
        """
        message = Message(role="user", content=content)
        self.messages.append(message)
        self._enforce_max_history()
    
    def add_ai_message(self, content: str) -> None:
        """Add AI message to memory.
        
        Args:
            content: Message content
        """
        message = Message(role="assistant", content=content)
        self.messages.append(message)
        self._enforce_max_history()
    
    def get_messages(self) -> List[Message]:
        """Get all messages in memory.
        
        Returns:
            List of messages
        """
        return self.messages[-self.max_history:]
    
    def _enforce_max_history(self) -> None:
        """Enforce maximum history limit."""
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]
    
    async def save_message(self, role: str, content: str) -> None:
        """Save message to database.
        
        Args:
            role: Message role (user or assistant)
            content: Message content
        """
        if self.db_session is None:
            return
        
        try:
            history = ConversationHistory(
                session_id=self.session_id,
                role=role,
                content=content,
                created_at=datetime.utcnow()
            )
            self.db_session.add(history)
            self.db_session.commit()
        except Exception as e:
            # Log error but don't fail
            print(f"Error saving message to database: {e}")
    
    async def load_history(self) -> List[Message]:
        """Load conversation history from database.
        
        Returns:
            List of messages from database
        """
        if self.db_session is None:
            return []
        
        try:
            histories = self.db_session.query(ConversationHistory).filter(
                ConversationHistory.session_id == self.session_id
            ).order_by(ConversationHistory.created_at).all()
            
            messages = []
            for history in histories[-self.max_history:]:
                messages.append(Message(role=history.role, content=history.content))
            
            return messages
        except Exception as e:
            # Log error but don't fail
            print(f"Error loading history from database: {e}")
            return []
    
    async def clear(self) -> None:
        """Clear conversation history.
        
        Clears both in-memory and database history.
        """
        self.messages.clear()
        
        if self.db_session is None:
            return
        
        try:
            self.db_session.query(ConversationHistory).filter(
                ConversationHistory.session_id == self.session_id
            ).delete()
            self.db_session.commit()
        except Exception as e:
            # Log error but don't fail
            print(f"Error clearing history from database: {e}")
