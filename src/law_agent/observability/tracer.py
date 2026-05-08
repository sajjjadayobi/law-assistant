"""
OpenTelemetry tracing setup and utilities for Law Agent.

Initializes OpenTelemetry SDK with OTLP exporter (Phoenix),
provides tracer for capturing agent execution traces.
"""

import os
from contextlib import contextmanager
from typing import Any, Dict

import structlog
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

logger = structlog.get_logger(__name__)


class OTelConfig:
    """OpenTelemetry configuration from environment."""

    def __init__(self):
        self.enabled = os.getenv("OTEL_ENABLED", "true").lower() == "true"
        self.endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        self.service_name = os.getenv("OTEL_SERVICE_NAME", "law-agent")
        self.service_version = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
        self.environment = os.getenv("ENVIRONMENT", "development")


_tracer_provider: TracerProvider | None = None
_meter_provider: MeterProvider | None = None
_config: OTelConfig | None = None


def initialize_tracing(config: OTelConfig | None = None) -> None:
    """
    Initialize OpenTelemetry tracing with OTLP exporter.

    Args:
        config: OTelConfig instance. If None, will create from environment.

    Returns:
        None

    Raises:
        Exception: If initialization fails
    """
    global _tracer_provider, _meter_provider, _config

    _config = config or OTelConfig()

    if not _config.enabled:
        logger.info("OpenTelemetry tracing disabled (OTEL_ENABLED=false)")
        return

    try:
        # Create resource (describes the service)
        resource = Resource.create({
            "service.name": _config.service_name,
            "service.version": _config.service_version,
            "deployment.environment": _config.environment,
        })

        # Create OTLP span exporter (sends to Phoenix)
        otlp_exporter = OTLPSpanExporter(
            endpoint=_config.endpoint,
            insecure=True,  # Use insecure connection for localhost
        )

        # Create and set tracer provider
        _tracer_provider = TracerProvider(resource=resource)
        _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        trace.set_tracer_provider(_tracer_provider)

        # Create metric exporter and meter provider
        metric_exporter = OTLPMetricExporter(
            endpoint=_config.endpoint,
            insecure=True,
        )
        metric_reader = PeriodicExportingMetricReader(metric_exporter)
        _meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(_meter_provider)

        # Auto-instrument popular libraries
        _instrument_libraries()

        logger.info(
            "OpenTelemetry tracing initialized",
            endpoint=_config.endpoint,
            service=_config.service_name,
        )

    except Exception as e:
        logger.exception("Failed to initialize OpenTelemetry tracing")
        raise


def _instrument_libraries() -> None:
    """Auto-instrument popular libraries for automatic tracing."""
    try:
        RequestsInstrumentor().instrument()
        HTTPXClientInstrumentor().instrument()
        SQLAlchemyInstrumentor().instrument()
        logger.debug("Auto-instrumented libraries")
    except Exception as e:
        logger.warning(f"Failed to auto-instrument libraries: {e}")

    # Psycopg2 instrumentation is handled by SQLAlchemy instrumentation
    # and is not available as a standalone package in recent versions


def get_tracer(name: str) -> trace.Tracer:
    """
    Get a tracer instance for the given name.

    Args:
        name: Module or component name for tracer identification

    Returns:
        Tracer instance
    """
    if _tracer_provider is None:
        # Return a no-op tracer if tracing not initialized
        return trace.get_tracer(name)
    return _tracer_provider.get_tracer(name)


@contextmanager
def create_span(
    name: str,
    attributes: Dict[str, Any] | None = None,
    tracer_name: str = "law-agent",
):
    """
    Context manager for creating and managing a span.

    Usage:
        with create_span("search_documents", attributes={"query": "بیمه"}) as span:
            # Do work
            span.set_attribute("results_count", 5)

    Args:
        name: Span name (e.g., "search_documents", "get_document")
        attributes: Optional dictionary of span attributes
        tracer_name: Name of the tracer to use

    Yields:
        The span object for adding custom attributes
    """
    tracer = get_tracer(tracer_name)

    with tracer.start_as_current_span(name) as span:
        # Set initial attributes
        if attributes:
            for key, value in attributes.items():
                try:
                    span.set_attribute(key, value)
                except Exception as e:
                    logger.debug(f"Could not set attribute {key}: {e}")

        yield span


def record_token_usage(
    input_tokens: int,
    output_tokens: int,
    model: str = "claude-sonnet-4.5",
    tool_name: str | None = None,
) -> Dict[str, Any]:
    """
    Record token usage and estimate costs.

    Uses Anthropic pricing as of 2024:
    - Claude Sonnet 4.5: $3/$1M input, $15/$1M output

    Args:
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens used
        model: Model name (for pricing lookup)
        tool_name: Optional tool name for attribution

    Returns:
        Dictionary with token counts and cost estimate
    """
    # Pricing per million tokens (as of 2024)
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

    # Add to current span if available
    span = trace.get_current_span()
    if span.is_recording():
        for key, value in usage_data.items():
            try:
                span.set_attribute(f"token_usage.{key}", value)
            except Exception as e:
                logger.debug(f"Could not set token attribute {key}: {e}")

    # Log for observability
    logger.info(
        "Token usage recorded",
        tool=tool_name,
        **usage_data
    )

    return usage_data


def record_error(
    error: Exception,
    span_name: str | None = None,
    attributes: Dict[str, Any] | None = None,
) -> None:
    """
    Record an error in the current span.

    Args:
        error: Exception that occurred
        span_name: Optional name of the span (for logging context)
        attributes: Optional additional attributes to record
    """
    span = trace.get_current_span()

    if span.is_recording():
        # Set error attributes on span
        span.set_attribute("error.type", type(error).__name__)
        span.set_attribute("error.message", str(error))

        if attributes:
            for key, value in attributes.items():
                try:
                    span.set_attribute(f"error.{key}", value)
                except Exception as e:
                    logger.debug(f"Could not set error attribute {key}: {e}")

        # Mark span as failed
        span.set_attribute("error", True)

    # Log error
    logger.error(
        f"Error in {span_name or 'span'}",
        error=type(error).__name__,
        message=str(error),
        **(attributes or {}),
    )


def record_event(
    event_name: str,
    attributes: Dict[str, Any] | None = None,
) -> None:
    """
    Record a named event in the current span.

    Args:
        event_name: Name of the event (e.g., "search_started", "tool_called")
        attributes: Optional event attributes
    """
    span = trace.get_current_span()

    if span.is_recording():
        span.add_event(event_name, attributes=attributes or {})

    logger.debug(f"Event recorded: {event_name}", **(attributes or {}))


def shutdown_tracing() -> None:
    """Gracefully shutdown OpenTelemetry providers."""
    global _tracer_provider, _meter_provider

    try:
        if _tracer_provider:
            _tracer_provider.force_flush()
        if _meter_provider:
            _meter_provider.force_flush()
        logger.info("OpenTelemetry tracing shutdown complete")
    except Exception as e:
        logger.warning(f"Error during OpenTelemetry shutdown: {e}")
