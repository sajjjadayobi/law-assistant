"""Unit tests for conversation management.

Tests ConversationState and ConversationManager classes.
"""

from datetime import datetime

import pytest

from law_agent.agent.conversation import ConversationManager, ConversationState


class TestConversationState:
    """Tests for ConversationState dataclass."""

    def test_conversation_state_creation(self):
        """Test creating a new conversation state."""
        state = ConversationState(
            conversation_id="test-123",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert state.conversation_id == "test-123"
        assert state.message_history == []
        assert state.turn_count == 0
        assert state.user_persona is None

    def test_conversation_state_get_summary(self):
        """Test getting conversation summary."""
        now = datetime.utcnow()
        state = ConversationState(
            conversation_id="test-456",
            created_at=now,
            updated_at=now,
            turn_count=3,
        )

        summary = state.get_messages_summary()

        assert summary["conversation_id"] == "test-456"
        assert summary["turn_count"] == 3
        assert summary["message_count"] == 0
        assert summary["user_persona"] is None
        assert "duration_seconds" in summary


class TestConversationManager:
    """Tests for ConversationManager class."""

    def test_manager_initialization(self):
        """Test initializing conversation manager."""
        manager = ConversationManager(max_turns=50)

        assert manager.max_turns == 50
        assert len(manager._conversations) == 0

    def test_create_conversation(self):
        """Test creating a new conversation."""
        manager = ConversationManager()
        state = manager.create_conversation()

        assert state.conversation_id is not None
        assert state.turn_count == 0
        assert state.user_persona is None

    def test_create_conversation_with_custom_id(self):
        """Test creating conversation with custom ID."""
        manager = ConversationManager()
        state = manager.create_conversation(conversation_id="custom-id")

        assert state.conversation_id == "custom-id"

    def test_create_conversation_duplicate_id_raises_error(self):
        """Test that creating conversation with existing ID raises error."""
        manager = ConversationManager()
        manager.create_conversation(conversation_id="test-id")

        with pytest.raises(ValueError, match="already exists"):
            manager.create_conversation(conversation_id="test-id")

    def test_get_conversation(self):
        """Test retrieving a conversation."""
        manager = ConversationManager()
        created_state = manager.create_conversation(conversation_id="test-id")

        retrieved_state = manager.get_conversation("test-id")

        assert retrieved_state is created_state

    def test_get_conversation_not_found(self):
        """Test retrieving non-existent conversation returns None."""
        manager = ConversationManager()

        result = manager.get_conversation("non-existent")

        assert result is None

    def test_get_or_create_conversation_existing(self):
        """Test get_or_create returns existing conversation."""
        manager = ConversationManager()
        created = manager.create_conversation(conversation_id="test-id")

        retrieved = manager.get_or_create_conversation("test-id")

        assert retrieved is created

    def test_get_or_create_conversation_new(self):
        """Test get_or_create creates new conversation if not found."""
        manager = ConversationManager()

        state = manager.get_or_create_conversation("new-id")

        assert state.conversation_id == "new-id"
        assert manager.get_conversation("new-id") is state

    def test_can_continue(self):
        """Test checking if conversation can continue."""
        manager = ConversationManager(max_turns=50)
        state = manager.create_conversation()

        # Should be able to continue
        assert manager.can_continue(state.conversation_id) is True

        # Simulate reaching turn limit
        state.turn_count = 50
        assert manager.can_continue(state.conversation_id) is False

    def test_can_continue_nonexistent_raises_error(self):
        """Test can_continue with non-existent conversation raises error."""
        manager = ConversationManager()

        with pytest.raises(ValueError, match="not found"):
            manager.can_continue("non-existent")

    def test_set_user_persona(self):
        """Test setting user persona."""
        manager = ConversationManager()
        state = manager.create_conversation()

        manager.set_user_persona(state.conversation_id, "layperson")

        assert state.user_persona == "layperson"

    def test_set_user_persona_nonexistent_raises_error(self):
        """Test setting persona for non-existent conversation raises error."""
        manager = ConversationManager()

        with pytest.raises(ValueError, match="not found"):
            manager.set_user_persona("non-existent", "layperson")

    def test_get_conversation_summary(self):
        """Test getting conversation summary."""
        manager = ConversationManager()
        state = manager.create_conversation(conversation_id="test-id")
        state.turn_count = 5

        summary = manager.get_conversation_summary("test-id")

        assert summary["conversation_id"] == "test-id"
        assert summary["turn_count"] == 5

    def test_list_conversations(self):
        """Test listing all conversations."""
        manager = ConversationManager()

        manager.create_conversation(conversation_id="conv-1")
        manager.create_conversation(conversation_id="conv-2")

        conversations = manager.list_conversations()

        assert len(conversations) == 2
        ids = [c["conversation_id"] for c in conversations]
        assert "conv-1" in ids
        assert "conv-2" in ids

    def test_delete_conversation(self):
        """Test deleting a conversation."""
        manager = ConversationManager()
        manager.create_conversation(conversation_id="test-id")

        # Verify it exists
        assert manager.get_conversation("test-id") is not None

        # Delete it
        result = manager.delete_conversation("test-id")

        assert result is True
        assert manager.get_conversation("test-id") is None

    def test_delete_conversation_not_found(self):
        """Test deleting non-existent conversation returns False."""
        manager = ConversationManager()

        result = manager.delete_conversation("non-existent")

        assert result is False

    def test_get_stats(self):
        """Test getting overall statistics."""
        manager = ConversationManager(max_turns=50)

        conv1 = manager.create_conversation()
        conv1.turn_count = 3
        conv2 = manager.create_conversation()
        conv2.turn_count = 5

        stats = manager.get_stats()

        assert stats["total_conversations"] == 2
        assert stats["total_turns"] == 8
        assert stats["max_turns_per_conversation"] == 50
        assert stats["average_turns_per_conversation"] == 4.0

    def test_turn_limit_enforcement(self):
        """Test that turn limit is properly enforced."""
        manager = ConversationManager(max_turns=3)

        state = manager.create_conversation()

        # Should be able to continue at 0, 1, 2 turns
        for _ in range(3):
            assert manager.can_continue(state.conversation_id) is True
            state.turn_count += 1

        # Should not be able to continue at 3 turns
        assert manager.can_continue(state.conversation_id) is False
