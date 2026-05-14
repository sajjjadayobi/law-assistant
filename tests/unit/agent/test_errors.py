"""Unit tests for error handling.

Tests custom exceptions and error handlers.
"""

from law_assistant.agent.errors import (
    AmbiguousQueryError,
    DatabaseConnectionError,
    DocumentNotFoundError,
    ErrorHandler,
    InvalidQueryError,
    LawAgentException,
    NoDocumentsFoundError,
    SearchTimeoutError,
    TurnLimitExceededError,
)


class TestCustomExceptions:
    """Tests for custom exception classes."""

    def test_law_assistant_exception_base(self):
        """Test base exception."""
        exc = LawAgentException(
            message="test error",
            error_code="TEST_ERROR",
            user_message="خطای تست",
        )

        assert exc.error_code == "TEST_ERROR"
        assert exc.get_user_message() == "خطای تست"
        assert str(exc) == "test error"

    def test_no_documents_found_error(self):
        """Test NoDocumentsFoundError."""
        exc = NoDocumentsFoundError("بیمه")

        assert exc.error_code == "NO_DOCUMENTS_FOUND"
        assert exc.query == "بیمه"
        assert "بیمه" in exc.get_user_message()
        assert "فارسی" in str(exc.get_user_message()) or "پیدا" in str(exc.get_user_message())

    def test_document_not_found_error(self):
        """Test DocumentNotFoundError."""
        exc = DocumentNotFoundError(12345)

        assert exc.error_code == "DOCUMENT_NOT_FOUND"
        assert exc.doc_id == 12345
        assert "12345" in exc.get_user_message()

    def test_turn_limit_exceeded_error(self):
        """Test TurnLimitExceededError."""
        exc = TurnLimitExceededError(50)

        assert exc.error_code == "TURN_LIMIT_EXCEEDED"
        assert exc.max_turns == 50
        assert "50" in exc.get_user_message()

    def test_search_timeout_error(self):
        """Test SearchTimeoutError."""
        exc = SearchTimeoutError("query", timeout_seconds=30)

        assert exc.error_code == "SEARCH_TIMEOUT"
        assert exc.query == "query"
        assert exc.timeout_seconds == 30

    def test_database_connection_error(self):
        """Test DatabaseConnectionError."""
        exc = DatabaseConnectionError("Connection refused")

        assert exc.error_code == "DATABASE_CONNECTION_ERROR"
        assert exc.detail == "Connection refused"

    def test_invalid_query_error(self):
        """Test InvalidQueryError."""
        exc = InvalidQueryError("Query is empty")

        assert exc.error_code == "INVALID_QUERY"
        assert exc.reason == "Query is empty"

    def test_ambiguous_query_error(self):
        """Test AmbiguousQueryError."""
        suggestions = ["Are you asking about X?", "Or are you asking about Y?"]
        exc = AmbiguousQueryError("ambiguous query", suggestions)

        assert exc.error_code == "AMBIGUOUS_QUERY"
        assert exc.query == "ambiguous query"
        assert exc.suggestions == suggestions


class TestErrorHandler:
    """Tests for ErrorHandler class."""

    def test_handle_law_assistant_exception(self):
        """Test handling LawAgentException."""
        exc = NoDocumentsFoundError("بیمه")

        result = ErrorHandler.handle_error(exc)

        assert result["error_code"] == "NO_DOCUMENTS_FOUND"
        assert result["error_type"] == "NoDocumentsFoundError"
        assert "خطا" in result["user_message"] or "متأسفانه" in result["user_message"]

    def test_handle_unexpected_exception(self):
        """Test handling unexpected exception."""
        exc = ValueError("Unexpected error")

        result = ErrorHandler.handle_error(exc)

        assert result["error_code"] == "INTERNAL_ERROR"
        assert result["error_type"] == "ValueError"
        assert "خطا" in result["user_message"]

    def test_handle_exception_contains_all_fields(self):
        """Test that error handler returns all required fields."""
        exc = DatabaseConnectionError()

        result = ErrorHandler.handle_error(exc)

        assert "error_code" in result
        assert "error_type" in result
        assert "user_message" in result
        assert "internal_message" in result

    def test_get_recovery_message_no_documents_found(self):
        """Test recovery message for NO_DOCUMENTS_FOUND."""
        msg = ErrorHandler.get_recovery_message("NO_DOCUMENTS_FOUND")

        assert "کلیدواژه" in msg or "جستجو" in msg

    def test_get_recovery_message_turn_limit_exceeded(self):
        """Test recovery message for TURN_LIMIT_EXCEEDED."""
        msg = ErrorHandler.get_recovery_message("TURN_LIMIT_EXCEEDED")

        assert "مکالمهی جدیدی" in msg or "جدیدی" in msg

    def test_get_recovery_message_database_error(self):
        """Test recovery message for DATABASE_CONNECTION_ERROR."""
        msg = ErrorHandler.get_recovery_message("DATABASE_CONNECTION_ERROR")

        assert "دسترس" in msg or "پایگاه" in msg

    def test_get_recovery_message_unknown_error(self):
        """Test recovery message for unknown error code."""
        msg = ErrorHandler.get_recovery_message("UNKNOWN_ERROR")

        # Should return default message
        assert "دوباره تلاش" in msg or "تلاش" in msg

    def test_error_messages_are_persian(self):
        """Test that all error messages are in Persian."""
        exceptions = [
            NoDocumentsFoundError("test"),
            DocumentNotFoundError(123),
            TurnLimitExceededError(50),
            SearchTimeoutError("test"),
            DatabaseConnectionError(),
            InvalidQueryError(),
            AmbiguousQueryError("test", []),
        ]

        for exc in exceptions:
            msg = exc.get_user_message()
            # Check that message contains Persian characters
            assert any(ord(c) >= 1536 for c in msg), f"Message not in Persian: {msg}"

    def test_error_code_consistency(self):
        """Test that error codes are consistent and uppercase."""
        exceptions = [
            NoDocumentsFoundError("test"),
            DocumentNotFoundError(123),
            TurnLimitExceededError(50),
        ]

        for exc in exceptions:
            # Error code should be uppercase with underscores
            assert exc.error_code.isupper()
            assert "_" in exc.error_code or exc.error_code.isalpha()
