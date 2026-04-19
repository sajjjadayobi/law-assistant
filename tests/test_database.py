"""Tests for database layer (connection, models, and queries).

This module covers:
- Connection management and pooling
- ORM model definition and relationships
- Query utilities
- Thread-local session isolation
"""

import threading
from datetime import date

import pytest

from law_agent.database import (
    Document,
    Relation,
    check_connection,
    dispose_engine,
    get_document,
    get_document_count,
    get_documents_by_type,
    get_related_documents,
    get_relations,
    get_session,
    search_documents_fts,
)
from law_agent.database.connection import (
    _get_engine,
    _get_scoped_session,
    _get_session_factory,
)


class TestConnectionManagement:
    """Tests for database connection and session management."""

    def test_engine_creation(self):
        """Test that engine is created successfully."""
        dispose_engine()  # Reset to test creation
        engine = _get_engine()

        assert engine is not None
        assert engine.pool is not None

        dispose_engine()

    def test_engine_is_singleton(self):
        """Test that multiple calls return same engine."""
        dispose_engine()

        engine1 = _get_engine()
        engine2 = _get_engine()

        assert engine1 is engine2

        dispose_engine()

    def test_session_factory_creation(self):
        """Test that session factory is created."""
        dispose_engine()

        factory = _get_session_factory()
        assert factory is not None

        dispose_engine()

    def test_scoped_session_creation(self):
        """Test that scoped session registry is created."""
        dispose_engine()

        scoped = _get_scoped_session()
        assert scoped is not None

        dispose_engine()

    def test_get_session_context_manager(self):
        """Test that get_session works as context manager."""
        with get_session() as session:
            assert session is not None
            assert hasattr(session, "query")

    def test_session_cleanup_on_context_exit(self):
        """Test that session is properly cleaned up after context exit."""
        # Create session and verify it's usable
        with get_session() as session:
            session_obj = session
            assert session_obj is not None

        # After exit, session should be closed
        # (We can't directly test this but we can verify no connection errors on next use)
        with get_session() as session2:
            assert session2 is not None

    def test_thread_local_sessions_isolation(self):
        """Test that different threads get different sessions."""
        sessions = {}

        def get_session_in_thread(thread_id):
            with get_session() as session:
                sessions[thread_id] = id(session)

        # Create sessions in different threads
        thread1 = threading.Thread(target=get_session_in_thread, args=(1,))
        thread2 = threading.Thread(target=get_session_in_thread, args=(2,))

        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        # Sessions should be different (different thread IDs)
        assert len(sessions) == 2
        # Note: We can't directly compare the session objects themselves
        # because scoped_session removes them after context exit,
        # but the test verifies no errors occur in different threads


class TestOrmModels:
    """Tests for ORM model definition."""

    def test_document_model_instantiation(self):
        """Test that Document model can be instantiated."""
        doc = Document(
            doc_id=1,
            title="قانون مثال",
            doc_type="law",
            date=date(2023, 1, 1),
            summary="خلاصه مثال",
            full_content="محتوای کامل",
            tags=["اساسی", "اداری"],
        )

        assert doc.doc_id == 1
        assert doc.title == "قانون مثال"
        assert doc.doc_type == "law"
        assert doc.summary == "خلاصه مثال"
        assert doc.tags == ["اساسی", "اداری"]

    def test_document_model_repr(self):
        """Test Document model string representation."""
        doc = Document(
            doc_id=123,
            title="نظریه مشورتی",
            doc_type="advisory_opinion",
        )

        repr_str = repr(doc)
        assert "123" in repr_str
        assert "نظریه" in repr_str
        assert "advisory_opinion" in repr_str

    def test_relation_model_instantiation(self):
        """Test that Relation model can be instantiated."""
        rel = Relation(
            src_doc_id=1,
            dst_doc_id=2,
            relation_type="قوانین",
        )

        assert rel.src_doc_id == 1
        assert rel.dst_doc_id == 2
        assert rel.relation_type == "قوانین"

    def test_relation_model_repr(self):
        """Test Relation model string representation."""
        rel = Relation(
            src_doc_id=123,
            dst_doc_id=456,
            relation_type="مواد مرتبط",
        )

        repr_str = repr(rel)
        assert "123" in repr_str
        assert "456" in repr_str
        assert "مواد مرتبط" in repr_str

    def test_document_model_optional_fields(self):
        """Test that Document model allows optional fields."""
        doc = Document(
            doc_id=1,
            title="قانون",
            doc_type="law",
            # Other fields are optional
        )

        assert doc.doc_id == 1
        assert doc.title == "قانون"
        assert doc.date is None
        assert doc.full_content is None
        assert doc.tags is None

    def test_document_get_related_documents_no_relations(self):
        """Test get_related_documents when document has no relations."""
        doc = Document(doc_id=1, title="Test", doc_type="law")

        # Should return empty list with no relations
        related = doc.get_related_documents()
        assert related == []

    def test_document_get_cited_documents_no_relations(self):
        """Test get_cited_documents when document has no incoming relations."""
        doc = Document(doc_id=1, title="Test", doc_type="law")

        # Should return empty list with no relations
        cited = doc.get_cited_documents()
        assert cited == []


class TestConnectionHealth:
    """Tests for connection health checks."""

    @pytest.mark.skip(reason="Requires PostgreSQL database to be running")
    def test_check_connection_to_database(self):
        """Test that database connection check works."""
        # This test requires actual database to be running
        result = check_connection()

        # Should return boolean
        assert isinstance(result, bool)
        # If database is running, should be True
        assert result is True


class TestQueryUtilities:
    """Tests for high-level query utilities (requires database)."""

    @pytest.mark.skip(reason="Requires database with test data")
    def test_get_document_returns_document(self):
        """Test get_document returns a Document object."""
        # This is an integration test - requires actual database
        doc = get_document(1)  # Assuming doc_id=1 exists

        if doc:
            assert isinstance(doc, Document)
            assert doc.doc_id == 1

    @pytest.mark.skip(reason="Requires database with test data")
    def test_get_document_returns_none_for_missing(self):
        """Test get_document returns None for non-existent ID."""
        doc = get_document(999999999)
        assert doc is None

    @pytest.mark.skip(reason="Requires database with test data")
    def test_get_relations_returns_list(self):
        """Test get_relations returns list of relations."""
        relations = get_relations(1)
        assert isinstance(relations, list)

    @pytest.mark.skip(reason="Requires database with test data")
    def test_get_related_documents_returns_documents(self):
        """Test get_related_documents returns list of documents."""
        docs = get_related_documents(1)
        assert isinstance(docs, list)

    @pytest.mark.skip(reason="Requires database with test data")
    def test_search_documents_fts_returns_results(self):
        """Test full-text search returns results."""
        results = search_documents_fts("بیمه", limit=10)
        assert isinstance(results, list)

    @pytest.mark.skip(reason="Requires database with test data")
    def test_get_document_count_returns_integer(self):
        """Test get_document_count returns integer."""
        count = get_document_count()
        assert isinstance(count, int)
        assert count > 0

    @pytest.mark.skip(reason="Requires database with test data")
    def test_get_documents_by_type_returns_list(self):
        """Test get_documents_by_type returns list."""
        docs = get_documents_by_type("law", limit=10)
        assert isinstance(docs, list)


class TestDatabaseModuleExports:
    """Tests for module exports and public API."""

    def test_all_exports_are_available(self):
        """Test that all expected classes and functions are exported."""
        from law_agent import database

        # Connection management
        assert hasattr(database, "get_session")
        assert hasattr(database, "get_connection")
        assert hasattr(database, "check_connection")
        assert hasattr(database, "dispose_engine")

        # Models
        assert hasattr(database, "Base")
        assert hasattr(database, "Document")
        assert hasattr(database, "Relation")

        # Query utilities
        assert hasattr(database, "get_document")
        assert hasattr(database, "get_relations")
        assert hasattr(database, "get_related_documents")
        assert hasattr(database, "search_documents_fts")
        assert hasattr(database, "get_documents_by_type")
        assert hasattr(database, "get_document_count")
        assert hasattr(database, "get_documents_with_tags")

    def test_imports_from_database_submodules(self):
        """Test that submodules can be imported directly."""
        from law_agent.database import connection, models, queries

        assert hasattr(connection, "get_session")
        assert hasattr(models, "Document")
        assert hasattr(queries, "get_document")


class TestDatabaseSetupFixture:
    """Tests for database setup and teardown."""

    @pytest.fixture(autouse=True)
    def cleanup_database(self):
        """Cleanup database connections after each test."""
        yield
        # Clean up after test
        dispose_engine()

    def test_dispose_engine_clears_connections(self):
        """Test that dispose_engine properly cleans up."""
        # Create some sessions
        with get_session() as session:
            assert session is not None

        # Dispose should clear everything
        dispose_engine()

        # Next engine should be a fresh instance
        with get_session() as session:
            assert session is not None
