"""
Chainlit UI configuration module.

Sets up Chainlit application settings, custom CSS, and integrations.
"""

from __future__ import annotations

from pathlib import Path

import chainlit as cl
import structlog

logger = structlog.get_logger(__name__)


def setup_chainlit_ui(
    title: str = "دستیار حقوقی ایران",
    subtitle: str = "پاسخ به سوالات حقوقی شما درباره قوانین ایران",
) -> None:
    """Configure Chainlit UI with Persian RTL support.

    Args:
        title: Application title (default: Persian "Iran Legal Assistant")
        subtitle: Application subtitle
    """
    try:
        # Configure application settings
        cl.app.title = title
        cl.app.description = subtitle

        # Load and inject custom RTL CSS
        rtl_css_path = Path(__file__).parent / "static" / "rtl.css"
        if rtl_css_path.exists():
            with open(rtl_css_path, encoding="utf-8") as f:
                rtl_css = f.read()
            cl.app.custom_css = rtl_css
            logger.info("rtl_css_loaded", path=str(rtl_css_path))
        else:
            logger.warning("rtl_css_not_found", path=str(rtl_css_path))

        # Set up session configuration
        cl.app.session_timeout = 3600  # 1 hour timeout

        # Enable data persistence
        cl.app.enable_chat_history = True

        # Configure message formatting
        cl.app.markdown_message = True

        logger.info(
            "chainlit_ui_configured",
            title=title,
            rtl_enabled=True,
        )

    except Exception as e:
        logger.exception("chainlit_ui_setup_error", error=str(e))
        raise


def configure_feedback_system() -> None:
    """Configure user feedback collection system.

    Enables thumbs up/down feedback for observability and eval-driven development.
    """
    try:
        # Enable feedback buttons
        cl.app.enable_feedback = True

        # Configure feedback callback
        @cl.feedback_callback
        async def feedback_callback(feedback: cl.Feedback) -> None:
            """Handle user feedback (👍/👎)."""
            logger.info(
                "feedback_received",
                score=feedback.score,
                comment=feedback.comment,
                message_id=feedback.message_id,
            )

            # TODO: Send feedback to Arize Phoenix for analysis
            # This would be implemented in Phase 6 (Observability)

        logger.info("feedback_system_configured")

    except Exception as e:
        logger.exception("feedback_system_setup_error", error=str(e))
        raise


def configure_session_management() -> None:
    """Configure conversation history and session management.

    Uses Chainlit's built-in session management with SQLite backend.
    """
    try:
        # Enable session persistence
        cl.app.enable_session_history = True

        # Set up session callback
        @cl.session_callback
        async def session_callback(session: cl.Session) -> None:
            """Handle session lifecycle events."""
            logger.info("session_event", session_id=session.id)

        logger.info("session_management_configured")

    except Exception as e:
        logger.exception("session_management_setup_error", error=str(e))
        raise


def inject_custom_styles() -> None:
    """Inject additional custom CSS for better UI."""
    custom_css = """
    /* Additional custom styles */

    /* Persian text styling */
    .cl-message-content {
        font-size: 16px;
        line-height: 1.6;
        word-wrap: break-word;
    }

    /* Citation link styling */
    a[href*="iran.ir"] {
        color: #0066cc;
        text-decoration: underline;
        cursor: pointer;
    }

    a[href*="iran.ir"]:hover {
        color: #0052a3;
    }

    /* Tool step styling */
    .tool-step {
        border-left: 4px solid #0066cc;
        padding: 10px;
        margin: 10px 0;
        background: #f9f9f9;
    }

    /* Example questions styling */
    .example-question {
        background: #f0f7ff;
        border: 1px solid #cce7ff;
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
        cursor: pointer;
    }

    .example-question:hover {
        background: #e0f0ff;
    }

    /* Loading spinner */
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    .spinner {
        animation: spin 1s linear infinite;
    }
    """

    if hasattr(cl.app, "custom_css"):
        cl.app.custom_css += "\n" + custom_css
    else:
        cl.app.custom_css = custom_css

    logger.info("custom_styles_injected")


def setup_all() -> None:
    """Complete Chainlit UI setup.

    Should be called once at application startup.
    """
    logger.info("setting_up_chainlit_ui")

    setup_chainlit_ui()
    configure_feedback_system()
    configure_session_management()
    inject_custom_styles()

    logger.info("chainlit_ui_setup_complete")
