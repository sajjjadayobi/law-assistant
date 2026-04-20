"""Agent response caching for reducing API calls and latency."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import structlog

from .cache import LRUCache

logger = structlog.get_logger(__name__)


@dataclass
class CachedResponse:
    """Container for cached agent response."""

    query: str
    persona: str
    response: str
    citations: list
    follow_ups: list
    timestamp: str
    tokens_saved: int = 0


class ResponseCache:
    """Caches agent responses to reduce LLM API calls."""

    def __init__(
        self,
        max_size: int = 500,
        ttl_days: int = 5,
    ):
        """Initialize response cache.

        Args:
            max_size: Maximum number of cached responses
            ttl_days: Time-to-live for cached responses in days
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_days * 86400
        self.cache = LRUCache[CachedResponse](
            max_size=max_size,
            ttl_seconds=self.ttl_seconds,
        )
        self.tokens_saved = 0

    @staticmethod
    def _generate_cache_key(
        query: str,
        persona: str,
    ) -> str:
        """Generate cache key for query.

        Args:
            query: User query
            persona: Detected persona (layperson, business, legal)

        Returns:
            Hash-based cache key
        """
        # Normalize query (lowercase, strip whitespace)
        normalized = query.lower().strip()

        # Create consistent key with persona
        key_data = {
            "query": normalized,
            "persona": persona,
        }

        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(
        self,
        query: str,
        persona: str,
    ) -> Optional[CachedResponse]:
        """Get cached response.

        Args:
            query: User query
            persona: Detected persona

        Returns:
            Cached response or None if not found
        """
        key = self._generate_cache_key(query, persona)
        cached = self.cache.get(key)

        if cached:
            logger.info(
                "response_cache_hit",
                query=query[:50],
                persona=persona,
            )

        return cached

    def set(
        self,
        query: str,
        persona: str,
        response: str,
        citations: list,
        follow_ups: list,
        tokens_saved: int = 0,
    ) -> None:
        """Cache agent response.

        Args:
            query: User query
            persona: Detected persona
            response: Agent response text
            citations: List of citation references
            follow_ups: List of follow-up questions
            tokens_saved: Estimated tokens saved (for cost tracking)
        """
        key = self._generate_cache_key(query, persona)

        cached_response = CachedResponse(
            query=query,
            persona=persona,
            response=response,
            citations=citations,
            follow_ups=follow_ups,
            timestamp=datetime.now().isoformat(),
            tokens_saved=tokens_saved,
        )

        self.cache.put(key, cached_response)
        self.tokens_saved += tokens_saved

        logger.info(
            "response_cached",
            query=query[:50],
            persona=persona,
            response_length=len(response),
            tokens_saved=tokens_saved,
        )

    def clear(self) -> None:
        """Clear all cached responses."""
        self.cache.clear()
        self.tokens_saved = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        cache_stats = self.cache.get_stats()
        return {
            **cache_stats,
            "ttl_days": self.ttl_seconds // 86400,
            "total_tokens_saved": self.tokens_saved,
        }

    def get_cost_savings(
        self,
        input_cost_per_1k: float = 0.003,
        output_cost_per_1k: float = 0.015,
    ) -> Dict[str, float]:
        """Calculate estimated cost savings from cache hits.

        Args:
            input_cost_per_1k: Cost per 1K input tokens (default: Sonnet 4.5)
            output_cost_per_1k: Cost per 1K output tokens

        Returns:
            Dictionary with cost estimates
        """
        cache_stats = self.get_stats()

        # Rough estimates:
        # - Average input: 500 tokens
        # - Average output: 800 tokens
        # - Cache hit saves both input and output
        avg_tokens_per_hit = 1300

        hits = cache_stats.get("hits", 0)
        tokens_saved = hits * avg_tokens_per_hit

        input_tokens_saved = hits * 500
        output_tokens_saved = hits * 800

        input_cost_saved = (input_tokens_saved / 1000) * input_cost_per_1k
        output_cost_saved = (output_tokens_saved / 1000) * output_cost_per_1k
        total_cost_saved = input_cost_saved + output_cost_saved

        return {
            "cache_hits": hits,
            "tokens_saved": tokens_saved,
            "input_cost_saved": round(input_cost_saved, 4),
            "output_cost_saved": round(output_cost_saved, 4),
            "total_cost_saved": round(total_cost_saved, 4),
        }


# Global response cache instance
_response_cache = ResponseCache()


def get_response_cache() -> ResponseCache:
    """Get global response cache instance.

    Returns:
        ResponseCache instance
    """
    return _response_cache


def cache_agent_response(
    func,
) -> callable:
    """Decorator for caching agent responses.

    Example:
        @cache_agent_response
        async def answer_question(query, persona):
            # ... agent logic ...
            return response, citations, follow_ups
    """

    async def wrapper(
        query: str,
        persona: str,
        **kwargs,
    ):
        cache = get_response_cache()

        # Try to get from cache
        cached = cache.get(query, persona)
        if cached:
            return {
                "response": cached.response,
                "citations": cached.citations,
                "follow_ups": cached.follow_ups,
                "from_cache": True,
            }

        # Cache miss - call function
        result = await func(query, persona=persona, **kwargs)

        # Extract components
        response = result.get("response", "")
        citations = result.get("citations", [])
        follow_ups = result.get("follow_ups", [])
        tokens_used = result.get("tokens_used", 0)

        # Estimate tokens saved if this was cached
        # Assume ~1300 tokens per response on average
        tokens_saved = 1300

        # Cache the response
        cache.set(
            query,
            persona,
            response,
            citations,
            follow_ups,
            tokens_saved=tokens_saved,
        )

        result["from_cache"] = False
        return result

    return wrapper
