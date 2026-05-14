"""Law Agent - Core agentic legal research assistant powered by PydanticAI.

This module exports the main LawAgent class and related utilities.
"""

from law_assistant.agent.conversation import ConversationManager, ConversationState
from law_assistant.agent.core import LawAgent

__all__ = ["LawAgent", "ConversationManager", "ConversationState"]
