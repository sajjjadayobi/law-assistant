"""Tests for Phoenix feedback client (Task 11.5).

Tests:
- PhoenixFeedbackClient sends correct payload to /v1/span_annotations
- Correct label/score mapping (thumbs_up=1.0, thumbs_down=0.0)
- Graceful handling when Phoenix is unavailable
- initialize_feedback_client / get_feedback_client singleton
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from law_assistant.observability.feedback import (
    PhoenixFeedbackClient,
    get_feedback_client,
    initialize_feedback_client,
)
import law_assistant.observability.feedback as feedback_module

# ---------------------------------------------------------------------------
# PhoenixFeedbackClient — payload correctness
# ---------------------------------------------------------------------------


class TestPhoenixFeedbackPayload:
    @pytest.mark.asyncio
    async def test_positive_feedback_sends_thumbs_up(self) -> None:
        client = PhoenixFeedbackClient("http://localhost:6006")
        captured = {}

        async def mock_post(url, json=None, **kwargs):
            captured["url"] = url
            captured["json"] = json
            resp = MagicMock()
            resp.status_code = 200
            return resp

        client._http = MagicMock()
        client._http.post = mock_post

        result = await client.send_feedback(
            span_id="abc123def456abcd",
            feedback_type="positive",
            comment="پاسخ خوبی بود",
        )

        assert result is True
        assert captured["url"] == "http://localhost:6006/v1/span_annotations"
        payload = captured["json"]
        assert len(payload["data"]) == 1
        annotation = payload["data"][0]
        assert annotation["span_id"] == "abc123def456abcd"
        assert annotation["name"] == "user_feedback"
        assert annotation["annotator_kind"] == "HUMAN"
        assert annotation["result"]["label"] == "thumbs_up"
        assert annotation["result"]["score"] == 1.0
        assert annotation["result"]["explanation"] == "پاسخ خوبی بود"

    @pytest.mark.asyncio
    async def test_negative_feedback_sends_thumbs_down(self) -> None:
        client = PhoenixFeedbackClient("http://localhost:6006")
        captured = {}

        async def mock_post(url, json=None, **kwargs):
            captured["json"] = json
            resp = MagicMock()
            resp.status_code = 200
            return resp

        client._http = MagicMock()
        client._http.post = mock_post

        await client.send_feedback(
            span_id="span123",
            feedback_type="negative",
            comment="پاسخ نادرست بود",
        )

        annotation = captured["json"]["data"][0]
        assert annotation["result"]["label"] == "thumbs_down"
        assert annotation["result"]["score"] == 0.0
        assert annotation["result"]["explanation"] == "پاسخ نادرست بود"

    @pytest.mark.asyncio
    async def test_none_comment_sends_empty_string(self) -> None:
        client = PhoenixFeedbackClient("http://localhost:6006")
        captured = {}

        async def mock_post(url, json=None, **kwargs):
            captured["json"] = json
            resp = MagicMock()
            resp.status_code = 200
            return resp

        client._http = MagicMock()
        client._http.post = mock_post

        await client.send_feedback(span_id="s1", feedback_type="positive", comment=None)

        assert captured["json"]["data"][0]["result"]["explanation"] == ""

    @pytest.mark.asyncio
    async def test_endpoint_strips_trailing_slash(self) -> None:
        """Endpoint should not double-slash."""
        client = PhoenixFeedbackClient("http://localhost:6006/")
        captured = {}

        async def mock_post(url, json=None, **kwargs):
            captured["url"] = url
            resp = MagicMock()
            resp.status_code = 200
            return resp

        client._http = MagicMock()
        client._http.post = mock_post

        await client.send_feedback(span_id="s1", feedback_type="positive")

        assert captured["url"] == "http://localhost:6006/v1/span_annotations"
        assert "//" not in captured["url"].replace("http://", "")


# ---------------------------------------------------------------------------
# PhoenixFeedbackClient — error handling
# ---------------------------------------------------------------------------


class TestPhoenixFeedbackErrors:
    @pytest.mark.asyncio
    async def test_returns_false_on_non_200(self) -> None:
        client = PhoenixFeedbackClient("http://localhost:6006")

        async def mock_post(url, json=None, **kwargs):
            resp = MagicMock()
            resp.status_code = 404
            resp.text = "Not found"
            return resp

        client._http = MagicMock()
        client._http.post = mock_post

        result = await client.send_feedback(span_id="s1", feedback_type="positive")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_connection_error(self) -> None:
        client = PhoenixFeedbackClient("http://localhost:9999")

        async def mock_post(*args, **kwargs):
            raise httpx.ConnectError("Connection refused")

        client._http = MagicMock()
        client._http.post = mock_post

        result = await client.send_feedback(span_id="s1", feedback_type="positive")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout(self) -> None:
        client = PhoenixFeedbackClient("http://localhost:6006")

        async def mock_post(*args, **kwargs):
            raise httpx.TimeoutException("Timeout")

        client._http = MagicMock()
        client._http.post = mock_post

        result = await client.send_feedback(span_id="s1", feedback_type="positive")
        assert result is False

    @pytest.mark.asyncio
    async def test_201_accepted_as_success(self) -> None:
        client = PhoenixFeedbackClient("http://localhost:6006")

        async def mock_post(url, json=None, **kwargs):
            resp = MagicMock()
            resp.status_code = 201
            return resp

        client._http = MagicMock()
        client._http.post = mock_post

        result = await client.send_feedback(span_id="s1", feedback_type="negative")
        assert result is True


# ---------------------------------------------------------------------------
# Singleton: initialize / get
# ---------------------------------------------------------------------------


class TestFeedbackClientSingleton:
    def setup_method(self) -> None:
        # Reset singleton before each test
        feedback_module._feedback_client = None

    def teardown_method(self) -> None:
        feedback_module._feedback_client = None

    def test_get_returns_none_before_init(self) -> None:
        assert get_feedback_client() is None

    def test_initialize_creates_client(self) -> None:
        initialize_feedback_client("http://localhost:6006")
        client = get_feedback_client()
        assert client is not None
        assert isinstance(client, PhoenixFeedbackClient)

    def test_initialize_sets_correct_endpoint(self) -> None:
        initialize_feedback_client("http://phoenix.example.com:6006")
        client = get_feedback_client()
        assert client.endpoint == "http://phoenix.example.com:6006"

    def test_initialize_idempotent(self) -> None:
        initialize_feedback_client("http://host-a:6006")
        initialize_feedback_client("http://host-b:6006")
        # Second call overwrites first
        assert get_feedback_client().endpoint == "http://host-b:6006"

    @pytest.mark.asyncio
    async def test_send_feedback_to_phoenix_returns_false_when_no_client(self) -> None:
        from law_assistant.observability.feedback import send_feedback_to_phoenix

        result = await send_feedback_to_phoenix("span-1", "positive")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_feedback_to_phoenix_delegates_to_client(self) -> None:
        initialize_feedback_client("http://localhost:6006")
        client = get_feedback_client()

        with patch.object(client, "send_feedback", new=AsyncMock(return_value=True)) as mock_send:
            from law_assistant.observability.feedback import send_feedback_to_phoenix

            result = await send_feedback_to_phoenix("span-1", "positive", comment="good")

        assert result is True
        mock_send.assert_called_once_with(
            span_id="span-1",
            feedback_type="positive",
            comment="good",
        )
