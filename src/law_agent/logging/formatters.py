"""Custom formatters for structlog.

This module provides formatters for both human-readable (development) and
machine-parseable (production) log output.
"""

import json
from typing import Any


def format_timestamp(logger: Any, name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Add ISO 8601 timestamp to log event.

    Args:
        logger: structlog logger instance
        name: Name of the logger
        event_dict: Event dictionary

    Returns:
        Event dictionary with timestamp added
    """
    from datetime import datetime, timezone

    event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    return event_dict


def add_log_level(logger: Any, name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Add log level to event dictionary if not already present.

    Args:
        logger: structlog logger instance
        name: Name of the logger
        event_dict: Event dictionary

    Returns:
        Event dictionary with log level added
    """
    if "level" not in event_dict:
        event_dict["level"] = name
    return event_dict


class TextFormatter:
    """Human-readable text formatter for development.

    Format: [timestamp] [level] logger: event - key=value key=value ...

    Example output:
        2024-01-15T10:30:45.123Z [INFO] search: search_executed - query=بیمه results=15 time_ms=234
    """

    def __call__(self, logger: Any, name: str, event_dict: dict[str, Any]) -> str:
        """Format event as human-readable text.

        Args:
            logger: structlog logger instance
            name: Name of the logger (log level)
            event_dict: Event dictionary

        Returns:
            Formatted log string
        """
        # Extract special fields
        timestamp = event_dict.pop("timestamp", "")
        level = event_dict.pop("level", name.upper())
        logger_name = event_dict.pop("_logger", "")
        message = event_dict.pop("event", "")

        # Format remaining fields as key=value pairs
        extra = " ".join(f"{k}={v}" for k, v in sorted(event_dict.items()))

        # Build log line
        parts = [timestamp, f"[{level}]", logger_name]
        if message:
            parts.append(f"{message}")
        if extra:
            parts.append(f"- {extra}")

        return " ".join(filter(None, parts))


class JSONFormatter:
    """Machine-parseable JSON formatter for production.

    Each log line is a complete JSON object that can be parsed, searched, and analyzed.
    Includes all context variables and event data.

    Example output:
        {"timestamp":"2024-01-15T10:30:45.123Z","level":"INFO","logger":"search","event":"search_executed","query":"بیمه","results":15,"time_ms":234}
    """

    def __call__(self, logger: Any, name: str, event_dict: dict[str, Any]) -> str:
        """Format event as JSON.

        Args:
            logger: structlog logger instance
            name: Name of the logger (log level)
            event_dict: Event dictionary

        Returns:
            JSON-formatted log string (one line)
        """
        # Ensure level is set
        if "level" not in event_dict:
            event_dict["level"] = name.upper()

        # Convert to JSON (ensure all values are JSON-serializable)
        try:
            return json.dumps(event_dict, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as e:
            # Fallback if any value is not JSON-serializable
            fallback = {
                "timestamp": event_dict.get("timestamp", ""),
                "level": event_dict.get("level", "ERROR"),
                "event": "json_serialization_error",
                "original_event": str(event_dict.get("event", "unknown")),
                "error": str(e),
            }
            return json.dumps(fallback, ensure_ascii=False, default=str)


class PrettyPrinter:
    """Pretty-printed formatter for readable console output (development).

    Format is more readable than TextFormatter, with colors (if terminal supports).

    Example output:
        2024-01-15 10:30:45 [INFO] search.search_executed
            query="بیمه مسئولیت"
            results=15
            time_ms=234
    """

    def __call__(self, logger: Any, name: str, event_dict: dict[str, Any]) -> str:
        """Format event as pretty-printed text.

        Args:
            logger: structlog logger instance
            name: Name of the logger (log level)
            event_dict: Event dictionary

        Returns:
            Pretty-printed log string (may span multiple lines)
        """
        # Extract special fields
        timestamp = event_dict.pop("timestamp", "")
        level = event_dict.pop("level", name.upper()).upper()
        logger_name = event_dict.pop("_logger", "")
        message = event_dict.pop("event", "")

        # Build header line
        header_parts = [timestamp, f"[{level}]"]
        if logger_name:
            header_parts.append(logger_name)
        if message:
            header_parts.append(message)

        header = " ".join(header_parts)

        # If no extra fields, just return header
        if not event_dict:
            return header

        # Build detailed output with indented fields
        lines = [header]
        for key, value in sorted(event_dict.items()):
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, ensure_ascii=False, default=str)
            else:
                value_str = str(value)
            lines.append(f"    {key}={value_str}")

        return "\n".join(lines)
