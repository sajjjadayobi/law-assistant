"""
OpenTelemetry tracing setup for Law Agent via Arize Phoenix.

Uses arize-phoenix-otel for proper Phoenix integration and
openinference-instrumentation-openai for LLM call tracing with
full input/output/token-count visibility.
"""

import os
from contextlib import contextmanager
from typing import Any, Optional

import structlog
from opentelemetry import trace
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider

logger = structlog.get_logger(__name__)

# DB span names and attributes that indicate connection noise we want to suppress.
_DB_SPAN_NAMES = frozenset({"connect", "query", "execute", "cursor"})
_DB_ATTRS = frozenset({"db.system", "db.statement", "db.name", "db.operation"})


class _DBNoiseFilterProcessor(SpanProcessor):
    """Wraps a SpanProcessor and drops database connection spans.

    Prevents SQLAlchemy / asyncpg 'connect' and query spans from reaching
    Phoenix, regardless of which library originally instrumented them.
    """

    def __init__(self, inner: SpanProcessor) -> None:
        self._inner = inner

    def on_start(self, span: Any, parent_context: Optional[Any] = None) -> None:
        self._inner.on_start(span, parent_context)

    def on_end(self, span: Any) -> None:
        attrs = span.attributes or {}
        if span.name in _DB_SPAN_NAMES or any(attrs.get(k) for k in _DB_ATTRS):
            return  # silently drop
        self._inner.on_end(span)

    def shutdown(self) -> None:
        self._inner.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self._inner.force_flush(timeout_millis)


class OTelConfig:
    """OpenTelemetry configuration from environment."""

    def __init__(self) -> None:
        self.enabled = os.getenv("OTEL_ENABLED", "true").lower() == "true"
        self.endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        self.service_name = os.getenv("OTEL_SERVICE_NAME", "law-agent")
        self.service_version = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
        self.environment = os.getenv("ENVIRONMENT", "development")


_tracer_provider: TracerProvider | None = None
_config: OTelConfig | None = None
_initialized: bool = False


def initialize_tracing(config: OTelConfig | None = None) -> None:
    """Initialize Phoenix tracing with OpenInference instrumentation.

    Sets up:
    - arize-phoenix-otel TracerProvider (exports spans to Phoenix)
    - OpenAIInstrumentor (captures LLM calls with prompts/responses/token counts)
    - DB noise filter (drops SQLAlchemy connect spans before Phoenix export)

    SQLAlchemy is redirected to our provider and filtered out — DB connection
    noise must never reach Phoenix regardless of which library instruments it.
    """
    global _tracer_provider, _config, _initialized

    if _initialized:
        return

    _config = config or OTelConfig()

    if not _config.enabled:
        logger.info("tracing_disabled")
        return

    try:
        from phoenix.otel import register

        endpoint = _config.endpoint
        if endpoint == "http://localhost:4317":
            phoenix_http = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces")
            endpoint = phoenix_http

        # Must be set before register() so all Phoenix-aware libraries use "law-agent".
        os.environ.setdefault("PHOENIX_PROJECT_NAME", _config.service_name)

        _tracer_provider = register(
            endpoint=endpoint,
            project_name=_config.service_name,
            batch=False,
            verbose=True,
        )

        # Wrap the default SimpleSpanProcessor with a DB noise filter.
        # This drops any 'connect'/'query' spans before they reach the Phoenix
        # exporter, regardless of which library created them.
        try:
            multi = _tracer_provider._active_span_processor  # SynchronousMultiSpanProcessor
            if hasattr(multi, "_span_processors") and multi._span_processors:
                multi._span_processors = tuple(
                    _DBNoiseFilterProcessor(p) for p in multi._span_processors
                )
                logger.info("db_noise_filter_installed")
        except Exception as filter_err:
            logger.warning("db_noise_filter_failed", error=str(filter_err))

        # Instrument the openai library — PydanticAI's OpenAIModel uses it
        # internally, so this captures every LLM call with full attributes:
        # model name, input messages, output, token counts, latency.
        # opentelemetry-instrumentation-openai is compatible with OTel 0.62b1;
        # the openinference variant has a version mismatch with wrap_function_wrapper.
        try:
            from opentelemetry.instrumentation.openai import (
                OpenAIInstrumentor,  # type: ignore[import]
            )

            OpenAIInstrumentor().instrument(tracer_provider=_tracer_provider)
            logger.info("llm_instrumentation_active", instrumentor="opentelemetry-openai")
        except Exception as llm_err:
            logger.warning("llm_instrumentation_failed", error=str(llm_err))

        # Redirect SQLAlchemy to our "law-agent" provider (not the global default).
        # This ensures that even if something else instruments SQLAlchemy, those
        # spans flow through our filter above and are silently dropped — they never
        # reach Phoenix under the "default" project.
        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

            SQLAlchemyInstrumentor().uninstrument()  # clear any previous instrumentation
            SQLAlchemyInstrumentor().instrument(tracer_provider=_tracer_provider)
            logger.info("sqlalchemy_redirected_to_law_agent")
        except Exception as sa_err:
            logger.warning("sqlalchemy_redirect_failed", error=str(sa_err))

        _initialized = True
        logger.info(
            "tracing_initialized",
            endpoint=endpoint,
            service=_config.service_name,
        )

    except Exception:
        logger.exception("tracing_init_failed")
        raise


def get_tracer(name: str = "law-agent") -> trace.Tracer:
    """Get a tracer instance for the given name."""
    if _tracer_provider is None:
        return trace.get_tracer(name)
    return _tracer_provider.get_tracer(name)


@contextmanager
def create_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    tracer_name: str = "law-agent",
):
    """Context manager for creating a span with optional attributes."""
    tracer = get_tracer(tracer_name)
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                try:
                    span.set_attribute(key, value)
                except Exception:
                    pass
        yield span


def record_token_usage(
    input_tokens: int,
    output_tokens: int,
    model: str = "claude-sonnet-4.5",
    tool_name: str | None = None,
) -> dict[str, Any]:
    """Record token usage and estimate costs on the current span."""
    pricing = {
        "claude-sonnet-4.5": {"input": 3.0, "output": 15.0},
        "claude-opus": {"input": 15.0, "output": 75.0},
        "claude-haiku": {"input": 0.80, "output": 4.0},
    }
    rates = pricing.get(model, pricing["claude-sonnet-4.5"])
    input_cost = (input_tokens / 1_000_000) * rates["input"]
    output_cost = (output_tokens / 1_000_000) * rates["output"]
    total_cost = input_cost + output_cost

    usage_data = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "input_cost": round(input_cost, 6),
        "output_cost": round(output_cost, 6),
        "total_cost": round(total_cost, 6),
        "model": model,
    }

    span = trace.get_current_span()
    if span.is_recording():
        for key, value in usage_data.items():
            try:
                span.set_attribute(f"token_usage.{key}", value)
            except Exception:
                pass

    logger.info("token_usage_recorded", tool=tool_name, **usage_data)
    return usage_data


def record_error(
    error: Exception,
    span_name: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> None:
    """Record an error in the current span."""
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute("error.type", type(error).__name__)
        span.set_attribute("error.message", str(error))
        span.set_attribute("error", True)
        if attributes:
            for key, value in attributes.items():
                try:
                    span.set_attribute(f"error.{key}", value)
                except Exception:
                    pass

    logger.error(
        f"error_in_{span_name or 'span'}",
        error=type(error).__name__,
        message=str(error),
        **(attributes or {}),
    )


def record_event(
    event_name: str,
    attributes: dict[str, Any] | None = None,
) -> None:
    """Record a named event in the current span."""
    span = trace.get_current_span()
    if span.is_recording():
        span.add_event(event_name, attributes=attributes or {})
    logger.debug(f"event_recorded_{event_name}", **(attributes or {}))


def shutdown_tracing() -> None:
    """Gracefully shutdown OpenTelemetry providers."""
    global _tracer_provider, _initialized
    try:
        if _tracer_provider:
            _tracer_provider.force_flush()
        _initialized = False
        logger.info("tracing_shutdown")
    except Exception as e:
        logger.warning("tracing_shutdown_error", error=str(e))
