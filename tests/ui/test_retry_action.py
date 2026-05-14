"""Tests for Task 11.8: Retry Failed Messages.

Verifies that:
- An error in on_message creates a cl.Action with name="retry"
- The retry action carries the original message content in its payload
- Previous retry actions are cleared at the start of each new message
- The action callback removes the error message and re-calls main()
- The error message text mentions the retry button
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session(session_data: dict | None = None) -> MagicMock:
    """Return a mock cl.user_session that stores values in a dict."""
    data = dict(session_data or {})

    session = MagicMock()
    session.get = MagicMock(side_effect=lambda key, *args: data.get(key, args[0] if args else None))
    session.set = MagicMock(side_effect=lambda key, val: data.update({key: val}))
    return session, data


# ---------------------------------------------------------------------------
# Error handler creates retry action
# ---------------------------------------------------------------------------


class TestRetryActionCreated:
    @pytest.mark.asyncio
    async def test_action_name_is_retry(self) -> None:
        """Exception handler must create a cl.Action with name='retry'."""
        from law_assistant.ui.app import main

        mock_message = MagicMock()
        mock_message.content = "حقوق مستأجر چیست؟"

        created_actions: list = []

        def capture_action(**kwargs):
            action = MagicMock()
            action.remove = AsyncMock()
            for k, v in kwargs.items():
                setattr(action, k, v)
            created_actions.append(action)
            return action

        sent_messages: list = []

        async def fake_send(self_msg):
            sent_messages.append(self_msg)

        with (
            patch("law_assistant.ui.app.cl.user_session") as mock_session,
            patch("law_assistant.ui.app.cl.Action", side_effect=capture_action),
            patch("law_assistant.ui.app.cl.Message") as mock_cl_message,
            patch("law_assistant.ui.app.get_agent", side_effect=RuntimeError("agent failed")),
            patch("law_assistant.ui.app.get_settings"),
        ):

            mock_session.get = MagicMock(return_value=None)
            mock_session.set = MagicMock()

            msg_instance = MagicMock()
            msg_instance.send = AsyncMock()
            mock_cl_message.return_value = msg_instance

            await main(mock_message)

        assert any(
            a.name == "retry" for a in created_actions
        ), "No action with name='retry' was created"

    @pytest.mark.asyncio
    async def test_action_payload_contains_original_message(self) -> None:
        """The retry action payload must contain the original user message content."""
        from law_assistant.ui.app import main

        original_query = "مدت مرخصی زایمان چقدر است؟"
        mock_message = MagicMock()
        mock_message.content = original_query

        captured_payloads: list = []

        def capture_action(**kwargs):
            captured_payloads.append(kwargs.get("payload", {}))
            action = MagicMock()
            action.remove = AsyncMock()
            action.name = kwargs.get("name", "")
            return action

        with (
            patch("law_assistant.ui.app.cl.user_session") as mock_session,
            patch("law_assistant.ui.app.cl.Action", side_effect=capture_action),
            patch("law_assistant.ui.app.cl.Message") as mock_cl_message,
            patch("law_assistant.ui.app.get_agent", side_effect=RuntimeError("failed")),
            patch("law_assistant.ui.app.get_settings"),
        ):

            mock_session.get = MagicMock(return_value=None)
            mock_session.set = MagicMock()

            msg_instance = MagicMock()
            msg_instance.send = AsyncMock()
            mock_cl_message.return_value = msg_instance

            await main(mock_message)

        retry_payloads = [p for p in captured_payloads if p.get("message_content")]
        assert retry_payloads, "No payload with 'message_content' was found"
        assert retry_payloads[0]["message_content"] == original_query

    @pytest.mark.asyncio
    async def test_error_message_has_retry_action_attached(self) -> None:
        """The error cl.Message must be sent with the retry action in its actions list."""
        from law_assistant.ui.app import main

        mock_message = MagicMock()
        mock_message.content = "سوال حقوقی"

        retry_action = MagicMock()
        retry_action.name = "retry"
        retry_action.remove = AsyncMock()

        sent_with_actions: list = []

        def capture_message(content="", **kwargs):
            msg = MagicMock()
            msg.send = AsyncMock()
            if "actions" in kwargs:
                sent_with_actions.append(kwargs["actions"])
            return msg

        with (
            patch("law_assistant.ui.app.cl.user_session") as mock_session,
            patch("law_assistant.ui.app.cl.Action", return_value=retry_action),
            patch("law_assistant.ui.app.cl.Message", side_effect=capture_message),
            patch("law_assistant.ui.app.get_agent", side_effect=RuntimeError("fail")),
            patch("law_assistant.ui.app.get_settings"),
        ):

            mock_session.get = MagicMock(return_value=None)
            mock_session.set = MagicMock()

            await main(mock_message)

        assert sent_with_actions, "No message was sent with actions"
        assert retry_action in sent_with_actions[0]

    @pytest.mark.asyncio
    async def test_error_message_mentions_retry_button(self) -> None:
        """Error message content must explicitly mention the retry button."""
        from law_assistant.ui.app import main

        mock_message = MagicMock()
        mock_message.content = "سوال"

        sent_contents: list[str] = []

        def capture_message(content="", **kwargs):
            sent_contents.append(content)
            msg = MagicMock()
            msg.send = AsyncMock()
            return msg

        retry_action = MagicMock()
        retry_action.remove = AsyncMock()

        with (
            patch("law_assistant.ui.app.cl.user_session") as mock_session,
            patch("law_assistant.ui.app.cl.Action", return_value=retry_action),
            patch("law_assistant.ui.app.cl.Message", side_effect=capture_message),
            patch("law_assistant.ui.app.get_agent", side_effect=RuntimeError("fail")),
            patch("law_assistant.ui.app.get_settings"),
        ):

            mock_session.get = MagicMock(return_value=None)
            mock_session.set = MagicMock()

            await main(mock_message)

        error_contents = [c for c in sent_contents if "خطا" in c or "مجدد" in c]
        assert error_contents, "Error message not found in sent content"
        assert (
            "تلاش مجدد" in error_contents[0]
        ), f"Expected 'تلاش مجدد' in error message, got: {error_contents[0]!r}"


# ---------------------------------------------------------------------------
# Previous retry actions are cleaned up
# ---------------------------------------------------------------------------


class TestRetryActionsCleanup:
    @pytest.mark.asyncio
    async def test_previous_retry_actions_removed_on_new_message(self) -> None:
        """At start of on_message, all previous retry actions must have remove() called."""
        from law_assistant.ui.app import main

        old_action = MagicMock()
        old_action.remove = AsyncMock()

        mock_message = MagicMock()
        mock_message.content = "سوال جدید"

        response_text = "پاسخ"

        agent_mock = MagicMock()
        agent_mock.run = AsyncMock(return_value=(response_text, []))

        conv_manager_mock = MagicMock()
        conv_state_mock = MagicMock()
        conv_state_mock.message_history = []
        conv_manager_mock.get_or_create_conversation = MagicMock(return_value=conv_state_mock)

        citation_mock = MagicMock()
        citation_mock.format_response = MagicMock(return_value=response_text)

        step_manager_mock = MagicMock()

        with (
            patch("law_assistant.ui.app.cl.user_session") as mock_session,
            patch("law_assistant.ui.app.cl.Message") as mock_cl_message,
            patch("law_assistant.ui.app.get_agent", return_value=agent_mock),
            patch("law_assistant.ui.app.get_conversation_manager", return_value=conv_manager_mock),
            patch("law_assistant.ui.app.get_citation_formatter", return_value=citation_mock),
            patch("law_assistant.ui.app.get_step_manager", return_value=step_manager_mock),
            patch("law_assistant.ui.app.get_settings"),
            patch("law_assistant.ui.app.otel_trace"),
        ):

            session_data = {"retry_actions": [old_action]}
            mock_session.get = MagicMock(
                side_effect=lambda key, *args: session_data.get(key, args[0] if args else None)
            )
            mock_session.set = MagicMock(
                side_effect=lambda key, val: session_data.update({key: val})
            )

            msg_instance = MagicMock()
            msg_instance.send = AsyncMock()
            mock_cl_message.return_value = msg_instance

            await main(mock_message)

        old_action.remove.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retry_actions_stored_in_session_on_error(self) -> None:
        """After an error, retry_actions must be stored in cl.user_session."""
        from law_assistant.ui.app import main

        mock_message = MagicMock()
        mock_message.content = "سوال"

        set_calls: dict = {}

        retry_action = MagicMock()
        retry_action.remove = AsyncMock()

        def capture_set(key, val):
            set_calls[key] = val

        with (
            patch("law_assistant.ui.app.cl.user_session") as mock_session,
            patch("law_assistant.ui.app.cl.Action", return_value=retry_action),
            patch("law_assistant.ui.app.cl.Message") as mock_cl_message,
            patch("law_assistant.ui.app.get_agent", side_effect=RuntimeError("error")),
            patch("law_assistant.ui.app.get_settings"),
        ):

            mock_session.get = MagicMock(return_value=None)
            mock_session.set = MagicMock(side_effect=capture_set)

            msg_instance = MagicMock()
            msg_instance.send = AsyncMock()
            mock_cl_message.return_value = msg_instance

            await main(mock_message)

        assert "retry_actions" in set_calls
        stored_actions = set_calls["retry_actions"]
        assert isinstance(stored_actions, list)
        assert retry_action in stored_actions


# ---------------------------------------------------------------------------
# Retry action callback
# ---------------------------------------------------------------------------


class TestRetryActionCallback:
    @pytest.mark.asyncio
    async def test_callback_removes_error_message(self) -> None:
        """handle_retry must call cl.Message(id=action.forId).remove()."""
        from law_assistant.ui.app import handle_retry

        action = MagicMock()
        action.forId = "error-msg-123"
        action.payload = {"message_content": "سوال اصلی"}

        removed_ids: list[str] = []

        def capture_message(content="", **kwargs):
            msg = MagicMock()
            if "id" in kwargs:
                removed_ids.append(kwargs["id"])
            msg.remove = AsyncMock()
            return msg

        with (
            patch("law_assistant.ui.app.cl.Message", side_effect=capture_message),
            patch("law_assistant.ui.app.main", new_callable=AsyncMock),
        ):
            await handle_retry(action)

        assert (
            "error-msg-123" in removed_ids
        ), f"Error message ID not passed to cl.Message for removal. Got: {removed_ids}"

    @pytest.mark.asyncio
    async def test_callback_calls_main_with_original_content(self) -> None:
        """handle_retry must call main() with a message containing the original content."""
        from law_assistant.ui.app import handle_retry

        original_content = "حقوق مستأجر چیست؟"
        action = MagicMock()
        action.forId = "msg-id"
        action.payload = {"message_content": original_content}

        main_calls: list = []

        async def fake_main(message):
            main_calls.append(message)

        def capture_message(content="", **kwargs):
            msg = MagicMock()
            msg.remove = AsyncMock()
            msg.content = content
            return msg

        with (
            patch("law_assistant.ui.app.cl.Message", side_effect=capture_message),
            patch("law_assistant.ui.app.main", side_effect=fake_main),
        ):
            await handle_retry(action)

        assert main_calls, "main() was not called from handle_retry"
        assert main_calls[0].content == original_content
