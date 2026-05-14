"""Tests for thinking steps visualization logic (Task 11.3).

Tests:
- show_thinking() creates a Chainlit step with correct name/type
- agent.iter() correctly identifies CallToolsNode and extracts parts
- Tool methods create retrieval steps with dynamic names
- Step names are updated after results are known
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# show_thinking was removed — thinking is displayed inline in each tool via cl.Step


# ---------------------------------------------------------------------------
# Tool step — search documents
# ---------------------------------------------------------------------------


class TestSearchDocumentToolStep:
    @pytest.mark.asyncio
    async def test_step_name_updated_with_result_count(self) -> None:
        """Step name should update to 'جستجو — N سند پیدا شد' after results."""
        from law_assistant.agent.core import LawAgent
        from law_assistant.tools.search import DocSummary

        mock_results = [
            DocSummary(
                doc_id=1,
                title="ماده ۷۶ قانون کار",
                doc_type="law",
                date="1369",
                summary="مرخصی زایمان",
                tags=[],
                relevance_score=0.95,
            ),
            DocSummary(
                doc_id=2,
                title="قانون حمایت خانواده",
                doc_type="law",
                date="1400",
                summary="خانواده",
                tags=[],
                relevance_score=0.85,
            ),
        ]

        step_mock = MagicMock()
        step_mock.__aenter__ = AsyncMock(return_value=step_mock)
        step_mock.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("law_assistant.agent.core.cl.Step", return_value=step_mock),
            patch("law_assistant.agent.core.search_documents", return_value=mock_results),
        ):
            ctx = MagicMock()
            result = await LawAgent._search_documents_tool(ctx, query="مرخصی")

        assert step_mock.name == "🔍 مرخصی — 2 سند یافت شد"
        assert step_mock.output is not None
        # Output should list documents
        assert "ماده ۷۶ قانون کار" in step_mock.output

    @pytest.mark.asyncio
    async def test_step_name_no_results(self) -> None:
        """Empty results should give 'نتیجه‌ای پیدا نشد' name."""
        from law_assistant.agent.core import LawAgent

        step_mock = MagicMock()
        step_mock.__aenter__ = AsyncMock(return_value=step_mock)
        step_mock.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("law_assistant.agent.core.cl.Step", return_value=step_mock),
            patch("law_assistant.agent.core.search_documents", return_value=[]),
        ):
            ctx = MagicMock()
            await LawAgent._search_documents_tool(ctx, query="query")

        assert "نتیجه‌ای یافت نشد" in step_mock.name

    @pytest.mark.asyncio
    async def test_returns_json_string(self) -> None:
        """Tool return value must be valid JSON for the agent."""
        from law_assistant.agent.core import LawAgent
        from law_assistant.tools.search import DocSummary

        mock_results = [
            DocSummary(
                doc_id=1,
                title="قانون",
                doc_type="law",
                date="1369",
                summary="خلاصه",
                tags=[],
                relevance_score=0.8,
            ),
        ]

        step_mock = MagicMock()
        step_mock.__aenter__ = AsyncMock(return_value=step_mock)
        step_mock.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("law_assistant.agent.core.cl.Step", return_value=step_mock),
            patch("law_assistant.agent.core.search_documents", return_value=mock_results),
        ):
            ctx = MagicMock()
            result = await LawAgent._search_documents_tool(ctx, query="query")

        # Must be parseable JSON
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert parsed[0]["doc_id"] == 1
        assert parsed[0]["title"] == "قانون"

    @pytest.mark.asyncio
    async def test_step_type_is_retrieval(self) -> None:
        """Search step type should be 'retrieval' for distinct icon in UI."""
        from law_assistant.agent.core import LawAgent

        step_mock = MagicMock()
        step_mock.__aenter__ = AsyncMock(return_value=step_mock)
        step_mock.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("law_assistant.agent.core.cl.Step", return_value=step_mock) as mock_step,
            patch("law_assistant.agent.core.search_documents", return_value=[]),
        ):
            ctx = MagicMock()
            await LawAgent._search_documents_tool(ctx, query="query")

        assert mock_step.call_args[1].get("type") == "retrieval"


# ---------------------------------------------------------------------------
# Tool step — get document
# ---------------------------------------------------------------------------


class TestGetDocumentToolStep:
    @pytest.mark.asyncio
    async def test_step_name_includes_doc_title(self) -> None:
        """Step name should be 'خواندن سند — {title}' after fetching."""
        from law_assistant.agent.core import LawAgent

        mock_doc = MagicMock()
        mock_doc.doc_id = 4068325
        mock_doc.title = "ماده ۷۶ قانون کار"
        mock_doc.doc_type = "law"
        mock_doc.date = "1369"
        mock_doc.summary = "مرخصی زایمان"
        mock_doc.tags = []
        mock_doc.full_content = "محتوای کامل"
        mock_doc.relations_count = 5

        step_mock = MagicMock()
        step_mock.__aenter__ = AsyncMock(return_value=step_mock)
        step_mock.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("law_assistant.agent.core.cl.Step", return_value=step_mock),
            patch("law_assistant.agent.core.get_document", return_value=mock_doc),
        ):
            ctx = MagicMock()
            await LawAgent._get_document_tool(ctx, doc_id=4068325)

        assert step_mock.name == "خواندن سند — ماده ۷۶ قانون کار"

    @pytest.mark.asyncio
    async def test_step_output_contains_title_and_summary(self) -> None:
        from law_assistant.agent.core import LawAgent

        mock_doc = MagicMock()
        mock_doc.doc_id = 1
        mock_doc.title = "قانون کار"
        mock_doc.doc_type = "law"
        mock_doc.date = "1369"
        mock_doc.summary = "خلاصه قانون کار"
        mock_doc.tags = []
        mock_doc.full_content = "محتوا"
        mock_doc.relations_count = 3

        step_mock = MagicMock()
        step_mock.__aenter__ = AsyncMock(return_value=step_mock)
        step_mock.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("law_assistant.agent.core.cl.Step", return_value=step_mock),
            patch("law_assistant.agent.core.get_document", return_value=mock_doc),
        ):
            ctx = MagicMock()
            await LawAgent._get_document_tool(ctx, doc_id=1)

        assert "قانون کار" in step_mock.output
        assert "خلاصه قانون کار" in step_mock.output

    @pytest.mark.asyncio
    async def test_not_found_sets_error_name(self) -> None:
        from law_assistant.agent.core import LawAgent
        from law_assistant.tools.search import DocumentNotFoundError

        step_mock = MagicMock()
        step_mock.__aenter__ = AsyncMock(return_value=step_mock)
        step_mock.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("law_assistant.agent.core.cl.Step", return_value=step_mock),
            patch("law_assistant.agent.core.get_document", side_effect=DocumentNotFoundError()),
        ):
            ctx = MagicMock()
            result = await LawAgent._get_document_tool(ctx, doc_id=99999)

        assert "پیدا نشد" in step_mock.name
        parsed = json.loads(result)
        assert "error" in parsed

    @pytest.mark.asyncio
    async def test_returns_valid_json(self) -> None:
        from law_assistant.agent.core import LawAgent

        mock_doc = MagicMock()
        mock_doc.doc_id = 1
        mock_doc.title = "قانون"
        mock_doc.doc_type = "law"
        mock_doc.date = "1369"
        mock_doc.summary = "خلاصه"
        mock_doc.tags = ["کار"]
        mock_doc.full_content = "محتوا"
        mock_doc.relations_count = 0

        step_mock = MagicMock()
        step_mock.__aenter__ = AsyncMock(return_value=step_mock)
        step_mock.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("law_assistant.agent.core.cl.Step", return_value=step_mock),
            patch("law_assistant.agent.core.get_document", return_value=mock_doc),
        ):
            ctx = MagicMock()
            result = await LawAgent._get_document_tool(ctx, doc_id=1)

        parsed = json.loads(result)
        assert parsed["doc_id"] == 1
        assert parsed["full_content"] == "محتوا"


# ---------------------------------------------------------------------------
# Tool step — related documents
# ---------------------------------------------------------------------------


class TestRelatedDocumentsToolStep:
    @pytest.mark.asyncio
    async def test_step_name_includes_count(self) -> None:
        from law_assistant.agent.core import LawAgent
        from law_assistant.tools.search import DocSummary

        mock_results = [
            DocSummary(
                doc_id=2,
                title="آیین‌نامه",
                doc_type="regulation",
                date="1370",
                summary="خلاصه",
                tags=[],
                relevance_score=0.7,
            ),
            DocSummary(
                doc_id=3,
                title="نظریه",
                doc_type="advisory_opinion",
                date="1380",
                summary="خلاصه",
                tags=[],
                relevance_score=0.6,
            ),
        ]

        step_mock = MagicMock()
        step_mock.__aenter__ = AsyncMock(return_value=step_mock)
        step_mock.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("law_assistant.agent.core.cl.Step", return_value=step_mock),
            patch("law_assistant.agent.core.get_related_documents", return_value=mock_results),
        ):
            ctx = MagicMock()
            await LawAgent._get_related_documents_tool(ctx, doc_id=1)

        assert step_mock.name == "اسناد مرتبط — 2 سند"

    @pytest.mark.asyncio
    async def test_empty_results_step_name(self) -> None:
        from law_assistant.agent.core import LawAgent

        step_mock = MagicMock()
        step_mock.__aenter__ = AsyncMock(return_value=step_mock)
        step_mock.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("law_assistant.agent.core.cl.Step", return_value=step_mock),
            patch("law_assistant.agent.core.get_related_documents", return_value=[]),
        ):
            ctx = MagicMock()
            await LawAgent._get_related_documents_tool(ctx, doc_id=1)

        assert "یافت نشد" in step_mock.name


# ---------------------------------------------------------------------------
# Tool label mapping in thinking step
# ---------------------------------------------------------------------------


class TestThinkingToolLabels:
    def test_search_tool_has_persian_label(self) -> None:
        """Search tool step must use a Persian step name."""
        import inspect
        from law_assistant.agent import core

        source = inspect.getsource(core.LawAgent._search_documents_tool)
        assert "جستجو" in source or "یافت شد" in source

    def test_get_document_tool_has_persian_label(self) -> None:
        """Get-document tool step must use a Persian step name."""
        import inspect
        from law_assistant.agent import core

        source = inspect.getsource(core.LawAgent._get_document_tool)
        assert "خواندن سند" in source
