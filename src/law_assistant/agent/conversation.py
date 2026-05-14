"""Conversation management for the Law Agent.

This module implements conversation state tracking, message history management,
and turn limit enforcement.

Key Classes:
- ConversationState: Data class holding conversation metadata and messages
- ConversationManager: Manages multiple conversations with state tracking
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

import structlog
from pydantic_ai.messages import ModelMessage

logger = structlog.get_logger(__name__)


@dataclass
class ConversationState:
    """State of a single conversation.

    Attributes:
        conversation_id: Unique identifier for this conversation
        created_at: Timestamp when conversation was created
        updated_at: Timestamp of last message
        message_history: List of all messages in this conversation
        turn_count: Number of turns (user messages) so far
        user_persona: Detected user persona (inferred from first few messages)
    """

    conversation_id: str
    created_at: datetime
    updated_at: datetime
    message_history: list[ModelMessage] = field(default_factory=list)
    turn_count: int = 0
    user_persona: str | None = None  # 'layperson', 'business', 'legal_professional', or None

    def add_message(self, message: ModelMessage) -> None:
        """Add a message to conversation history.

        Args:
            message: Message to add
        """
        self.message_history.append(message)
        self.updated_at = datetime.utcnow()

        # Increment turn count on user messages
        if hasattr(message, "role") and message.role == "user":
            self.turn_count += 1

    def get_messages_summary(self) -> dict:
        """Get summary of conversation.

        Returns:
            Dictionary with conversation stats
        """
        return {
            "conversation_id": self.conversation_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "turn_count": self.turn_count,
            "message_count": len(self.message_history),
            "user_persona": self.user_persona,
            "duration_seconds": (self.updated_at - self.created_at).total_seconds(),
        }


class ConversationManager:
    """Manages multiple conversations with state tracking and enforcement.

    Key Responsibilities:
    1. Create and retrieve conversation state
    2. Add messages to conversation history
    3. Enforce turn limit (max 50 turns per conversation)
    4. Track conversation metadata

    Usage:
        manager = ConversationManager(max_turns=50)

        # Create new conversation
        state = manager.create_conversation()

        # Add messages (these are added by the agent)
        state.add_message(user_message)
        state.add_message(agent_response)

        # Check if conversation can continue
        if manager.can_continue(state.conversation_id):
            # Continue conversation
            pass
    """

    def __init__(self, max_turns: int = 50):
        """Initialize conversation manager.

        Args:
            max_turns: Maximum turns per conversation (default: 50)
        """
        self.max_turns = max_turns
        self._conversations: dict[str, ConversationState] = {}

        logger.info("conversation_manager_initialized", max_turns=max_turns)

    def create_conversation(self, conversation_id: str | None = None) -> ConversationState:
        """Create a new conversation.

        Args:
            conversation_id: Optional custom ID. If None, generates UUID.

        Returns:
            New ConversationState object

        Raises:
            ValueError: If conversation_id already exists
        """
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())

        if conversation_id in self._conversations:
            raise ValueError(f"Conversation {conversation_id} already exists")

        now = datetime.utcnow()
        state = ConversationState(
            conversation_id=conversation_id,
            created_at=now,
            updated_at=now,
        )

        self._conversations[conversation_id] = state

        logger.info("conversation_created", conversation_id=conversation_id)
        return state

    def get_conversation(self, conversation_id: str) -> ConversationState | None:
        """Retrieve existing conversation.

        Args:
            conversation_id: ID of conversation to retrieve

        Returns:
            ConversationState if found, None otherwise
        """
        return self._conversations.get(conversation_id)

    def get_or_create_conversation(self, conversation_id: str) -> ConversationState:
        """Get existing conversation or create new one.

        Args:
            conversation_id: ID of conversation

        Returns:
            Existing ConversationState or newly created one
        """
        state = self.get_conversation(conversation_id)
        if state is None:
            state = self.create_conversation(conversation_id)
        return state

    def can_continue(self, conversation_id: str) -> bool:
        """Check if conversation can continue (hasn't hit turn limit).

        Args:
            conversation_id: ID of conversation

        Returns:
            True if conversation can continue, False if turn limit reached

        Raises:
            ValueError: If conversation not found
        """
        state = self.get_conversation(conversation_id)
        if state is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        can_continue = state.turn_count < self.max_turns
        if not can_continue:
            logger.warning(
                "conversation_turn_limit_reached",
                conversation_id=conversation_id,
                turn_count=state.turn_count,
                max_turns=self.max_turns,
            )
        return can_continue

    def set_user_persona(self, conversation_id: str, persona: str) -> None:
        """Set detected user persona for a conversation.

        Args:
            conversation_id: ID of conversation
            persona: User persona ('layperson', 'business', 'legal_professional')

        Raises:
            ValueError: If conversation not found
        """
        state = self.get_conversation(conversation_id)
        if state is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        state.user_persona = persona
        logger.info(
            "user_persona_set",
            conversation_id=conversation_id,
            persona=persona,
        )

    def get_conversation_summary(self, conversation_id: str) -> dict:
        """Get summary statistics for a conversation.

        Args:
            conversation_id: ID of conversation

        Returns:
            Dictionary with conversation stats

        Raises:
            ValueError: If conversation not found
        """
        state = self.get_conversation(conversation_id)
        if state is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        return state.get_messages_summary()

    def list_conversations(self) -> list[dict]:
        """List all conversations with summary info.

        Returns:
            List of conversation summaries sorted by created_at (newest first)
        """
        summaries = [state.get_messages_summary() for state in self._conversations.values()]
        # Sort by created_at, newest first
        summaries.sort(
            key=lambda x: x["created_at"],
            reverse=True,
        )
        return summaries

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation.

        Args:
            conversation_id: ID of conversation to delete

        Returns:
            True if deleted, False if not found
        """
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            logger.info("conversation_deleted", conversation_id=conversation_id)
            return True
        return False

    def get_stats(self) -> dict:
        """Get overall statistics for the manager.

        Returns:
            Dictionary with stats across all conversations
        """
        total_turns = sum(state.turn_count for state in self._conversations.values())
        total_messages = sum(len(state.message_history) for state in self._conversations.values())

        return {
            "total_conversations": len(self._conversations),
            "total_turns": total_turns,
            "total_messages": total_messages,
            "average_turns_per_conversation": (
                total_turns / len(self._conversations) if self._conversations else 0
            ),
            "max_turns_per_conversation": self.max_turns,
        }
