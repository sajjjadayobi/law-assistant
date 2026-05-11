"""Tests for share conversations (task 11.6).

Covers:
- on_shared_thread_view callback (authorises cross-user read access)
- create_step user_id lookup fix (threads need userIdentifier for is_thread_author)
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# on_shared_thread_view callback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shared_thread_is_viewable() -> None:
    from law_agent.ui.app import on_shared_thread_view

    thread = {"id": "t1", "metadata": {"is_shared": True}}
    assert await on_shared_thread_view(thread, None) is True


@pytest.mark.asyncio
async def test_unshared_thread_is_not_viewable() -> None:
    from law_agent.ui.app import on_shared_thread_view

    thread = {"id": "t1", "metadata": {"is_shared": False}}
    assert await on_shared_thread_view(thread, None) is False


@pytest.mark.asyncio
async def test_missing_metadata_returns_false() -> None:
    from law_agent.ui.app import on_shared_thread_view

    assert await on_shared_thread_view({"id": "t1", "metadata": None}, None) is False
    assert await on_shared_thread_view({"id": "t1"}, None) is False


@pytest.mark.asyncio
async def test_string_metadata_parsed_correctly() -> None:
    from law_agent.ui.app import on_shared_thread_view

    shared = json.dumps({"is_shared": True})
    assert await on_shared_thread_view({"id": "t1", "metadata": shared}, None) is True

    not_shared = json.dumps({"is_shared": False})
    assert await on_shared_thread_view({"id": "t1", "metadata": not_shared}, None) is False


@pytest.mark.asyncio
async def test_malformed_string_metadata_returns_false() -> None:
    from law_agent.ui.app import on_shared_thread_view

    assert await on_shared_thread_view({"id": "t1", "metadata": "not-json"}, None) is False


@pytest.mark.asyncio
async def test_viewer_arg_is_ignored() -> None:
    """The callback grants access based only on metadata, not who the viewer is."""
    import chainlit as cl

    from law_agent.ui.app import on_shared_thread_view

    thread = {"id": "t1", "metadata": {"is_shared": True}}
    viewer = cl.User(identifier="someuser")
    assert await on_shared_thread_view(thread, viewer) is True
    assert await on_shared_thread_view(thread, None) is True


# ---------------------------------------------------------------------------
# create_step — user_id lookup fix
# Threads must have userIdentifier set so that Chainlit's is_thread_author()
# can authorise the PUT /project/thread/share endpoint.
# The fix: when user.id is None (cl.User), fall back to get_user(identifier).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_step_resolves_user_id_via_get_user_when_id_is_none() -> None:
    """
    If the session user has no .id (plain cl.User, not PersistedUser),
    create_step must call get_user(identifier) to obtain the UUID.
    """
    from chainlit.user import PersistedUser

    from law_agent.data.data_layer import LawAgentDataLayer

    # Build a minimal layer double
    layer = MagicMock(spec=LawAgentDataLayer)
    layer.step_creation_lock = __import__("asyncio").Lock()

    # Simulated cl.User without an 'id' attribute
    mock_user = MagicMock()
    mock_user.identifier = "alice"
    type(mock_user).id = property(lambda self: None)  # id returns None

    persisted = PersistedUser(identifier="alice", id="uuid-alice", createdAt="2026-01-01")
    layer.get_thread = AsyncMock(return_value=None)
    layer.get_user = AsyncMock(return_value=persisted)
    layer.update_thread = AsyncMock()

    step_dict = {
        "threadId": "thread-1",
        "type": "user_message",
        "output": "Hello",
        "id": "step-1",
        "createdAt": "2026-01-01T00:00:00Z",
        "name": "User",
    }

    with patch("chainlit.user_session") as mock_session:
        mock_session.get = MagicMock(return_value=mock_user)

        # Bind the real create_step to our mock layer
        bound = LawAgentDataLayer.create_step.__get__(layer, LawAgentDataLayer)

        with patch(
            "chainlit.data.sql_alchemy.SQLAlchemyDataLayer.create_step",
            new=AsyncMock(),
        ):
            await bound(step_dict)

    layer.get_user.assert_awaited_once_with("alice")
    _, kwargs = layer.update_thread.call_args
    assert kwargs.get("user_id") == "uuid-alice"


@pytest.mark.asyncio
async def test_create_step_skips_get_user_when_id_already_present() -> None:
    """If user.id is already set (PersistedUser), skip the get_user lookup."""
    from chainlit.user import PersistedUser

    from law_agent.data.data_layer import LawAgentDataLayer

    layer = MagicMock(spec=LawAgentDataLayer)
    layer.step_creation_lock = __import__("asyncio").Lock()

    persisted_user = PersistedUser(identifier="bob", id="uuid-bob", createdAt="2026-01-01")
    layer.get_thread = AsyncMock(return_value=None)
    layer.get_user = AsyncMock()
    layer.update_thread = AsyncMock()

    step_dict = {
        "threadId": "thread-2",
        "type": "user_message",
        "output": "Hi",
        "id": "step-2",
        "createdAt": "2026-01-01T00:00:00Z",
        "name": "User",
    }

    with patch("chainlit.user_session") as mock_session:
        mock_session.get = MagicMock(return_value=persisted_user)

        bound = LawAgentDataLayer.create_step.__get__(layer, LawAgentDataLayer)

        with patch(
            "chainlit.data.sql_alchemy.SQLAlchemyDataLayer.create_step",
            new=AsyncMock(),
        ):
            await bound(step_dict)

    layer.get_user.assert_not_awaited()
    _, kwargs = layer.update_thread.call_args
    assert kwargs.get("user_id") == "uuid-bob"
