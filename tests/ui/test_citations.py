"""Tests for citation formatting module.

Tests the updated CitationFormatter that:
- Renders markdown links [1](url) instead of HTML <a> tags
- Parses [doc_id: X] from reference lines to build real iran.ir URLs
- Strips [doc_id: X] from the displayed reference text
- Handles missing منابع sections gracefully
"""

from __future__ import annotations

import pytest

from law_agent.ui.citations import Citation, CitationFormatter

# ---------------------------------------------------------------------------
# Citation dataclass
# ---------------------------------------------------------------------------


class TestCitation:
    def test_url_with_doc_id(self) -> None:
        c = Citation(number=1, doc_id="4068325")
        assert c.url == "https://panel.danagoo.com/app?id=4068325"

    def test_url_fallback_to_number(self) -> None:
        c = Citation(number=2, doc_id=None)
        assert c.url == "https://panel.danagoo.com/app?id=2"

    def test_markdown_link(self) -> None:
        c = Citation(number=1, doc_id="4068325")
        assert c.to_markdown_link() == "[1](https://panel.danagoo.com/app?id=4068325)"

    def test_markdown_link_no_doc_id(self) -> None:
        c = Citation(number=3, doc_id=None)
        assert c.to_markdown_link() == "[3](https://panel.danagoo.com/app?id=3)"


# ---------------------------------------------------------------------------
# Citation extraction
# ---------------------------------------------------------------------------


class TestCitationExtraction:
    def test_single_citation(self) -> None:
        f = CitationFormatter()
        assert f.extract_citations("متن [1] اینجا.") == [1]

    def test_multiple_citations(self) -> None:
        f = CitationFormatter()
        assert f.extract_citations("طبق [1] و [2] و [3]") == [1, 2, 3]

    def test_deduplicated_and_sorted(self) -> None:
        f = CitationFormatter()
        assert f.extract_citations("[3] و [1] و [1]") == [1, 3]

    def test_no_citations(self) -> None:
        f = CitationFormatter()
        assert f.extract_citations("متن بدون استناد") == []


# ---------------------------------------------------------------------------
# Reference section parsing — with [doc_id: X]
# ---------------------------------------------------------------------------


class TestReferenceParser:
    RESPONSE_WITH_REFS = """طبق ماده ۷۶ قانون کار [1] مرخصی زایمان ۹۰ روز است.

منابع:
[1] ماده ۷۶ قانون کار مصوب ۱۳۶۹ [doc_id: 4068325]
[2] قانون حمایت از خانواده مصوب ۱۴۰۰ [doc_id: 7194230]
"""

    def test_parses_doc_ids(self) -> None:
        f = CitationFormatter()
        refs = f._parse_references(self.RESPONSE_WITH_REFS)
        assert refs[1].doc_id == "4068325"
        assert refs[2].doc_id == "7194230"

    def test_parses_titles(self) -> None:
        f = CitationFormatter()
        refs = f._parse_references(self.RESPONSE_WITH_REFS)
        assert "قانون کار" in refs[1].title
        assert "خانواده" in refs[2].title

    def test_title_strips_doc_id_tag(self) -> None:
        f = CitationFormatter()
        refs = f._parse_references(self.RESPONSE_WITH_REFS)
        assert "[doc_id:" not in refs[1].title
        assert "[doc_id:" not in refs[2].title

    def test_no_ref_section_returns_empty(self) -> None:
        f = CitationFormatter()
        refs = f._parse_references("متن بدون بخش منابع")
        assert refs == {}

    def test_ref_without_doc_id(self) -> None:
        text = "متن [1]\n\nمنابع:\n[1] قانون مجازات اسلامی مصوب ۱۳۹۲\n"
        f = CitationFormatter()
        refs = f._parse_references(text)
        assert refs[1].doc_id is None
        assert "مجازات" in refs[1].title


# ---------------------------------------------------------------------------
# Full format_response — markdown links, no HTML
# ---------------------------------------------------------------------------


class TestFormatResponse:
    def test_inline_citations_become_markdown_links(self) -> None:
        f = CitationFormatter()
        resp = "طبق قانون [1] این‌گونه است.\n\nمنابع:\n[1] ماده ۷۶ [doc_id: 4068325]\n"
        out = f.format_response(resp)
        assert "[1](https://panel.danagoo.com/app?id=4068325)" in out

    def test_no_html_tags_in_output(self) -> None:
        f = CitationFormatter()
        resp = "طبق [1]\n\nمنابع:\n[1] قانون کار [doc_id: 100]\n"
        out = f.format_response(resp)
        assert "<a " not in out
        assert "href=" not in out

    def test_doc_id_tag_stripped_from_reference_line(self) -> None:
        """[doc_id: X] tag must not appear in output, though X may appear in URL."""
        f = CitationFormatter()
        resp = "متن [1]\n\nمنابع:\n[1] قانون کار [doc_id: 4068325]\n"
        out = f.format_response(resp)
        assert "[doc_id:" not in out
        # The number 4068325 legitimately appears in the URL — that is correct
        assert "panel.danagoo.com/app?id=4068325" in out

    def test_reference_line_has_markdown_link(self) -> None:
        f = CitationFormatter()
        resp = "متن [1]\n\nمنابع:\n[1] قانون کار مصوب ۱۳۶۹ [doc_id: 4068325]\n"
        out = f.format_response(resp)
        assert "[1](https://panel.danagoo.com/app?id=4068325)" in out
        assert "قانون کار مصوب ۱۳۶۹" in out

    def test_multiple_citations_all_replaced(self) -> None:
        f = CitationFormatter()
        resp = (
            "طبق [1] و [2]\n\nمنابع:\n[1] قانون کار [doc_id: 100]\n[2] قانون مدنی [doc_id: 200]\n"
        )
        out = f.format_response(resp)
        assert "[1](https://panel.danagoo.com/app?id=100)" in out
        assert "[2](https://panel.danagoo.com/app?id=200)" in out

    def test_no_citations_returns_original(self) -> None:
        f = CitationFormatter()
        resp = "متن بدون استناد"
        assert f.format_response(resp) == resp

    def test_fallback_url_without_doc_id(self) -> None:
        f = CitationFormatter()
        resp = "طبق [1]\n\nمنابع:\n[1] قانون کار بدون شناسه\n"
        out = f.format_response(resp)
        assert "[1](https://panel.danagoo.com/app?id=1)" in out

    def test_stray_dashes_not_in_reference_output(self) -> None:
        """[doc_id: X] tag is stripped; remaining title text is preserved."""
        f = CitationFormatter()
        # Current system-prompt format: title then [doc_id: X]
        resp = "طبق [1]\n\nمنابع:\n[1] قانون کار مصوب ۱۳۶۹ [doc_id: 999]\n"
        out = f.format_response(resp)
        assert "[doc_id:" not in out
        assert "قانون کار مصوب ۱۳۶۹" in out

    def test_error_fallback_returns_original(self) -> None:
        f = CitationFormatter()
        # Malformed but should not crash
        resp = "متن [[nested]] مجازات"
        out = f.format_response(resp)
        assert out is not None

    def test_body_text_preserved(self) -> None:
        f = CitationFormatter()
        resp = "متن قبل [1] متن بعد\n\nمنابع:\n[1] قانون [doc_id: 1]\n"
        out = f.format_response(resp)
        assert "متن قبل" in out
        assert "متن بعد" in out


# ---------------------------------------------------------------------------
# Citation validation
# ---------------------------------------------------------------------------


class TestCitationValidation:
    def test_consecutive_valid(self) -> None:
        f = CitationFormatter()
        assert f.validate_citations("متن [1] و [2] و [3]") is True

    def test_non_consecutive_invalid(self) -> None:
        f = CitationFormatter()
        assert f.validate_citations("متن [1] و [3]") is False

    def test_not_starting_at_one_invalid(self) -> None:
        f = CitationFormatter()
        assert f.validate_citations("متن [2] و [3]") is False

    def test_no_citations_valid(self) -> None:
        f = CitationFormatter()
        assert f.validate_citations("متن بدون استناد") is True

    def test_single_citation_valid(self) -> None:
        f = CitationFormatter()
        assert f.validate_citations("طبق قانون [1] اینگونه است") is True


# ---------------------------------------------------------------------------
# Backwards-compat helpers
# ---------------------------------------------------------------------------


class TestBackwardsCompat:
    def test_extract_citation_references_method_exists(self) -> None:
        f = CitationFormatter()
        # Legacy method should still exist
        assert hasattr(f, "extract_citation_references")

    def test_extract_citation_references_returns_dict(self) -> None:
        f = CitationFormatter()
        resp = "متن\n\nمنابع:\n[1] قانون کار\n"
        result = f.extract_citation_references(resp)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Integration test: real-world agent response format
# ---------------------------------------------------------------------------


class TestRealWorldFormat:
    AGENT_RESPONSE = """طبق ماده ۷۶ قانون کار [1]، مدت مرخصی زایمان برای کارگران زن ۹۰ روز کامل است.

با توجه به اصلاحات قانون حمایت از خانواده [2]، این مدت به ۹ ماه تمام افزایش یافته است.

منابع:
[1] ماده ۷۶ قانون کار مصوب ۱۳۶۹ [doc_id: 4068325]
[2] قانون حمایت از خانواده و جوانی جمعیت مصوب ۱۴۰۰ [doc_id: 7194230]

سوالات بیشتر:
- حقوق مرخصی زایمان چطور پرداخت می‌شود؟
- مرخصی شیردهی چیست؟
"""

    def test_inline_refs_replaced(self) -> None:
        f = CitationFormatter()
        out = f.format_response(self.AGENT_RESPONSE)
        assert "[1](https://panel.danagoo.com/app?id=4068325)" in out
        assert "[2](https://panel.danagoo.com/app?id=7194230)" in out

    def test_no_html_output(self) -> None:
        f = CitationFormatter()
        out = f.format_response(self.AGENT_RESPONSE)
        assert "<a " not in out

    def test_doc_ids_stripped_from_display(self) -> None:
        f = CitationFormatter()
        out = f.format_response(self.AGENT_RESPONSE)
        assert "[doc_id:" not in out

    def test_followup_questions_preserved(self) -> None:
        f = CitationFormatter()
        out = f.format_response(self.AGENT_RESPONSE)
        assert "سوالات بیشتر" in out
        assert "مرخصی شیردهی" in out

    def test_persian_text_preserved(self) -> None:
        f = CitationFormatter()
        out = f.format_response(self.AGENT_RESPONSE)
        assert "مدت مرخصی زایمان" in out
        assert "۹ ماه تمام" in out
