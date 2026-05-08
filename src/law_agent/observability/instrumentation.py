"""
OpenTelemetry instrumentation for Law Agent components.

Provides decorators and context managers for tracing agent execution,
tool calls, and LLM interactions.
"""

import time
import logging
from functools import wraps
from typing import Any, Callable, Dict, Union, Optional

from opentelemetry import trace

from .tracer import create_span, record_token_usage, record_error

logger = logging.getLogger(__name__)


def instrument_agent_run(original_method: Callable) -> Callable:
    """
    Decorator to instrument agent.run() method with OpenTelemetry tracing.

    Captures:
    - User query
    - Conversation ID
    - Response length
    - Execution time
    - Tool calls (via automatic instrumentation)
    - Errors (with full context)

    Usage:
        @instrument_agent_run
        async def run(self, user_query: str, ...):
            ...
    """
    @wraps(original_method)
    async def wrapper(
        self,
        user_query: str,
        conversation_history: Optional[list] = None,
        conversation_id: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        with create_span(
            "law_agent.run",
            attributes={
                "user_query_length": len(user_query),
                "conversation_id": conversation_id or "new",
                "history_length": len(conversation_history or []),
            },
        ) as span:
            start_time = time.time()
            try:
                # Call the actual agent run method
                response = await original_method(
                    self,
                    user_query,
                    conversation_history,
                    conversation_id,
                    **kwargs,
                )

                # Record metrics
                duration = time.time() - start_time
                span.set_attribute("response_length", len(response))
                span.set_attribute("duration_seconds", duration)
                span.set_attribute("status", "success")

                return response

            except Exception as e:
                duration = time.time() - start_time
                span.set_attribute("duration_seconds", duration)
                span.set_attribute("status", "error")

                record_error(e, "law_agent.run")
                raise

    return wrapper


def instrument_search_tool(original_method: Callable) -> Callable:
    """
    Decorator to instrument search_documents tool.

    Captures:
    - Query parameters
    - Result count
    - Execution time
    - Relevance scores
    """
    @wraps(original_method)
    async def wrapper(
        ctx: Any,
        query: str,
        tags: Optional[list[str]] = None,
        doc_types: Optional[list[str]] = None,
        limit: int = 20,
        **kwargs: Any,
    ) -> str:
        with create_span(
            "tool.search_documents",
            attributes={
                "query_length": len(query),
                "limit": limit,
                "filter_tags": str(tags or []),
                "filter_doc_types": str(doc_types or []),
            },
        ) as span:
            start_time = time.time()
            try:
                result = await original_method(
                    ctx, query, tags, doc_types, limit, **kwargs
                )

                # Parse result to count documents
                import json
                try:
                    result_data = json.loads(result)
                    if isinstance(result_data, list):
                        span.set_attribute("result_count", len(result_data))
                    elif isinstance(result_data, dict) and "error" not in result_data:
                        span.set_attribute("result_count", 1)
                except:
                    pass

                duration = time.time() - start_time
                span.set_attribute("duration_seconds", duration)
                span.set_attribute("status", "success")

                return result

            except Exception as e:
                duration = time.time() - start_time
                span.set_attribute("duration_seconds", duration)
                span.set_attribute("status", "error")

                record_error(e, "tool.search_documents")
                raise

    return wrapper


def instrument_get_document_tool(original_method: Callable) -> Callable:
    """
    Decorator to instrument get_document tool.

    Captures:
    - Document ID
    - Execution time
    - Document metadata (size, type)
    """
    @wraps(original_method)
    async def wrapper(ctx: Any, doc_id: int, **kwargs: Any) -> str:
        with create_span(
            "tool.get_document",
            attributes={"doc_id": doc_id},
        ) as span:
            start_time = time.time()
            try:
                result = await original_method(ctx, doc_id, **kwargs)

                # Parse result to get metadata
                import json
                try:
                    result_data = json.loads(result)
                    if not isinstance(result_data, dict) or "error" not in result_data:
                        if "full_content" in result_data:
                            span.set_attribute(
                                "content_length",
                                len(result_data.get("full_content", "")),
                            )
                        if "title" in result_data:
                            span.set_attribute("title_length", len(result_data["title"]))
                except:
                    pass

                duration = time.time() - start_time
                span.set_attribute("duration_seconds", duration)
                span.set_attribute("status", "success")

                return result

            except Exception as e:
                duration = time.time() - start_time
                span.set_attribute("duration_seconds", duration)
                span.set_attribute("status", "error")

                record_error(e, "tool.get_document", {"doc_id": doc_id})
                raise

    return wrapper


def instrument_get_related_documents_tool(original_method: Callable) -> Callable:
    """
    Decorator to instrument get_related_documents tool.

    Captures:
    - Source document ID
    - Relation types
    - Result count
    - Graph traversal depth
    """
    @wraps(original_method)
    async def wrapper(
        ctx: Any,
        doc_id: int,
        relation_types: Optional[list[str]] = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> str:
        with create_span(
            "tool.get_related_documents",
            attributes={
                "source_doc_id": doc_id,
                "limit": limit,
                "filter_relation_types": str(relation_types or []),
            },
        ) as span:
            start_time = time.time()
            try:
                result = await original_method(
                    ctx, doc_id, relation_types, limit, **kwargs
                )

                # Parse result to count documents
                import json
                try:
                    result_data = json.loads(result)
                    if isinstance(result_data, list):
                        span.set_attribute("result_count", len(result_data))
                except:
                    pass

                duration = time.time() - start_time
                span.set_attribute("duration_seconds", duration)
                span.set_attribute("status", "success")

                return result

            except Exception as e:
                duration = time.time() - start_time
                span.set_attribute("duration_seconds", duration)
                span.set_attribute("status", "error")

                record_error(e, "tool.get_related_documents", {"doc_id": doc_id})
                raise

    return wrapper


def instrument_llm_call(original_method: Callable) -> Callable:
    """
    Decorator to instrument LLM API calls.

    Captures:
    - Model name
    - Input/output tokens
    - Execution time
    - Cost estimation
    """
    @wraps(original_method)
    async def wrapper(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        with create_span(
            "llm.call",
            attributes={"model": self.model},
        ) as span:
            start_time = time.time()
            try:
                result = await original_method(self, *args, **kwargs)

                # Try to extract token usage from result
                if hasattr(result, "usage"):
                    usage = result.usage
                    if hasattr(usage, "input_tokens") and hasattr(usage, "output_tokens"):
                        record_token_usage(
                            input_tokens=usage.input_tokens,
                            output_tokens=usage.output_tokens,
                            model=self.model,
                            tool_name="llm_call",
                        )

                duration = time.time() - start_time
                span.set_attribute("duration_seconds", duration)
                span.set_attribute("status", "success")

                return result

            except Exception as e:
                duration = time.time() - start_time
                span.set_attribute("duration_seconds", duration)
                span.set_attribute("status", "error")

                record_error(e, "llm.call")
                raise

    return wrapper
