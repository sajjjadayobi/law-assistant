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
from typing import Optional

import chainlit as cl
import structlog
import yaml

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
    initialize_feedback_client(
        phoenix_endpoint=os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006")
    )
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
async def auth_callback(username: str, password: str) -> Optional[cl.User]:
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
    settings = get_settings()
    session_id = cl.user_session.get("id")  # type: ignore

    logger.info("chat_started", session_id=session_id)

    # Initialize conversation manager for this session
    get_conversation_manager(session_id)


@cl.on_message
async def main(message: cl.Message) -> None:
    """Handle incoming user messages and generate responses."""
    session_id = cl.user_session.get("id")  # type: ignore
    settings = get_settings()

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

        # Run agent — thinking and tool steps appear during execution
        # The final cl.Message is sent AFTER, so steps appear before the answer
        logger.info("calling_agent", session_id=session_id)

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

        # Format and send the final response AFTER all tool steps are complete
        formatted_response = citation_formatter.format_response(response_text)
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
        error_msg = """
متاسفانه خطایی رخ داده است. 😔

لطفاً دوباره تلاش کنید یا سوال خود را به شکل دیگری بیان کنید.
"""
        await cl.Message(content=error_msg).send()  # type: ignore


@cl.on_chat_end
async def end() -> None:
    """Handle chat session end."""
    session_id = cl.user_session.get("id")
    logger.info("chat_ended", session_id=session_id)
    # Shutdown observability for this session
    shutdown_tracing()


# TODO: Implement feedback handler when Chainlit feedback API is available
# Currently disabled because it was conflicting with message handler
# @cl.on_feedback
# async def handle_feedback(feedback: cl.Feedback) -> None:
#     """Handle user feedback (thumbs up/down)."""
#     from law_agent.observability import log_feedback_local, send_feedback_to_phoenix
#
#     session_id = cl.user_session.get("id") or "unknown"  # type: ignore
#     feedback_type = "positive" if feedback.score > 0 else "negative"
#     comment = getattr(feedback, "comment", None)
#
#     logger.info(
#         "feedback_received",
#         session_id=session_id,
#         feedback_type=feedback_type,
#         comment=comment,
#     )
#
#     # Send to Phoenix
#     success = await send_feedback_to_phoenix(
#         trace_id=session_id,
#         feedback_type=feedback_type,
#         comment=comment,
#         tags=["chainlit_ui"],
#     )
#
#     if not success:
#         # Fallback to local logging
#         log_feedback_local(
#             trace_id=session_id,
#             feedback_type=feedback_type,
#             comment=comment,
#             tags=["chainlit_ui"],
#         )


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
