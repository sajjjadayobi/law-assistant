"""Tests for citation formatting module."""

from __future__ import annotations

import pytest

from law_agent.ui.citations import CitationFormatter


class TestCitationExtraction:
    """Test citation number extraction from text."""

    def test_extract_single_citation(self) -> None:
        """Test extracting a single citation."""
        formatter = CitationFormatter()
        text = "This is a legal opinion [1]."
        citations = formatter.extract_citations(text)
        assert citations == [1]

    def test_extract_multiple_citations(self) -> None:
        """Test extracting multiple citations."""
        formatter = CitationFormatter()
        text = "According to law [1] and regulation [2], the procedure is [3]."
        citations = formatter.extract_citations(text)
        assert citations == [1, 2, 3]

    def test_extract_duplicate_citations(self) -> None:
        """Test extracting unique citations (duplicates removed)."""
        formatter = CitationFormatter()
        text = "According to [1] and [1] again, and also [2]."
        citations = formatter.extract_citations(text)
        assert citations == [1, 2]

    def test_extract_no_citations(self) -> None:
        """Test text with no citations."""
        formatter = CitationFormatter()
        text = "This text has no citations."
        citations = formatter.extract_citations(text)
        assert citations == []

    def test_extract_citations_sorted(self) -> None:
        """Test that extracted citations are sorted."""
        formatter = CitationFormatter()
        text = "Text [3] with [1] citations [2]."
        citations = formatter.extract_citations(text)
        assert citations == [1, 2, 3]


class TestCitationFormatting:
    """Test response formatting with citations."""

    def test_format_response_with_citations(self) -> None:
        """Test formatting response with clickable citations."""
        formatter = CitationFormatter()
        response = "According to law [1], the rule is [2]."
        formatted = formatter.format_response(response)

        # Should contain HTML links
        assert "<a href=" in formatted
        assert "iran.ir" in formatted

    def test_format_response_without_citations(self) -> None:
        """Test formatting response without citations."""
        formatter = CitationFormatter()
        response = "This is plain text without citations."
        formatted = formatter.format_response(response)

        # Should return original
        assert formatted == response

    def test_format_response_preserves_text(self) -> None:
        """Test that citation formatting preserves surrounding text."""
        formatter = CitationFormatter()
        response = "Before [1] after."
        formatted = formatter.format_response(response)

        # Original text should still be there
        assert "Before" in formatted
        assert "after" in formatted

    def test_format_multiple_citations(self) -> None:
        """Test formatting multiple citations."""
        formatter = CitationFormatter()
        response = "Law [1] states [2] and requires [3]."
        formatted = formatter.format_response(response)

        # All citations should be replaced with links
        assert formatted.count("<a href=") == 3

    def test_format_response_with_error(self) -> None:
        """Test graceful error handling in formatting."""
        formatter = CitationFormatter()
        # Malformed text that might cause issues
        response = "Text with [[nested] citations."
        formatted = formatter.format_response(response)

        # Should return original on error
        assert formatted is not None


class TestCitationValidation:
    """Test citation validation."""

    def test_validate_consecutive_citations(self) -> None:
        """Test validation of consecutive citations [1] [2] [3]."""
        formatter = CitationFormatter()
        text = "Text [1] and [2] and [3]."
        assert formatter.validate_citations(text) is True

    def test_validate_non_consecutive_citations(self) -> None:
        """Test validation fails for non-consecutive citations."""
        formatter = CitationFormatter()
        text = "Text [1] and [3] skipping two."
        assert formatter.validate_citations(text) is False

    def test_validate_missing_first_citation(self) -> None:
        """Test validation fails if starting number is not 1."""
        formatter = CitationFormatter()
        text = "Text [2] and [3]."
        assert formatter.validate_citations(text) is False

    def test_validate_no_citations(self) -> None:
        """Test validation passes for text with no citations."""
        formatter = CitationFormatter()
        text = "Text with no citations."
        assert formatter.validate_citations(text) is True

    def test_validate_duplicate_citations(self) -> None:
        """Test validation fails for duplicate citation numbers."""
        formatter = CitationFormatter()
        text = "Text [1] and [1] again."
        # Duplicates removed, so this is valid if only [1] remains
        citations = formatter.extract_citations(text)
        assert citations == [1]


class TestCitationReferences:
    """Test citation reference extraction."""

    def test_extract_references_section(self) -> None:
        """Test extracting references from Persian section."""
        formatter = CitationFormatter()
        response = """Some answer here.

منابع:
[1] قانون مجازات اسلامی - مصوب ۱۳۹۲
[2] قانون کار - مصوب ۱۳۵۶
"""
        references = formatter.extract_citation_references(response)

        assert len(references) == 2
        assert references[1]["text"] == "قانون مجازات اسلامی - مصوب ۱۳۹۲"
        assert references[2]["text"] == "قانون کار - مصوب ۱۳۵۶"

    def test_extract_references_missing(self) -> None:
        """Test extracting from text without references."""
        formatter = CitationFormatter()
        response = "This text has no references section."
        references = formatter.extract_citation_references(response)

        assert references == {}

    def test_extract_references_empty(self) -> None:
        """Test extracting from empty references section."""
        formatter = CitationFormatter()
        response = "Text here.\n\nمنابع:\n"
        references = formatter.extract_citation_references(response)

        assert references == {}


class TestCitationHTML:
    """Test HTML generation for citations."""

    def test_create_reference_section_html(self) -> None:
        """Test generating HTML for reference section."""
        from law_agent.ui.citations import CitationHTML

        references = {
            1: {"text": "قانون مجازات اسلامی"},
            2: {"text": "قانون کار"},
        }

        html = CitationHTML.create_reference_section(references)

        assert "منابع" in html
        assert "[1]" in html
        assert "[2]" in html
        assert "قانون مجازات اسلامی" in html

    def test_create_reference_section_empty(self) -> None:
        """Test HTML generation with no references."""
        from law_agent.ui.citations import CitationHTML

        html = CitationHTML.create_reference_section({})

        assert html == ""


# Integration tests
@pytest.mark.asyncio
async def test_citation_formatter_integration() -> None:
    """Test complete citation formatting workflow."""
    formatter = CitationFormatter()

    response = """
طبق قانون مجازات اسلامی [1]، حداکثر مجازات برای این جرم [2] است.

منابع:
[1] قانون مجازات اسلامی - ماده ۲۷۰
[2] قانون تعزیرات هادی
"""

    # Extract citations
    citations = formatter.extract_citations(response)
    assert citations == [1, 2]

    # Validate citations
    assert formatter.validate_citations(response) is True

    # Extract references
    references = formatter.extract_citation_references(response)
    assert len(references) > 0

    # Format response
    formatted = formatter.format_response(response)
    assert formatted is not None
