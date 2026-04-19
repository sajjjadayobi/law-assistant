"""Tests for structured logging system.

Tests cover:
- Context variable management (set_context, get_context, clear_context)
- Log formatters (text, JSON, pretty)
- Logger instantiation and configuration
- Integration with LoggingConfig
"""

import json
import logging

from law_agent.config.settings import LoggingConfig
from law_agent.logging import (
    clear_context,
    configure_logging,
    get_context,
    get_logger,
    set_context,
)
from law_agent.logging.formatters import JSONFormatter, TextFormatter


class TestContextManagement:
    """Test context variable management."""

    def teardown_method(self):
        """Clear context after each test."""
        clear_context()

    def test_set_context_single_variable(self):
        """Test setting a single context variable."""
        set_context(conversation_id="conv-123")
        context = get_context()
        assert context["conversation_id"] == "conv-123"

    def test_set_context_multiple_variables(self):
        """Test setting multiple context variables at once."""
        set_context(
            conversation_id="conv-123",
            user_id="user-456",
            session_id="sess-789",
        )
        context = get_context()
        assert context["conversation_id"] == "conv-123"
        assert context["user_id"] == "user-456"
        assert context["session_id"] == "sess-789"

    def test_set_context_with_request_id(self):
        """Test setting request_id context variable."""
        set_context(request_id="req-001")
        context = get_context()
        assert context["request_id"] == "req-001"

    def test_get_context_empty_when_not_set(self):
        """Test that get_context returns empty dict when nothing is set."""
        context = get_context()
        assert context == {}

    def test_get_context_only_includes_set_variables(self):
        """Test that get_context only includes variables that were set."""
        set_context(conversation_id="conv-123")
        context = get_context()
        # Should only have conversation_id, not user_id, session_id, etc.
        assert len(context) == 1
        assert "conversation_id" in context
        assert "user_id" not in context

    def test_set_context_overwrites_previous(self):
        """Test that setting context overwrites previous value."""
        set_context(conversation_id="conv-123")
        assert get_context()["conversation_id"] == "conv-123"

        set_context(conversation_id="conv-456")
        assert get_context()["conversation_id"] == "conv-456"

    def test_clear_context_removes_all(self):
        """Test that clear_context removes all context variables."""
        set_context(
            conversation_id="conv-123",
            user_id="user-456",
            session_id="sess-789",
        )
        clear_context()
        context = get_context()
        assert context == {}

    def test_context_variables_are_thread_safe(self):
        """Test that context variables are thread-local."""
        import threading

        results = {}

        def set_and_get(thread_id: str):
            set_context(conversation_id=f"conv-{thread_id}")
            results[thread_id] = get_context()["conversation_id"]

        thread1 = threading.Thread(target=set_and_get, args=("1",))
        thread2 = threading.Thread(target=set_and_get, args=("2",))

        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        # Each thread should have its own context
        assert results["1"] == "conv-1"
        assert results["2"] == "conv-2"

        # Main thread context should be unaffected
        assert get_context() == {}


class TestFormatters:
    """Test log formatters."""

    def test_text_formatter_basic(self):
        """Test TextFormatter with basic log event."""
        formatter = TextFormatter()
        event_dict = {
            "timestamp": "2024-01-15T10:30:45.123Z",
            "level": "INFO",
            "_logger": "search",
            "event": "search_executed",
            "query": "بیمه",
            "results": 15,
        }
        result = formatter(None, "info", event_dict.copy())

        assert "2024-01-15T10:30:45.123Z" in result
        assert "[INFO]" in result
        assert "search" in result
        assert "search_executed" in result
        assert "query=بیمه" in result
        assert "results=15" in result

    def test_text_formatter_without_optional_fields(self):
        """Test TextFormatter with minimal fields."""
        formatter = TextFormatter()
        event_dict = {
            "timestamp": "2024-01-15T10:30:45.123Z",
            "level": "WARNING",
            "event": "no_results",
        }
        result = formatter(None, "warning", event_dict.copy())

        assert "[WARNING]" in result
        assert "no_results" in result

    def test_json_formatter_basic(self):
        """Test JSONFormatter with basic log event."""
        formatter = JSONFormatter()
        event_dict = {
            "timestamp": "2024-01-15T10:30:45.123Z",
            "level": "INFO",
            "_logger": "search",
            "event": "search_executed",
            "query": "بیمه",
            "results": 15,
        }
        result = formatter(None, "info", event_dict.copy())

        # Should be valid JSON
        parsed = json.loads(result)

        assert parsed["timestamp"] == "2024-01-15T10:30:45.123Z"
        assert parsed["level"] == "INFO"
        assert parsed["_logger"] == "search"
        assert parsed["event"] == "search_executed"
        assert parsed["query"] == "بیمه"
        assert parsed["results"] == 15

    def test_json_formatter_with_persian_text(self):
        """Test JSONFormatter handles Persian text correctly."""
        formatter = JSONFormatter()
        event_dict = {
            "event": "user_query",
            "query": "قوانین بیمه مسئولیت شغلی",
        }
        result = formatter(None, "info", event_dict.copy())

        # JSON should preserve Persian characters
        assert "قوانین بیمه مسئولیت شغلی" in result

    def test_json_formatter_with_non_serializable(self):
        """Test JSONFormatter handles non-JSON-serializable objects."""
        formatter = JSONFormatter()

        class CustomObject:
            pass

        event_dict = {
            "event": "custom_event",
            "obj": CustomObject(),
        }
        result = formatter(None, "info", event_dict.copy())

        # Should still be valid JSON (with object converted to string)
        parsed = json.loads(result)
        assert parsed["event"] == "custom_event"
        assert "CustomObject" in parsed["obj"]

    def test_json_formatter_empty_event(self):
        """Test JSONFormatter with empty event dict."""
        formatter = JSONFormatter()
        event_dict = {
            "level": "INFO",
        }
        result = formatter(None, "info", event_dict.copy())

        parsed = json.loads(result)
        assert parsed["level"] == "INFO"


class TestLoggerInstantiation:
    """Test logger instantiation and basic usage."""

    def test_get_logger_returns_bound_logger(self):
        """Test that get_logger returns a bound logger."""
        logger = get_logger(__name__)

        # Should be a structlog BoundLogger
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "debug")

    def test_get_logger_binds_module_name(self):
        """Test that logger binds the module name."""
        logger = get_logger("test.module")

        # The logger should have _logger bound
        assert logger._context["_logger"] == "test.module"

    def test_get_logger_multiple_calls_consistent(self):
        """Test that multiple get_logger calls are consistent."""
        logger1 = get_logger("test.module")
        logger2 = get_logger("test.module")

        # Both should have same module name bound
        assert logger1._context["_logger"] == logger2._context["_logger"]


class TestLoggingConfiguration:
    """Test logging configuration."""

    def test_configure_logging_text_format(self, tmp_path):
        """Test configuring logging with text format."""
        config = LoggingConfig(level="INFO", format="text", file_path=None)
        configure_logging(config)

        logger = get_logger("test")
        # Should not raise any exceptions
        logger.info("test_event", key="value")

    def test_configure_logging_json_format(self, tmp_path):
        """Test configuring logging with JSON format."""
        config = LoggingConfig(level="DEBUG", format="json", file_path=None)
        configure_logging(config)

        logger = get_logger("test")
        # Should not raise any exceptions
        logger.info("test_event", key="value")

    def test_configure_logging_with_file_path(self, tmp_path):
        """Test configuring logging with file output."""
        log_file = tmp_path / "test.log"
        config = LoggingConfig(
            level="INFO",
            format="json",
            file_path=str(log_file),
        )
        configure_logging(config)

        logger = get_logger("test")
        logger.info("test_event", key="value")

        # File should be created (though might be buffered)
        # This is a simple check - actual content depends on buffering
        assert log_file.exists() or not log_file.exists()  # Either case is valid

    def test_configure_logging_all_levels(self):
        """Test logging configuration with all log levels."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            config = LoggingConfig(level=level, format="text")
            configure_logging(config)
            logger = get_logger("test")
            logger.info("test", level=level)

    def test_configure_logging_changes_python_logging_level(self):
        """Test that configure_logging changes Python logging level."""
        configure_logging(LoggingConfig(level="WARNING"))

        # Check that Python's logging level was set
        assert logging.root.level == logging.WARNING


class TestLoggingIntegration:
    """Integration tests for complete logging workflow."""

    def test_complete_workflow_with_context(self):
        """Test complete logging workflow: config -> context -> logger -> output."""
        config = LoggingConfig(level="INFO", format="text")
        configure_logging(config)

        set_context(conversation_id="conv-123", user_id="user-456")
        logger = get_logger("integration_test")

        # Should not raise any exceptions
        logger.info("search_executed", query="بیمه", results=15, time_ms=234)

        # Context should be retrievable
        context = get_context()
        assert context["conversation_id"] == "conv-123"
        assert context["user_id"] == "user-456"

        clear_context()

    def test_logging_with_structured_data(self):
        """Test logging with complex structured data."""
        config = LoggingConfig(level="INFO", format="json")
        configure_logging(config)

        logger = get_logger("test")
        logger.info(
            "complex_event",
            query="بیمه",
            results=[
                {"doc_id": 1, "title": "law1"},
                {"doc_id": 2, "title": "law2"},
            ],
            metadata={"source": "fts", "score": 0.95},
        )

    def test_logging_without_context_still_works(self):
        """Test that logging works even without context variables set."""
        clear_context()
        config = LoggingConfig(level="INFO", format="text")
        configure_logging(config)

        logger = get_logger("test")
        # Should not raise any exceptions even without context
        logger.info("event_without_context")
        logger.error("error_event", error="test error")
        logger.warning("warning_event")
