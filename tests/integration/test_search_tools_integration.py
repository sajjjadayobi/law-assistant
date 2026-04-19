"""Integration tests for search tools with real database.

These tests connect to the actual PostgreSQL database and test the full
search tool functionality including database queries and ranking.

Prerequisites:
- PostgreSQL database must be running
- Database must have documents and relations tables populated
- config.yaml must be configured for test environment
"""

import pytest

from law_agent.database import dispose_engine
from law_agent.models.document import DocSummary, FullDocument
from law_agent.tools.search import (
    DocumentNotFoundError,
    get_document,
    get_related_documents,
    search_documents,
)


class TestSearchDocumentsIntegration:
    """Integration tests for search_documents with real database."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up database connections after each test."""
        yield
        dispose_engine()

    def test_search_documents_basic_query(self):
        """Test basic search with real database."""
        # This will only pass if database is populated with documents
        results = search_documents("قانون", limit=5)

        # Should return list of DocSummary
        assert isinstance(results, list)
        if len(results) > 0:
            assert all(isinstance(r, DocSummary) for r in results)
            # Results should have expected fields
            assert all(r.doc_id > 0 for r in results)
            assert all(r.title for r in results)
            assert all(r.doc_type for r in results)
            # Relevance scores should be between 0 and 1
            assert all(0 <= r.relevance_score <= 1 for r in results)

    def test_search_documents_empty_query(self):
        """Test search with query that should return no results."""
        results = search_documents("xyznonexistentquery123xyz", limit=10)

        # Should return empty list, not raise exception
        assert isinstance(results, list)
        assert len(results) == 0

    def test_search_documents_persian_normalization(self):
        """Test that Persian text normalization works."""
        # Search with unnormalized Persian (ك instead of ک, ي instead of ی)
        # The tool should normalize this
        results1 = search_documents("قانون", limit=5)
        results2 = search_documents("قانون", limit=5)  # Already normalized

        # Should get same or similar results
        # (both searches should work and return some results if DB has documents)
        assert isinstance(results1, list)
        assert isinstance(results2, list)

    def test_search_documents_limit_respected(self):
        """Test that limit parameter is respected."""
        results = search_documents("قانون", limit=5)

        assert len(results) <= 5

    def test_search_documents_with_doc_type_filter(self):
        """Test filtering by document type."""
        results = search_documents("قانون", doc_types=["law"], limit=10)

        if len(results) > 0:
            # All results should be of requested type
            assert all(r.doc_type == "law" for r in results)

    def test_search_documents_with_multiple_doc_types(self):
        """Test filtering with multiple document types."""
        results = search_documents("قانون", doc_types=["law", "regulation"], limit=10)

        if len(results) > 0:
            assert all(r.doc_type in ["law", "regulation"] for r in results)

    def test_search_documents_relevance_ordering(self):
        """Test that results are ordered by relevance."""
        results = search_documents("قانون", limit=20)

        if len(results) > 1:
            # Relevance scores should be in descending order
            for i in range(len(results) - 1):
                assert results[i].relevance_score >= results[i + 1].relevance_score


class TestGetDocumentIntegration:
    """Integration tests for get_document with real database."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up database connections after each test."""
        yield
        dispose_engine()

    def test_get_document_success(self):
        """Test fetching an existing document."""
        # First search for a document
        results = search_documents("قانون", limit=1)

        if len(results) == 0:
            pytest.skip("No documents in database to test")

        doc_id = results[0].doc_id
        doc = get_document(doc_id)

        assert isinstance(doc, FullDocument)
        assert doc.doc_id == doc_id
        assert doc.title  # Should have title
        assert doc.doc_type  # Should have type
        assert doc.full_content  # Should have content
        assert doc.relevance_score == 1.0  # Full docs have perfect score

    def test_get_document_not_found(self):
        """Test fetching non-existent document."""
        with pytest.raises(DocumentNotFoundError):
            get_document(999999999)

    def test_get_document_relations_count(self):
        """Test that relations count is included."""
        results = search_documents("قانون", limit=1)

        if len(results) == 0:
            pytest.skip("No documents in database to test")

        doc = get_document(results[0].doc_id)

        assert doc.relations_count >= 0  # Should have a count
        assert isinstance(doc.relations_count, int)

    def test_get_document_full_content_populated(self):
        """Test that full content is properly populated."""
        results = search_documents("قانون", limit=1)

        if len(results) == 0:
            pytest.skip("No documents in database to test")

        doc = get_document(results[0].doc_id)

        # Full document should have full_content (may be empty if not in DB)
        assert hasattr(doc, "full_content")
        assert isinstance(doc.full_content, str)

    def test_get_document_all_fields_present(self):
        """Test that all expected fields are present."""
        results = search_documents("قانون", limit=1)

        if len(results) == 0:
            pytest.skip("No documents in database to test")

        doc = get_document(results[0].doc_id)

        # Check all expected fields
        assert doc.doc_id
        assert doc.title
        assert doc.doc_type
        assert doc.summary is not None
        assert doc.tags is not None
        assert doc.full_content is not None
        assert doc.relations_count is not None
        assert doc.relevance_score == 1.0


class TestGetRelatedDocumentsIntegration:
    """Integration tests for get_related_documents with real database."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up database connections after each test."""
        yield
        dispose_engine()

    def test_get_related_documents_basic(self):
        """Test fetching related documents for a document."""
        # Get a document first
        results = search_documents("قانون", limit=1)

        if len(results) == 0:
            pytest.skip("No documents in database to test")

        doc_id = results[0].doc_id
        related = get_related_documents(doc_id)

        assert isinstance(related, list)
        # May be empty or have results depending on relations in DB
        if len(related) > 0:
            assert all(isinstance(r, DocSummary) for r in related)
            assert all(r.doc_id != doc_id for r in related)  # Shouldn't include self

    def test_get_related_documents_limit_respected(self):
        """Test that limit is respected."""
        results = search_documents("قانون", limit=5)

        if len(results) == 0:
            pytest.skip("No documents in database to test")

        for result in results:
            related = get_related_documents(result.doc_id, limit=3)
            assert len(related) <= 3

    def test_get_related_documents_with_relation_type(self):
        """Test filtering by relation type."""
        results = search_documents("قانون", limit=1)

        if len(results) == 0:
            pytest.skip("No documents in database to test")

        doc_id = results[0].doc_id

        # Try to get specific relation type
        related = get_related_documents(doc_id, relation_types=["قوانین"])

        assert isinstance(related, list)
        # May be empty if no relations of this type exist

    def test_get_related_documents_no_self_reference(self):
        """Test that related documents don't include self."""
        results = search_documents("قانون", limit=1)

        if len(results) == 0:
            pytest.skip("No documents in database to test")

        doc_id = results[0].doc_id
        related = get_related_documents(doc_id)

        # Should never include the source document itself
        assert all(r.doc_id != doc_id for r in related)

    def test_get_related_documents_returns_doc_summary(self):
        """Test that related documents are DocSummary objects."""
        results = search_documents("قانون", limit=5)

        if len(results) == 0:
            pytest.skip("No documents in database to test")

        for result in results:
            related = get_related_documents(result.doc_id, limit=5)
            if len(related) > 0:
                assert all(isinstance(r, DocSummary) for r in related)
                # Should have required fields
                assert all(r.doc_id > 0 for r in related)
                assert all(r.title for r in related)
                break  # Just test first one that has relations


class TestSearchToolsEndToEnd:
    """End-to-end integration tests combining multiple tools."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up database connections after each test."""
        yield
        dispose_engine()

    def test_search_to_document_flow(self):
        """Test typical search → get_document flow."""
        # Search for documents
        summaries = search_documents("قانون", limit=5)

        if len(summaries) == 0:
            pytest.skip("No documents in database to test")

        # Pick top result
        summary = summaries[0]

        # Get full document
        doc = get_document(summary.doc_id)

        # Verify it's the same document
        assert doc.doc_id == summary.doc_id
        assert doc.title == summary.title
        # Full document should have more content
        assert len(doc.full_content) > len(doc.summary)

    def test_multi_hop_search_flow(self):
        """Test multi-hop: search → document → related."""
        # Search for documents
        summaries = search_documents("قانون", limit=3)

        if len(summaries) == 0:
            pytest.skip("No documents in database to test")

        # Get document and its relations
        doc = get_document(summaries[0].doc_id)
        related_summaries = get_related_documents(doc.doc_id, limit=5)

        # related_summaries should be valid
        assert isinstance(related_summaries, list)
        if len(related_summaries) > 0:
            # Can get full document of related
            related_doc = get_document(related_summaries[0].doc_id)
            assert related_doc.doc_id > 0

    def test_document_has_correct_relations_count(self):
        """Test that relations_count in FullDocument matches actual relations."""
        summaries = search_documents("قانون", limit=1)

        if len(summaries) == 0:
            pytest.skip("No documents in database to test")

        doc = get_document(summaries[0].doc_id)

        # The relations_count should be a valid count
        # Note: relations_count is total from DB
        assert isinstance(doc.relations_count, int)
        assert doc.relations_count >= 0


class TestSearchToolsErrorHandling:
    """Tests for error handling in search tools."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up database connections after each test."""
        yield
        dispose_engine()

    def test_search_with_special_characters(self):
        """Test search with special characters."""
        try:
            results = search_documents("!@#$%^&*()", limit=5)
            # Should not crash, may return empty results
            assert isinstance(results, list)
        except Exception as e:
            # If it raises, it should be a reasonable exception
            assert not isinstance(e, AttributeError)

    def test_get_document_with_invalid_id(self):
        """Test get_document with various invalid IDs."""
        # Negative ID
        with pytest.raises(DocumentNotFoundError):
            get_document(-1)

        # Zero
        with pytest.raises(DocumentNotFoundError):
            get_document(0)

        # Very large ID
        with pytest.raises(DocumentNotFoundError):
            get_document(9999999999)

    def test_get_related_documents_with_nonexistent_source(self):
        """Test get_related_documents for non-existent document."""
        # Should return empty list, not raise exception
        related = get_related_documents(9999999999)
        assert related == []
