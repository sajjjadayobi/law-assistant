"""
Law Agent UI module - Chainlit interface for the legal assistant.

This module provides the web UI for the Law Agent, including:
- Chat interface with message handling
- RTL support for Persian text
- Citation linking to iran.ir
- Tool call visualization
- Feedback collection
- Conversation history management
"""

from law_agent.ui.citations import CitationFormatter
from law_agent.ui.steps import ToolStepManager

__all__ = ["CitationFormatter", "ToolStepManager"]
