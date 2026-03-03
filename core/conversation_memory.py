"""Conversation memory system for RagDocMan Agent.

This module implements a conversation memory system for storing and managing
conversation history with support for persistence and context retention.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, get_buffer_string

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Conversation memory system for managing chat history.
    
    This class provides a memory system for storing and retrieving conversation
    history with support for:
    - Storage of user and AI messages
    - Message retrieval with max_history limit
    - Message truncation for long conversations
    - Support for persistence (database integration)
    
    Attributes:
        session_id: Unique identifier for the conversation session
        max_history: Maximum number of messages to retain (default: 10)
        messages: List of conversation messages
        memory_key: Key used to store memory in the context (default: "history")
    """
    
    def __init__(
        self,
        session_id: str,
        max_history: int = 10,
        memory_key: str = "history",
        return_messages: bool = True,
        **kwargs
    ):
        """Initialize conversation memory.
        
        Args:
            session_id: Unique identifier for the conversation session
            max_history: Maximum number of messages to retain
            memory_key: Key used to store memory in the context
            return_messages: Whether to return messages as objects or strings
            **kwargs: Additional arguments for future extensions
        """
        self.session_id = session_id
        self.max_history = max_history
        self.messages: List[BaseMessage] = []
        self.memory_key = memory_key
        self.return_messages = return_messages
        logger.info(f"Initialized ConversationMemory for session {session_id} with max_history={max_history}")
    
    @property
    def memory_variables(self) -> List[str]:
        """Return memory variables.
        
        Returns:
            List of memory variable keys
        """
        return [self.memory_key]
    
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Load memory variables for the current context.
        
        This method retrieves conversation history for use in prompts and agent execution.
        
        Args:
            inputs: Input variables (not used in this implementation)
            
        Returns:
            Dictionary containing the conversation history
        """
        messages = self.get_messages()
        
        if self.return_messages:
            return {self.memory_key: messages}
        else:
            # Convert messages to string format
            return {self.memory_key: get_buffer_string(messages)}
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """Save context from this conversation turn.
        
        This method stores the user input and AI response from a conversation turn.
        
        Args:
            inputs: Dictionary containing user input (expects 'input' key)
            outputs: Dictionary containing AI output (expects 'output' key)
        """
        # Extract user input
        user_input = inputs.get("input", "")
        if user_input:
            self.add_user_message(user_input)
        
        # Extract AI output
        ai_output = outputs.get("output", "")
        if ai_output:
            self.add_ai_message(ai_output)
    
    def clear(self) -> None:
        """Clear all messages from memory.
        
        This method removes all conversation history for the current session.
        """
        logger.info(f"Clearing conversation history for session {self.session_id}")
        self.messages.clear()
    
    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation history.
        
        Args:
            content: The user's message content
        """
        message = HumanMessage(content=content)
        self.messages.append(message)
        logger.debug(f"Added user message to session {self.session_id}: {content[:50]}...")
        
        # Apply truncation if needed
        self._truncate_if_needed()
    
    def add_ai_message(self, content: str) -> None:
        """Add an AI message to the conversation history.
        
        Args:
            content: The AI's message content
        """
        message = AIMessage(content=content)
        self.messages.append(message)
        logger.debug(f"Added AI message to session {self.session_id}: {content[:50]}...")
        
        # Apply truncation if needed
        self._truncate_if_needed()
    
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the conversation history.
        
        Args:
            message: The message to add
        """
        self.messages.append(message)
        logger.debug(f"Added {message.__class__.__name__} to session {self.session_id}")
        
        # Apply truncation if needed
        self._truncate_if_needed()
    
    def get_messages(self) -> List[BaseMessage]:
        """Get the conversation messages with max_history limit applied.
        
        Returns the most recent messages up to max_history limit.
        
        Returns:
            List of messages (most recent max_history messages)
        """
        if len(self.messages) <= self.max_history:
            return self.messages
        
        # Return only the most recent max_history messages
        return self.messages[-self.max_history:]
    
    def get_all_messages(self) -> List[BaseMessage]:
        """Get all conversation messages without limit.
        
        Returns:
            List of all messages in the conversation
        """
        return self.messages
    
    def _truncate_if_needed(self) -> None:
        """Truncate messages if they exceed a reasonable buffer.
        
        This method keeps a buffer of messages beyond max_history to avoid
        frequent truncation, but prevents unlimited growth.
        """
        # Keep a buffer of 2x max_history to avoid frequent truncation
        buffer_size = self.max_history * 2
        
        if len(self.messages) > buffer_size:
            # Keep only the most recent buffer_size messages
            removed_count = len(self.messages) - buffer_size
            self.messages = self.messages[-buffer_size:]
            logger.info(
                f"Truncated {removed_count} old messages from session {self.session_id}. "
                f"Current message count: {len(self.messages)}"
            )
    
    def get_message_count(self) -> int:
        """Get the total number of messages in memory.
        
        Returns:
            Total number of messages
        """
        return len(self.messages)
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of the current conversation context.
        
        Returns:
            Dictionary containing context statistics
        """
        return {
            "session_id": self.session_id,
            "total_messages": len(self.messages),
            "visible_messages": len(self.get_messages()),
            "max_history": self.max_history,
            "user_messages": sum(1 for m in self.messages if isinstance(m, HumanMessage)),
            "ai_messages": sum(1 for m in self.messages if isinstance(m, AIMessage)),
        }
