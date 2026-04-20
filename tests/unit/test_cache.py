"""Tests for caching utilities."""

import time

from src.law_agent.cache import LRUCache, QueryCache, get_query_cache


class TestLRUCache:
    """Tests for LRUCache class."""

    def test_cache_put_and_get(self) -> None:
        """Test basic cache put and get operations."""
        cache = LRUCache[str](max_size=10)

        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_cache_miss(self) -> None:
        """Test cache miss returns None."""
        cache = LRUCache[str](max_size=10)

        assert cache.get("nonexistent") is None

    def test_cache_eviction(self) -> None:
        """Test LRU eviction when cache is full."""
        cache = LRUCache[str](max_size=3)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        cache.put("key4", "value4")  # Should evict key1

        assert cache.get("key1") is None
        assert cache.get("key4") == "value4"

    def test_cache_ttl(self) -> None:
        """Test cache expiration with TTL."""
        cache = LRUCache[str](max_size=10, ttl_seconds=1)

        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_cache_stats(self) -> None:
        """Test cache statistics."""
        cache = LRUCache[str](max_size=10)

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        # Hits
        cache.get("key1")
        cache.get("key1")

        # Misses
        cache.get("nonexistent")
        cache.get("nonexistent")

        stats = cache.get_stats()
        assert stats["size"] == 2
        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert stats["hit_rate"] == 50.0

    def test_cache_clear(self) -> None:
        """Test clearing cache."""
        cache = LRUCache[str](max_size=10)

        cache.put("key1", "value1")
        cache.clear()

        assert cache.get("key1") is None
        assert cache.get_stats()["size"] == 0


class TestQueryCache:
    """Tests for QueryCache class."""

    def test_search_cache_key_generation(self) -> None:
        """Test search cache key generation."""
        cache = QueryCache()

        key1 = cache.get_search_cache_key("query1")
        key2 = cache.get_search_cache_key("query1")
        key3 = cache.get_search_cache_key("query2")

        # Same query should generate same key
        assert key1 == key2
        # Different query should generate different key
        assert key1 != key3

    def test_search_result_caching(self) -> None:
        """Test caching search results."""
        cache = QueryCache()

        results = [{"doc_id": 1}, {"doc_id": 2}]
        cache.cache_search_result("test_query", results)

        cached = cache.get_search_result("test_query")
        assert cached == results

    def test_document_caching(self) -> None:
        """Test caching documents."""
        cache = QueryCache()

        doc = {"doc_id": 1, "title": "Test Document"}
        cache.cache_document(1, doc)

        cached = cache.get_document(1)
        assert cached == doc

    def test_search_result_with_filters(self) -> None:
        """Test search result caching with filters."""
        cache = QueryCache()

        results = [{"doc_id": 1}]
        cache.cache_search_result(
            "query",
            results,
            tags=["tag1", "tag2"],
            doc_types=["law"],
        )

        # Get with same filters
        cached = cache.get_search_result(
            "query",
            tags=["tag1", "tag2"],
            doc_types=["law"],
        )
        assert cached == results

        # Get with different filters
        cached = cache.get_search_result("query", tags=["tag1"])
        assert cached is None

    def test_cache_stats(self) -> None:
        """Test getting cache statistics."""
        cache = QueryCache()

        cache.cache_search_result("query1", [{"doc_id": 1}])
        cache.cache_document(1, {"doc_id": 1})

        stats = cache.get_stats()
        assert "search_cache" in stats
        assert "document_cache" in stats
        assert stats["search_cache"]["size"] == 1
        assert stats["document_cache"]["size"] == 1

    def test_cache_clear(self) -> None:
        """Test clearing all caches."""
        cache = QueryCache()

        cache.cache_search_result("query", [{"doc_id": 1}])
        cache.cache_document(1, {"doc_id": 1})

        cache.clear()

        assert cache.get_search_result("query") is None
        assert cache.get_document(1) is None

    def test_global_cache_instance(self) -> None:
        """Test global cache instance."""
        cache = get_query_cache()
        assert cache is not None

        # Same instance on subsequent calls
        cache2 = get_query_cache()
        assert cache is cache2
