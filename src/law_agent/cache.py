"""Caching utilities for performance optimization."""

import hashlib
import json
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, Generic, Tuple
from collections import OrderedDict

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class LRUCache(Generic[T]):
    """Least Recently Used (LRU) cache implementation."""

    def __init__(self, max_size: int = 1000, ttl_seconds: Optional[int] = None):
        """Initialize LRU cache.

        Args:
            max_size: Maximum number of items to store
            ttl_seconds: Time-to-live for cached items (None = no expiry)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[T]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        if key not in self.cache:
            self.misses += 1
            return None

        value, timestamp = self.cache[key]

        # Check TTL
        if self.ttl_seconds and (time.time() - timestamp) > self.ttl_seconds:
            del self.cache[key]
            self.misses += 1
            return None

        # Move to end (most recently used)
        self.cache.move_to_end(key)
        self.hits += 1
        return value

    def put(self, key: str, value: T) -> None:
        """Put value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        # Remove oldest item if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        # Add or update value
        self.cache[key] = (value, time.time())
        self.cache.move_to_end(key)

    def clear(self) -> None:
        """Clear all cached items."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with hit rate and size info
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0.0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2),
            "ttl_seconds": self.ttl_seconds,
        }


class QueryCache:
    """Cache for database query results."""

    def __init__(self, max_size: int = 1000):
        """Initialize query cache.

        Args:
            max_size: Maximum cache size
        """
        # Search results cache (1 hour TTL)
        self.search_cache = LRUCache[list](max_size=max_size // 2, ttl_seconds=3600)
        # Document cache (24 hour TTL)
        self.doc_cache = LRUCache[dict](max_size=max_size // 2, ttl_seconds=86400)

    def get_search_cache_key(
        self,
        query: str,
        tags: Optional[list] = None,
        doc_types: Optional[list] = None,
        limit: int = 20,
    ) -> str:
        """Generate cache key for search query.

        Args:
            query: Search query
            tags: Optional tag filters
            doc_types: Optional document type filters
            limit: Result limit

        Returns:
            Cache key
        """
        cache_dict = {
            "query": query.lower().strip(),
            "tags": sorted(tags) if tags else None,
            "doc_types": sorted(doc_types) if doc_types else None,
            "limit": limit,
        }
        cache_str = json.dumps(cache_dict, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def get_document_cache_key(self, doc_id: int) -> str:
        """Generate cache key for document.

        Args:
            doc_id: Document ID

        Returns:
            Cache key
        """
        return f"doc_{doc_id}"

    def get_search_result(
        self,
        query: str,
        tags: Optional[list] = None,
        doc_types: Optional[list] = None,
        limit: int = 20,
    ) -> Optional[list]:
        """Get cached search result.

        Args:
            query: Search query
            tags: Optional tag filters
            doc_types: Optional document type filters
            limit: Result limit

        Returns:
            Cached result or None
        """
        key = self.get_search_cache_key(query, tags, doc_types, limit)
        return self.search_cache.get(key)

    def cache_search_result(
        self,
        query: str,
        results: list,
        tags: Optional[list] = None,
        doc_types: Optional[list] = None,
        limit: int = 20,
    ) -> None:
        """Cache search result.

        Args:
            query: Search query
            results: Search results to cache
            tags: Optional tag filters
            doc_types: Optional document type filters
            limit: Result limit
        """
        key = self.get_search_cache_key(query, tags, doc_types, limit)
        self.search_cache.put(key, results)

    def get_document(self, doc_id: int) -> Optional[dict]:
        """Get cached document.

        Args:
            doc_id: Document ID

        Returns:
            Cached document or None
        """
        key = self.get_document_cache_key(doc_id)
        return self.doc_cache.get(key)

    def cache_document(self, doc_id: int, document: dict) -> None:
        """Cache document.

        Args:
            doc_id: Document ID
            document: Document to cache
        """
        key = self.get_document_cache_key(doc_id)
        self.doc_cache.put(key, document)

    def clear(self) -> None:
        """Clear all caches."""
        self.search_cache.clear()
        self.doc_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with statistics for both caches
        """
        return {
            "search_cache": self.search_cache.get_stats(),
            "document_cache": self.doc_cache.get_stats(),
        }


# Global query cache instance
_query_cache = QueryCache()


def get_query_cache() -> QueryCache:
    """Get global query cache instance.

    Returns:
        QueryCache instance
    """
    return _query_cache


def cached_search(
    func: Callable[..., T],
) -> Callable[..., T]:
    """Decorator for caching search results.

    Example:
        @cached_search
        async def search_documents(query, tags=None, doc_types=None, limit=20):
            ...
    """

    @wraps(func)
    async def wrapper(
        query: str,
        tags=None,
        doc_types=None,
        limit=20,
        **kwargs,
    ):
        cache = get_query_cache()

        # Try to get from cache
        cached_result = cache.get_search_result(query, tags, doc_types, limit)
        if cached_result is not None:
            logger.debug(
                "cache_hit",
                operation="search",
                query=query[:50],
            )
            return cached_result

        # Cache miss - call function
        result = await func(query, tags=tags, doc_types=doc_types, limit=limit, **kwargs)

        # Cache result
        if result:
            cache.cache_search_result(query, result, tags, doc_types, limit)
            logger.debug(
                "cache_stored",
                operation="search",
                query=query[:50],
                result_count=len(result),
            )

        return result

    return wrapper


def cached_document(
    func: Callable[..., T],
) -> Callable[..., T]:
    """Decorator for caching document retrieval.

    Example:
        @cached_document
        async def get_document(doc_id):
            ...
    """

    @wraps(func)
    async def wrapper(doc_id: int, **kwargs):
        cache = get_query_cache()

        # Try to get from cache
        cached_doc = cache.get_document(doc_id)
        if cached_doc is not None:
            logger.debug("cache_hit", operation="get_document", doc_id=doc_id)
            return cached_doc

        # Cache miss - call function
        document = await func(doc_id, **kwargs)

        # Cache document
        if document:
            cache.cache_document(doc_id, document)
            logger.debug(
                "cache_stored",
                operation="get_document",
                doc_id=doc_id,
            )

        return document

    return wrapper
