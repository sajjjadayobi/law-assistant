"""UI configuration and styling for Chainlit interface."""

from typing import Dict, Any
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
    def get_theme() -> Dict[str, str]:
        """Get theme configuration."""
        return UIConfig.THEME

    @staticmethod
    def validate_config() -> bool:
        """Validate UI configuration."""
        logger.info("validating_ui_config")
        return True
