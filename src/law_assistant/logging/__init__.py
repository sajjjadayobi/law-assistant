"""Structured logging for Law Agent.

This module provides:
- Centralized logging configuration via config.yaml
- structlog integration with text and JSON formatters
- Context management (conversation_id, user_id, etc.)
- Thread-safe and async-safe context variables

Usage:
    # At application startup
    from src.law_assistant.logging import configure_logging
    from src.law_assistant.config import get_settings

    settings = get_settings()
    configure_logging(settings.logging)

    # In application code
    from src.law_assistant.logging import get_logger, set_context, clear_context

    logger = get_logger(__name__)
    set_context(conversation_id="conv-123", user_id="user-456")
    logger.info("search_executed", query="بیمه", results=15, execution_time_ms=234)
    clear_context()

Log Output Examples:

Text format (development):
    2024-01-15T10:30:45.123Z [INFO] search: search_executed - conversation_id=conv-123 query=بیمه results=15 execution_time_ms=234

JSON format (production):
    {"timestamp":"2024-01-15T10:30:45.123Z","level":"INFO","_logger":"search","event":"search_executed","conversation_id":"conv-123","query":"بیمه","results":15,"execution_time_ms":234}

Logging Patterns:

    # User interaction
    logger.info("user_query", conversation_id="conv-123", query="بیمه", language="fa")

    # Tool execution
    logger.info("tool_executed", tool="search_documents", execution_time_ms=234, result_count=15)

    # Errors
    logger.error("search_failed", query="بیمه", error="timeout", retry_attempt=1)

    # Performance metrics
    logger.info("response_sent", conversation_id="conv-123", tokens_used=1234, total_time_ms=2500)

Context Variables (auto-included in all logs):
    - conversation_id: Unique identifier for conversation
    - user_id: Unique identifier for user (optional)
    - session_id: Unique identifier for session (optional)
    - request_id: Unique identifier for request (optional)

All context variables are thread-safe and async-safe (PEP 567).
"""

from .config import configure_logging, get_logger
from .context import clear_context, get_context, set_context

__all__ = [
    "configure_logging",
    "get_logger",
    "set_context",
    "get_context",
    "clear_context",
]
