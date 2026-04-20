"""Accessibility utilities for the Chainlit UI."""

from dataclasses import dataclass
from typing import Optional, Dict, Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class AccessibilityLabel:
    """ARIA label for accessible components."""

    text: str
    description: Optional[str] = None
    hint: Optional[str] = None

    def to_aria(self) -> str:
        """Convert to ARIA label string.

        Returns:
            Formatted ARIA label
        """
        parts = [self.text]
        if self.description:
            parts.append(self.description)
        if self.hint:
            parts.append(f"({self.hint})")
        return " ".join(parts)


class AccessibilityConfig:
    """Configuration for accessibility features."""

    # Keyboard shortcuts
    KEYBOARD_SHORTCUTS = {
        "send_message": {"key": "Enter", "description": "Send message"},
        "open_history": {"key": "Cmd/Ctrl+H", "description": "Open conversation history"},
        "clear_chat": {"key": "Cmd/Ctrl+K", "description": "Clear current chat"},
        "focus_input": {"key": "Cmd/Ctrl+L", "description": "Focus message input"},
    }

    # ARIA labels for common elements
    ARIA_LABELS = {
        "message_input": AccessibilityLabel(
            "Message input field",
            description="Type your legal question here",
            hint="Use Enter to send or Shift+Enter for new line",
        ),
        "send_button": AccessibilityLabel(
            "Send message button",
            description="Send your question to the legal assistant",
        ),
        "thinking_indicator": AccessibilityLabel(
            "Agent thinking",
            description="The AI is processing your question",
            hint="This usually takes 5-10 seconds",
        ),
        "citations": AccessibilityLabel(
            "Legal citations",
            description="Links to official legal documents",
            hint="Click to open document in new tab",
        ),
        "feedback_thumbs_up": AccessibilityLabel(
            "Helpful response",
            description="Mark this response as helpful",
        ),
        "feedback_thumbs_down": AccessibilityLabel(
            "Unhelpful response",
            description="Mark this response as unhelpful",
        ),
        "followup_questions": AccessibilityLabel(
            "Suggested follow-up questions",
            description="Click any question to continue the conversation",
        ),
    }

    # Error messages with helpful suggestions
    ERROR_MESSAGES = {
        "no_documents_found": {
            "title": "متأسفانه، مستندی یافت نشد",
            "message": "نتوانستیم اطلاعات مربوط به سؤال شما پیدا کنیم.",
            "suggestions": [
                "سؤال را با کلمات کلیدی متفاوت مطرح کنید",
                "از اصطلاحات قانونی استفاده کنید",
                "سؤال را ساده تر کنید",
            ],
        },
        "timeout": {
            "title": "زمان درخواست پایان یافت",
            "message": "درخواست شما بیش از حد مورد انتظار طول کشید.",
            "suggestions": [
                "دوباره تلاش کنید",
                "سؤال را ساده تر کنید",
                "اینترنت خود را بررسی کنید",
            ],
        },
        "server_error": {
            "title": "خطای سرور",
            "message": "مشکلی در پردازش درخواست شما پیش آمد.",
            "suggestions": [
                "صفحه را تازه کنید",
                "دوباره تلاش کنید",
                "اگر مشکل ادامه یافت، با پشتیبانی تماس بگیرید",
            ],
        },
    }

    @staticmethod
    def get_keyboard_shortcuts() -> Dict[str, Dict[str, str]]:
        """Get keyboard shortcuts for user assistance.

        Returns:
            Dictionary of shortcuts
        """
        return AccessibilityConfig.KEYBOARD_SHORTCUTS

    @staticmethod
    def get_aria_label(component: str) -> str:
        """Get ARIA label for component.

        Args:
            component: Component name

        Returns:
            ARIA label string
        """
        label = AccessibilityConfig.ARIA_LABELS.get(component)
        if label:
            return label.to_aria()
        return component

    @staticmethod
    def get_error_response(error_type: str) -> Dict[str, Any]:
        """Get user-friendly error message.

        Args:
            error_type: Type of error

        Returns:
            Dictionary with error message and suggestions
        """
        return AccessibilityConfig.ERROR_MESSAGES.get(
            error_type,
            {
                "title": "مشکلی پیش آمد",
                "message": "لطفاً دوباره تلاش کنید",
                "suggestions": ["تلاش مجدد", "برای کمک پشتیبانی را تماس بگیرید"],
            },
        )


class AccessibilityHelper:
    """Helper functions for accessibility features."""

    @staticmethod
    def format_error_message(error_type: str) -> str:
        """Format error message for display.

        Args:
            error_type: Type of error

        Returns:
            Formatted error message in Persian
        """
        error_info = AccessibilityConfig.get_error_response(error_type)

        message_parts = [f"**{error_info['title']}**"]
        message_parts.append(error_info["message"])

        if error_info.get("suggestions"):
            message_parts.append("\n**پیشنهادات:**")
            for suggestion in error_info["suggestions"]:
                message_parts.append(f"• {suggestion}")

        return "\n\n".join(message_parts)

    @staticmethod
    def get_loading_status_message(step: int, total_steps: int = 3) -> str:
        """Get loading status message.

        Args:
            step: Current step (1-indexed)
            total_steps: Total steps in process

        Returns:
            Status message in Persian
        """
        steps = [
            "جستجو در مستندات قانونی...",
            "تجزیه و تحلیل نتایج...",
            "تدوین پاسخ...",
        ]

        if step <= len(steps):
            status = steps[step - 1]
        else:
            status = "تکمیل درخواست..."

        progress_bar = "█" * step + "░" * (total_steps - step)
        return f"{status} [{progress_bar}]"

    @staticmethod
    def format_keyboard_help() -> str:
        """Format keyboard shortcuts for display.

        Returns:
            Formatted help text
        """
        shortcuts = AccessibilityConfig.get_keyboard_shortcuts()

        help_text = "**میانبرهای صفحه کلید:**\n"
        for action, info in shortcuts.items():
            key = info["key"]
            desc = info["description"]
            help_text += f"• **{key}**: {desc}\n"

        return help_text

    @staticmethod
    def log_accessibility_event(event_type: str, details: Dict[str, Any]) -> None:
        """Log accessibility-related events.

        Args:
            event_type: Type of event
            details: Event details
        """
        logger.info(
            "accessibility_event",
            event_type=event_type,
            **details,
        )


class AccessibilityReport:
    """Generates accessibility audit reports."""

    def __init__(self):
        """Initialize accessibility report."""
        self.issues = []
        self.suggestions = []

    def add_issue(self, component: str, issue: str, severity: str = "warning"):
        """Add accessibility issue.

        Args:
            component: Component name
            issue: Issue description
            severity: Severity level (info, warning, error)
        """
        self.issues.append({
            "component": component,
            "issue": issue,
            "severity": severity,
        })

    def add_suggestion(self, component: str, suggestion: str):
        """Add accessibility suggestion.

        Args:
            component: Component name
            suggestion: Suggestion description
        """
        self.suggestions.append({
            "component": component,
            "suggestion": suggestion,
        })

    def generate_report(self) -> Dict[str, Any]:
        """Generate accessibility report.

        Returns:
            Report dictionary
        """
        return {
            "total_issues": len(self.issues),
            "total_suggestions": len(self.suggestions),
            "issues": self.issues,
            "suggestions": self.suggestions,
            "scores": {
                "wcag_aa": self._calculate_wcag_score(),
                "overall_accessibility": self._calculate_overall_score(),
            },
        }

    def _calculate_wcag_score(self) -> int:
        """Calculate WCAG AA compliance score.

        Returns:
            Score out of 100
        """
        error_count = sum(1 for i in self.issues if i["severity"] == "error")
        warning_count = sum(1 for i in self.issues if i["severity"] == "warning")

        score = 100 - (error_count * 10) - (warning_count * 5)
        return max(0, score)

    def _calculate_overall_score(self) -> int:
        """Calculate overall accessibility score.

        Returns:
            Score out of 100
        """
        total_issues = len(self.issues)
        total_suggestions = len(self.suggestions)

        # Start with WCAG score
        wcag_score = self._calculate_wcag_score()

        # Deduct for unimplemented suggestions
        suggestion_penalty = min(total_suggestions * 2, 20)

        return max(0, wcag_score - suggestion_penalty)

    def print_report(self) -> None:
        """Print formatted accessibility report."""
        report = self.generate_report()

        print("\n" + "=" * 80)
        print("ACCESSIBILITY AUDIT REPORT")
        print("=" * 80)

        print(f"\nWCAG AA Score: {report['scores']['wcag_aa']}/100")
        print(f"Overall Accessibility Score: {report['scores']['overall_accessibility']}/100")

        if report["total_issues"] > 0:
            print(f"\nIssues Found: {report['total_issues']}")
            for issue in report["issues"]:
                severity = issue["severity"].upper()
                print(f"  [{severity}] {issue['component']}: {issue['issue']}")

        if report["total_suggestions"] > 0:
            print(f"\nSuggestions: {report['total_suggestions']}")
            for suggestion in report["suggestions"]:
                print(f"  • {suggestion['component']}: {suggestion['suggestion']}")

        print("\n" + "=" * 80)
