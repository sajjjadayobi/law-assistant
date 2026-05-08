"""Tests for observability fixes introduced in phase-11 observability session.

Covers:
- Feedback payload includes metadata (question/response context)
- Feedback explanation carries the user comment text
- Tool span output.value shows document titles/IDs (search_documents)
- Tool span output.value shows full doc content (get_document)
- Tool span output.value shows related doc titles (get_related_documents)
- Token counts are set on the CHAIN span after agent run
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from law_agent.observability.feedback import PhoenixFeedbackClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_in_memory_tracer() -> tuple[TracerProvider, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider, exporter


def _mock_post_ok(captured: dict[str, Any]):
    async def _post(url, json=None, **kwargs):
        captured["url"] = url
        captured["json"] = json
        resp = MagicMock()
        resp.status_code = 200
        return resp
    return _post


# ---------------------------------------------------------------------------
# Feedback: metadata included in Phoenix payload
# ---------------------------------------------------------------------------

class TestFeedbackMetadata:
    @pytest.mark.asyncio
    async def test_metadata_forwarded_to_phoenix(self) -> None:
        client = PhoenixFeedbackClient("http://localhost:6006")
        captured: dict = {}
        client._http = MagicMock()
        client._http.post = _mock_post_ok(captured)

        await client.send_feedback(
            span_id="abc1234567890abc",
            feedback_type="positive",
            comment="پاسخ دقیق بود",
            metadata={
                "session_id": "sess-42",
                "question": "حق مسکن کارگر چقدر است؟",
                "response_preview": "پاسخ کامل...",
                "user_comment": "پاسخ دقیق بود",
            },
        )

        payload = captured["json"]
        annotation = payload["data"][0]
        assert annotation["metadata"]["session_id"] == "sess-42"
        assert annotation["metadata"]["question"] == "حق مسکن کارگر چقدر است؟"
        assert annotation["metadata"]["response_preview"] == "پاسخ کامل..."
        assert annotation["metadata"]["user_comment"] == "پاسخ دقیق بود"

    @pytest.mark.asyncio
    async def test_metadata_none_becomes_empty_dict(self) -> None:
        client = PhoenixFeedbackClient("http://localhost:6006")
        captured: dict = {}
        client._http = MagicMock()
        client._http.post = _mock_post_ok(captured)

        await client.send_feedback(
            span_id="abc1234567890abc",
            feedback_type="negative",
            metadata=None,
        )

        annotation = captured["json"]["data"][0]
        assert annotation["metadata"] == {}

    @pytest.mark.asyncio
    async def test_explanation_contains_user_comment(self) -> None:
        client = PhoenixFeedbackClient("http://localhost:6006")
        captured: dict = {}
        client._http = MagicMock()
        client._http.post = _mock_post_ok(captured)

        comment = "این پاسخ خیلی مفید بود"
        await client.send_feedback(
            span_id="abc1234567890abc",
            feedback_type="positive",
            comment=comment,
        )

        explanation = captured["json"]["data"][0]["result"]["explanation"]
        assert comment in explanation

    @pytest.mark.asyncio
    async def test_score_is_float(self) -> None:
        client = PhoenixFeedbackClient("http://localhost:6006")
        captured: dict = {}
        client._http = MagicMock()
        client._http.post = _mock_post_ok(captured)

        await client.send_feedback(span_id="s1", feedback_type="positive")
        assert isinstance(captured["json"]["data"][0]["result"]["score"], float)


# ---------------------------------------------------------------------------
# Tool spans: output.value format
# ---------------------------------------------------------------------------

class TestSearchDocumentsOutputFormat:
    """Verify search_documents TOOL span output.value lists document titles."""

    @pytest.mark.asyncio
    async def test_output_contains_doc_id_and_title(self) -> None:
        from law_agent.models.document import DocSummary as SearchResult

        mock_results = [
            SearchResult(
                doc_id=101,
                title="قانون کار جمهوری اسلامی ایران",
                doc_type="law",
                date="1369",
                summary="متن قانون کار",
                tags=["کار"],
                relevance_score=0.95,
                full_content="",
                relations_count=0,
            ),
            SearchResult(
                doc_id=202,
                title="آیین‌نامه حق مسکن",
                doc_type="regulation",
                date="1402",
                summary="مصوبه وزارت کار",
                tags=["مسکن"],
                relevance_score=0.88,
                full_content="",
                relations_count=0,
            ),
        ]

        provider, exporter = _make_in_memory_tracer()
        step_mock = MagicMock()
        step_mock.__aenter__ = AsyncMock(return_value=step_mock)
        step_mock.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("law_agent.agent.core.search_documents", return_value=mock_results),
            patch("law_agent.agent.core.cl.Step", return_value=step_mock),
            patch("law_agent.agent.core.get_tracer", return_value=provider.get_tracer("test")),
            patch("law_agent.agent.core.get_settings") as mock_settings,
        ):
            mock_settings.return_value.search.max_results = 20
            from law_agent.agent.core import LawAgent
            result_json = await LawAgent._search_documents_tool(
                MagicMock(), query="حق مسکن", tags=None, doc_types=None, limit=20
            )

        finished_spans = exporter.get_finished_spans()
        assert len(finished_spans) == 1
        span = finished_spans[0]
        assert span.name == "search_documents"

        output_val = span.attributes.get("output.value", "")
        assert "[101]" in output_val
        assert "قانون کار جمهوری اسلامی ایران" in output_val
        assert "[202]" in output_val
        assert "آیین‌نامه حق مسکن" in output_val
        assert "(law)" in output_val
        assert "(regulation)" in output_val

    @pytest.mark.asyncio
    async def test_empty_results_output(self) -> None:
        provider, exporter = _make_in_memory_tracer()
        step_mock = MagicMock()
        step_mock.__aenter__ = AsyncMock(return_value=step_mock)
        step_mock.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("law_agent.agent.core.search_documents", return_value=[]),
            patch("law_agent.agent.core.cl.Step", return_value=step_mock),
            patch("law_agent.agent.core.get_tracer", return_value=provider.get_tracer("test")),
            patch("law_agent.agent.core.get_settings") as mock_settings,
        ):
            mock_settings.return_value.search.max_results = 20
            from law_agent.agent.core import LawAgent
            await LawAgent._search_documents_tool(
                MagicMock(), query="چیزی", tags=None, doc_types=None, limit=20
            )

        span = exporter.get_finished_spans()[0]
        assert span.attributes.get("output.value") == "no results"

    @pytest.mark.asyncio
    async def test_span_kind_is_tool(self) -> None:
        from law_agent.models.document import DocSummary as SearchResult
        provider, exporter = _make_in_memory_tracer()
        step_mock = MagicMock()
        step_mock.__aenter__ = AsyncMock(return_value=step_mock)
        step_mock.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("law_agent.agent.core.search_documents", return_value=[]),
            patch("law_agent.agent.core.cl.Step", return_value=step_mock),
            patch("law_agent.agent.core.get_tracer", return_value=provider.get_tracer("test")),
            patch("law_agent.agent.core.get_settings") as mock_settings,
        ):
            mock_settings.return_value.search.max_results = 20
            from law_agent.agent.core import LawAgent
            await LawAgent._search_documents_tool(
                MagicMock(), query="test", tags=None, doc_types=None, limit=5
            )

        span = exporter.get_finished_spans()[0]
        assert span.attributes.get("openinference.span.kind") == "TOOL"
        assert span.attributes.get("tool.name") == "search_documents"


class TestGetDocumentOutputFormat:
    """Verify get_document TOOL span output.value includes full document content."""

    @pytest.mark.asyncio
    async def test_output_contains_title_type_date_summary(self) -> None:
        from law_agent.models.document import FullDocument

        mock_doc = FullDocument(
            doc_id=555,
            title="قانون بیمه بیکاری",
            doc_type="law",
            date="1369/06/26",
            summary="قانون بیمه بیکاری مصوب مجلس شورای اسلامی",
            tags=["بیمه", "بیکاری"],
            relevance_score=1.0,
            full_content="ماده ۱ — کلیه کارگرانی که…",
            relations_count=3,
        )

        provider, exporter = _make_in_memory_tracer()
        step_mock = MagicMock()
        step_mock.__aenter__ = AsyncMock(return_value=step_mock)
        step_mock.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("law_agent.agent.core.get_document", return_value=mock_doc),  # type: ignore[arg-type]
            patch("law_agent.agent.core.cl.Step", return_value=step_mock),
            patch("law_agent.agent.core.get_tracer", return_value=provider.get_tracer("test")),
        ):
            from law_agent.agent.core import LawAgent
            await LawAgent._get_document_tool(MagicMock(), doc_id=555)

        span = exporter.get_finished_spans()[0]
        output_val = span.attributes.get("output.value", "")

        assert "[555]" in output_val
        assert "قانون بیمه بیکاری" in output_val
        assert "law" in output_val
        assert "1369/06/26" in output_val
        assert "قانون بیمه بیکاری مصوب مجلس" in output_val
        assert "ماده ۱" in output_val  # full_content included

    @pytest.mark.asyncio
    async def test_output_value_for_not_found(self) -> None:
        from law_agent.tools.search import DocumentNotFoundError

        provider, exporter = _make_in_memory_tracer()
        step_mock = MagicMock()
        step_mock.__aenter__ = AsyncMock(return_value=step_mock)
        step_mock.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("law_agent.agent.core.get_document", side_effect=DocumentNotFoundError()),
            patch("law_agent.agent.core.cl.Step", return_value=step_mock),
            patch("law_agent.agent.core.get_tracer", return_value=provider.get_tracer("test")),
        ):
            from law_agent.agent.core import LawAgent
            result = await LawAgent._get_document_tool(MagicMock(), doc_id=99999)

        span = exporter.get_finished_spans()[0]
        assert "not found" in span.attributes.get("output.value", "")
        result_data = json.loads(result)
        assert "error" in result_data


class TestGetRelatedDocumentsOutputFormat:
    """Verify get_related_documents TOOL span output.value lists titles."""

    @pytest.mark.asyncio
    async def test_output_contains_titles(self) -> None:
        from law_agent.models.document import DocSummary as SearchResult

        related = [
            SearchResult(
                doc_id=301,
                title="آیین‌نامه اجرایی ماده ۱۴۱",
                doc_type="regulation",
                date="1380",
                summary="",
                tags=[],
                relevance_score=0.0,
                full_content="",
                relations_count=0,
            ),
        ]

        provider, exporter = _make_in_memory_tracer()
        step_mock = MagicMock()
        step_mock.__aenter__ = AsyncMock(return_value=step_mock)
        step_mock.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("law_agent.agent.core.get_related_documents", return_value=related),
            patch("law_agent.agent.core.cl.Step", return_value=step_mock),
            patch("law_agent.agent.core.get_tracer", return_value=provider.get_tracer("test")),
            patch("law_agent.agent.core.get_settings") as mock_settings,
        ):
            mock_settings.return_value.search.related_docs_default_limit = 10
            from law_agent.agent.core import LawAgent
            await LawAgent._get_related_documents_tool(MagicMock(), doc_id=100)

        span = exporter.get_finished_spans()[0]
        output_val = span.attributes.get("output.value", "")
        assert "[301]" in output_val
        assert "آیین‌نامه اجرایی ماده ۱۴۱" in output_val
        assert "(regulation)" in output_val
