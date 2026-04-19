"""Database layer for Law Agent.

This package provides:
- Connection management (get_session, check_connection)
- ORM models (Document, Relation)
- Query utilities (get_document, get_related_documents, search_documents_fts)

Usage:
    from law_agent.database import get_session, get_document
    from law_agent.database.models import Document, Relation

    # Use a session
    with get_session() as session:
        documents = session.query(Document).all()

    # Use query utilities
    doc = get_document(12345)
    related = get_related_documents(12345)
"""

from law_agent.database.connection import (
    check_connection,
    dispose_engine,
    get_connection,
    get_session,
)
from law_agent.database.models import Base, Document, Relation
from law_agent.database.queries import (
    get_document,
    get_document_count,
    get_documents_by_type,
    get_documents_with_tags,
    get_related_documents,
    get_relations,
    search_documents_fts,
)

__all__ = [
    # Connection management
    "get_session",
    "get_connection",
    "check_connection",
    "dispose_engine",
    # Models
    "Base",
    "Document",
    "Relation",
    # Query utilities
    "get_document",
    "get_relations",
    "get_related_documents",
    "search_documents_fts",
    "get_documents_by_type",
    "get_document_count",
    "get_documents_with_tags",
]
