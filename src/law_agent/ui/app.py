"""
Main Chainlit application for the Law Agent.

This module sets up the Chainlit chat interface and integrates with the Law Agent backend.
Handles message processing, tool visualization, citations, and feedback.
"""

from __future__ import annotations

import json

import chainlit as cl
import structlog

from law_agent.agent import ConversationManager, LawAgent
from law_agent.config.settings import Settings
from law_agent.ui.citations import CitationFormatter
from law_agent.ui.steps import ToolStepManager

logger = structlog.get_logger(__name__)

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
            _settings = Settings()
        _agent = LawAgent(
            model=_settings.model.primary_model,
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
        _settings = Settings()
    return _settings


@cl.on_chat_start
async def start() -> None:
    """Handle chat initialization."""
    settings = get_settings()
    session_id = cl.user_session.get("id")

    logger.info("chat_started", session_id=session_id)

    # Initialize conversation manager for this session
    get_conversation_manager(session_id)

    # Send welcome message in Persian
    welcome_msg = """
سلام! 👋

من دستیار حقوقی هوشمند هستم که برای پاسخ به سوالات شما درباره قوانین ایران آماده‌ام.

می‌تونید هر سوالی درباره:
- قوانین و مقررات
- حقوق و تکالیف شهروندان
- مسائل قانونی تجاری
- و دیگر مسائل حقوقی

رو بپرسید و من براتون جواب می‌دم.

چی می‌تونم برات کمک کنم؟
"""

    await cl.Message(content=welcome_msg).send()

    # Send example questions if enabled
    if settings.ui.example_questions:
        examples_msg = "\n\n**سوالات نمونه:**\n"
        for i, question in enumerate(settings.ui.example_questions[:5], 1):
            examples_msg += f"{i}. {question}\n"
        await cl.Message(content=examples_msg).send()


@cl.on_message
async def main(message: cl.Message) -> None:
    """Handle incoming user messages and generate responses."""
    session_id = cl.user_session.get("id")
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

        # Get conversation history
        history = conv_manager.get_history()

        # Create a message for streaming response
        msg = cl.Message(content="")
        await msg.send()

        # Call agent
        logger.info("calling_agent", session_id=session_id)

        response_text = await agent.run(
            user_query=user_query,
            conversation_history=history,
            conversation_id=session_id,
        )

        # Add user message and agent response to history
        conv_manager.add_user_message(user_query)
        conv_manager.add_assistant_message(response_text)

        # Format response with clickable citations
        formatted_response = citation_formatter.format_response(response_text)

        # Update message with formatted response
        msg.content = formatted_response
        await msg.update()

        # Show tool steps if enabled
        if settings.ui.show_tool_calls:
            steps = step_manager.extract_steps(response_text)
            for step_data in steps:
                step = cl.Step(
                    name=step_data.get("tool_name", "Tool"),
                    type="tool",
                    show_input=True,
                )
                step.input = json.dumps(step_data.get("input", {}), ensure_ascii=False)
                step.output = json.dumps(step_data.get("output", {}), ensure_ascii=False)
                await step.send()

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
        await cl.Message(content=error_msg).send()


@cl.on_chat_end
async def end() -> None:
    """Handle chat session end."""
    session_id = cl.user_session.get("id")
    logger.info("chat_ended", session_id=session_id)


# The app is automatically created by Chainlit when decorators are used
# No need to explicitly instantiate it
