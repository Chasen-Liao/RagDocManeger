"""Persistent conversation memory system with database integration.

This module extends ConversationMemory to provide database persistence
for conversation history across application restarts.
"""
import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from .conversation_memory import ConversationMemory
from models.orm import ConversationHistory

logger = logging.getLogger(__name__)


class PersistentConversationMemory(ConversationMemory):
    """Persistent conversation memory with database storage.
    
    This class extends ConversationMemory to add database persistence,
    allowing conversation history to be saved and restored across sessions.
    
    Attributes:
        db_session: SQLAlchemy database session for persistence
        auto_save: Whether to automatically save messages to database
    """
    
    db_session: Optional[Session] = None
    auto_save: bool = True
    _loaded: bool = False
    retention_days: Optional[int] = None
    
    def __init__(
        self,
        session_id: str,
        max_history: int = 10,
        memory_key: str = "history",
        return_messages: bool = True,
        db_session: Optional[Session] = None,
        auto_save: bool = True,
        retention_days: Optional[int] = None,
        **kwargs
    ):
        """Initialize persistent conversation memory.
        
        Args:
            session_id: Unique identifier for the conversation session
            max_history: Maximum number of messages to retain
            memory_key: Key used to store memory in the context
            return_messages: Whether to return messages as objects or strings
            db_session: SQLAlchemy database session for persistence
            auto_save: Whether to automatically save messages to database
            retention_days: Number of days to retain conversation history (None = keep forever)
            **kwargs: Additional arguments passed to ConversationMemory
        """
        super().__init__(
            session_id=session_id,
            max_history=max_history,
            memory_key=memory_key,
            return_messages=return_messages,
            **kwargs
        )
        self.db_session = db_session
        self.auto_save = auto_save
        self.retention_days = retention_days
        self._loaded = False
        
        # Load history from database if available
        if self.db_session:
            try:
                # Clean up expired records if retention policy is set
                if self.retention_days is not None:
                    self._cleanup_expired_records()
                
                self._load_from_database()
            except Exception as e:
                logger.error(f"Failed to load history from database: {e}")
                # Continue with empty history (degradation strategy)
    
    def _load_from_database(self) -> None:
        """Load conversation history from database.
        
        Retrieves all messages for the current session from the database
        and populates the in-memory message list.
        """
        if not self.db_session or self._loaded:
            return
        
        try:
            # Query messages ordered by creation time
            db_messages = (
                self.db_session.query(ConversationHistory)
                .filter(ConversationHistory.session_id == self.session_id)
                .order_by(ConversationHistory.created_at.asc())
                .all()
            )
            
            # Convert database records to LangChain messages
            for db_msg in db_messages:
                if db_msg.role == "user":
                    message = HumanMessage(content=db_msg.content)
                elif db_msg.role == "assistant":
                    message = AIMessage(content=db_msg.content)
                else:
                    logger.warning(f"Unknown message role: {db_msg.role}")
                    continue
                
                self.messages.append(message)
            
            self._loaded = True
            logger.info(
                f"Loaded {len(db_messages)} messages from database for session {self.session_id}"
            )
        except Exception as e:
            logger.error(f"Error loading messages from database: {e}")
            raise
    
    def _save_message_to_database(self, message: BaseMessage) -> None:
        """Save a single message to the database.
        
        Args:
            message: The message to save
        """
        if not self.db_session or not self.auto_save:
            return
        
        try:
            # Determine role
            if isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage):
                role = "assistant"
            else:
                role = "unknown"
            
            # Create database record
            db_message = ConversationHistory(
                id=str(uuid.uuid4()),
                session_id=self.session_id,
                role=role,
                content=message.content,
                message_metadata=None,  # Can be extended to store message metadata
                created_at=datetime.utcnow()
            )
            
            self.db_session.add(db_message)
            self.db_session.commit()
            
            logger.debug(f"Saved {role} message to database for session {self.session_id}")
        except Exception as e:
            logger.error(f"Error saving message to database: {e}")
            self.db_session.rollback()
            # Don't raise - continue with in-memory storage (degradation strategy)
    
    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation history and save to database.
        
        Args:
            content: The user's message content
        """
        message = HumanMessage(content=content)
        self.messages.append(message)
        logger.debug(f"Added user message to session {self.session_id}: {content[:50]}...")
        
        # Save to database
        self._save_message_to_database(message)
        
        # Apply truncation if needed
        self._truncate_if_needed()
    
    def add_ai_message(self, content: str) -> None:
        """Add an AI message to the conversation history and save to database.
        
        Args:
            content: The AI's message content
        """
        message = AIMessage(content=content)
        self.messages.append(message)
        logger.debug(f"Added AI message to session {self.session_id}: {content[:50]}...")
        
        # Save to database
        self._save_message_to_database(message)
        
        # Apply truncation if needed
        self._truncate_if_needed()
    
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the conversation history and save to database.
        
        Args:
            message: The message to add
        """
        self.messages.append(message)
        logger.debug(f"Added {message.__class__.__name__} to session {self.session_id}")
        
        # Save to database
        self._save_message_to_database(message)
        
        # Apply truncation if needed
        self._truncate_if_needed()
    
    def clear(self) -> None:
        """Clear all messages from memory and database.
        
        This method removes all conversation history for the current session
        from both memory and the database.
        """
        logger.info(f"Clearing conversation history for session {self.session_id}")
        
        # Clear from database
        if self.db_session:
            try:
                self.db_session.query(ConversationHistory).filter(
                    ConversationHistory.session_id == self.session_id
                ).delete()
                self.db_session.commit()
                logger.info(f"Deleted database records for session {self.session_id}")
            except Exception as e:
                logger.error(f"Error deleting messages from database: {e}")
                self.db_session.rollback()
        
        # Clear from memory
        self.messages.clear()
    
    async def aclear(self) -> None:
        """Async version of clear method.
        
        This is provided for compatibility with async workflows.
        """
        self.clear()
    
    def reload_from_database(self) -> None:
        """Reload conversation history from database.
        
        This method clears the in-memory cache and reloads all messages
        from the database. Useful for syncing state after external changes.
        """
        if not self.db_session:
            logger.warning("Cannot reload: no database session available")
            return
        
        logger.info(f"Reloading conversation history for session {self.session_id}")
        self.messages.clear()
        self._loaded = False
        self._load_from_database()
    
    def _cleanup_expired_records(self) -> None:
        """Clean up expired conversation records based on retention policy.
        
        This method deletes conversation records older than the retention period
        for the current session. Called automatically during initialization if
        retention_days is configured.
        """
        if not self.db_session or self.retention_days is None:
            return
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
            
            deleted_count = (
                self.db_session.query(ConversationHistory)
                .filter(
                    ConversationHistory.session_id == self.session_id,
                    ConversationHistory.created_at < cutoff_date
                )
                .delete()
            )
            
            if deleted_count > 0:
                self.db_session.commit()
                logger.info(
                    f"Cleaned up {deleted_count} expired records for session {self.session_id} "
                    f"(older than {self.retention_days} days)"
                )
            
        except Exception as e:
            logger.error(f"Error cleaning up expired records: {e}")
            self.db_session.rollback()
            # Don't raise - continue with existing records (degradation strategy)
    
    @staticmethod
    def cleanup_all_expired_records(
        db_session: Session,
        retention_days: int
    ) -> int:
        """Clean up expired conversation records for all sessions.
        
        This is a utility method for batch cleanup of expired records across
        all sessions. Useful for scheduled maintenance tasks.
        
        Args:
            db_session: SQLAlchemy database session
            retention_days: Number of days to retain records
            
        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            deleted_count = (
                db_session.query(ConversationHistory)
                .filter(ConversationHistory.created_at < cutoff_date)
                .delete()
            )
            
            db_session.commit()
            
            if deleted_count > 0:
                logger.info(
                    f"Batch cleanup: Deleted {deleted_count} expired records "
                    f"(older than {retention_days} days)"
                )
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error in batch cleanup of expired records: {e}")
            db_session.rollback()
            raise
