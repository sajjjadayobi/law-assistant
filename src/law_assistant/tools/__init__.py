"""Agent tools for searching and retrieving legal documents.

This module provides three core tools for the agent:
1. search_documents - Full-text search on document summaries
2. get_document - Fetch complete document by ID
3. get_related_documents - Follow citation relationships

These tools are designed to be used by PydanticAI agent for legal document retrieval.
"""

from law_assistant.tools.search import (
    DocumentNotFoundError,
    get_document,
    get_related_documents,
    search_documents,
)

__all__ = [
    "search_documents",
    "get_document",
    "get_related_documents",
    "DocumentNotFoundError",
]
