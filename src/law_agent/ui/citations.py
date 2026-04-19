"""
Citation parsing and formatting for the UI.

Extracts citation references [1], [2], etc. from agent responses
and converts them to clickable links to iran.ir documentation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Citation:
    """Represents a single citation reference."""

    number: int
    doc_id: str | None = None
    doc_title: str | None = None
    url: str | None = None


class CitationFormatter:
    """Formats citations in agent responses as clickable links."""

    # Base URL for Iranian legal documents
    IRAN_IR_BASE_URL = "https://iran.ir/en/law"

    # Pattern to match citations like [1], [2], etc.
    CITATION_PATTERN = re.compile(r"\[(\d+)\]")

    def __init__(self) -> None:
        """Initialize citation formatter."""
        self.citations: list[Citation] = []

    def extract_citations(self, text: str) -> list[int]:
        """Extract citation numbers from text.

        Args:
            text: Text containing citations like [1], [2]

        Returns:
            List of unique citation numbers found
        """
        matches = self.CITATION_PATTERN.findall(text)
        return sorted({int(m) for m in matches})

    def format_response(self, response: str) -> str:
        """Format response text with clickable citation links.

        Args:
            response: Agent response text with citations

        Returns:
            HTML-formatted response with clickable links
        """
        try:
            # Extract citations
            citation_numbers = self.extract_citations(response)

            if not citation_numbers:
                # No citations found, return as-is
                return response

            # Format each citation as a clickable link
            formatted = response
            for num in citation_numbers:
                citation_link = self._create_citation_link(num)
                # Replace [N] with clickable link
                formatted = formatted.replace(
                    f"[{num}]", citation_link, 1  # Replace only first occurrence
                )

            return formatted

        except Exception as e:
            # If formatting fails, return original response
            import structlog

            logger = structlog.get_logger(__name__)
            logger.warning("citation_formatting_error", error=str(e))
            return response

    def _create_citation_link(self, citation_number: int) -> str:
        """Create HTML link for a citation.

        Args:
            citation_number: Citation number like 1, 2, 3

        Returns:
            HTML link string
        """
        # URL with citation number (could be enhanced with doc_id if available)
        url = f"{self.IRAN_IR_BASE_URL}/{citation_number}"

        # Create clickable link in Persian
        link_html = (
            f'<a href="{url}" target="_blank" '
            f'style="color: #0066cc; text-decoration: underline; '
            f'direction: rtl; text-align: right;">'
            f"[{citation_number}]</a>"
        )

        return link_html

    def extract_citation_references(self, text: str) -> dict[int, dict[str, str]]:
        """Extract and parse citation reference section from response.

        Looks for "منابع:" (References) section at end of response.

        Args:
            text: Full response text

        Returns:
            Dictionary mapping citation number to reference details
        """
        references: dict[int, dict[str, str]] = {}

        # Look for references section (Persian header)
        ref_pattern = re.compile(
            r"منابع\s*:\s*(.*?)(?:\n\n|$)",
            re.DOTALL | re.IGNORECASE,
        )
        match = ref_pattern.search(text)

        if not match:
            return references

        ref_section = match.group(1)

        # Parse individual references like [1] قانون مجازات اسلامی
        ref_lines = ref_section.strip().split("\n")

        for line in ref_lines:
            # Match pattern: [N] Reference text
            ref_match = re.match(r"\s*\[(\d+)\]\s+(.*)", line)
            if ref_match:
                num = int(ref_match.group(1))
                ref_text = ref_match.group(2).strip()
                references[num] = {
                    "number": str(num),
                    "text": ref_text,
                }

        return references

    def validate_citations(self, response: str) -> bool:
        """Validate that citation numbers are consecutive and complete.

        Args:
            response: Response text with citations

        Returns:
            True if citations are valid (consecutive [1], [2], [3], etc.)
            False if there are gaps or duplicates
        """
        citation_numbers = self.extract_citations(response)

        if not citation_numbers:
            return True  # No citations is valid

        # Check if consecutive starting from 1
        if citation_numbers[0] != 1:
            return False

        for i, num in enumerate(citation_numbers):
            if num != i + 1:
                return False

        return True


class CitationHTML:
    """Helper to generate citation HTML elements."""

    @staticmethod
    def create_reference_section(references: dict[int, dict[str, str]]) -> str:
        """Create HTML for references section.

        Args:
            references: Dictionary of reference data

        Returns:
            HTML formatted references section
        """
        if not references:
            return ""

        html = '<div style="direction: rtl; text-align: right; margin-top: 20px; border-top: 1px solid #ccc; padding-top: 10px;">'
        html += "<strong>منابع:</strong><br/>"

        for num in sorted(references.keys()):
            ref_data = references[num]
            ref_text = ref_data.get("text", "")
            html += (
                f'<div style="margin: 5px 0;">'
                f'<a href="https://iran.ir/en/law/{num}" target="_blank">'
                f"[{num}]</a> {ref_text}</div>"
            )

        html += "</div>"
        return html
