"""Law Agent - Core agentic legal research assistant powered by PydanticAI.

This module exports the main LawAgent class and related utilities.
"""

from law_agent.agent.conversation import ConversationManager, ConversationState
from law_agent.agent.core import LawAgent

__all__ = ["LawAgent", "ConversationManager", "ConversationState"]
