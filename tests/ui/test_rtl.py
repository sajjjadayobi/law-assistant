"""Tests for RTL (right-to-left) styling support."""

from __future__ import annotations

import pytest


class TestRTLStyles:
    """Test RTL CSS loading and application."""

    def test_rtl_css_exists(self) -> None:
        """Test that RTL CSS file exists."""
        from pathlib import Path

        rtl_css_path = (
            Path(__file__).parent.parent.parent / "src" / "law_agent" / "ui" / "static" / "rtl.css"
        )
        assert rtl_css_path.exists(), f"RTL CSS not found at {rtl_css_path}"

    def test_rtl_css_contains_direction(self) -> None:
        """Test that RTL CSS contains direction: rtl rules."""
        from pathlib import Path

        rtl_css_path = (
            Path(__file__).parent.parent.parent / "src" / "law_agent" / "ui" / "static" / "rtl.css"
        )

        with open(rtl_css_path, encoding="utf-8") as f:
            content = f.read()

        assert "direction: rtl" in content

    def test_rtl_css_contains_text_align(self) -> None:
        """Test that RTL CSS contains text-align: right rules."""
        from pathlib import Path

        rtl_css_path = (
            Path(__file__).parent.parent.parent / "src" / "law_agent" / "ui" / "static" / "rtl.css"
        )

        with open(rtl_css_path, encoding="utf-8") as f:
            content = f.read()

        assert "text-align: right" in content

    def test_rtl_css_contains_flex_reverse(self) -> None:
        """Test that RTL CSS contains flex-direction: row-reverse."""
        from pathlib import Path

        rtl_css_path = (
            Path(__file__).parent.parent.parent / "src" / "law_agent" / "ui" / "static" / "rtl.css"
        )

        with open(rtl_css_path, encoding="utf-8") as f:
            content = f.read()

        assert "flex-direction: row-reverse" in content or "row-reverse" in content


class TestPersianTextHandling:
    """Test Persian text rendering support."""

    def test_persian_text_encoding(self) -> None:
        """Test that Persian text can be encoded/decoded properly."""
        persian_text = "سلام دنیا"
        encoded = persian_text.encode("utf-8")
        decoded = encoded.decode("utf-8")
        assert decoded == persian_text

    def test_persian_citations(self) -> None:
        """Test Persian citations in response."""
        response = "طبق قانون [1]"
        from law_agent.ui.citations import CitationFormatter

        formatter = CitationFormatter()
        citations = formatter.extract_citations(response)
        assert citations == [1]

    def test_persian_example_questions(self) -> None:
        """Test Persian example questions loading."""
        from law_agent.config.settings import Settings

        settings = Settings()
        assert len(settings.ui.example_questions) > 0

        for question in settings.ui.example_questions:
            # Verify Persian text (contains Persian Unicode characters)
            assert any(
                "\u0600" <= c <= "\u06ff" for c in question
            ), f"Question doesn't contain Persian text: {question}"


class TestRTLIntegration:
    """Test RTL integration with Chainlit."""

    def test_chainlit_config_module_exists(self) -> None:
        """Test that Chainlit config module exists."""
        from law_agent.ui import config

        assert hasattr(config, "setup_chainlit_ui")
        assert hasattr(config, "setup_all")

    @pytest.mark.asyncio
    async def test_ui_module_imports(self) -> None:
        """Test that UI module can be imported."""
        from law_agent.ui import CitationFormatter, ToolStepManager, app

        assert app is not None
        assert CitationFormatter is not None
        assert ToolStepManager is not None
