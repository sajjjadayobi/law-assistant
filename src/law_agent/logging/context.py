"""Context management for structured logging.

This module provides context variables for request/conversation-level tracking.
Context variables are thread-safe and automatically propagated to all logs.

Usage:
    from src.law_agent.logging import set_context, clear_context

    set_context(conversation_id="conv-123", user_id="user-456")
    # All logs in this context will include conversation_id and user_id

    clear_context()  # Clear when done
"""

import contextvars
from typing import Any, Optional

# Context variables for request/conversation tracking
# These are thread-safe and async-safe (PEP 567)
conversation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "conversation_id", default=None
)
user_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("user_id", default=None)
session_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "session_id", default=None
)
request_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)


def set_context(**kwargs: Any) -> None:
    """Set context variables for current request/conversation.

    Args:
        conversation_id: Unique identifier for conversation
        user_id: Unique identifier for user
        session_id: Unique identifier for session
        request_id: Unique identifier for request

    Example:
        set_context(conversation_id="conv-123", user_id="user-456")
    """
    for key, value in kwargs.items():
        if key == "conversation_id":
            conversation_id.set(value)
        elif key == "user_id":
            user_id.set(value)
        elif key == "session_id":
            session_id.set(value)
        elif key == "request_id":
            request_id.set(value)


def get_context() -> dict[str, str]:
    """Get current context as a dictionary.

    Returns:
        Dictionary with all context variables (only includes non-None values)
    """
    context: dict[str, str] = {}

    if (conv_id := conversation_id.get()) is not None:
        context["conversation_id"] = conv_id
    if (uid := user_id.get()) is not None:
        context["user_id"] = uid
    if (sess_id := session_id.get()) is not None:
        context["session_id"] = sess_id
    if (req_id := request_id.get()) is not None:
        context["request_id"] = req_id

    return context


def clear_context() -> None:
    """Clear all context variables."""
    conversation_id.set(None)
    user_id.set(None)
    session_id.set(None)
    request_id.set(None)
