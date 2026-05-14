"""Unit tests for citation system.

Tests citation extraction, formatting, and response post-processing.
"""

from law_agent.agent.citations import (
    Citation,
    CitationExtractor,
    ResponsePostProcessor,
)


class TestCitation:
    """Tests for Citation dataclass."""

    def test_citation_creation(self):
        """Test creating a citation."""
        citation = Citation(
            number=1,
            doc_id=12345,
            doc_title="قانون مجازات اسلامی",
            doc_type="law",
            doc_date="1392",
        )

        assert citation.number == 1
        assert citation.doc_id == 12345
        assert citation.doc_title == "قانون مجازات اسلامی"
        assert citation.doc_type == "law"

    def test_citation_format_as_reference_law(self):
        """Test formatting law citation."""
        citation = Citation(
            number=1,
            doc_id=123,
            doc_title="قانون مجازات اسلامی",
            doc_type="law",
            doc_date="1392",
        )

        ref = citation.format_as_reference()

        assert "[1]" in ref
        assert "قانون" in ref
        assert "قانون مجازات اسلامی" in ref

    def test_citation_format_as_reference_opinion(self):
        """Test formatting advisory opinion citation."""
        citation = Citation(
            number=2,
            doc_id=456,
            doc_title="نظریهی مشورتی شماره 7/97/1596",
            doc_type="advisory_opinion",
        )

        ref = citation.format_as_reference()

        assert "[2]" in ref
        assert "نظریهی مشورتی" in ref

    def test_citation_get_url(self):
        """Test getting URL for citation."""
        citation = Citation(
            number=1,
            doc_id=12345,
            doc_title="قانون",
            doc_type="law",
        )

        url = citation.get_url()

        assert "12345" in url
        assert "danagoo.com" in url


class TestCitationExtractor:
    """Tests for CitationExtractor class."""

    def test_extract_citations_from_text_single(self):
        """Test extracting single citation from text."""
        text = "طبق ماده ۲۷۰ قانون مجازات اسلامی [1]، حداکثر مجازات است."

        numbers = CitationExtractor.extract_citations_from_text(text)

        assert numbers == [1]

    def test_extract_citations_from_text_multiple(self):
        """Test extracting multiple citations from text."""
        text = "طبق قانون [1] و نظریهی [2] و حکم دادگاه [3]."

        numbers = CitationExtractor.extract_citations_from_text(text)

        assert numbers == [1, 2, 3]

    def test_extract_citations_from_text_duplicates(self):
        """Test that duplicate citations are deduplicated."""
        text = "اول [1] و دوم [1] و سوم [2]"

        numbers = CitationExtractor.extract_citations_from_text(text)

        assert numbers == [1, 2]

    def test_extract_citations_from_text_none(self):
        """Test extracting from text with no citations."""
        text = "متن بدون نقل"

        numbers = CitationExtractor.extract_citations_from_text(text)

        assert numbers == []

    def test_build_citations(self):
        """Test building Citation objects."""
        cited_docs = {
            1: {
                "doc_id": 123,
                "title": "قانون مجازات",
                "doc_type": "law",
                "date": "1392",
            },
            2: {
                "doc_id": 456,
                "title": "نظریهی مشورتی",
                "doc_type": "advisory_opinion",
            },
        }

        citations = CitationExtractor.build_citations(cited_docs)

        assert len(citations) == 2
        assert citations[0].number == 1
        assert citations[0].doc_id == 123
        assert citations[1].number == 2
        assert citations[1].doc_id == 456

    def test_build_citations_with_explicit_numbers(self):
        """Test building citations with specific numbers."""
        cited_docs = {
            1: {"doc_id": 111, "title": "قانون", "doc_type": "law"},
            2: {"doc_id": 222, "title": "نظریه", "doc_type": "advisory_opinion"},
            3: {"doc_id": 333, "title": "حکم", "doc_type": "court_ruling"},
        }

        # Only request citations 1 and 3
        citations = CitationExtractor.build_citations(
            cited_docs,
            citation_numbers=[1, 3],
        )

        assert len(citations) == 2
        assert citations[0].number == 1
        assert citations[1].number == 3

    def test_format_citations_section_empty(self):
        """Test formatting empty citations list."""
        result = CitationExtractor.format_citations_section([])

        assert result == ""

    def test_format_citations_section_single(self):
        """Test formatting single citation."""
        citation = Citation(
            number=1,
            doc_id=123,
            doc_title="قانون مجازات اسلامی",
            doc_type="law",
            doc_date="1392",
        )

        result = CitationExtractor.format_citations_section([citation])

        assert "منابع:" in result
        assert "[1]" in result
        assert "قانون مجازات اسلامی" in result

    def test_format_citations_section_multiple(self):
        """Test formatting multiple citations."""
        citations = [
            Citation(
                number=1,
                doc_id=123,
                doc_title="قانون اول",
                doc_type="law",
            ),
            Citation(
                number=2,
                doc_id=456,
                doc_title="نظریهی دوم",
                doc_type="advisory_opinion",
            ),
        ]

        result = CitationExtractor.format_citations_section(citations)

        assert "منابع:" in result
        assert "[1]" in result
        assert "[2]" in result
        assert "قانون اول" in result
        assert "نظریهی دوم" in result

    def test_add_citations_section_with_citations(self):
        """Test adding citations section to response."""
        response = "این است پاسخ"
        citations = [
            Citation(
                number=1,
                doc_id=123,
                doc_title="قانون",
                doc_type="law",
            ),
        ]

        result = CitationExtractor.add_citations_section(response, citations)

        assert "این است پاسخ" in result
        assert "منابع:" in result
        assert "[1]" in result

    def test_add_citations_section_without_citations(self):
        """Test adding citations section when no citations."""
        response = "پاسخ بدون نقل"

        result = CitationExtractor.add_citations_section(response, [])

        assert result == "پاسخ بدون نقل"


class TestResponsePostProcessor:
    """Tests for ResponsePostProcessor class."""

    def test_add_citations_to_response(self):
        """Test adding citations to response."""
        response = "جواب شامل [1] و [2]"
        cited_docs = {
            1: {
                "doc_id": 111,
                "title": "منبع اول",
                "doc_type": "law",
            },
            2: {
                "doc_id": 222,
                "title": "منبع دوم",
                "doc_type": "regulation",
            },
        }

        result = ResponsePostProcessor.add_citations_to_response(response, cited_docs)

        assert "جواب شامل [1] و [2]" in result
        assert "منابع:" in result
        assert "منبع اول" in result
        assert "منبع دوم" in result

    def test_add_citations_to_response_empty(self):
        """Test adding citations when no cited_docs."""
        response = "جواب بدون نقل"

        result = ResponsePostProcessor.add_citations_to_response(response, {})

        assert result == "جواب بدون نقل"

    def test_add_followup_questions(self):
        """Test adding follow-up questions to response."""
        response = "جواب اصلی"
        questions = [
            "سوال اول چیست؟",
            "سوال دوم چیست؟",
        ]

        result = ResponsePostProcessor.add_followup_questions(response, questions)

        assert "جواب اصلی" in result
        assert "سوالات پیگیری:" in result
        assert "سوال اول چیست؟" in result
        assert "سوال دوم چیست؟" in result

    def test_add_followup_questions_empty(self):
        """Test adding follow-up questions when list is empty."""
        response = "جواب"

        result = ResponsePostProcessor.add_followup_questions(response, [])

        assert result == "جواب"

    def test_postprocess_response_complete(self):
        """Test complete response post-processing."""
        response = "جواب با [1]"
        cited_docs = {
            1: {"doc_id": 111, "title": "قانون", "doc_type": "law"},
        }
        questions = ["سوال اول?"]

        result = ResponsePostProcessor.postprocess_response(
            response,
            cited_docs=cited_docs,
            followup_questions=questions,
        )

        assert "جواب با [1]" in result
        assert "منابع:" in result
        assert "سوالات پیگیری:" in result
        assert "سوال اول?" in result

    def test_postprocess_response_only_citations(self):
        """Test post-processing with only citations."""
        response = "جواب [1]"
        cited_docs = {1: {"doc_id": 111, "title": "قانون", "doc_type": "law"}}

        result = ResponsePostProcessor.postprocess_response(
            response,
            cited_docs=cited_docs,
        )

        assert "منابع:" in result
        assert "سوالات پیگیری:" not in result

    def test_postprocess_response_only_questions(self):
        """Test post-processing with only questions."""
        response = "جواب"
        questions = ["سوال؟"]

        result = ResponsePostProcessor.postprocess_response(
            response,
            followup_questions=questions,
        )

        assert "سوالات پیگیری:" in result
        assert "منابع:" not in result
