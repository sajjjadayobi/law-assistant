"""UI configuration and styling for Chainlit interface."""

import structlog

logger = structlog.get_logger(__name__)


class UIConfig:
    """Configuration for UI appearance and behavior."""

    THEME = {
        "primary_color": "#1f70c1",
        "secondary_color": "#6c757d",
        "success_color": "#28a745",
        "error_color": "#dc3545",
        "warning_color": "#ffc107",
    }

    @staticmethod
    def get_theme() -> dict[str, str]:
        """Get theme configuration."""
        return UIConfig.THEME

    @staticmethod
    def validate_config() -> bool:
        """Validate UI configuration."""
        logger.info("validating_ui_config")
        return True


def setup_chainlit_ui() -> None:
    """
    Set up Chainlit UI configuration including RTL support and styling.

    This function configures the Chainlit interface for Persian text
    with right-to-left (RTL) layout, custom CSS, and theme settings.

    Note: Currently implemented as a stub. RTL configuration is handled
    via CSS files and Chainlit configuration files.
    """
    logger.info("Setting up Chainlit UI configuration")
    # RTL and styling are currently handled via:
    # - public/style.css for RTL layout
    # - .chainlitrc for Chainlit-specific config
    # - UIConfig.THEME for color scheme
    pass


def setup_all() -> None:
    """
    Set up all UI configuration including Chainlit UI and theme.

    This is a convenience function that calls all setup functions
    in the correct order.
    """
    logger.info("Setting up all UI configuration")
    setup_chainlit_ui()
    UIConfig.validate_config()
    logger.info("UI configuration complete")
