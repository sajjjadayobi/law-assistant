"""Search tools for the Law Agent.

This module implements three core search tools that form the foundation of the agent's
legal document retrieval system:

1. search_documents(query, tags=None, doc_types=None, limit=20)
   - Full-text search on document summaries using PostgreSQL FTS
   - Returns list of DocSummary with relevance scores

2. get_document(doc_id)
   - Fetch complete document content by ID
   - Returns FullDocument with all metadata and full text

3. get_related_documents(doc_id, relation_types=None, limit=10)
   - Follow citation relationships in the legal document graph
   - Single-hop only (agent decides if more hops needed)
   - Returns list of DocSummary for related documents

All tools use the existing database query functions from database/queries.py and wrap
results in Pydantic models for type safety and JSON serialization.
"""

import structlog
from hazm import Normalizer

from law_agent.config.settings import get_settings
from law_agent.database import queries
from law_agent.models.document import DocSummary, FullDocument

logger = structlog.get_logger(__name__)

# Persian text normalizer (normalize ك→ک, ي→ی, etc.)
_normalizer = Normalizer()

# Load settings at module level (cached singleton)
_settings = get_settings()


def search_documents(
    query: str,
    tags: list[str] | None = None,
    doc_types: list[str] | None = None,
    limit: int = 20,
) -> list[DocSummary]:
    """Search for documents using full-text search.

    Performs PostgreSQL full-text search on document summaries (title + summary).
    Optionally filters by subject tags or document types.
    Results are ranked by relevance score.

    Args:
        query: Search query in Persian or English
               Will be normalized for Persian text (ك→ک, ي→ی, etc.)
        tags: Optional list of subject tags to filter by (e.g., ['بیمه', 'کار'])
        doc_types: Optional list of document types to filter by
                   (law, regulation, advisory_opinion, court_ruling, unified_precedent)
        limit: Maximum number of results to return (default 20, max 100)

    Returns:
        List of DocSummary objects sorted by relevance score (highest first)
        Empty list if no documents match the query

    Raises:
        Exception: If database query fails (caught and logged)

    Examples:
        # Simple search
        results = search_documents("بیمه")

        # Search with filters
        results = search_documents(
            "بیمه",
            tags=["اجتماعی"],
            doc_types=["law", "regulation"],
            limit=10
        )

        # Check relevance before fetching full document
        for summary in results:
            if summary.relevance_score > 0.8:
                doc = get_document(summary.doc_id)
                # Use doc.full_content for answering
    """
    try:
        # Normalize Persian input
        normalized_query = _normalizer.normalize(query)

        logger.info(
            "search_documents_called",
            query=query,
            normalized_query=normalized_query,
            tags=tags,
            doc_types=doc_types,
            limit=limit,
        )

        # Ensure limit is reasonable (respect hard limit from config)
        limit = min(limit, _settings.search.hard_limit)

        # Get raw documents from FTS search
        documents = queries.search_documents_fts(normalized_query, limit=limit)

        # Convert to DocSummary with relevance scores and apply filters
        summaries: list[DocSummary] = []
        for doc in documents:
            # Skip if tags filter specified and no match
            if tags and not any(tag in (doc.tags or []) for tag in tags):
                continue

            # Skip if doc_types filter specified and no match
            if doc_types and doc.doc_type not in doc_types:
                continue

            # Create DocSummary (calculate relevance score from result position)
            # PostgreSQL FTS returns results already ranked, so we use position as score
            # Decrement by configured step value per result position
            relevance_score = 1.0 - (len(summaries) * _settings.search.relevance_score_step)
            relevance_score = max(0.0, min(1.0, relevance_score))  # Clamp to 0-1

            date_str = doc.date.isoformat() if doc.date else None
            summary = DocSummary(
                doc_id=int(doc.doc_id),
                title=str(doc.title),
                doc_type=str(doc.doc_type),
                date=date_str,
                summary=str(doc.summary or ""),
                tags=list(doc.tags[: _settings.search.max_tags_per_result]) if doc.tags else [],
                relevance_score=relevance_score,
            )
            summaries.append(summary)

        logger.info(
            "search_documents_success",
            query=query,
            result_count=len(summaries),
            tags_filter=bool(tags),
            doc_types_filter=bool(doc_types),
        )
        return summaries

    except Exception as e:
        logger.exception(
            "search_documents_error",
            query=query,
            tags=tags,
            doc_types=doc_types,
            error=str(e),
        )
        raise


def get_document(doc_id: int) -> FullDocument:
    """Fetch complete document by ID.

    Retrieves the full content and all metadata for a specific document.
    Should only be called after identifying relevant documents via search_documents()
    or get_related_documents().

    Args:
        doc_id: Document ID to fetch

    Returns:
        FullDocument object with all metadata, full content, and relations count

    Raises:
        DocumentNotFound: If document with given ID does not exist
        Exception: If database query fails (caught and logged)

    Examples:
        # Get document by ID
        doc = get_document(12345)
        if doc:
            print(f"Title: {doc.title}")
            print(f"Content: {doc.full_content[:200]}...")
            print(f"Related documents: {doc.relations_count}")

        # Use for answering user query
        summary = search_results[0]
        full_doc = get_document(summary.doc_id)
        # Use full_doc.full_content to craft answer
    """
    try:
        logger.info("get_document_called", doc_id=doc_id)

        # Fetch document from database
        doc = queries.get_document(doc_id)

        if doc is None:
            logger.warning("get_document_not_found", doc_id=doc_id)
            raise DocumentNotFoundError(f"Document with ID {doc_id} not found")

        # Count related documents (prefetch using configured limit)
        relations = queries.get_relations(doc_id, limit=_settings.search.relations_prefetch_limit)
        relations_count = len(relations)

        # Create FullDocument
        date_str = doc.date.isoformat() if doc.date else None
        full_doc = FullDocument(
            doc_id=int(doc.doc_id),
            title=str(doc.title),
            doc_type=str(doc.doc_type),
            date=date_str,
            summary=str(doc.summary or ""),
            tags=list(doc.tags or []),
            relevance_score=1.0,  # Full document has perfect relevance
            full_content=str(doc.full_content or ""),
            relations_count=relations_count,
        )

        logger.info(
            "get_document_success",
            doc_id=doc_id,
            title=doc.title,
            relations_count=relations_count,
        )
        return full_doc

    except DocumentNotFoundError:
        # Re-raise our custom exception
        raise
    except Exception as e:
        logger.exception("get_document_error", doc_id=doc_id, error=str(e))
        raise


def get_related_documents(
    doc_id: int,
    relation_types: list[str] | None = None,
    limit: int = 10,
) -> list[DocSummary]:
    """Get documents related to a specific document via citations/references.

    Follows the legal document relationship graph (DAG) to find documents cited by
    or related to the given document. Returns single-hop relations only - the agent
    decides if additional hops are needed.

    Useful for:
    - Finding parent laws cited by a ruling or regulation
    - Finding related articles/regulations about the same topic
    - Exploring the legal context around a document

    Args:
        doc_id: Source document ID
        relation_types: Optional list of relation types to filter by
                        (e.g., ['قوانین'] for laws cited, ['مواد مرتبط'] for related articles)
                        If None, returns all relations
        limit: Maximum related documents to return (default 10, max 100)

    Returns:
        List of DocSummary objects for related documents
        Empty list if document has no relations or no matches after filtering

    Raises:
        Exception: If database query fails (caught and logged)

    Examples:
        # Get all documents related to a ruling
        related = get_related_documents(67890)

        # Get only parent laws cited by a ruling
        laws = get_related_documents(67890, relation_types=['قوانین'], limit=5)

        # Get related articles (lateral connections)
        articles = get_related_documents(12345, relation_types=['مواد مرتبط'])

        # Multi-hop example (agent logic):
        doc1 = get_document(query_id)
        for rel_summary in get_related_documents(query_id):
            doc2 = get_document(rel_summary.doc_id)
            for rel_summary2 in get_related_documents(doc2.doc_id):
                # Now we have docs at 2 hops away
                pass
    """
    try:
        limit = min(limit, _settings.search.hard_limit)  # Ensure limit is reasonable

        logger.info(
            "get_related_documents_called",
            doc_id=doc_id,
            relation_types=relation_types,
            limit=limit,
        )

        # Get related documents using existing query
        related_docs = queries.get_related_documents(
            doc_id=doc_id,
            relation_type=(
                relation_types[0] if relation_types and len(relation_types) == 1 else None
            ),
            limit=limit,
        )

        # If multiple relation types specified, filter in Python
        if relation_types and len(relation_types) > 1:
            # For multiple types, need to query each type separately
            all_related = []
            for rel_type in relation_types:
                docs = queries.get_related_documents(
                    doc_id=doc_id,
                    relation_type=rel_type,
                    limit=limit,
                )
                all_related.extend(docs)

            # Remove duplicates while preserving order
            seen = set()
            related_docs = []
            for doc in all_related:
                if doc.doc_id not in seen:
                    seen.add(doc.doc_id)
                    related_docs.append(doc)
                    if len(related_docs) >= limit:
                        break

        # Convert to DocSummary list
        summaries = [
            DocSummary(
                doc_id=int(doc.doc_id),
                title=str(doc.title),
                doc_type=str(doc.doc_type),
                date=doc.date.isoformat() if doc.date else None,
                summary=str(doc.summary or ""),
                tags=list(doc.tags[: _settings.search.max_tags_per_result]) if doc.tags else [],
                relevance_score=_settings.search.related_docs_relevance_score,
            )
            for doc in related_docs
        ]

        logger.info(
            "get_related_documents_success",
            doc_id=doc_id,
            relation_types=relation_types,
            result_count=len(summaries),
        )
        return summaries

    except Exception as e:
        logger.exception(
            "get_related_documents_error",
            doc_id=doc_id,
            relation_types=relation_types,
            error=str(e),
        )
        raise


class DocumentNotFoundError(Exception):
    """Exception raised when a document is not found in the database."""

    pass
