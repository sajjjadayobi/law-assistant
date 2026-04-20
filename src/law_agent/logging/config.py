"""Structlog configuration and initialization.

This module sets up structlog based on the application configuration.
It should be called once at application startup.

Usage:
    from src.law_agent.logging import configure_logging
    from src.law_agent.config import get_settings

    settings = get_settings()
    configure_logging(settings.logging)
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, TextIO, Union

import structlog

from ..config.settings import LoggingConfig
from .context import get_context
from .formatters import JSONFormatter, TextFormatter, add_log_level, format_timestamp


def configure_logging(config: LoggingConfig) -> None:
    """Configure structlog based on LoggingConfig settings.

    Args:
        config: LoggingConfig instance with level, format, and file_path

    This sets up:
    - Python logging level
    - structlog processors (timestamp, level, context, format)
    - Output formatters (text for dev, JSON for production)
    - File or console output based on config.file_path
    """
    # Convert string level to logging constant
    log_level = getattr(logging, config.level.upper(), logging.INFO)

    # Configure Python's built-in logging module
    # This ensures compatibility with third-party libraries that use standard logging
    logging.basicConfig(
        level=log_level,
        format="%(message)s",  # structlog handles formatting
        stream=sys.stderr,  # All logs to stderr
    )

    # Choose formatter based on config
    if config.format == "json":
        formatter: Union[JSONFormatter, TextFormatter] = JSONFormatter()
    else:  # text
        formatter = TextFormatter()

    # Determine processors with custom formatter
    processors: list[Any] = [
        # Add timestamp in ISO 8601 format
        format_timestamp,
        # Add log level to event_dict
        add_log_level,
        # Add context variables (conversation_id, user_id, etc.)
        _add_context_processor,
        # Apply custom formatter (text or JSON)
        formatter,
    ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=_get_output_file(config.file_path)),
        cache_logger_on_first_use=True,
    )

    # Note: The above configuration uses PrintLoggerFactory which outputs to file or stderr
    # For more advanced use cases (async, remote logging), see Phase 3+ tasks


def _add_context_processor(logger: object, name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Add context variables (conversation_id, user_id, etc.) to log event.

    This processor runs for every log call and enriches events with context.

    Args:
        logger: structlog logger instance
        name: Logger name / log level
        event_dict: Event dictionary to enrich

    Returns:
        Event dictionary with context variables added
    """
    context = get_context()
    # Only add context variables if they're set (non-empty dict)
    if context:
        event_dict.update(context)
    return event_dict


def _get_output_file(file_path: str | None) -> Union[TextIO, Any]:
    """Get file handle for log output with rotation support.

    Args:
        file_path: Path to log file, or None for stderr

    Returns:
        File handle (stderr or rotating file handler)
    """
    if file_path:
        # Create directory if it doesn't exist
        log_dir = Path(file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create rotating file handler for log rotation
        # Max 10MB per file, keep 5 backup files
        handler = RotatingFileHandler(
            filename=file_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,  # Keep 5 backup files
            encoding="utf-8",
        )
        return handler.stream  # Return the stream for structlog
    else:
        # Log to stderr (default)
        return sys.stderr


def get_logger(name: str = __name__) -> Any:
    """Get a logger instance for the given module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Configured structlog logger

    Usage:
        logger = get_logger(__name__)
        logger.info("search_executed", query="بیمه", results=15)
    """
    logger = structlog.get_logger(name)

    # Bind logger name to all logs from this logger instance
    return logger.bind(_logger=name)
