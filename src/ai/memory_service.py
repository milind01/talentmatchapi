"""Conversation Memory Service - Maintains conversation history for context."""
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Single message in conversation."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class ConversationMemory:
    """Maintains conversation history per user with context retrieval."""
    
    def __init__(self, user_id: int, max_messages: int = 50):
        """Initialize conversation memory.
        
        Args:
            user_id: User ID
            max_messages: Maximum messages to store (FIFO when exceeded)
        """
        self.user_id = user_id
        self.max_messages = max_messages
        self.messages: List[Message] = []
        self.created_at = datetime.utcnow()
    
    async def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add message to conversation.
        
        Args:
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional metadata (tool calls, scores, etc.)
        """
        if role not in ["user", "assistant", "system"]:
            logger.warning(f"Unknown role: {role}, using 'assistant'")
            role = "assistant"
        
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        
        self.messages.append(message)
        
        # FIFO overflow handling
        if len(self.messages) > self.max_messages:
            removed = self.messages.pop(0)
            logger.info(f"Memory overflow for user {self.user_id}, removed oldest message")
        
        logger.debug(f"Added {role} message for user {self.user_id}")
    
    async def get_context(
        self,
        limit: Optional[int] = None,
        include_metadata: bool = False,
    ) -> str:
        """Get formatted conversation context.
        
        Args:
            limit: Number of recent messages to include (None = all)
            include_metadata: Whether to include metadata
            
        Returns:
            Formatted conversation context
        """
        if not self.messages:
            return ""
        
        messages_to_include = self.messages[-limit:] if limit else self.messages
        
        context_parts = []
        for msg in messages_to_include:
            role_str = msg.role.upper()
            context_parts.append(f"{role_str}: {msg.content}")
            
            if include_metadata and msg.metadata:
                metadata_str = json.dumps(msg.metadata, indent=2)
                context_parts.append(f"  [Metadata: {metadata_str}]")
        
        return "\n".join(context_parts)
    
    async def get_context_with_summaries(
        self,
        limit: Optional[int] = 10,
        summary_window: int = 3,
    ) -> str:
        """Get context with automatic summarization of older messages.
        
        Args:
            limit: Number of recent messages to show in detail
            summary_window: Number of old messages to summarize together
            
        Returns:
            Formatted context with summaries
        """
        if not self.messages:
            return ""
        
        context_parts = []
        
        # Include all messages if less than limit
        if len(self.messages) <= limit:
            return await self.get_context(limit=limit)
        
        # Add summary of old messages
        old_messages = self.messages[:-limit]
        if old_messages:
            context_parts.append(
                f"[Previous conversation: {len(old_messages)} messages summarized]\n"
                f"Topics: {self._extract_topics(old_messages)}\n"
            )
        
        # Add recent messages in detail
        recent_messages = self.messages[-limit:]
        for msg in recent_messages:
            context_parts.append(f"{msg.role.upper()}: {msg.content}")
        
        return "\n".join(context_parts)
    
    def _extract_topics(self, messages: List[Message]) -> str:
        """Extract key topics from messages (basic).
        
        Args:
            messages: List of messages
            
        Returns:
            Comma-separated topics
        """
        # Simple extraction: take first N words of each message
        topics = []
        for msg in messages[:5]:  # Sample first 5
            words = msg.content.split()[:3]
            topics.extend(words)
        
        # Deduplicate and limit
        unique_topics = list(set(topics))[:10]
        return ", ".join(unique_topics)
    
    async def get_last_user_query(self) -> Optional[str]:
        """Get the last user message.
        
        Returns:
            Last user message or None
        """
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg.content
        return None
    
    async def get_last_assistant_response(self) -> Optional[str]:
        """Get the last assistant message.
        
        Returns:
            Last assistant message or None
        """
        for msg in reversed(self.messages):
            if msg.role == "assistant":
                return msg.content
        return None
    
    async def search_messages(self, keyword: str) -> List[Message]:
        """Search messages by keyword.
        
        Args:
            keyword: Search keyword (case-insensitive)
            
        Returns:
            List of matching messages
        """
        keyword_lower = keyword.lower()
        return [
            msg for msg in self.messages
            if keyword_lower in msg.content.lower()
        ]
    
    async def clear(self) -> None:
        """Clear all messages."""
        self.messages.clear()
        logger.info(f"Cleared memory for user {self.user_id}")
    
    async def get_summary(self) -> Dict[str, Any]:
        """Get memory summary.
        
        Returns:
            Summary statistics
        """
        user_msgs = len([m for m in self.messages if m.role == "user"])
        assistant_msgs = len([m for m in self.messages if m.role == "assistant"])
        
        return {
            "user_id": self.user_id,
            "total_messages": len(self.messages),
            "user_messages": user_msgs,
            "assistant_messages": assistant_msgs,
            "created_at": self.created_at.isoformat(),
            "last_message_at": self.messages[-1].timestamp.isoformat() if self.messages else None,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "user_id": self.user_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "summary": {
                "total": len(self.messages),
                "created_at": self.created_at.isoformat(),
            }
        }


class MemoryStore:
    """Manages multiple conversation memories (one per user)."""
    
    def __init__(self, max_users: int = 100, max_messages_per_user: int = 50):
        """Initialize memory store.
        
        Args:
            max_users: Maximum users to store memories for
            max_messages_per_user: Max messages per conversation
        """
        self.max_users = max_users
        self.max_messages_per_user = max_messages_per_user
        self.memories: Dict[int, ConversationMemory] = {}
    
    async def get_or_create_memory(self, user_id: int) -> ConversationMemory:
        """Get existing or create new conversation memory.
        
        Args:
            user_id: User ID
            
        Returns:
            ConversationMemory instance
        """
        if user_id not in self.memories:
            if len(self.memories) >= self.max_users:
                # Remove oldest memory (FIFO)
                oldest_uid = next(iter(self.memories))
                del self.memories[oldest_uid]
                logger.info(f"Memory store overflow, removed user {oldest_uid}")
            
            self.memories[user_id] = ConversationMemory(
                user_id=user_id,
                max_messages=self.max_messages_per_user,
            )
            logger.info(f"Created new memory for user {user_id}")
        
        return self.memories[user_id]
    
    async def clear_memory(self, user_id: int) -> None:
        """Clear specific user's memory.
        
        Args:
            user_id: User ID
        """
        if user_id in self.memories:
            await self.memories[user_id].clear()
            del self.memories[user_id]
            logger.info(f"Cleared memory for user {user_id}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory store statistics.
        
        Returns:
            Statistics dictionary
        """
        total_messages = sum(len(m.messages) for m in self.memories.values())
        
        return {
            "users_with_memory": len(self.memories),
            "total_messages": total_messages,
            "avg_messages_per_user": total_messages / len(self.memories) if self.memories else 0,
            "capacity": {
                "max_users": self.max_users,
                "max_messages_per_user": self.max_messages_per_user,
            }
        }


# Global memory store instance
_memory_store: Optional[MemoryStore] = None


def get_memory_store(
    max_users: int = 100,
    max_messages_per_user: int = 50,
) -> MemoryStore:
    """Get or create global memory store.
    
    Args:
        max_users: Maximum users to store
        max_messages_per_user: Max messages per conversation
        
    Returns:
        MemoryStore instance
    """
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore(
            max_users=max_users,
            max_messages_per_user=max_messages_per_user,
        )
        logger.info(f"Initialized MemoryStore with capacity: {max_users} users")
    return _memory_store
