"""
Citation parsing and formatting for the UI.

Extracts [1], [2] citation markers from agent responses and converts them
to markdown links pointing to the real document URLs using the
doc_id extracted from the reference section.

The citation base URL is configurable in config.yaml (ui.citation_base_url).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from law_agent.config.settings import get_settings

# Load settings at module level (cached singleton)
_settings = get_settings()


@dataclass
class Citation:
    number: int
    doc_id: str | None = None
    title: str | None = None

    @property
    def url(self) -> str:
        base = _settings.ui.citation_base_url
        target = self.doc_id if self.doc_id else str(self.number)
        return f"{base}/{target}"

    def to_markdown_link(self) -> str:
        return f"[{self.number}]({self.url})"


# Matches [1], [2], [12] etc. — used inline and in reference lines
_CITATION_RE = re.compile(r"\[(\d+)\]")

# Matches [doc_id: 12345] as written by the agent
_DOC_ID_RE = re.compile(r"\[doc_id:\s*(\d+)\]", re.IGNORECASE)

# Matches the reference section header  (منابع:  or  :منابع)
_REF_SECTION_RE = re.compile(r"(منابع\s*:|:منابع)", re.IGNORECASE)


class CitationFormatter:
    """
    Converts agent citations to clean markdown links.

    Flow:
      1. Scan the reference section (منابع:) to build citation → doc_id map.
      2. Replace every [N] in the body with a markdown link [N](url).
      3. Clean the reference section: strip [doc_id: X] tags and render
         each reference as a proper markdown link.
    """

    def __init__(self) -> None:
        self._citations: dict[int, Citation] = {}

    def format_response(self, response: str) -> str:
        try:
            self._citations = self._parse_references(response)
            if not self._citations and not _CITATION_RE.search(response):
                return response
            return self._render(response)
        except Exception:
            return response

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_references(self, text: str) -> dict[int, Citation]:
        """Extract citation numbers and their doc_ids from the منابع section."""
        citations: dict[int, Citation] = {}

        match = _REF_SECTION_RE.search(text)
        if not match:
            return citations

        section = text[match.end():]

        for line in section.splitlines():
            m = _CITATION_RE.match(line.strip())
            if not m:
                continue
            num = int(m.group(1))
            doc_id_m = _DOC_ID_RE.search(line)
            # Title: everything between [N] and [doc_id:...] or end of line
            raw_title = _CITATION_RE.sub("", line, count=1)
            raw_title = _DOC_ID_RE.sub("", raw_title).strip(" \t–—-")
            citations[num] = Citation(
                number=num,
                doc_id=doc_id_m.group(1) if doc_id_m else None,
                title=raw_title or None,
            )

        return citations

    def _render(self, text: str) -> str:
        """Replace [N] with markdown links and clean up the reference section."""
        ref_match = _REF_SECTION_RE.search(text)

        if ref_match:
            body = text[: ref_match.start()]
            ref_block = text[ref_match.start():]
        else:
            body = text
            ref_block = ""

        # Replace [N] in body (but not inside markdown links already)
        body = _CITATION_RE.sub(self._replace_inline, body)

        # Rebuild the reference section cleanly
        if ref_block:
            ref_block = self._clean_ref_section(ref_block)

        return body + ref_block

    def _replace_inline(self, m: re.Match) -> str:
        num = int(m.group(1))
        citation = self._citations.get(num)
        if citation:
            return citation.to_markdown_link()
        # Fallback: link by number even without doc_id
        base_url = _settings.ui.citation_base_url
        return f"[{num}]({base_url}/{num})"

    def _clean_ref_section(self, section: str) -> str:
        """Render منابع block with markdown links and no raw [doc_id: X] tags."""
        lines = section.splitlines()
        result = []
        for line in lines:
            # Ref line: [N] Title [doc_id: X]
            m = _CITATION_RE.match(line.strip())
            if m:
                num = int(m.group(1))
                citation = self._citations.get(num)
                # Strip [doc_id:...] from display title
                clean_title = _DOC_ID_RE.sub("", line)
                # Also remove the citation number itself — we'll replace with link
                clean_title = _CITATION_RE.sub("", clean_title, count=1)
                # Strip stray dashes/spaces that may surround the removed [doc_id:] tag
                clean_title = re.sub(r'\s*[-–—]\s*$', '', clean_title).strip()
                # Build the line: markdown link + clean title
                link = citation.to_markdown_link() if citation else f"[{num}]"
                result.append(f"{link} {clean_title}")
            else:
                result.append(line)
        return "\n".join(result)

    # ------------------------------------------------------------------
    # Legacy helpers kept for backwards compatibility
    # ------------------------------------------------------------------

    def extract_citations(self, text: str) -> list[int]:
        matches = _CITATION_RE.findall(text)
        return sorted({int(m) for m in matches})

    def validate_citations(self, response: str) -> bool:
        nums = self.extract_citations(response)
        if not nums:
            return True
        return nums == list(range(1, len(nums) + 1))

    def extract_citation_references(self, text: str) -> dict[int, dict[str, str]]:
        """Return reference details keyed by citation number (legacy API).

        Returns: {1: {"number": "1", "text": "title"}, ...}
        """
        citations = self._parse_references(text)
        return {
            num: {"number": str(num), "text": c.title or ""}
            for num, c in citations.items()
        }
