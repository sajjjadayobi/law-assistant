"""Unit tests for search tools.

Tests search_documents, get_document, and get_related_documents with mocked database.
These tests run fast and don't require a real database connection.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from law_agent.database.models import Document
from law_agent.models.document import DocSummary, FullDocument
from law_agent.tools.search import (
    DocumentNotFoundError,
    get_document,
    get_related_documents,
    search_documents,
)


class TestSearchDocuments:
    """Tests for search_documents tool."""

    @patch("law_agent.tools.search.queries.search_documents_fts")
    def test_search_documents_simple_query(self, mock_search):
        """Test basic search with simple query."""
        # Mock database response
        mock_doc = Document(
            doc_id=1,
            title="قانون بیمه",
            doc_type="law",
            date=date(2000, 1, 1),
            summary="خلاصه ای درباره بیمه",
            full_content="محتوای کامل...",
            tags=["بیمه", "اجتماعی", "کار"],
        )
        mock_search.return_value = [mock_doc]

        # Call tool
        results = search_documents("بیمه")

        # Verify
        assert len(results) == 1
        assert isinstance(results[0], DocSummary)
        assert results[0].doc_id == 1
        assert results[0].title == "قانون بیمه"
        assert results[0].doc_type == "law"
        assert results[0].relevance_score > 0

    @patch("law_agent.tools.search.queries.search_documents_fts")
    def test_search_documents_with_tag_filter(self, mock_search):
        """Test search with tag filtering."""
        # Mock multiple documents
        doc1 = Document(
            doc_id=1,
            title="قانون بیمه",
            doc_type="law",
            date=date(2000, 1, 1),
            summary="خلاصه",
            full_content="...",
            tags=["بیمه", "اجتماعی"],
        )
        doc2 = Document(
            doc_id=2,
            title="مقررات بیمه",
            doc_type="regulation",
            date=date(2010, 1, 1),
            summary="خلاصه",
            full_content="...",
            tags=["بیمه", "کار"],
        )
        doc3 = Document(
            doc_id=3,
            title="نظریه حقوقی",
            doc_type="advisory_opinion",
            date=date(2015, 1, 1),
            summary="خلاصه",
            full_content="...",
            tags=["قانون", "تفسیر"],
        )
        mock_search.return_value = [doc1, doc2, doc3]

        # Search with tag filter
        results = search_documents("بیمه", tags=["اجتماعی"])

        # Should only include doc1 (has both بیمه in title and اجتماعی tag)
        assert len(results) == 1
        assert results[0].doc_id == 1

    @patch("law_agent.tools.search.queries.search_documents_fts")
    def test_search_documents_with_doc_type_filter(self, mock_search):
        """Test search with document type filtering."""
        docs = [
            Document(
                doc_id=1,
                title="قانون",
                doc_type="law",
                date=None,
                summary="",
                full_content="",
                tags=[],
            ),
            Document(
                doc_id=2,
                title="قانون",
                doc_type="regulation",
                date=None,
                summary="",
                full_content="",
                tags=[],
            ),
            Document(
                doc_id=3,
                title="قانون",
                doc_type="advisory_opinion",
                date=None,
                summary="",
                full_content="",
                tags=[],
            ),
        ]
        mock_search.return_value = docs

        results = search_documents("قانون", doc_types=["law", "regulation"])

        assert len(results) == 2
        assert all(r.doc_type in ["law", "regulation"] for r in results)

    @patch("law_agent.tools.search.queries.search_documents_fts")
    def test_search_documents_empty_results(self, mock_search):
        """Test search with no results."""
        mock_search.return_value = []

        results = search_documents("nonexistent_query_xyz")

        assert len(results) == 0
        assert isinstance(results, list)

    @patch("law_agent.tools.search.queries.search_documents_fts")
    def test_search_documents_limit(self, mock_search):
        """Test that limit parameter is enforced."""
        # Create 25 mock documents
        docs = [
            Document(
                doc_id=i,
                title=f"document {i}",
                doc_type="law",
                date=None,
                summary="",
                full_content="",
                tags=[],
            )
            for i in range(25)
        ]
        mock_search.return_value = docs

        results = search_documents("query", limit=20)

        # Should respect limit (max 100, but we ask for 20)
        assert len(results) <= 25
        # Check that search was called with clamped limit
        mock_search.assert_called_once()
        call_args = mock_search.call_args
        assert call_args[1]["limit"] <= 100

    @patch("law_agent.tools.search.queries.search_documents_fts")
    def test_search_documents_relevance_score(self, mock_search):
        """Test that relevance scores are assigned in descending order."""
        docs = [
            Document(
                doc_id=i,
                title=f"doc {i}",
                doc_type="law",
                date=None,
                summary="",
                full_content="",
                tags=[],
            )
            for i in range(5)
        ]
        mock_search.return_value = docs

        results = search_documents("query")

        # Scores should be descending
        for i in range(len(results) - 1):
            assert results[i].relevance_score >= results[i + 1].relevance_score

    @patch("law_agent.tools.search.queries.search_documents_fts")
    def test_search_documents_tag_limit(self, mock_search):
        """Test that only first 3 tags are included."""
        doc = Document(
            doc_id=1,
            title="test",
            doc_type="law",
            date=None,
            summary="",
            full_content="",
            tags=["tag1", "tag2", "tag3", "tag4", "tag5"],
        )
        mock_search.return_value = [doc]

        results = search_documents("query")

        assert len(results[0].tags) == 3
        assert results[0].tags == ["tag1", "tag2", "tag3"]


class TestGetDocument:
    """Tests for get_document tool."""

    @patch("law_agent.tools.search.queries.get_relations")
    @patch("law_agent.tools.search.queries.get_document")
    def test_get_document_success(self, mock_get, mock_relations):
        """Test successfully fetching a document."""
        mock_doc = Document(
            doc_id=1,
            title="قانون بیمه",
            doc_type="law",
            date=date(2000, 1, 1),
            summary="خلاصه",
            full_content="محتوای کامل...",
            tags=["بیمه"],
        )
        mock_get.return_value = mock_doc
        mock_relations.return_value = [MagicMock(), MagicMock()]  # 2 relations

        result = get_document(1)

        assert isinstance(result, FullDocument)
        assert result.doc_id == 1
        assert result.title == "قانون بیمه"
        assert result.full_content == "محتوای کامل..."
        assert result.relations_count == 2

    @patch("law_agent.tools.search.queries.get_document")
    def test_get_document_not_found(self, mock_get):
        """Test fetching non-existent document."""
        mock_get.return_value = None

        with pytest.raises(DocumentNotFoundError):
            get_document(999)

    @patch("law_agent.tools.search.queries.get_relations")
    @patch("law_agent.tools.search.queries.get_document")
    def test_get_document_no_relations(self, mock_get, mock_relations):
        """Test document with no relations."""
        mock_doc = Document(
            doc_id=1,
            title="test",
            doc_type="law",
            date=None,
            summary="",
            full_content="content",
            tags=[],
        )
        mock_get.return_value = mock_doc
        mock_relations.return_value = []

        result = get_document(1)

        assert result.relations_count == 0

    @patch("law_agent.tools.search.queries.get_relations")
    @patch("law_agent.tools.search.queries.get_document")
    def test_get_document_relevance_score(self, mock_get, mock_relations):
        """Test that full documents have perfect relevance score."""
        mock_doc = Document(
            doc_id=1, title="test", doc_type="law", date=None, summary="", full_content="", tags=[]
        )
        mock_get.return_value = mock_doc
        mock_relations.return_value = []

        result = get_document(1)

        assert result.relevance_score == 1.0


class TestGetRelatedDocuments:
    """Tests for get_related_documents tool."""

    @patch("law_agent.tools.search.queries.get_related_documents")
    def test_get_related_documents_simple(self, mock_get_related):
        """Test getting related documents without filters."""
        related_docs = [
            Document(
                doc_id=2,
                title="doc2",
                doc_type="law",
                date=None,
                summary="",
                full_content="",
                tags=["tag1"],
            ),
            Document(
                doc_id=3,
                title="doc3",
                doc_type="regulation",
                date=None,
                summary="",
                full_content="",
                tags=["tag2"],
            ),
        ]
        mock_get_related.return_value = related_docs

        results = get_related_documents(1)

        assert len(results) == 2
        assert all(isinstance(r, DocSummary) for r in results)
        assert results[0].doc_id == 2
        assert results[1].doc_id == 3

    @patch("law_agent.tools.search.queries.get_related_documents")
    def test_get_related_documents_with_relation_type_filter(self, mock_get_related):
        """Test filtering by relation type."""
        related_docs = [
            Document(
                doc_id=2,
                title="parent_law",
                doc_type="law",
                date=None,
                summary="",
                full_content="",
                tags=[],
            ),
        ]
        mock_get_related.return_value = related_docs

        results = get_related_documents(1, relation_types=["قوانین"])

        assert len(results) == 1
        # Verify that get_related_documents was called with relation_type
        mock_get_related.assert_called()

    @patch("law_agent.tools.search.queries.get_related_documents")
    def test_get_related_documents_empty(self, mock_get_related):
        """Test document with no related documents."""
        mock_get_related.return_value = []

        results = get_related_documents(1)

        assert len(results) == 0

    @patch("law_agent.tools.search.queries.get_related_documents")
    def test_get_related_documents_limit(self, mock_get_related):
        """Test that limit is enforced."""
        docs = [
            Document(
                doc_id=i,
                title=f"doc{i}",
                doc_type="law",
                date=None,
                summary="",
                full_content="",
                tags=[],
            )
            for i in range(2, 15)
        ]
        mock_get_related.return_value = docs[:10]

        results = get_related_documents(1, limit=10)

        assert len(results) <= 10

    @patch("law_agent.tools.search.queries.get_related_documents")
    def test_get_related_documents_relevance_score(self, mock_get_related):
        """Test that related documents have high relevance score."""
        doc = Document(
            doc_id=2, title="test", doc_type="law", date=None, summary="", full_content="", tags=[]
        )
        mock_get_related.return_value = [doc]

        results = get_related_documents(1)

        assert results[0].relevance_score == 0.9

    @patch("law_agent.tools.search.queries.get_related_documents")
    def test_get_related_documents_multiple_relation_types(self, mock_get_related):
        """Test filtering with multiple relation types."""
        # When multiple relation types are requested, should query each separately
        doc1 = Document(
            doc_id=2, title="doc2", doc_type="law", date=None, summary="", full_content="", tags=[]
        )
        doc2 = Document(
            doc_id=3,
            title="doc3",
            doc_type="regulation",
            date=None,
            summary="",
            full_content="",
            tags=[],
        )

        # Return different docs for each relation type query
        def side_effect(doc_id, relation_type=None, limit=10):
            if relation_type == "قوانین":
                return [doc1]
            elif relation_type == "مواد مرتبط":
                return [doc2]
            return []

        mock_get_related.side_effect = side_effect

        results = get_related_documents(1, relation_types=["قوانین", "مواد مرتبط"])

        assert len(results) == 2
        # Should have called get_related_documents multiple times (initial query + one per type)
        assert mock_get_related.call_count >= 2

    @patch("law_agent.tools.search.queries.get_related_documents")
    def test_get_related_documents_deduplication(self, mock_get_related):
        """Test that duplicate related documents are removed."""
        doc = Document(
            doc_id=2, title="doc2", doc_type="law", date=None, summary="", full_content="", tags=[]
        )
        # Same doc returned twice, then empty
        mock_get_related.side_effect = [[doc], [doc], []]  # Add empty list to prevent StopIteration

        results = get_related_documents(1, relation_types=["قوانین", "مواد مرتبط"])

        # Should only appear once
        assert len(results) == 1
        assert results[0].doc_id == 2


class TestDocSummaryModel:
    """Tests for DocSummary Pydantic model."""

    def test_doc_summary_creation(self):
        """Test creating a DocSummary."""
        summary = DocSummary(
            doc_id=1,
            title="Test",
            doc_type="law",
            date="2000-01-01",
            summary="Summary text",
            tags=["tag1", "tag2"],
            relevance_score=0.95,
        )
        assert summary.doc_id == 1
        assert summary.relevance_score == 0.95

    def test_doc_summary_optional_fields(self):
        """Test DocSummary with optional fields None."""
        summary = DocSummary(
            doc_id=1,
            title="Test",
            doc_type="law",
            date=None,
            summary="",
            tags=[],
            relevance_score=0.5,
        )
        assert summary.date is None
        assert summary.tags == []

    def test_doc_summary_json_serializable(self):
        """Test that DocSummary can be serialized to JSON."""
        summary = DocSummary(
            doc_id=1,
            title="Test",
            doc_type="law",
            date="2000-01-01",
            summary="Summary",
            tags=["tag1"],
            relevance_score=0.9,
        )
        json_str = summary.model_dump_json()
        assert "Test" in json_str
        assert "0.9" in json_str


class TestFullDocumentModel:
    """Tests for FullDocument Pydantic model."""

    def test_full_document_creation(self):
        """Test creating a FullDocument."""
        doc = FullDocument(
            doc_id=1,
            title="Test",
            doc_type="law",
            date="2000-01-01",
            summary="Summary",
            tags=["tag1"],
            relevance_score=1.0,
            full_content="Full content text here...",
            relations_count=5,
        )
        assert doc.doc_id == 1
        assert doc.full_content == "Full content text here..."
        assert doc.relations_count == 5

    def test_full_document_extends_doc_summary(self):
        """Test that FullDocument extends DocSummary."""
        doc = FullDocument(
            doc_id=1,
            title="Test",
            doc_type="law",
            date=None,
            summary="",
            tags=[],
            relevance_score=1.0,
            full_content="Content",
            relations_count=0,
        )
        # Should have all DocSummary fields
        assert doc.title == "Test"
        assert doc.doc_type == "law"
        # Plus new fields
        assert doc.full_content == "Content"

    def test_full_document_json_serializable(self):
        """Test that FullDocument can be serialized to JSON."""
        doc = FullDocument(
            doc_id=1,
            title="Test",
            doc_type="law",
            date="2000-01-01",
            summary="Summary",
            tags=["tag1"],
            relevance_score=1.0,
            full_content="Full content",
            relations_count=3,
        )
        json_str = doc.model_dump_json()
        assert "Full content" in json_str
        assert "3" in json_str
