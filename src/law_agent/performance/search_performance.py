"""Search tool performance monitoring and optimization."""

from datetime import datetime
from typing import Any, Optional

import structlog

from ..cache import get_query_cache
from .metrics import MetricsCollector, PerformanceTimer

logger = structlog.get_logger(__name__)


class SearchPerformanceMonitor:
    """Monitors and optimizes search tool performance."""

    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        """Initialize search performance monitor.

        Args:
            metrics_collector: Optional metrics collector for tracking
        """
        self.metrics_collector = metrics_collector or MetricsCollector()
        self.query_cache = get_query_cache()

    async def monitor_search(
        self,
        query: str,
        search_fn,
        tags: Optional[list[str]] = None,
        doc_types: Optional[list[str]] = None,
        limit: int = 20,
    ) -> Any:
        """Monitor search operation with caching and metrics.

        Args:
            query: Search query
            search_fn: Async search function to call
            tags: Optional tag filters
            doc_types: Optional document type filters
            limit: Result limit

        Returns:
            Search results
        """
        metadata = {
            "query": query[:50],
            "limit": limit,
            "tags": len(tags) if tags else 0,
            "doc_types": len(doc_types) if doc_types else 0,
        }

        # Check cache first
        cached_result = self.query_cache.get_search_result(query, tags, doc_types, limit)
        if cached_result is not None:
            logger.info(
                "search_cache_hit",
                query=query[:50],
                result_count=len(cached_result),
            )
            metadata["cache_hit"] = True
            return cached_result

        # Cache miss - execute search with timing
        with PerformanceTimer("search_documents", self.metrics_collector, metadata):
            results = await search_fn(query, tags=tags, doc_types=doc_types, limit=limit)

        # Cache results
        if results:
            self.query_cache.cache_search_result(query, results, tags, doc_types, limit)
            logger.info(
                "search_results_cached",
                query=query[:50],
                result_count=len(results),
            )

        return results

    async def monitor_document_fetch(
        self,
        doc_id: int,
        fetch_fn,
    ) -> Any:
        """Monitor document fetch operation with caching.

        Args:
            doc_id: Document ID to fetch
            fetch_fn: Async function to fetch document

        Returns:
            Document or None
        """
        # Check cache first
        cached_doc = self.query_cache.get_document(doc_id)
        if cached_doc is not None:
            logger.info("document_cache_hit", doc_id=doc_id)
            return cached_doc

        # Cache miss - fetch with timing
        with PerformanceTimer(
            "get_document",
            self.metrics_collector,
            {"doc_id": doc_id, "cache_hit": False},
        ):
            document = await fetch_fn(doc_id)

        # Cache document
        if document:
            self.query_cache.cache_document(doc_id, document)
            logger.info("document_cached", doc_id=doc_id)

        return document

    async def monitor_relations(
        self,
        doc_id: int,
        relations_fn,
        direction: str = "outgoing",
        relation_types: Optional[list[str]] = None,
        limit: int = 10,
    ) -> list[Any]:
        """Monitor relation traversal operation.

        Args:
            doc_id: Source document ID
            relations_fn: Async function to fetch relations
            direction: "outgoing" or "incoming"
            relation_types: Optional relation type filters
            limit: Result limit

        Returns:
            Related documents
        """
        metadata = {
            "doc_id": doc_id,
            "direction": direction,
            "relation_types": len(relation_types) if relation_types else 0,
            "limit": limit,
        }

        with PerformanceTimer(
            "get_related_documents",
            self.metrics_collector,
            metadata,
        ):
            results = await relations_fn(
                doc_id,
                direction=direction,
                relation_types=relation_types,
                limit=limit,
            )

        return results if results else []

    def get_performance_report(self) -> dict[str, Any]:
        """Get performance report.

        Returns:
            Dictionary with performance metrics and cache stats
        """
        cache_stats = self.query_cache.get_stats()
        metrics_summaries = self.metrics_collector.get_all_summaries()

        return {
            "timestamp": datetime.now().isoformat(),
            "cache_statistics": cache_stats,
            "operation_metrics": metrics_summaries,
        }

    def print_performance_report(self) -> None:
        """Print formatted performance report."""
        report = self.get_performance_report()

        print("\n" + "=" * 80)
        print("SEARCH PERFORMANCE REPORT")
        print("=" * 80)
        print(f"Generated: {report['timestamp']}")

        # Cache stats
        print("\nCACHE STATISTICS:")
        search_cache = report["cache_statistics"]["search_cache"]
        doc_cache = report["cache_statistics"]["document_cache"]

        print("\nSearch Cache:")
        print(f"  Size:     {search_cache['size']}/{search_cache['max_size']}")
        print(f"  Hits:     {search_cache['hits']}")
        print(f"  Misses:   {search_cache['misses']}")
        print(f"  Hit Rate: {search_cache['hit_rate']}%")

        print("\nDocument Cache:")
        print(f"  Size:     {doc_cache['size']}/{doc_cache['max_size']}")
        print(f"  Hits:     {doc_cache['hits']}")
        print(f"  Misses:   {doc_cache['misses']}")
        print(f"  Hit Rate: {doc_cache['hit_rate']}%")

        # Operation metrics
        print("\nOPERATION METRICS:")
        for operation, metrics in report["operation_metrics"].items():
            if not metrics:
                continue
            print(f"\n{operation}:")
            print(f"  Count:    {metrics.get('count', 0)}")
            print(f"  Mean:     {metrics.get('mean_ms', 0):.2f}ms")
            print(f"  Median:   {metrics.get('median_ms', 0):.2f}ms")
            print(f"  P95:      {metrics.get('p95_ms', 0):.2f}ms")
            print(f"  P99:      {metrics.get('p99_ms', 0):.2f}ms")

        print("\n" + "=" * 80)


class SearchOptimizationTips:
    """Provides optimization recommendations based on metrics."""

    @staticmethod
    def analyze_cache_efficiency(cache_stats: dict[str, Any]) -> list[str]:
        """Analyze cache efficiency and provide recommendations.

        Args:
            cache_stats: Cache statistics from SearchPerformanceMonitor

        Returns:
            List of recommendations
        """
        recommendations = []

        search_cache = cache_stats["search_cache"]
        hit_rate = search_cache["hit_rate"]

        if hit_rate < 20:
            recommendations.append(
                "Low search cache hit rate - consider increasing cache size or TTL"
            )

        if search_cache["size"] == search_cache["max_size"]:
            recommendations.append("Search cache is full - increase max_size for better retention")

        doc_cache = cache_stats["document_cache"]
        if doc_cache["hit_rate"] < 30:
            recommendations.append(
                "Low document cache hit rate - ensure documents are fetched multiple times"
            )

        return recommendations

    @staticmethod
    def analyze_operation_metrics(
        metrics: dict[str, dict[str, float]],
    ) -> list[str]:
        """Analyze operation performance and provide recommendations.

        Args:
            metrics: Operation metrics from SearchPerformanceMonitor

        Returns:
            List of recommendations
        """
        recommendations = []

        for operation, stats in metrics.items():
            if not stats:
                continue

            p99 = stats.get("p99_ms", 0)
            mean = stats.get("mean_ms", 0)

            # Check for high latency
            if operation == "search_documents" and p99 > 1000:
                recommendations.append(
                    f"{operation}: P99 latency ({p99:.0f}ms) exceeds target (< 1000ms) - consider index optimization"
                )

            if operation == "get_document" and p99 > 500:
                recommendations.append(
                    f"{operation}: P99 latency ({p99:.0f}ms) exceeds target (< 500ms) - consider batch fetching"
                )

            # Check for high variance
            if mean > 0:
                stdev = stats.get("stdev_ms", 0)
                if stdev / mean > 2:
                    recommendations.append(
                        f"{operation}: High latency variance detected - some queries are much slower than others"
                    )

        return recommendations
