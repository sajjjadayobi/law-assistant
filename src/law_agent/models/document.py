"""Pydantic models for document schemas.

These models define the structure of documents returned by search tools.
They provide type-safe outputs for the agent and ensure consistent JSON serialization.

Models:
    - DocSummary: Brief document info for search results (id, title, type, date, summary, tags, relevance_score)
    - FullDocument: Complete document for detailed reading (extends DocSummary + full_content)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["DocSummary", "FullDocument"]


class DocSummary(BaseModel):
    """Brief document summary returned by search results.

    Used as the return type for search_documents() and get_related_documents().
    Contains essential metadata and summary for the agent to decide if it should fetch the full document.

    Attributes:
        doc_id: Unique document identifier
        title: Document title in Persian
        doc_type: Type of document (law, regulation, advisory_opinion, court_ruling, unified_precedent)
        date: Document date (Gregorian calendar), may be None if not available
        summary: 200-500 word summary for preview (may be truncated for display)
        tags: List of subject classifications (first 3 tags shown, may be abbreviated)
        relevance_score: FTS relevance ranking from PostgreSQL (0.0-1.0, higher is more relevant)
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "doc_id": 12345,
                "title": "قانون بیمه اجتماعی",
                "doc_type": "law",
                "date": "2000-01-01",
                "summary": "این قانون در مورد بیمه اجتماعی ...",
                "tags": ["بیمه", "کار", "اجتماعی"],
                "relevance_score": 0.95,
            }
        }
    )

    doc_id: int = Field(..., description="Unique document identifier (BIGINT)")
    title: str = Field(..., description="Document title in Persian")
    doc_type: str = Field(
        ...,
        description="Document type: law, regulation, advisory_opinion, court_ruling, or unified_precedent",
    )
    date: str | None = Field(None, description="Document date in YYYY-MM-DD format (Gregorian)")
    summary: str = Field(..., description="200-500 word summary for search preview")
    tags: list[str] = Field(default_factory=list, description="Subject classifications (Persian)")
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Search relevance score (0.0-1.0)"
    )


class FullDocument(DocSummary):
    """Complete document with full content for detailed reading.

    Used as the return type for get_document().
    Extends DocSummary with the full text content for answering user queries.

    Additional Attributes (beyond DocSummary):
        full_content: Complete document text (may be very long, 10KB-1MB+)
        relations_count: Number of related documents (for context about the document's connectivity)
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "doc_id": 12345,
                "title": "قانون بیمه اجتماعی",
                "doc_type": "law",
                "date": "2000-01-01",
                "summary": "این قانون در مورد بیمه اجتماعی ...",
                "tags": ["بیمه", "کار", "اجتماعی"],
                "relevance_score": 1.0,
                "full_content": "فصل اول: تعاریف و مقررات عمومی ...",
                "relations_count": 42,
            }
        }
    )

    full_content: str = Field(..., description="Complete document text")
    relations_count: int = Field(
        default=0, ge=0, description="Number of related documents in the graph"
    )
