"""Citation system for extracting and formatting document references.

This module implements citation extraction and formatting for agent responses.

Key Functions:
- extract_citations_from_response(): Parse citations from agent text
- format_citations(): Format citations as numbered list
- generate_citation_urls(): Create iran.ir URLs for documents
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class Citation:
    """Extracted citation from response.

    Attributes:
        number: Citation number in response [1], [2], etc.
        doc_id: Document ID being cited
        doc_title: Document title
        doc_type: Type of document (law, regulation, etc.)
        doc_date: Document date if available
    """

    number: int
    doc_id: int
    doc_title: str
    doc_type: str
    doc_date: str | None = None

    def format_as_reference(self) -> str:
        """Format citation as a reference line.

        Returns:
            Formatted reference string in Persian
            Example: "[1] قانون مجازات اسلامی مصوب ۱۳۹۲ - ماده ۲۷۰"
        """
        # Map doc_type to Persian label
        type_labels = {
            "law": "قانون",
            "regulation": "آئین‌نامه",
            "advisory_opinion": "نظریهی مشورتی",
            "court_ruling": "حکم دادگاه",
            "unified_precedent": "آرای وحدت رویه",
        }

        type_label = type_labels.get(self.doc_type, self.doc_type)

        # Build reference
        ref = f"[{self.number}] {type_label}: {self.doc_title}"

        if self.doc_date:
            # Convert date to Persian calendar-style display
            ref += f" - {self.doc_date}"

        return ref

    def get_url(self) -> str:
        """Get iran.ir URL for this document.

        Returns:
            URL to document on iran.ir (or placeholder if not available)
        """
        # This is a placeholder - in production, would look up actual URLs
        # For now, return a generic reference format
        return f"https://iran.ir/doc/{self.doc_id}"


class CitationExtractor:
    """Extract citations from agent responses and document metadata.

    This system handles:
    1. Extracting citation patterns from response text
    2. Matching citations to document metadata
    3. Formatting as numbered list
    4. Creating clickable links
    """

    # Pattern to match [N] citation markers in text
    CITATION_PATTERN = re.compile(r"\[(\d+)\]")

    @staticmethod
    def extract_citations_from_text(text: str) -> list[int]:
        """Extract citation numbers from response text.

        Args:
            text: Response text that may contain [1], [2], etc.

        Returns:
            List of citation numbers found, deduplicated and sorted
        """
        matches = CitationExtractor.CITATION_PATTERN.findall(text)
        citation_numbers = sorted({int(m) for m in matches})
        return citation_numbers

    @staticmethod
    def build_citations(
        cited_docs: dict[int, dict],
        citation_numbers: list[int] | None = None,
    ) -> list[Citation]:
        """Build Citation objects from document data.

        Args:
            cited_docs: Dictionary mapping citation number to document data
                       Document data should have: doc_id, title, doc_type, date (optional)
            citation_numbers: List of citation numbers expected in response
                            If None, uses all keys from cited_docs

        Returns:
            List of Citation objects numbered and formatted
        """
        if citation_numbers is None:
            citation_numbers = sorted(cited_docs.keys())

        citations = []
        for number in citation_numbers:
            if number not in cited_docs:
                logger.warning(
                    "citation_not_found",
                    number=number,
                    available_citations=list(cited_docs.keys()),
                )
                continue

            doc = cited_docs[number]
            citation = Citation(
                number=number,
                doc_id=doc.get("doc_id", 0),
                doc_title=doc.get("title", "Unknown"),
                doc_type=doc.get("doc_type", "unknown"),
                doc_date=doc.get("date"),
            )
            citations.append(citation)

        return citations

    @staticmethod
    def format_citations_section(citations: list[Citation]) -> str:
        """Format citations as a section for end of response.

        Args:
            citations: List of Citation objects

        Returns:
            Formatted citations section in Persian
            Example:
            ```
            منابع:
            [1] قانون مجازات اسلامی - ماده ۲۷۰
            [2] نظریهی مشورتی شماره 7/97/1596
            ```
        """
        if not citations:
            return ""

        lines = ["منابع:"]
        for citation in citations:
            lines.append(citation.format_as_reference())

        return "\n".join(lines)

    @staticmethod
    def add_citations_section(
        response_text: str,
        citations: list[Citation],
    ) -> str:
        """Add citations section to end of response.

        Args:
            response_text: Original response text
            citations: List of Citation objects

        Returns:
            Response text with citations section appended
        """
        citations_section = CitationExtractor.format_citations_section(citations)

        if citations_section:
            return f"{response_text}\n\n{citations_section}"
        else:
            return response_text


class ResponsePostProcessor:
    """Post-process agent responses to add citations and follow-up questions.

    This class handles:
    1. Extracting citations from response text
    2. Adding citations section if citations exist
    3. Adding follow-up questions if provided
    """

    @staticmethod
    def add_citations_to_response(
        response_text: str,
        cited_docs: dict[int, dict],
    ) -> str:
        """Add citations section to response.

        Args:
            response_text: Original response from agent
            cited_docs: Dictionary mapping citation number to document data

        Returns:
            Response with citations section added

        Example:
            response = "تو باید ماده ۲۷۰ را رعایت کنی [1]"
            cited_docs = {
                1: {
                    "doc_id": 12345,
                    "title": "قانون مجازات اسلامی",
                    "doc_type": "law",
                    "date": "2013"
                }
            }
            result = ResponsePostProcessor.add_citations_to_response(response, cited_docs)
            # Result: "تو باید ماده ۲۷۰ را رعایت کنی [1]\n\nمنابع:\n[1] قانون: قانون مجازات اسلامی - 2013"
        """
        if not cited_docs:
            return response_text

        # Extract citation numbers from response
        citation_numbers = CitationExtractor.extract_citations_from_text(response_text)

        # Build Citation objects
        citations = CitationExtractor.build_citations(cited_docs, citation_numbers)

        # Add citations section
        return CitationExtractor.add_citations_section(response_text, citations)

    @staticmethod
    def add_followup_questions(
        response_text: str,
        followup_questions: list[str] | None = None,
    ) -> str:
        """Add follow-up questions to response.

        Args:
            response_text: Original response
            followup_questions: List of 2-3 follow-up questions in Persian

        Returns:
            Response with follow-up questions section added
        """
        if not followup_questions or len(followup_questions) == 0:
            return response_text

        lines = [response_text, ""]
        lines.append("سوالات پیگیری:")
        for question in followup_questions:
            lines.append(f"• {question}")

        return "\n".join(lines)

    @staticmethod
    def postprocess_response(
        response_text: str,
        cited_docs: dict[int, dict] | None = None,
        followup_questions: list[str] | None = None,
    ) -> str:
        """Complete post-processing of agent response.

        Args:
            response_text: Original response from agent
            cited_docs: Optional document citations
            followup_questions: Optional follow-up questions

        Returns:
            Fully processed response with citations and questions
        """
        # Add citations if provided
        if cited_docs:
            response_text = ResponsePostProcessor.add_citations_to_response(
                response_text,
                cited_docs,
            )

        # Add follow-up questions if provided
        if followup_questions:
            response_text = ResponsePostProcessor.add_followup_questions(
                response_text,
                followup_questions,
            )

        return response_text
