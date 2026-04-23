"""Core Law Agent implementation using PydanticAI framework.

This module implements the LawAgent class that:
1. Orchestrates search tools (search_documents, get_document, get_related_documents)
2. Manages conversation history and state
3. Handles citations and follow-up question generation
4. Implements persona detection via system prompt
5. Provides error handling with Persian error messages

The agent is stateless (state is managed by ConversationManager).
Each call to run() should include conversation history and conversation ID.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import structlog
import yaml
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.openai import OpenAIModel

from law_agent.config.settings import get_settings
from law_agent.tools.search import (
    DocumentNotFoundError,
    get_document,
    get_related_documents,
    search_documents,
)

logger = structlog.get_logger(__name__)


class LawAgent:
    """Agentic legal research assistant powered by PydanticAI.

    This agent orchestrates three search tools to answer questions about Iranian law:
    1. search_documents() - Full-text search with filtering
    2. get_document() - Fetch complete document
    3. get_related_documents() - Follow citation graph

    The agent:
    - Decides search strategy at each step (agent-driven, not algorithmic)
    - Detects user persona and adapts response style (in system prompt)
    - Generates inline citations with iran.ir links
    - Produces 2-3 follow-up questions
    - Handles errors gracefully with Persian messages

    Key Design:
    - Stateless agent (state via ConversationManager)
    - System prompt loaded from prompts/system_prompt.yaml
    - Tools are simple, agent reasoning is complex
    - All Persian UI text always in Persian
    - Observable: all calls logged to structlog/Phoenix
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-5",
        system_prompt_path: Path | None = None,
        temperature: float = 0.0,
    ):
        """Initialize the Law Agent.

        Args:
            model: LLM model to use (default: claude-sonnet-4-5)
            system_prompt_path: Path to system_prompt.yaml
                                If None, loads from src/prompts/system_prompt.yaml
            temperature: LLM temperature (default: 0.0 for deterministic legal reasoning)
        """
        self.model = model
        self.temperature = temperature

        # Load settings to get LLM credentials (LLM_AUTH_TOKEN, LLM_BASE_URL)
        settings = get_settings()

        # Store settings for model initialization
        self.settings = settings

        # For custom LLM endpoints, use OpenAI-compatible provider
        if settings.model.base_url:
            # Custom endpoint (like LiteLLM) - use OpenAI provider
            logger.info("using_custom_llm_endpoint", base_url=settings.model.base_url)
            # Set environment variables for OpenAI provider
            if settings.model.auth_token:
                os.environ["OPENAI_API_KEY"] = settings.model.auth_token
            os.environ["OPENAI_BASE_URL"] = settings.model.base_url
        else:
            # Default Anthropic endpoint
            if settings.model.auth_token and not os.getenv("ANTHROPIC_API_KEY"):
                os.environ["ANTHROPIC_API_KEY"] = settings.model.auth_token
                logger.info("set_anthropic_api_key_from_llm_auth_token")

        # Load system prompt from YAML
        if system_prompt_path is None:
            system_prompt_path = Path(__file__).parent.parent / "prompts" / "system_prompt.yaml"

        self.system_prompt_path = system_prompt_path
        self._load_system_prompt()

        # Create PydanticAI agent
        self._create_agent()

        logger.info(
            "law_agent_initialized",
            model=model,
            temperature=temperature,
            system_prompt_path=str(system_prompt_path),
            has_auth_token=bool(settings.model.auth_token),
            has_base_url=bool(settings.model.base_url),
        )

    def _load_system_prompt(self) -> None:
        """Load system prompt from YAML file."""
        try:
            with open(self.system_prompt_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)

            self.system_prompt = config.get("system_prompt", "")
            self.prompt_metadata = config.get("metadata", {})
            self.search_config = config.get("search_config", {})

            if not self.system_prompt:
                raise ValueError("system_prompt not found in YAML file")

            logger.info(
                "system_prompt_loaded",
                path=str(self.system_prompt_path),
                metadata=self.prompt_metadata,
            )

        except Exception as e:
            logger.exception(
                "system_prompt_load_error",
                path=str(self.system_prompt_path),
                error=str(e),
            )
            raise

    def _create_agent(self) -> None:
        """Create PydanticAI agent with search tools."""
        # If custom base_url is set, use OpenAI-compatible provider
        if self.settings.model.base_url:
            # OpenAI provider with custom endpoint (base_url set via OPENAI_BASE_URL env var)
            model_instance = OpenAIModel(model_name=self.model)
        else:
            # Default: let PydanticAI infer the model provider
            model_instance = self.model

        self.agent = Agent(
            model=model_instance,
            system_prompt=self.system_prompt,
            tools=[
                self._search_documents_tool,
                self._get_document_tool,
                self._get_related_documents_tool,
            ],
            retries=1,  # Single retry for transient errors
        )

    @staticmethod
    async def _search_documents_tool(
        ctx: RunContext,
        query: str,
        tags: list[str] | None = None,
        doc_types: list[str] | None = None,
        limit: int = 20,
    ) -> str:
        """Tool: Search documents using full-text search.

        This tool is called by the agent to search for legal documents.
        Results are returned as JSON for the agent to parse.

        Args:
            ctx: PydanticAI RunContext
            query: Search query (Persian or English)
            tags: Optional subject tags to filter by
            doc_types: Optional document types to filter by
            limit: Maximum results (1-20, default 20)

        Returns:
            JSON string with search results for agent to parse
        """
        try:
            logger.info(
                "search_documents_tool_called",
                query=query,
                tags=tags,
                doc_types=doc_types,
                limit=limit,
            )

            # Clamp limit
            limit = min(max(1, limit), 20)

            # Call search function
            results = search_documents(
                query=query,
                tags=tags,
                doc_types=doc_types,
                limit=limit,
            )

            # Convert to JSON for agent
            results_json = json.dumps(
                [
                    {
                        "doc_id": r.doc_id,
                        "title": r.title,
                        "doc_type": r.doc_type,
                        "date": r.date,
                        "summary": r.summary[:200] + ("..." if len(r.summary) > 200 else ""),
                        "tags": r.tags,
                        "relevance_score": round(r.relevance_score, 3),
                    }
                    for r in results
                ],
                ensure_ascii=False,
                indent=2,
            )

            logger.info(
                "search_documents_tool_success",
                query=query,
                result_count=len(results),
            )

            return results_json

        except Exception as e:
            logger.exception(
                "search_documents_tool_error",
                query=query,
                error=str(e),
            )
            error_msg = f"خطا در جستجو: {str(e)}"
            return json.dumps({"error": error_msg}, ensure_ascii=False)

    @staticmethod
    async def _get_document_tool(ctx: RunContext, doc_id: int) -> str:
        """Tool: Fetch complete document content.

        This tool is called by the agent to load the full content of a document.
        The document is returned as JSON including full_content field.

        Args:
            ctx: PydanticAI RunContext
            doc_id: Document ID to fetch

        Returns:
            JSON string with complete document for agent to parse
        """
        try:
            logger.info("get_document_tool_called", doc_id=doc_id)

            # Call get_document function
            doc = get_document(doc_id)

            # Convert to JSON for agent
            doc_json = json.dumps(
                {
                    "doc_id": doc.doc_id,
                    "title": doc.title,
                    "doc_type": doc.doc_type,
                    "date": doc.date,
                    "summary": doc.summary,
                    "tags": doc.tags,
                    "full_content": doc.full_content,
                    "relations_count": doc.relations_count,
                },
                ensure_ascii=False,
                indent=2,
            )

            logger.info("get_document_tool_success", doc_id=doc_id)
            return doc_json

        except DocumentNotFoundError:
            logger.warning("get_document_tool_not_found", doc_id=doc_id)
            error_msg = f"سند شماره {doc_id} پیدا نشد"
            return json.dumps({"error": error_msg}, ensure_ascii=False)
        except Exception as e:
            logger.exception("get_document_tool_error", doc_id=doc_id, error=str(e))
            error_msg = f"خطا در دریافت سند: {str(e)}"
            return json.dumps({"error": error_msg}, ensure_ascii=False)

    @staticmethod
    async def _get_related_documents_tool(
        ctx: RunContext,
        doc_id: int,
        relation_types: list[str] | None = None,
        limit: int = 10,
    ) -> str:
        """Tool: Get related documents via citation graph.

        This tool is called by the agent to follow document relationships.
        Useful for finding parent laws, related articles, or precedents.

        Args:
            ctx: PydanticAI RunContext
            doc_id: Source document ID
            relation_types: Optional relation types to filter by
            limit: Maximum related documents (1-10, default 10)

        Returns:
            JSON string with related documents for agent to parse
        """
        try:
            logger.info(
                "get_related_documents_tool_called",
                doc_id=doc_id,
                relation_types=relation_types,
                limit=limit,
            )

            # Clamp limit
            limit = min(max(1, limit), 10)

            # Call get_related_documents function
            results = get_related_documents(
                doc_id=doc_id,
                relation_types=relation_types,
                limit=limit,
            )

            # Convert to JSON for agent
            results_json = json.dumps(
                [
                    {
                        "doc_id": r.doc_id,
                        "title": r.title,
                        "doc_type": r.doc_type,
                        "date": r.date,
                        "summary": r.summary[:200] + ("..." if len(r.summary) > 200 else ""),
                        "tags": r.tags,
                        "relevance_score": round(r.relevance_score, 3),
                    }
                    for r in results
                ],
                ensure_ascii=False,
                indent=2,
            )

            logger.info(
                "get_related_documents_tool_success",
                doc_id=doc_id,
                result_count=len(results),
            )

            return results_json

        except Exception as e:
            logger.exception(
                "get_related_documents_tool_error",
                doc_id=doc_id,
                error=str(e),
            )
            error_msg = f"خطا در دریافت اسناد مرتبط: {str(e)}"
            return json.dumps({"error": error_msg}, ensure_ascii=False)

    async def run(
        self,
        user_query: str,
        conversation_history: list[ModelMessage] | None = None,
        conversation_id: str | None = None,
    ) -> tuple[str, list[ModelMessage]]:
        """Run agent to answer a user query.

        Args:
            user_query: User's question in Persian
            conversation_history: List of previous messages in the conversation
                                 If None, starts fresh conversation
            conversation_id: Unique ID for tracking this conversation
                           If None, generates new UUID

        Returns:
            Tuple of (response_text, updated_message_history)
            - response_text: Agent's response in Persian with citations and follow-up questions
            - updated_message_history: Complete conversation history including current exchange

        Raises:
            Exception: If agent fails (logged and re-raised)
        """
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())

        try:
            logger.info(
                "law_agent_run_called",
                conversation_id=conversation_id,
                user_query_length=len(user_query),
            )

            # Run agent with conversation history
            result = await self.agent.run(
                user_query,
                message_history=conversation_history or [],
            )

            response_text = result.output
            # Get the complete updated message history including this exchange
            updated_history = result.all_messages()

            logger.info(
                "law_agent_run_success",
                conversation_id=conversation_id,
                response_length=len(response_text),
                message_history_length=len(updated_history),
            )

            return response_text, updated_history

        except Exception as e:
            logger.exception(
                "law_agent_run_error",
                conversation_id=conversation_id,
                error=str(e),
            )
            raise

    def get_agent_info(self) -> dict:
        """Get information about the agent configuration.

        Returns:
            Dictionary with agent metadata
        """
        return {
            "model": self.model,
            "temperature": self.temperature,
            "system_prompt_path": str(self.system_prompt_path),
            "prompt_metadata": self.prompt_metadata,
            "search_config": self.search_config,
        }
