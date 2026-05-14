"""
Observability module for Law Agent.

Provides OpenTelemetry instrumentation for tracing agent execution,
token usage tracking, and observability platform integration (Arize Phoenix).
"""

from .tracer import (
    initialize_tracing,
    get_tracer,
    create_span,
    record_token_usage,
    record_error,
    record_event,
    shutdown_tracing,
)
from .instrumentation import (
    instrument_agent_run,
    instrument_search_tool,
    instrument_get_document_tool,
    instrument_get_related_documents_tool,
    instrument_llm_call,
)
from .feedback import (
    get_feedback_client,
    initialize_feedback_client,
    log_feedback_local,
    send_feedback_to_phoenix,
)

__all__ = [
    # Tracing
    "initialize_tracing",
    "get_tracer",
    "create_span",
    "record_token_usage",
    "record_error",
    "record_event",
    "shutdown_tracing",
    # Instrumentation
    "instrument_agent_run",
    "instrument_search_tool",
    "instrument_get_document_tool",
    "instrument_get_related_documents_tool",
    "instrument_llm_call",
    # Feedback
    "get_feedback_client",
    "initialize_feedback_client",
    "send_feedback_to_phoenix",
    "log_feedback_local",
]
