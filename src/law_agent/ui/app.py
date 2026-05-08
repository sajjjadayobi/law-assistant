"""
Main Chainlit application for the Law Agent.

This module sets up the Chainlit chat interface and integrates with the Law Agent backend.
Handles message processing, tool visualization, citations, and feedback.
"""

from __future__ import annotations

import atexit
import json
import os
from pathlib import Path

import chainlit as cl
import structlog
import yaml
from opentelemetry import trace as otel_trace

from law_agent.agent import ConversationManager, LawAgent
from law_agent.config.settings import Settings, StarterQuestion
from law_agent.data import get_data_layer
from law_agent.observability import (
    initialize_feedback_client,
    initialize_tracing,
    shutdown_tracing,
)
from law_agent.ui.citations import CitationFormatter
from law_agent.ui.steps import ToolStepManager

logger = structlog.get_logger(__name__)

# Initialize observability at startup
try:
    initialize_tracing()
    # Load Phoenix endpoint from config (or PHOENIX_ENDPOINT env var if set)
    phoenix_endpoint = os.getenv("PHOENIX_ENDPOINT") or None
    initialize_feedback_client(phoenix_endpoint=phoenix_endpoint)
    logger.info("Observability initialized")
    # Register shutdown hook
    atexit.register(shutdown_tracing)
except Exception as e:
    logger.warning(f"Failed to initialize observability: {e}")

# Global state
_agent: LawAgent | None = None
_conversation_managers: dict[str, ConversationManager] = {}
_citation_formatter: CitationFormatter | None = None
_step_manager: ToolStepManager | None = None
_settings: Settings | None = None
# Maps session_id → last OTel span_id hex string (for Phoenix feedback annotation)
_session_span_ids: dict[str, str] = {}


def get_agent() -> LawAgent:
    """Get or initialize the global Law Agent instance."""
    global _agent, _settings
    if _agent is None:
        if _settings is None:
            _settings = Settings.from_yaml()
        _agent = LawAgent(
            model=_settings.model.name,
            temperature=_settings.model.temperature,
        )
    return _agent


def get_conversation_manager(session_id: str) -> ConversationManager:
    """Get or create conversation manager for a session."""
    if session_id not in _conversation_managers:
        _conversation_managers[session_id] = ConversationManager(max_turns=50)
    return _conversation_managers[session_id]


def get_citation_formatter() -> CitationFormatter:
    """Get or initialize the citation formatter."""
    global _citation_formatter
    if _citation_formatter is None:
        _citation_formatter = CitationFormatter()
    return _citation_formatter


def get_step_manager() -> ToolStepManager:
    """Get or initialize the step manager."""
    global _step_manager
    if _step_manager is None:
        _step_manager = ToolStepManager()
    return _step_manager


def get_settings() -> Settings:
    """Get or initialize settings."""
    global _settings
    if _settings is None:
        _settings = Settings.from_yaml()
    return _settings


def load_starters() -> list[StarterQuestion]:
    """Load starter questions from prompts/starters.yaml.

    Returns:
        List of StarterQuestion objects with SVG icons
    """
    starters_file = Path(__file__).parent.parent / "prompts" / "starters.yaml"

    if not starters_file.exists():
        logger.warning(f"Starters file not found at {starters_file}, using defaults")
        return [
            StarterQuestion(
                message="حقوق و تکالیف مستأجر در قانون چیست؟", icon="/public/tenant-rights.svg"
            ),
            StarterQuestion(
                message="مدت مرخصی زایمان طبق قانون کار چقدر است؟",
                icon="/public/maternity-leave.svg",
            ),
            StarterQuestion(
                message="شرایط ثبت شرکت با مسئولیت محدود چیست؟",
                icon="/public/company-registration.svg",
            ),
        ]

    with open(starters_file) as f:
        data = yaml.safe_load(f)

    starters = []
    for item in data.get("starters", []):
        starters.append(StarterQuestion(**item))

    return starters


@cl.password_auth_callback
async def auth_callback(username: str, password: str) -> cl.User | None:
    """Accept any username/password to enable per-user conversation history."""
    return cl.User(identifier=username, metadata={"role": "user"})


@cl.set_chat_profiles
async def chat_profile(user: cl.User) -> list[cl.ChatProfile]:
    """Define Law Assistant chat profile with description and starters.

    This displays the agent description below the logo and provides starter buttons.
    """
    starters = load_starters()
    return [
        cl.ChatProfile(
            name="Law Assistant",
            markdown_description="دستیار حقوقی هوشمند برای پاسخ به سوالات درباره قوانین ایران 📜",
            icon="/public/logo.svg",
            starters=[
                cl.Starter(
                    label=q.message,
                    message=q.message,
                    icon=q.icon,
                )
                for q in starters
            ],
        )
    ]


@cl.data_layer
def setup_data_layer() -> object:
    """Register Chainlit data layer for conversation persistence.

    This enables:
    - Conversation history saved to PostgreSQL
    - Sidebar showing past conversations grouped by time period
    - Ability to resume conversations across sessions
    """
    logger.info("setup_data_layer called")
    layer = get_data_layer()
    logger.info(f"data_layer returned: {type(layer).__name__}")
    return layer


@cl.on_chat_start
async def start() -> None:
    """Handle chat initialization with centered welcome screen.

    Chainlit 2.11 automatically displays:
    - Custom Law Agent logo (from config.toml logo_file_url)
    - Starter question buttons (defined via @cl.set_starters)
    - Centered layout when chat is empty

    Note: Do NOT send messages here - they break the centered layout.
    Chainlit handles everything natively.
    """
    session_id = cl.user_session.get("id")  # type: ignore

    logger.info("chat_started", session_id=session_id)

    # Initialize conversation manager for this session
    get_conversation_manager(session_id)


@cl.on_message
async def main(message: cl.Message) -> None:
    """Handle incoming user messages and generate responses."""
    session_id = cl.user_session.get("id")  # type: ignore
    settings = get_settings()

    # Remove any retry buttons from the previous failed message
    prev_retry_actions: list[cl.Action] = cl.user_session.get("retry_actions") or []  # type: ignore
    for action in prev_retry_actions:
        try:
            await action.remove()
        except Exception:
            pass
    cl.user_session.set("retry_actions", [])  # type: ignore

    try:
        user_query = message.content.strip()

        if not user_query:
            await cl.Message(content="لطفاً یک سوال بپرسید.").send()
            return

        logger.info(
            "message_received",
            session_id=session_id,
            query_length=len(user_query),
        )

        # Get agent and conversation manager
        agent = get_agent()
        conv_manager = get_conversation_manager(session_id)
        citation_formatter = get_citation_formatter()
        step_manager = get_step_manager()

        # Get or create conversation state
        conv_state = conv_manager.get_or_create_conversation(session_id)

        # Get conversation history from state
        history = conv_state.message_history

        # Run agent inside an explicit OTel span so we can capture the span_id
        # for Phoenix feedback annotations later.
        logger.info("calling_agent", session_id=session_id)
        _tracer = otel_trace.get_tracer("law-agent-ui")
        streaming_msg: cl.Message | None = None

        with _tracer.start_as_current_span("user_turn") as _span:
            _ctx = _span.get_span_context()
            if _ctx.is_valid:
                _span_hex = format(_ctx.span_id, "016x")
                _session_span_ids[session_id] = _span_hex
                logger.info("span_id_stored", session_id=session_id, span_id=_span_hex)

            if settings.ui.enable_streaming:
                streaming_msg = cl.Message(content="")
                await streaming_msg.send()  # type: ignore

                async def _on_delta(delta: str) -> None:
                    await streaming_msg.stream_token(delta)  # type: ignore

                response_text, updated_history = await agent.run_streaming(
                    user_query=user_query,
                    conversation_history=history,
                    conversation_id=session_id,
                    on_delta=_on_delta,
                )
            else:
                response_text, updated_history = await agent.run(
                    user_query=user_query,
                    conversation_history=history,
                    conversation_id=session_id,
                )

        # Update conversation state
        conv_state.message_history = updated_history
        logger.info(
            "conversation_state_updated",
            session_id=session_id,
            message_count=len(updated_history),
        )

        # Format citations on the full response text, then send or update
        formatted_response = citation_formatter.format_response(response_text)
        if streaming_msg is not None:
            streaming_msg.content = formatted_response
            await streaming_msg.update()  # type: ignore
        else:
            await cl.Message(content=formatted_response).send()  # type: ignore

        # Legacy tool step extraction (kept for compatibility, now superseded by cl.step in tools)
        if False and settings.ui.show_tool_calls:
            steps = step_manager.extract_steps(response_text)
            for step_data in steps:
                step = cl.Step(
                    name=step_data.get("tool_name", "Tool"),
                    type="tool",
                    show_input=True,
                )
                step.input = json.dumps(step_data.get("input", {}), ensure_ascii=False)
                step.output = json.dumps(step_data.get("output", {}), ensure_ascii=False)
                await step.send()  # type: ignore

        logger.info(
            "message_processed_success",
            session_id=session_id,
            response_length=len(response_text),
        )

    except Exception as e:
        logger.exception(
            "message_processing_error",
            session_id=session_id,
            error=str(e),
        )

        retry_action = cl.Action(
            name="retry",
            label="تلاش مجدد",
            icon="refresh-cw",
            payload={"message_content": message.content},
            tooltip="تلاش مجدد برای این پیام",
        )
        cl.user_session.set("retry_actions", [retry_action])  # type: ignore

        error_msg = "متاسفانه خطایی رخ داده است. 😔\n\nبا زدن دکمه «تلاش مجدد» دوباره امتحان کنید."
        await cl.Message(content=error_msg, actions=[retry_action]).send()  # type: ignore


@cl.action_callback(name="retry")
async def handle_retry(action: cl.Action) -> None:
    """Remove the error message and re-process the original user query."""
    try:
        await cl.Message(content="", id=action.forId).remove()  # type: ignore
    except Exception:
        pass

    original_content = action.payload.get("message_content", "")
    if original_content:
        retry_message = cl.Message(content=original_content, type="user_message")
        await main(retry_message)


@cl.on_chat_end
async def end() -> None:
    """Handle chat session end."""
    session_id = cl.user_session.get("id")
    logger.info("chat_ended", session_id=session_id)
    # Shutdown observability for this session
    shutdown_tracing()


@cl.on_feedback
async def handle_feedback(feedback: cl.Feedback) -> None:
    """Handle user feedback (👍/👎).

    DB persistence is handled automatically by the data layer's upsert_feedback.
    This handler adds logging and optional Phoenix integration.
    """
    session_id = cl.user_session.get("id") or "unknown"  # type: ignore
    is_positive = feedback.value == 1
    label = "مفید بود 👍" if is_positive else "مفید نبود 👎"

    logger.info(
        "feedback_received",
        session_id=session_id,
        value=feedback.value,
        label=label,
        for_id=feedback.forId,
        thread_id=getattr(feedback, "threadId", None),
        comment=feedback.comment,
    )

    # Send to Phoenix as a span annotation (best-effort — Phoenix may be offline)
    span_id: str | None = _session_span_ids.get(session_id)
    logger.info("feedback_phoenix_attempt", session_id=session_id, span_id=span_id)
    if span_id:
        try:
            from law_agent.observability.feedback import get_feedback_client

            client = get_feedback_client()
            if client:
                sent = await client.send_feedback(
                    span_id=span_id,
                    feedback_type="positive" if is_positive else "negative",
                    comment=feedback.comment,
                )
                if sent:
                    logger.info("feedback_sent_to_phoenix", span_id=span_id)
        except Exception as e:
            logger.debug("feedback_phoenix_unavailable", error=str(e))
    else:
        logger.debug("feedback_no_span_id_available")


# The app is automatically created by Chainlit when decorators are used
# No need to explicitly instantiate it


# ============================================================================
# Health Check Routes
# ============================================================================
# These routes are used by Docker health checks and monitoring systems
#
# NOTE: The @cl.get_app() decorator doesn't exist in current Chainlit version.
# Health checks are accessible via separate health.py module for now.
# TODO: Implement proper FastAPI app access for health check routes

# @cl.get_app()  # type: ignore
# def setup_health_routes(app: FastAPI) -> None:
#     """Set up health check routes for the FastAPI app."""

#     @app.get("/health", tags=["health"])
#     async def health() -> dict[str, any]:  # type: ignore
#         """
#         Health check endpoint for Docker and monitoring systems.

#         Returns:
#             JSON with health status of all components
#         """
#         return await get_health_status()

#     @app.get("/ready", tags=["health"])
#     async def readiness() -> dict[str, any]:  # type: ignore
#         """
#         Readiness check endpoint for Kubernetes and orchestration systems.

#         Returns:
#             JSON with readiness status (ready: true/false)
#         """
#         return await get_readiness()
