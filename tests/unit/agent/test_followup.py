"""Unit tests for follow-up question generation and extraction.

Tests follow-up question extraction from responses and formatting.
"""

from law_assistant.agent.followup import (
    FollowupQuestionExtractor,
    FollowupQuestionGenerator,
)


class TestFollowupQuestionExtractor:
    """Tests for FollowupQuestionExtractor class."""

    def test_extract_followup_section(self):
        """Test extracting follow-up section from response."""
        response = """جواب اصلی

سوالات پیگیری:
• سوال اول؟
• سوال دوم؟"""

        section = FollowupQuestionExtractor.extract_followup_section(response)

        assert section is not None
        assert "سوالات پیگیری" in section
        assert "سوال اول" in section

    def test_extract_followup_section_not_found(self):
        """Test extracting when no follow-up section."""
        response = "فقط جواب بدون سوالات"

        section = FollowupQuestionExtractor.extract_followup_section(response)

        assert section is None

    def test_extract_followup_questions_single(self):
        """Test extracting single follow-up question."""
        response = """جواب

سوالات پیگیری:
• سوال اول؟"""

        questions = FollowupQuestionExtractor.extract_followup_questions(response)

        assert len(questions) >= 1
        assert any("اول" in q for q in questions)

    def test_extract_followup_questions_multiple(self):
        """Test extracting multiple follow-up questions."""
        response = """جواب

سوالات پیگیری:
• سوال اول؟
• سوال دوم؟
• سوال سوم؟"""

        questions = FollowupQuestionExtractor.extract_followup_questions(response)

        assert len(questions) >= 2

    def test_extract_followup_questions_with_dash_separator(self):
        """Test extracting questions with dash separator."""
        response = """جواب

سوالات پیگیری:
- سوال اول؟
- سوال دوم؟"""

        questions = FollowupQuestionExtractor.extract_followup_questions(response)

        assert len(questions) >= 1

    def test_extract_followup_questions_with_numbers(self):
        """Test extracting questions with number separators."""
        response = """جواب

سوالات پیگیری:
1. سوال اول؟
2. سوال دوم؟"""

        questions = FollowupQuestionExtractor.extract_followup_questions(response)

        assert len(questions) >= 1

    def test_extract_followup_questions_max_three(self):
        """Test that at most 3 questions are extracted."""
        response = """جواب

سوالات پیگیری:
• سوال ۱؟
• سوال ۲؟
• سوال ۳؟
• سوال ۴؟
• سوال ۵؟"""

        questions = FollowupQuestionExtractor.extract_followup_questions(response)

        assert len(questions) <= 3

    def test_extract_followup_questions_none(self):
        """Test extracting when no follow-up section."""
        response = "فقط جواب بدون سوالات"

        questions = FollowupQuestionExtractor.extract_followup_questions(response)

        assert questions == []

    def test_remove_followup_section(self):
        """Test removing follow-up section from response."""
        response = """جواب اصلی

سوالات پیگیری:
• سوال اول؟"""

        cleaned = FollowupQuestionExtractor.remove_followup_section(response)

        assert "جواب اصلی" in cleaned
        assert "سوالات پیگیری" not in cleaned
        assert "سوال اول" not in cleaned

    def test_remove_followup_section_no_section(self):
        """Test removing when no follow-up section."""
        response = "فقط جواب"

        cleaned = FollowupQuestionExtractor.remove_followup_section(response)

        assert cleaned == "فقط جواب"


class TestFollowupQuestionGenerator:
    """Tests for FollowupQuestionGenerator class."""

    def test_format_followup_questions_with_header(self):
        """Test formatting questions with header."""
        questions = ["سوال اول؟", "سوال دوم؟"]

        formatted = FollowupQuestionGenerator.format_followup_questions(
            questions,
            include_header=True,
        )

        assert "سوالات پیگیری:" in formatted
        assert "سوال اول؟" in formatted
        assert "سوال دوم؟" in formatted

    def test_format_followup_questions_without_header(self):
        """Test formatting questions without header."""
        questions = ["سوال اول؟", "سوال دوم؟"]

        formatted = FollowupQuestionGenerator.format_followup_questions(
            questions,
            include_header=False,
        )

        assert "سوالات پیگیری:" not in formatted
        assert "سوال اول؟" in formatted
        assert "•" in formatted

    def test_format_followup_questions_empty(self):
        """Test formatting empty questions list."""
        formatted = FollowupQuestionGenerator.format_followup_questions([])

        assert formatted == ""

    def test_extract_and_separate(self):
        """Test separating response into content and questions."""
        response = """جواب اصلی

سوالات پیگیری:
• سوال اول؟
• سوال دوم؟"""

        main, questions = FollowupQuestionGenerator.extract_and_separate(response)

        assert "جواب اصلی" in main
        assert "سوالات پیگیری" not in main
        assert len(questions) >= 1

    def test_extract_and_separate_no_questions(self):
        """Test separating when no follow-up questions."""
        response = "فقط جواب"

        main, questions = FollowupQuestionGenerator.extract_and_separate(response)

        assert main == "فقط جواب"
        assert questions == []

    def test_followup_templates_exist(self):
        """Test that followup templates are defined."""
        templates = FollowupQuestionGenerator.FOLLOWUP_TEMPLATES

        assert "clarification" in templates
        assert "related_topic" in templates
        assert "specific_case" in templates

    def test_followup_templates_contain_placeholders(self):
        """Test that templates are non-empty questions."""
        templates = FollowupQuestionGenerator.FOLLOWUP_TEMPLATES

        for key, template in templates.items():
            # Each template should be a non-empty string
            assert isinstance(template, str), f"Template {key} is not a string"
            assert len(template) > 0, f"Template {key} is empty"
            # Templates may have placeholders {topic} or be static questions (with ? or Persian ؟)
            has_question = "?" in template or "؟" in template
            has_placeholder = "{" in template
            assert (
                has_question or has_placeholder
            ), f"Template {key} should be a question or have placeholder"

    def test_persian_questions_preserved(self):
        """Test that Persian text in questions is preserved."""
        response = """پاسخ به فارسی

سوالات پیگیری:
• آیا می‌توانید درباره موضوع بیشتر بگویید؟"""

        main, questions = FollowupQuestionGenerator.extract_and_separate(response)

        # Should preserve Persian characters
        if questions:
            for q in questions:
                # Question should contain Persian characters
                assert any(ord(c) >= 1536 for c in q)
