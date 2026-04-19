"""Error handling and Persian error messages for the Law Agent.

This module defines custom exceptions and error handlers with user-friendly
Persian error messages for common failure scenarios.
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


class LawAgentException(Exception):
    """Base exception for Law Agent errors."""

    def __init__(self, message: str, error_code: str, user_message: str):
        """Initialize exception.

        Args:
            message: Internal error message (English)
            error_code: Machine-readable error code
            user_message: User-friendly message in Persian
        """
        super().__init__(message)
        self.error_code = error_code
        self.user_message = user_message

    def get_user_message(self) -> str:
        """Get user-friendly error message in Persian.

        Returns:
            Error message to display to user
        """
        return self.user_message


class NoDocumentsFoundError(LawAgentException):
    """Raised when search returns no relevant documents."""

    def __init__(self, query: str):
        """Initialize exception.

        Args:
            query: Search query that returned no results
        """
        super().__init__(
            message=f"No documents found for query: {query}",
            error_code="NO_DOCUMENTS_FOUND",
            user_message=f"متأسفانه اسناد مرتبطی برای «{query}» پیدا نشد. لطفاً با کلیدواژه‌های متفاوتی جستجو کنید.",
        )
        self.query = query


class DocumentNotFoundError(LawAgentException):
    """Raised when a specific document cannot be retrieved."""

    def __init__(self, doc_id: int):
        """Initialize exception.

        Args:
            doc_id: ID of document that was not found
        """
        super().__init__(
            message=f"Document {doc_id} not found",
            error_code="DOCUMENT_NOT_FOUND",
            user_message=f"سند شماره {doc_id} در پایگاه‌داده پیدا نشد.",
        )
        self.doc_id = doc_id


class TurnLimitExceededError(LawAgentException):
    """Raised when conversation exceeds maximum number of turns."""

    def __init__(self, max_turns: int):
        """Initialize exception.

        Args:
            max_turns: Maximum allowed turns
        """
        super().__init__(
            message=f"Conversation exceeded {max_turns} turns",
            error_code="TURN_LIMIT_EXCEEDED",
            user_message=f"مکالمه از حد مجاز ({max_turns} دور) فراتر رفت. لطفاً مکالمهی جدیدی شروع کنید.",
        )
        self.max_turns = max_turns


class SearchTimeoutError(LawAgentException):
    """Raised when search operation times out."""

    def __init__(self, query: str, timeout_seconds: int = 30):
        """Initialize exception.

        Args:
            query: Search query that timed out
            timeout_seconds: Timeout duration
        """
        super().__init__(
            message=f"Search query timed out after {timeout_seconds}s: {query}",
            error_code="SEARCH_TIMEOUT",
            user_message="جستجو زمان بیشتری طول کشید از حد انتظار. لطفاً بعداً دوباره تلاش کنید.",
        )
        self.query = query
        self.timeout_seconds = timeout_seconds


class DatabaseConnectionError(LawAgentException):
    """Raised when database connection fails."""

    def __init__(self, detail: str = ""):
        """Initialize exception.

        Args:
            detail: Additional error details
        """
        super().__init__(
            message=f"Database connection failed: {detail}",
            error_code="DATABASE_CONNECTION_ERROR",
            user_message="خطا در برقراری ارتباط با پایگاه‌داده. لطفاً بعداً دوباره تلاش کنید.",
        )
        self.detail = detail


class InvalidQueryError(LawAgentException):
    """Raised when user query is invalid or cannot be processed."""

    def __init__(self, reason: str = ""):
        """Initialize exception.

        Args:
            reason: Reason query is invalid
        """
        super().__init__(
            message=f"Invalid query: {reason}",
            error_code="INVALID_QUERY",
            user_message=f"سوال شما واضح نیست. {reason}",
        )
        self.reason = reason


class AmbiguousQueryError(LawAgentException):
    """Raised when query is too vague to answer without clarification."""

    def __init__(self, query: str, suggestions: list[str]):
        """Initialize exception.

        Args:
            query: Ambiguous user query
            suggestions: List of clarification questions/suggestions
        """
        super().__init__(
            message=f"Query too ambiguous: {query}",
            error_code="AMBIGUOUS_QUERY",
            user_message="سوال شما می‌تواند معانی متفاوتی داشته باشد. لطفاً دقیق‌تر توضیح دهید.",
        )
        self.query = query
        self.suggestions = suggestions


class ErrorHandler:
    """Centralized error handling with logging and user messages.

    This class provides:
    1. Structured logging of errors
    2. User-friendly error messages
    3. Error recovery suggestions
    """

    @staticmethod
    def handle_error(exception: Exception) -> dict:
        """Handle any exception with logging and message extraction.

        Args:
            exception: Exception to handle

        Returns:
            Dictionary with error information:
            {
                'error_code': 'INTERNAL_ERROR',
                'error_type': 'ValueError',
                'user_message': 'خطای داخلی رخ داد',
                'internal_message': 'Original error message'
            }
        """
        if isinstance(exception, LawAgentException):
            # Our custom exception - structured logging
            logger.warning(
                "law_agent_error",
                error_code=exception.error_code,
                error_type=exception.__class__.__name__,
                message=str(exception),
            )
            return {
                "error_code": exception.error_code,
                "error_type": exception.__class__.__name__,
                "user_message": exception.get_user_message(),
                "internal_message": str(exception),
            }
        else:
            # Unexpected error
            logger.exception(
                "unexpected_error",
                error_type=exception.__class__.__name__,
                message=str(exception),
            )
            return {
                "error_code": "INTERNAL_ERROR",
                "error_type": exception.__class__.__name__,
                "user_message": "خطای داخلی رخ داد. لطفاً بعداً دوباره تلاش کنید.",
                "internal_message": str(exception),
            }

    @staticmethod
    def get_recovery_message(error_code: str) -> str:
        """Get recovery suggestion for error.

        Args:
            error_code: Error code

        Returns:
            Recovery message in Persian
        """
        recovery_messages = {
            "NO_DOCUMENTS_FOUND": "سعی کنید کلیدواژه‌های متفاوتی استفاده کنید یا سوال خود را دقیق‌تر بیان کنید.",
            "DOCUMENT_NOT_FOUND": "سند مورد نظر حذف شده یا موجود نیست.",
            "TURN_LIMIT_EXCEEDED": "برای ادامهی مکالمه، لطفاً مکالمهی جدیدی شروع کنید.",
            "SEARCH_TIMEOUT": "جستجو زمان بیشتری طول کشید. لطفاً سوال ساده‌تری بپرسید.",
            "DATABASE_CONNECTION_ERROR": "پایگاه‌داده موقتاً در دسترس نیست. بعداً دوباره تلاش کنید.",
            "INVALID_QUERY": "لطفاً سوالتان را واضح‌تر بیان کنید.",
            "AMBIGUOUS_QUERY": "سوالتان می‌تواند معانی مختلفی داشته باشد. توضیح بیشتری بدهید.",
            "INTERNAL_ERROR": "خطایی رخ داد. تیم فنی را در جریان قرار دادیم.",
        }
        return recovery_messages.get(error_code, "لطفاً دوباره تلاش کنید.")
