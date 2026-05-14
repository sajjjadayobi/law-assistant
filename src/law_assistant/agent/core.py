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
from collections.abc import Awaitable, Callable
from pathlib import Path

import chainlit as cl
import httpx
import structlog
import yaml
from opentelemetry import trace as otel_trace
from pydantic_ai import Agent, RunContext
from pydantic_ai.agent import CallToolsNode
from pydantic_ai.messages import ModelMessage, ToolCallPart
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.profiles.openai import OpenAIModelProfile
from pydantic_ai.providers.openai import OpenAIProvider

from law_assistant.config.settings import get_settings
from law_assistant.observability.tracer import get_tracer
from law_assistant.tools.search import (
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
            "law_assistant_initialized",
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
        if self.settings.model.base_url:
            http_client = httpx.AsyncClient(timeout=30.0)
            provider = OpenAIProvider(
                base_url=self.settings.model.base_url,
                api_key=self.settings.model.auth_token,
                http_client=http_client,
            )
            # openai_supports_strict_tool_definition=False removes "strict": true
            # from tool schemas — required for non-OpenAI providers like MetisAI
            profile = OpenAIModelProfile(openai_supports_strict_tool_definition=False)
            model_instance = OpenAIModel(
                model_name=self.model, provider=provider, profile=profile
            )
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
            retries=self.settings.model.retries,
        )

    @staticmethod
    async def _search_documents_tool(
        ctx: RunContext,
        query: str,
        tags: list[str] = [],
        doc_types: list[str] = [],
        limit: int = 20,
    ) -> str:
        """Tool: Search documents using full-text search."""
        settings = get_settings()
        limit = min(max(1, limit), settings.search.max_results)
        logger.info(
            "search_documents_tool_called", query=query, tags=tags, doc_types=doc_types, limit=limit
        )

        tracer = get_tracer("law-agent-tools")
        tool_input = json.dumps(
            {"query": query, "tags": tags or [], "doc_types": doc_types or [], "limit": limit},
            ensure_ascii=False,
        )

        with tracer.start_as_current_span("search_documents") as span:
            span.set_attribute("openinference.span.kind", "TOOL")
            span.set_attribute("tool.name", "search_documents")
            span.set_attribute("input.value", tool_input)

            async with cl.Step(name="در حال جستجو ...", type="retrieval", show_input=False) as step:
                try:
                    results = search_documents(
                        query=query, tags=tags, doc_types=doc_types, limit=limit
                    )

                    if results:
                        step.name = f"🔍 {query} — {len(results)} سند یافت شد"
                        step.output = "\n\n".join(
                            f"**{r.title}**\n"
                            f"{r.summary[:150]}{'...' if len(r.summary) > 150 else ''}"
                            for r in results
                        )
                    else:
                        step.name = f"🔍 {query} — نتیجه‌ای یافت نشد"
                        step.output = "سندی با این عبارت پیدا نشد. ممکن است با کلمات دیگری جستجو شود."

                    results_json = json.dumps(
                        [
                            {
                                "doc_id": r.doc_id,
                                "title": r.title,
                                "doc_type": r.doc_type,
                                "date": r.date,
                                "summary": r.summary[:200]
                                + ("..." if len(r.summary) > 200 else ""),
                                "tags": r.tags,
                                "relevance_score": round(r.relevance_score, 3),
                            }
                            for r in results
                        ],
                        ensure_ascii=False,
                        indent=2,
                    )
                    titles = "\n".join(f"[{r.doc_id}] {r.title}" for r in results)
                    span.set_attribute("output.value", titles if results else "no results")
                    logger.info(
                        "search_documents_tool_success", query=query, result_count=len(results)
                    )
                    return results_json

                except Exception as e:
                    logger.exception("search_documents_tool_error", query=query, error=str(e))
                    step.name = "جستجو — خطا"
                    step.output = f"خطا در جستجو: {e}"
                    span.set_attribute("output.value", f"error: {e}")
                    return json.dumps({"error": f"خطا در جستجو: {e}"}, ensure_ascii=False)

    @staticmethod
    async def _get_document_tool(ctx: RunContext, doc_id: int) -> str:
        """Tool: Fetch complete document content."""
        logger.info("get_document_tool_called", doc_id=doc_id)

        tracer = get_tracer("law-agent-tools")
        with tracer.start_as_current_span("get_document") as span:
            span.set_attribute("openinference.span.kind", "TOOL")
            span.set_attribute("tool.name", "get_document")
            span.set_attribute("input.value", json.dumps({"doc_id": doc_id}))

            async with cl.Step(
                name="در حال خواندن سند ...", type="retrieval", show_input=False
            ) as step:
                try:
                    doc = get_document(doc_id)
                    step.name = f"خواندن سند — {doc.title}"
                    date_part = f"\n_{doc.date}_" if doc.date else ""
                    step.output = f"**{doc.title}**{date_part}\n\n{doc.summary[:300]}{'...' if len(doc.summary) > 300 else ''}"

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
                    meta_line = doc.date or ""
                    doc_output = f"[{doc.doc_id}] {doc.title}\n{meta_line}\n\n{doc.summary}"
                    if doc.full_content and doc.full_content != doc.summary:
                        doc_output += f"\n\n---\n{doc.full_content[:3000]}"
                    span.set_attribute("output.value", doc_output)
                    logger.info("get_document_tool_success", doc_id=doc_id)
                    return doc_json

                except DocumentNotFoundError:
                    logger.warning("get_document_tool_not_found", doc_id=doc_id)
                    step.name = f"سند {doc_id} پیدا نشد"
                    step.output = f"سند شماره {doc_id} در پایگاه داده موجود نیست."
                    span.set_attribute("output.value", f"not found: {doc_id}")
                    return json.dumps({"error": f"سند شماره {doc_id} پیدا نشد"}, ensure_ascii=False)
                except Exception as e:
                    logger.exception("get_document_tool_error", doc_id=doc_id, error=str(e))
                    step.name = "خواندن سند — خطا"
                    step.output = f"خطا: {e}"
                    span.set_attribute("output.value", f"error: {e}")
                    return json.dumps({"error": f"خطا در دریافت سند: {e}"}, ensure_ascii=False)

    @staticmethod
    async def _get_related_documents_tool(
        ctx: RunContext,
        doc_id: int,
        relation_types: list[str] = [],
        limit: int = 10,
    ) -> str:
        """Tool: Get related documents via citation graph."""
        settings = get_settings()
        limit = min(max(1, limit), settings.search.related_docs_default_limit)
        logger.info(
            "get_related_documents_tool_called",
            doc_id=doc_id,
            relation_types=relation_types,
            limit=limit,
        )

        tracer = get_tracer("law-agent-tools")
        tool_input = json.dumps(
            {"doc_id": doc_id, "relation_types": relation_types or [], "limit": limit}
        )

        with tracer.start_as_current_span("get_related_documents") as span:
            span.set_attribute("openinference.span.kind", "TOOL")
            span.set_attribute("tool.name", "get_related_documents")
            span.set_attribute("input.value", tool_input)

            async with cl.Step(
                name="در حال جستجوی اسناد مرتبط ...", type="retrieval", show_input=False
            ) as step:
                try:
                    results = get_related_documents(
                        doc_id=doc_id, relation_types=relation_types, limit=limit
                    )

                    if results:
                        step.name = f"اسناد مرتبط — {len(results)} سند"
                        step.output = "\n".join(f"- **{r.title}**" for r in results)
                    else:
                        step.name = "اسناد مرتبط — موردی یافت نشد"
                        step.output = "هیچ سند مرتبطی یافت نشد."

                    results_json = json.dumps(
                        [
                            {
                                "doc_id": r.doc_id,
                                "title": r.title,
                                "doc_type": r.doc_type,
                                "date": r.date,
                                "summary": r.summary[:200]
                                + ("..." if len(r.summary) > 200 else ""),
                                "tags": r.tags,
                                "relevance_score": round(r.relevance_score, 3),
                            }
                            for r in results
                        ],
                        ensure_ascii=False,
                        indent=2,
                    )
                    related_titles = "\n".join(f"[{r.doc_id}] {r.title}" for r in results)
                    span.set_attribute("output.value", related_titles if results else "no results")
                    logger.info(
                        "get_related_documents_tool_success",
                        doc_id=doc_id,
                        result_count=len(results),
                    )
                    return results_json

                except Exception as e:
                    logger.exception(
                        "get_related_documents_tool_error", doc_id=doc_id, error=str(e)
                    )
                    step.name = "اسناد مرتبط — خطا"
                    step.output = f"خطا: {e}"
                    span.set_attribute("output.value", f"error: {e}")
                    return json.dumps(
                        {"error": f"خطا در دریافت اسناد مرتبط: {e}"}, ensure_ascii=False
                    )

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
                "law_assistant_run_called",
                conversation_id=conversation_id,
                user_query_length=len(user_query),
            )

            async with self.agent.iter(
                user_query,
                message_history=conversation_history or [],
            ) as agent_run:
                async for node in agent_run:
                    if isinstance(node, CallToolsNode):
                        pass  # tool steps render themselves inside each tool function

            response_text = agent_run.result.output
            updated_history = agent_run.result.all_messages()

            # Attach token counts to the parent CHAIN span (user_turn in app.py).
            # All tool sub-spans are closed at this point so get_current_span()
            # returns user_turn. Phoenix uses these to compute cost.
            usage = agent_run.result.usage()
            parent_span = otel_trace.get_current_span()
            if parent_span.is_recording() and usage:
                parent_span.set_attribute("llm.token_count.prompt", usage.request_tokens or 0)
                parent_span.set_attribute("llm.token_count.completion", usage.response_tokens or 0)
                parent_span.set_attribute("llm.token_count.total", usage.total_tokens or 0)
                parent_span.set_attribute("llm.model_name", self.model)

            logger.info(
                "law_assistant_run_success",
                conversation_id=conversation_id,
                response_length=len(response_text),
                message_history_length=len(updated_history),
                request_tokens=getattr(usage, "request_tokens", 0),
                response_tokens=getattr(usage, "response_tokens", 0),
            )

            return response_text, updated_history

        except Exception as e:
            logger.exception(
                "law_assistant_run_error",
                conversation_id=conversation_id,
                error=str(e),
            )
            raise

    async def run_streaming(
        self,
        user_query: str,
        conversation_history: list[ModelMessage] | None = None,
        conversation_id: str | None = None,
        on_delta: Callable[[str], Awaitable[None]] | None = None,
    ) -> tuple[str, list[ModelMessage]]:
        """Run agent with token-by-token streaming via callback.

        Tool call steps (جستجو، خواندن سند) still render via cl.Step inside each tool.
        The synthetic planning step (تحلیل سوال) is not shown in streaming mode.

        Args:
            on_delta: Async callback invoked with each text token as it arrives.

        Returns:
            Tuple of (full_response_text, updated_message_history)
        """
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())

        try:
            logger.info(
                "law_assistant_run_streaming_called",
                conversation_id=conversation_id,
                user_query_length=len(user_query),
            )

            full_text = ""
            async with self.agent.run_stream(
                user_query,
                message_history=conversation_history or [],
            ) as result:
                async for delta in result.stream_text(delta=True):
                    full_text += delta
                    if on_delta:
                        await on_delta(delta)

            updated_history = result.all_messages()

            # Attach token counts to the parent CHAIN span (same as non-streaming run).
            usage = result.usage()
            parent_span = otel_trace.get_current_span()
            if parent_span.is_recording() and usage:
                parent_span.set_attribute("llm.token_count.prompt", usage.request_tokens or 0)
                parent_span.set_attribute("llm.token_count.completion", usage.response_tokens or 0)
                parent_span.set_attribute("llm.token_count.total", usage.total_tokens or 0)
                parent_span.set_attribute("llm.model_name", self.model)

            logger.info(
                "law_assistant_run_streaming_success",
                conversation_id=conversation_id,
                response_length=len(full_text),
                request_tokens=getattr(usage, "request_tokens", 0),
                response_tokens=getattr(usage, "response_tokens", 0),
            )

            return full_text, updated_history

        except Exception as e:
            logger.exception(
                "law_assistant_run_streaming_error",
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
