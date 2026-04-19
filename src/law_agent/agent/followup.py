"""Follow-up question generation for agent responses.

This module handles extraction and generation of follow-up questions
to guide the user toward deeper exploration of legal topics.

The agent's system prompt already instructs it to generate 2-3 follow-up
questions after each answer. This module provides utilities to extract
and format them.
"""

from __future__ import annotations

import re
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


class FollowupQuestionExtractor:
    """Extract follow-up questions from agent responses.

    The agent naturally generates follow-up questions based on its response.
    This class helps extract and format them for display.
    """

    # Pattern to match follow-up questions section
    FOLLOWUP_PATTERN = re.compile(
        r"(?:سوالات پیگیری|پیشنهاد شده|سوالات مرتبط):?\s*\n((?:•|-|\d+\.)\s*.+\n?)+",
        re.MULTILINE | re.UNICODE,
    )

    # Pattern to match individual questions
    QUESTION_PATTERN = re.compile(r"(?:•|-|\d+\.)\s*(.+?)(?=\n|$)", re.UNICODE)

    @staticmethod
    def extract_followup_section(response_text: str) -> Optional[str]:
        """Extract follow-up questions section from response.

        Args:
            response_text: Full agent response

        Returns:
            Follow-up questions section if found, None otherwise
        """
        match = FollowupQuestionExtractor.FOLLOWUP_PATTERN.search(response_text)
        if match:
            return match.group(0)
        return None

    @staticmethod
    def extract_followup_questions(response_text: str) -> list[str]:
        """Extract individual follow-up questions from response.

        Args:
            response_text: Full agent response

        Returns:
            List of follow-up questions found
        """
        followup_section = FollowupQuestionExtractor.extract_followup_section(response_text)
        if not followup_section:
            return []

        questions = []
        for match in FollowupQuestionExtractor.QUESTION_PATTERN.finditer(followup_section):
            question = match.group(1).strip()
            if question and len(question) > 5:  # Filter out very short items
                questions.append(question)

        return questions[:3]  # Return max 3 questions

    @staticmethod
    def remove_followup_section(response_text: str) -> str:
        """Remove follow-up questions section from response.

        Useful if you want to separate the main answer from follow-ups.

        Args:
            response_text: Full agent response

        Returns:
            Response without follow-up questions section
        """
        # Remove everything from "سوالات پیگیری" onwards
        return re.split(
            r"(?:سوالات پیگیری|پیشنهاد شده|سوالات مرتبط)",
            response_text,
        )[0].strip()


class FollowupQuestionGenerator:
    """Generate follow-up questions based on response content.

    This class provides utilities for creating contextual follow-up questions
    to guide conversation. Note: The agent already generates these in its response,
    so this is mainly for formatting and extraction.
    """

    # Predefined follow-up question templates for different scenarios
    FOLLOWUP_TEMPLATES = {
        "clarification": "آیا می‌توانید در مورد {topic} بیشتر توضیح دهید؟",
        "related_topic": "آیا قوانین مرتبط با {related} برای شما مفید است؟",
        "specific_case": "این قانون چگونه در {case} اعمال می‌شود؟",
        "exceptions": "استثناهای این قانون چیست؟",
        "procedure": "روند قانونی برای {action} چیست؟",
    }

    @staticmethod
    def format_followup_questions(
        questions: list[str],
        include_header: bool = True,
    ) -> str:
        """Format follow-up questions as a section.

        Args:
            questions: List of follow-up questions in Persian
            include_header: Whether to include header "سوالات پیگیری:"

        Returns:
            Formatted follow-up questions section
        """
        if not questions:
            return ""

        lines = []
        if include_header:
            lines.append("\n\nسوالات پیگیری:")

        for question in questions:
            lines.append(f"• {question}")

        return "\n".join(lines)

    @staticmethod
    def extract_and_separate(
        response_text: str,
    ) -> tuple[str, list[str]]:
        """Separate response into main content and follow-up questions.

        Args:
            response_text: Full agent response

        Returns:
            Tuple of (main_response, followup_questions)
        """
        questions = FollowupQuestionExtractor.extract_followup_questions(response_text)
        main_response = FollowupQuestionExtractor.remove_followup_section(response_text)

        return main_response, questions


# Backward compatibility - expose main classes at module level
__all__ = [
    "FollowupQuestionExtractor",
    "FollowupQuestionGenerator",
]
