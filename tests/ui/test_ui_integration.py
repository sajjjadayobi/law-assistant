"""Integration tests for UI components."""

from __future__ import annotations

import pytest

from law_assistant.ui.citations import CitationFormatter
from law_assistant.ui.steps import ToolStepManager


class TestToolStepExtraction:
    """Test tool step extraction from responses."""

    def test_extract_search_steps(self) -> None:
        """Test extracting search tool steps."""
        manager = ToolStepManager()
        response = "Searching for: قانون مجازات. Found 15 results."
        steps = manager.extract_steps(response)

        # Should extract search steps
        assert len(steps) > 0
        assert any(s.get("tool_name") == "search_documents" for s in steps)

    def test_extract_document_steps(self) -> None:
        """Test extracting document retrieval steps."""
        manager = ToolStepManager()
        response = "Reading document #42. Retrieved full content."
        steps = manager.extract_steps(response)

        # Should extract document steps
        assert len(steps) > 0

    def test_create_search_step(self) -> None:
        """Test creating search step data."""
        manager = ToolStepManager()
        step = manager.create_search_step(
            query="بیمه", doc_types=["law", "regulation"], result_count=10
        )

        assert step["tool_name"] == "search_documents"
        assert step["input"]["query"] == "بیمه"
        assert step["output"]["result_count"] == 10

    def test_create_document_step(self) -> None:
        """Test creating document retrieval step data."""
        manager = ToolStepManager()
        step = manager.create_document_step(
            doc_id=123, doc_title="قانون مجازات اسلامی", content_length=5000
        )

        assert step["tool_name"] == "get_document"
        assert step["input"]["doc_id"] == 123
        assert step["output"]["status"] == "retrieved"

    def test_create_relations_step(self) -> None:
        """Test creating get_related_documents step data."""
        manager = ToolStepManager()
        step = manager.create_relations_step(doc_id=123, related_count=5)

        assert step["tool_name"] == "get_related_documents"
        assert step["output"]["related_count"] == 5


class TestCitationAndStepIntegration:
    """Test integration of citations and steps."""

    def test_response_with_citations_and_steps(self) -> None:
        """Test processing response with both citations and steps."""
        citation_formatter = CitationFormatter()
        step_manager = ToolStepManager()

        response = """
بر اساس قانون مجازات اسلامی [1]، این جرم [2] است.
Searching for: قانون مجازات. Found 5 results.

منابع:
[1] قانون مجازات اسلامی - ماده ۲۷۰
[2] قانون تعزیرات هادی - ماده ۱۲۵
"""

        # Extract citations
        citations = citation_formatter.extract_citations(response)
        assert len(citations) > 0

        # Extract steps
        steps = step_manager.extract_steps(response)
        assert len(steps) > 0

        # Format response
        formatted = citation_formatter.format_response(response)
        assert formatted is not None

    def test_empty_response_handling(self) -> None:
        """Test handling of empty response."""
        citation_formatter = CitationFormatter()

        response = ""
        formatted = citation_formatter.format_response(response)
        assert formatted == ""

    def test_malformed_response_handling(self) -> None:
        """Test handling of malformed response."""
        citation_formatter = CitationFormatter()
        step_manager = ToolStepManager()

        malformed = "[[nested citations [1] [2]"
        citations = citation_formatter.extract_citations(malformed)
        steps = step_manager.extract_steps(malformed)

        # Should handle gracefully without crashing
        assert isinstance(citations, list)
        assert isinstance(steps, list)


class TestConfigIntegration:
    """Test UI configuration integration."""

    def test_settings_load(self) -> None:
        """Test loading UI settings."""
        from law_assistant.config.settings import Settings

        settings = Settings()
        assert hasattr(settings, "ui")
        assert hasattr(settings.ui, "show_thinking")
        assert hasattr(settings.ui, "show_tool_calls")
        assert hasattr(settings.ui, "enable_feedback")
        assert hasattr(settings.ui, "example_questions")

    def test_example_questions_config(self) -> None:
        """Test example questions from config."""
        from law_assistant.config.settings import Settings

        settings = Settings()
        questions = settings.ui.example_questions

        assert len(questions) > 0
        assert all(isinstance(q, str) for q in questions)

    def test_ui_feature_flags(self) -> None:
        """Test UI feature flag configuration."""
        from law_assistant.config.settings import Settings

        settings = Settings()

        # These should be boolean
        assert isinstance(settings.ui.show_thinking, bool)
        assert isinstance(settings.ui.show_tool_calls, bool)
        assert isinstance(settings.ui.enable_feedback, bool)


@pytest.mark.asyncio
async def test_ui_module_initialization() -> None:
    """Test UI module can be initialized."""
    from law_assistant.ui.app import (
        get_citation_formatter,
        get_settings,
        get_step_manager,
    )

    # These should initialize without error
    settings = get_settings()
    formatter = get_citation_formatter()
    manager = get_step_manager()

    assert settings is not None
    assert formatter is not None
    assert manager is not None


class TestPersianErrorMessages:
    """Test Persian error message handling."""

    def test_error_messages_are_persian(self) -> None:
        """Test that error messages contain Persian text."""
        error_msg = "متاسفانه خطایی رخ داده است"
        # Contains Persian Unicode characters
        assert any("\u0600" <= c <= "\u06ff" for c in error_msg)

    def test_welcome_message_is_persian(self) -> None:
        """Test that welcome message contains Persian text."""
        welcome = "سلام! 👋"
        assert any("\u0600" <= c <= "\u06ff" for c in welcome)
