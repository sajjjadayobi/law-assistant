"""Reusable database query utilities.

This module provides high-level query functions for common database operations:
- get_document(doc_id): Fetch single document
- get_relations(doc_id, relation_type): Fetch relations
- get_related_documents(doc_id): Traverse document graph
- search_documents_fts(query, limit): Full-text search

These functions use the ORM models and are the primary way to query the database.
They wrap session management and handle errors gracefully.

Usage:
    from law_agent.database import get_document, get_related_documents

    document = get_document(123)
    if document:
        related = get_related_documents(document.doc_id)
        for rel_doc in related:
            print(rel_doc.title)
"""

import structlog
from sqlalchemy import text

from law_agent.database.connection import get_session
from law_agent.database.models import Document, Relation

logger = structlog.get_logger(__name__)


def get_document(doc_id: int) -> Document | None:
    """Fetch a single document by ID.

    Args:
        doc_id: Document ID to fetch

    Returns:
        Document object if found, None otherwise

    Example:
        doc = get_document(12345)
        if doc:
            print(f"Title: {doc.title}")
            print(f"Content: {doc.full_content[:100]}...")
    """
    try:
        with get_session() as session:
            document = session.query(Document).filter(Document.doc_id == doc_id).first()

            logger.info("get_document", doc_id=doc_id, found=document is not None)
            return document

    except Exception as e:
        logger.exception("get_document_error", doc_id=doc_id, error=str(e))
        raise


def get_relations(
    doc_id: int, relation_type: str | None = None, limit: int = 100
) -> list[Relation]:
    """Get relations originating from a document.

    Args:
        doc_id: Source document ID
        relation_type: Filter by relation type (e.g., 'قوانین', 'مواد مرتبط')
                      If None, returns all relations
        limit: Maximum number of relations to return

    Returns:
        List of Relation objects

    Example:
        # Get all relations from document
        relations = get_relations(123)

        # Get only law citations
        laws = get_relations(123, relation_type='قوانین', limit=10)
    """
    try:
        with get_session() as session:
            query = session.query(Relation).filter(Relation.src_doc_id == doc_id)

            if relation_type is not None:
                query = query.filter(Relation.relation_type == relation_type)

            relations = query.limit(limit).all()

            logger.info(
                "get_relations",
                src_doc_id=doc_id,
                relation_type=relation_type,
                count=len(relations),
            )
            return relations

    except Exception as e:
        logger.exception(
            "get_relations_error",
            doc_id=doc_id,
            relation_type=relation_type,
            error=str(e),
        )
        raise


def get_related_documents(
    doc_id: int, relation_type: str | None = None, limit: int = 10
) -> list[Document]:
    """Get documents related to a given document by following relations.

    Convenience function that combines get_relations() with document fetching.

    Args:
        doc_id: Document ID
        relation_type: Filter by relation type
        limit: Maximum related documents to return

    Returns:
        List of related Document objects

    Example:
        # Get documents cited by a ruling
        laws = get_related_documents(67890, relation_type='قوانین')

        # Get all related documents
        related = get_related_documents(67890)
    """
    try:
        with get_session() as session:
            # Get relations from this document
            query = session.query(Relation).filter(Relation.src_doc_id == doc_id)

            if relation_type is not None:
                query = query.filter(Relation.relation_type == relation_type)

            relations = query.limit(limit).all()

            # Fetch related documents
            related_docs = []
            for relation in relations:
                doc = session.query(Document).filter(Document.doc_id == relation.dst_doc_id).first()
                if doc:
                    related_docs.append(doc)

            logger.info(
                "get_related_documents",
                doc_id=doc_id,
                relation_type=relation_type,
                count=len(related_docs),
            )
            return related_docs

    except Exception as e:
        logger.exception(
            "get_related_documents_error",
            doc_id=doc_id,
            relation_type=relation_type,
            error=str(e),
        )
        raise


def search_documents_fts(query_text: str, limit: int = 20) -> list[Document]:
    """Full-text search in document summaries using PostgreSQL.

    Uses PostgreSQL's native full-text search (tsvector/tsquery) for efficient searching.
    Searches the search_vector column which indexes both title and summary.

    Args:
        query_text: Search query in Persian or English
        limit: Maximum results to return (default 20)

    Returns:
        List of Document objects ranked by relevance

    Example:
        results = search_documents_fts('بیمه', limit=10)
        for doc in results:
            print(f"{doc.title} (type: {doc.doc_type})")

    Note:
        For better Persian text handling, consider normalizing the query text
        using Hazm (Persian text processing library) before search.
    """
    try:
        with get_session() as session:
            # PostgreSQL full-text search query
            # Note: This uses raw SQL because SQLAlchemy's FTS support is limited
            search_query = text("""
                SELECT doc_id, title, doc_type, date, summary, full_content, tags, search_vector,
                       ts_rank(search_vector, query) as rank
                FROM documents,
                     plainto_tsquery('simple', :query) query
                WHERE search_vector @@ query
                ORDER BY rank DESC
                LIMIT :limit
                """)

            result = session.execute(
                search_query,
                {"query": query_text, "limit": limit},
            )

            # Convert raw results back to Document objects
            documents = []
            for row in result:
                doc = Document(
                    doc_id=row[0],
                    title=row[1],
                    doc_type=row[2],
                    date=row[3],
                    summary=row[4],
                    full_content=row[5],
                    tags=row[6],
                    search_vector=row[7],
                )
                documents.append(doc)

            logger.info(
                "search_documents_fts",
                query=query_text,
                result_count=len(documents),
                limit=limit,
            )
            return documents

    except Exception as e:
        logger.exception("search_documents_fts_error", query=query_text, error=str(e))
        raise


def get_documents_by_type(doc_type: str, limit: int = 100) -> list[Document]:
    """Get all documents of a specific type.

    Args:
        doc_type: Document type (law, regulation, advisory_opinion, court_ruling, unified_precedent)
        limit: Maximum documents to return

    Returns:
        List of Document objects of the specified type

    Example:
        # Get all laws
        laws = get_documents_by_type('law')

        # Get first 10 court rulings
        rulings = get_documents_by_type('court_ruling', limit=10)
    """
    try:
        with get_session() as session:
            documents = (
                session.query(Document).filter(Document.doc_type == doc_type).limit(limit).all()
            )

            logger.info(
                "get_documents_by_type",
                doc_type=doc_type,
                count=len(documents),
            )
            return documents

    except Exception as e:
        logger.exception("get_documents_by_type_error", doc_type=doc_type, error=str(e))
        raise


def get_document_count() -> int:
    """Get total count of documents in the database.

    Returns:
        Total number of documents

    Example:
        total = get_document_count()
        print(f"Database contains {total} legal documents")
    """
    try:
        with get_session() as session:
            count = session.query(Document).count()
            logger.info("get_document_count", count=count)
            return count

    except Exception as e:
        logger.exception("get_document_count_error", error=str(e))
        raise


def get_documents_with_tags(tags: list[str], limit: int = 50) -> list[Document]:
    """Get documents that have any of the specified tags.

    Args:
        tags: List of tag names to search for
        limit: Maximum documents to return

    Returns:
        List of Document objects that have at least one of the specified tags

    Example:
        # Find documents about law or regulation
        docs = get_documents_with_tags(['اساسی', 'اداری'], limit=20)
    """
    try:
        with get_session() as session:
            # Use PostgreSQL array contains operator
            # This is a simple implementation - could be optimized with proper indexing
            documents = []

            for tag in tags:
                docs = (
                    session.query(Document)
                    .filter(Document.tags.astext.contains(tag))
                    .limit(limit)
                    .all()
                )
                documents.extend(docs)

            # Remove duplicates while preserving order
            seen = set()
            unique_docs = []
            for doc in documents:
                if doc.doc_id not in seen:
                    seen.add(doc.doc_id)
                    unique_docs.append(doc)

            logger.info("get_documents_with_tags", tags=tags, count=len(unique_docs))
            return unique_docs

    except Exception as e:
        logger.exception("get_documents_with_tags_error", tags=tags, error=str(e))
        raise
