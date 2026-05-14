"""Tests for the custom Chainlit data layer (Task 11.2).

Tests:
- LawAgentDataLayer initialization
- Thread auto-creation logic in create_step()
- Date-based sorting in get_all_user_threads()
- upsert_feedback() logging override
- Singleton factory functions
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from law_assistant.data.data_layer import LawAgentDataLayer, _parse_thread_date

# ---------------------------------------------------------------------------
# _parse_thread_date helper
# ---------------------------------------------------------------------------


class TestParseThreadDate:
    def test_iso_string_with_z(self) -> None:
        thread = {"createdAt": "2026-05-07T10:00:00.000000Z"}
        dt = _parse_thread_date(thread)
        assert dt.year == 2026
        assert dt.month == 5
        assert dt.day == 7

    def test_iso_string_without_z(self) -> None:
        thread = {"createdAt": "2026-05-07T10:00:00+00:00"}
        dt = _parse_thread_date(thread)
        assert dt.year == 2026

    def test_none_returns_min(self) -> None:
        thread = {"createdAt": None}
        assert _parse_thread_date(thread) == datetime.min

    def test_missing_key_returns_min(self) -> None:
        assert _parse_thread_date({}) == datetime.min

    def test_invalid_string_returns_min(self) -> None:
        thread = {"createdAt": "not-a-date"}
        assert _parse_thread_date(thread) == datetime.min


# ---------------------------------------------------------------------------
# LawAgentDataLayer — initialization
# ---------------------------------------------------------------------------


class TestDataLayerInit:
    def test_has_step_creation_lock(self) -> None:
        """Class-level lock must exist for thread safety."""
        assert hasattr(LawAgentDataLayer, "step_creation_lock")
        assert isinstance(LawAgentDataLayer.step_creation_lock, asyncio.Lock)

    def test_lock_is_class_level(self) -> None:
        """Two instances share the same lock."""
        # We can't easily instantiate without a DB, so check the class attribute
        lock1 = LawAgentDataLayer.step_creation_lock
        lock2 = LawAgentDataLayer.step_creation_lock
        assert lock1 is lock2


# ---------------------------------------------------------------------------
# Thread sorting in get_all_user_threads
# ---------------------------------------------------------------------------


class TestThreadSorting:
    """Test that get_all_user_threads sorts threads newest-first."""

    @pytest.mark.asyncio
    async def test_threads_sorted_newest_first(self) -> None:
        """Threads returned by parent should be sorted newest → oldest."""
        older = {"id": "t1", "createdAt": "2026-05-01T10:00:00Z", "steps": [], "elements": []}
        newer = {"id": "t2", "createdAt": "2026-05-07T10:00:00Z", "steps": [], "elements": []}
        middle = {"id": "t3", "createdAt": "2026-05-04T10:00:00Z", "steps": [], "elements": []}

        # Mock the parent's get_all_user_threads to return unsorted list
        with patch.object(LawAgentDataLayer, "__init__", lambda self, **kwargs: None):
            layer = object.__new__(LawAgentDataLayer)
            with patch(
                "law_assistant.data.data_layer.SQLAlchemyDataLayer.get_all_user_threads",
                new=AsyncMock(return_value=[older, middle, newer]),
            ):
                result = await layer.get_all_user_threads(user_id="test-user")

        assert result[0]["id"] == "t2"  # newest first
        assert result[1]["id"] == "t3"
        assert result[2]["id"] == "t1"  # oldest last

    @pytest.mark.asyncio
    async def test_returns_none_when_parent_returns_none(self) -> None:
        with patch.object(LawAgentDataLayer, "__init__", lambda self, **kwargs: None):
            layer = object.__new__(LawAgentDataLayer)
            with patch(
                "law_assistant.data.data_layer.SQLAlchemyDataLayer.get_all_user_threads",
                new=AsyncMock(return_value=None),
            ):
                result = await layer.get_all_user_threads(user_id="user")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_parent_returns_empty(self) -> None:
        with patch.object(LawAgentDataLayer, "__init__", lambda self, **kwargs: None):
            layer = object.__new__(LawAgentDataLayer)
            with patch(
                "law_assistant.data.data_layer.SQLAlchemyDataLayer.get_all_user_threads",
                new=AsyncMock(return_value=[]),
            ):
                result = await layer.get_all_user_threads(user_id="user")
        assert result == []


# ---------------------------------------------------------------------------
# create_step — thread auto-creation logic
# ---------------------------------------------------------------------------


class TestCreateStepLogic:
    """Test the thread auto-creation guard in create_step()."""

    def _make_layer(self) -> LawAgentDataLayer:
        """Create a layer instance without connecting to a real DB."""
        with patch.object(LawAgentDataLayer, "__init__", lambda self, **kwargs: None):
            layer = object.__new__(LawAgentDataLayer)
        return layer

    @pytest.mark.asyncio
    async def test_skips_non_user_message_when_no_thread(self) -> None:
        """Non-user steps before thread creation should be silently skipped."""
        layer = self._make_layer()
        step_dict = {"id": "s1", "type": "run", "threadId": "t1", "output": ""}

        with patch.object(layer, "get_thread", new=AsyncMock(return_value=None)):
            # Should return without calling super().create_step()
            result = await layer.create_step(step_dict)
        assert result is None

    @pytest.mark.asyncio
    async def test_creates_thread_on_first_user_message(self) -> None:
        """First user_message should trigger update_thread()."""
        layer = self._make_layer()
        step_dict = {
            "id": "s1",
            "type": "user_message",
            "threadId": "t1",
            "output": "مرخصی زایمان چقدر است؟",
        }

        mock_update = AsyncMock()
        mock_super_create = AsyncMock()

        with (
            patch.object(layer, "get_thread", new=AsyncMock(return_value=None)),
            patch.object(layer, "update_thread", mock_update),
            patch("law_assistant.data.data_layer.SQLAlchemyDataLayer.create_step", mock_super_create),
            patch("chainlit.user_session", MagicMock(get=MagicMock(return_value=None))),
        ):
            await layer.create_step(step_dict)

        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args
        assert call_kwargs[0][0] == "t1"  # thread_id
        assert "مرخصی زایمان" in call_kwargs[1].get("name", "")

    @pytest.mark.asyncio
    async def test_calls_super_when_thread_exists(self) -> None:
        """When thread already exists, should call super().create_step()."""
        layer = self._make_layer()
        step_dict = {
            "id": "s2",
            "type": "assistant_message",
            "threadId": "t1",
            "output": "پاسخ",
        }
        existing_thread = {"id": "t1", "steps": [], "elements": []}

        mock_super_create = AsyncMock()

        with (
            patch.object(layer, "get_thread", new=AsyncMock(return_value=existing_thread)),
            patch("law_assistant.data.data_layer.SQLAlchemyDataLayer.create_step", mock_super_create),
        ):
            await layer.create_step(step_dict)

        mock_super_create.assert_called_once_with(step_dict)


# ---------------------------------------------------------------------------
# upsert_feedback — logging and delegation
# ---------------------------------------------------------------------------


class TestUpsertFeedback:
    def _make_layer(self) -> LawAgentDataLayer:
        with patch.object(LawAgentDataLayer, "__init__", lambda self, **kwargs: None):
            return object.__new__(LawAgentDataLayer)

    @pytest.mark.asyncio
    async def test_calls_super_upsert(self) -> None:
        """upsert_feedback must delegate to parent class."""
        layer = self._make_layer()
        feedback = MagicMock()
        feedback.value = 1
        feedback.forId = "step-1"
        feedback.comment = None
        feedback.threadId = "thread-1"

        mock_super = AsyncMock(return_value="feedback-id-123")
        with patch("law_assistant.data.data_layer.SQLAlchemyDataLayer.upsert_feedback", mock_super):
            result = await layer.upsert_feedback(feedback)

        mock_super.assert_called_once_with(feedback)
        assert result == "feedback-id-123"

    @pytest.mark.asyncio
    async def test_positive_feedback_logs_correctly(self) -> None:
        """Value=1 should log 👍 مفید label."""
        layer = self._make_layer()
        feedback = MagicMock()
        feedback.value = 1
        feedback.forId = "s1"
        feedback.comment = "عالی بود"
        feedback.threadId = "t1"

        with (
            patch(
                "law_assistant.data.data_layer.SQLAlchemyDataLayer.upsert_feedback",
                AsyncMock(return_value="id"),
            ),
            patch("law_assistant.data.data_layer.logger") as mock_log,
        ):
            await layer.upsert_feedback(feedback)

        logged_kwargs = mock_log.info.call_args[1]
        assert logged_kwargs["label"] == "👍 مفید"
        assert logged_kwargs["value"] == 1

    @pytest.mark.asyncio
    async def test_negative_feedback_logs_correctly(self) -> None:
        """Value=0 should log 👎 نامفید label."""
        layer = self._make_layer()
        feedback = MagicMock()
        feedback.value = 0
        feedback.forId = "s1"
        feedback.comment = "پاسخ نادرست"
        feedback.threadId = "t1"

        with (
            patch(
                "law_assistant.data.data_layer.SQLAlchemyDataLayer.upsert_feedback",
                AsyncMock(return_value="id"),
            ),
            patch("law_assistant.data.data_layer.logger") as mock_log,
        ):
            await layer.upsert_feedback(feedback)

        logged_kwargs = mock_log.info.call_args[1]
        assert logged_kwargs["label"] == "👎 نامفید"


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------


class TestDataLayerFactory:
    def test_get_data_layer_raises_if_not_initialized(self) -> None:
        """get_data_layer() raises RuntimeError when module failed to init."""
        import law_assistant.data.data_layer as dl_module

        original = dl_module._data_layer
        try:
            dl_module._data_layer = None
            with pytest.raises(RuntimeError, match="not initialized"):
                from law_assistant.data.data_layer import get_data_layer

                get_data_layer()
        finally:
            dl_module._data_layer = original

    def test_reset_data_layer_sets_to_none(self) -> None:
        import law_assistant.data.data_layer as dl_module

        original = dl_module._data_layer
        try:
            from law_assistant.data.data_layer import reset_data_layer

            reset_data_layer()
            assert dl_module._data_layer is None
        finally:
            dl_module._data_layer = original
