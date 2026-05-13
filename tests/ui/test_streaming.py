"""Tests for Task 11.12: Response Streaming.

Verifies that:
- enable_streaming=True causes run_streaming() to be called and tokens streamed
- enable_streaming=False uses the existing run() (non-streaming) path
- Citations are formatted and the message updated after streaming completes
- run_streaming() in core.py calls on_delta for each token and returns full text
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session(session_data: dict | None = None):
    data = dict(session_data or {"id": "test-session-id"})
    session = MagicMock()
    session.get = MagicMock(side_effect=lambda key, *args: data.get(key, args[0] if args else None))
    session.set = MagicMock(side_effect=lambda key, val: data.update({key: val}))
    return session, data


def _make_settings(enable_streaming: bool = True):
    settings = MagicMock()
    settings.ui.enable_streaming = enable_streaming
    settings.ui.show_tool_calls = False
    return settings


# ---------------------------------------------------------------------------
# LawAgent.run_streaming()
# ---------------------------------------------------------------------------


class TestRunStreamingMethod:
    @pytest.mark.asyncio
    async def test_on_delta_called_per_token(self) -> None:
        """run_streaming() must call on_delta for every text token."""
        from law_agent.agent.core import LawAgent

        agent = MagicMock(spec=LawAgent)
        agent.agent = MagicMock()

        tokens = ["طبق", " ماده", " ۷۶"]
        stream_ctx = MagicMock()
        stream_ctx.__aenter__ = AsyncMock(return_value=stream_ctx)
        stream_ctx.__aexit__ = AsyncMock(return_value=False)

        async def _stream_text(delta=False, debounce_by=None):
            for t in tokens:
                yield t

        stream_ctx.stream_text = _stream_text
        stream_ctx.all_messages = MagicMock(return_value=[])
        agent.agent.run_stream = MagicMock(return_value=stream_ctx)

        received: list[str] = []

        async def on_delta(delta: str) -> None:
            received.append(delta)

        result_text, result_history = await LawAgent.run_streaming(
            agent,
            user_query="مرخصی زایمان؟",
            on_delta=on_delta,
        )

        assert received == tokens
        assert result_text == "".join(tokens)

    @pytest.mark.asyncio
    async def test_full_text_assembled_correctly(self) -> None:
        """run_streaming() must join all deltas into a single string."""
        from law_agent.agent.core import LawAgent

        agent = MagicMock(spec=LawAgent)
        agent.agent = MagicMock()
        tokens = ["سلام", "!", " خوش آمدید"]
        stream_ctx = MagicMock()
        stream_ctx.__aenter__ = AsyncMock(return_value=stream_ctx)
        stream_ctx.__aexit__ = AsyncMock(return_value=False)

        async def _stream_text(delta=False, debounce_by=None):
            for t in tokens:
                yield t

        stream_ctx.stream_text = _stream_text
        stream_ctx.all_messages = MagicMock(return_value=["msg1", "msg2"])
        agent.agent.run_stream = MagicMock(return_value=stream_ctx)

        text, history = await LawAgent.run_streaming(agent, user_query="سلام")

        assert text == "سلام! خوش آمدید"
        assert history == ["msg1", "msg2"]

    @pytest.mark.asyncio
    async def test_no_callback_does_not_raise(self) -> None:
        """run_streaming() with on_delta=None must not raise."""
        from law_agent.agent.core import LawAgent

        agent = MagicMock(spec=LawAgent)
        agent.agent = MagicMock()
        stream_ctx = MagicMock()
        stream_ctx.__aenter__ = AsyncMock(return_value=stream_ctx)
        stream_ctx.__aexit__ = AsyncMock(return_value=False)

        async def _stream_text(delta=False, debounce_by=None):
            yield "پاسخ"

        stream_ctx.stream_text = _stream_text
        stream_ctx.all_messages = MagicMock(return_value=[])
        agent.agent.run_stream = MagicMock(return_value=stream_ctx)

        text, _ = await LawAgent.run_streaming(agent, user_query="?", on_delta=None)
        assert text == "پاسخ"


# ---------------------------------------------------------------------------
# app.py streaming path
# ---------------------------------------------------------------------------


class TestStreamingPath:
    @pytest.mark.asyncio
    async def test_streaming_sends_empty_message_first(self) -> None:
        """When streaming, an empty cl.Message must be sent before tokens arrive."""
        from law_agent.ui.app import main

        mock_message = MagicMock()
        mock_message.content = "مرخصی زایمان چقدر است؟"

        sent_messages: list = []
        streamed_tokens: list = []

        streaming_msg_mock = MagicMock()
        streaming_msg_mock.send = AsyncMock(side_effect=lambda: sent_messages.append("initial"))
        streaming_msg_mock.stream_token = AsyncMock(side_effect=lambda t: streamed_tokens.append(t))
        streaming_msg_mock.update = AsyncMock()

        session, _ = _make_session({"id": "sess1"})

        with (
            patch("law_agent.ui.app.cl.user_session", session),
            patch(
                "law_agent.ui.app.get_settings", return_value=_make_settings(enable_streaming=True)
            ),
            patch("law_agent.ui.app.get_agent") as mock_get_agent,
            patch("law_agent.ui.app.get_conversation_manager") as mock_conv,
            patch("law_agent.ui.app.get_citation_formatter") as mock_fmt,
            patch("law_agent.ui.app.get_step_manager"),
            patch("law_agent.ui.app.cl.Message", return_value=streaming_msg_mock),
            patch("law_agent.ui.app.otel_trace") as mock_trace,
        ):
            mock_trace.get_tracer.return_value.start_as_current_span.return_value.__enter__ = (
                MagicMock(
                    return_value=MagicMock(
                        get_span_context=MagicMock(return_value=MagicMock(is_valid=False))
                    )
                )
            )
            mock_trace.get_tracer.return_value.start_as_current_span.return_value.__exit__ = (
                MagicMock(return_value=False)
            )

            agent_mock = MagicMock()
            agent_mock.run_streaming = AsyncMock(return_value=("پاسخ کامل [1]", []))
            mock_get_agent.return_value = agent_mock

            conv_state = MagicMock()
            conv_state.message_history = []
            mock_conv.return_value.get_or_create_conversation.return_value = conv_state

            fmt_mock = MagicMock()
            fmt_mock.format_response = MagicMock(return_value="پاسخ کامل [1](url)")
            mock_fmt.return_value = fmt_mock

            await main(mock_message)

        assert "initial" in sent_messages
        streaming_msg_mock.update.assert_called_once()
        assert streaming_msg_mock.content == "پاسخ کامل [1](url)"

    @pytest.mark.asyncio
    async def test_non_streaming_sends_complete_message(self) -> None:
        """When streaming is disabled, a single cl.Message with formatted content is sent."""
        from law_agent.ui.app import main

        mock_message = MagicMock()
        mock_message.content = "مرخصی زایمان چقدر است؟"

        sent_contents: list[str] = []

        def make_msg(content=""):
            m = MagicMock()
            m.send = AsyncMock(side_effect=lambda: sent_contents.append(content))
            return m

        session, _ = _make_session({"id": "sess2"})

        with (
            patch("law_agent.ui.app.cl.user_session", session),
            patch(
                "law_agent.ui.app.get_settings", return_value=_make_settings(enable_streaming=False)
            ),
            patch("law_agent.ui.app.get_agent") as mock_get_agent,
            patch("law_agent.ui.app.get_conversation_manager") as mock_conv,
            patch("law_agent.ui.app.get_citation_formatter") as mock_fmt,
            patch("law_agent.ui.app.get_step_manager"),
            patch("law_agent.ui.app.cl.Message", side_effect=make_msg),
            patch("law_agent.ui.app.otel_trace") as mock_trace,
        ):
            mock_trace.get_tracer.return_value.start_as_current_span.return_value.__enter__ = (
                MagicMock(
                    return_value=MagicMock(
                        get_span_context=MagicMock(return_value=MagicMock(is_valid=False))
                    )
                )
            )
            mock_trace.get_tracer.return_value.start_as_current_span.return_value.__exit__ = (
                MagicMock(return_value=False)
            )

            agent_mock = MagicMock()
            agent_mock.run = AsyncMock(return_value=("پاسخ خام", []))
            mock_get_agent.return_value = agent_mock

            conv_state = MagicMock()
            conv_state.message_history = []
            mock_conv.return_value.get_or_create_conversation.return_value = conv_state

            fmt_mock = MagicMock()
            fmt_mock.format_response = MagicMock(return_value="پاسخ فرمت‌شده")
            mock_fmt.return_value = fmt_mock

            await main(mock_message)

        assert "پاسخ فرمت‌شده" in sent_contents
        agent_mock.run.assert_called_once()
        agent_mock.run_streaming.assert_not_called()

    @pytest.mark.asyncio
    async def test_streaming_calls_run_streaming_not_run(self) -> None:
        """Streaming path must call run_streaming() not run()."""
        from law_agent.ui.app import main

        mock_message = MagicMock()
        mock_message.content = "سوال حقوقی"

        streaming_msg_mock = MagicMock()
        streaming_msg_mock.send = AsyncMock()
        streaming_msg_mock.stream_token = AsyncMock()
        streaming_msg_mock.update = AsyncMock()

        session, _ = _make_session({"id": "sess3"})

        with (
            patch("law_agent.ui.app.cl.user_session", session),
            patch(
                "law_agent.ui.app.get_settings", return_value=_make_settings(enable_streaming=True)
            ),
            patch("law_agent.ui.app.get_agent") as mock_get_agent,
            patch("law_agent.ui.app.get_conversation_manager") as mock_conv,
            patch("law_agent.ui.app.get_citation_formatter") as mock_fmt,
            patch("law_agent.ui.app.get_step_manager"),
            patch("law_agent.ui.app.cl.Message", return_value=streaming_msg_mock),
            patch("law_agent.ui.app.otel_trace") as mock_trace,
        ):
            mock_trace.get_tracer.return_value.start_as_current_span.return_value.__enter__ = (
                MagicMock(
                    return_value=MagicMock(
                        get_span_context=MagicMock(return_value=MagicMock(is_valid=False))
                    )
                )
            )
            mock_trace.get_tracer.return_value.start_as_current_span.return_value.__exit__ = (
                MagicMock(return_value=False)
            )

            agent_mock = MagicMock()
            agent_mock.run_streaming = AsyncMock(return_value=("text", []))
            agent_mock.run = AsyncMock(return_value=("text", []))
            mock_get_agent.return_value = agent_mock

            conv_state = MagicMock()
            conv_state.message_history = []
            mock_conv.return_value.get_or_create_conversation.return_value = conv_state

            fmt_mock = MagicMock()
            fmt_mock.format_response = MagicMock(return_value="text")
            mock_fmt.return_value = fmt_mock

            await main(mock_message)

        agent_mock.run_streaming.assert_called_once()
        agent_mock.run.assert_not_called()
