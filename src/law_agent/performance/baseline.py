"""Baseline performance testing and metrics collection."""

import asyncio
from pathlib import Path
from typing import List, Dict, Any

import structlog

from ..tools.search import search_documents, get_document, get_related_documents
from .metrics import MetricsCollector, PerformanceTimer

logger = structlog.get_logger(__name__)


class BaselinePerformanceTester:
    """Tests and establishes baseline performance metrics."""

    def __init__(self, output_dir: Path = Path("./performance_baselines")):
        """Initialize baseline tester.

        Args:
            output_dir: Directory to save baseline results
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.collector = MetricsCollector(
            output_file=self.output_dir / "baseline_metrics.jsonl"
        )

    async def test_search_documents(self, queries: List[str]) -> Dict[str, Any]:
        """Test search_documents performance.

        Args:
            queries: List of test queries

        Returns:
            Summary of test results
        """
        logger.info("testing_search_documents", count=len(queries))
        results = []

        for query in queries:
            with PerformanceTimer("search_documents", self.collector, {"query": query}):
                result = await search_documents(query, limit=20)
                results.append(
                    {
                        "query": query,
                        "result_count": len(result) if result else 0,
                        "status": "success" if result is not None else "failed",
                    }
                )

        return {
            "operation": "search_documents",
            "test_count": len(queries),
            "results": results,
        }

    async def test_get_document(self, doc_ids: List[int]) -> Dict[str, Any]:
        """Test get_document performance.

        Args:
            doc_ids: List of document IDs to fetch

        Returns:
            Summary of test results
        """
        logger.info("testing_get_document", count=len(doc_ids))
        results = []

        for doc_id in doc_ids:
            with PerformanceTimer(
                "get_document", self.collector, {"doc_id": doc_id}
            ):
                result = await get_document(doc_id)
                results.append(
                    {
                        "doc_id": doc_id,
                        "found": result is not None,
                        "status": "success",
                    }
                )

        return {
            "operation": "get_document",
            "test_count": len(doc_ids),
            "results": results,
        }

    async def test_get_related_documents(self, doc_ids: List[int]) -> Dict[str, Any]:
        """Test get_related_documents performance.

        Args:
            doc_ids: List of document IDs to find relations for

        Returns:
            Summary of test results
        """
        logger.info("testing_get_related_documents", count=len(doc_ids))
        results = []

        for doc_id in doc_ids:
            with PerformanceTimer(
                "get_related_documents",
                self.collector,
                {"doc_id": doc_id, "direction": "outgoing"},
            ):
                result = await get_related_documents(doc_id, direction="outgoing", limit=10)
                results.append(
                    {
                        "doc_id": doc_id,
                        "relation_count": len(result) if result else 0,
                        "status": "success",
                    }
                )

        return {
            "operation": "get_related_documents",
            "test_count": len(doc_ids),
            "results": results,
        }

    async def run_baseline(
        self,
        search_queries: List[str],
        doc_ids: List[int],
        runs: int = 3,
    ) -> Dict[str, Any]:
        """Run complete baseline test suite.

        Args:
            search_queries: List of queries to test
            doc_ids: List of document IDs to test
            runs: Number of times to run each test

        Returns:
            Complete baseline report
        """
        logger.info("running_baseline_tests", runs=runs)

        all_results = {}

        # Run tests multiple times
        for i in range(runs):
            logger.info("baseline_run", run=i + 1, total=runs)

            results = {}
            results["search_documents"] = await self.test_search_documents(search_queries)
            results["get_document"] = await self.test_get_document(doc_ids)
            results["get_related_documents"] = await self.test_get_related_documents(doc_ids)

            for operation, result in results.items():
                if operation not in all_results:
                    all_results[operation] = []
                all_results[operation].append(result)

        # Print report
        self.collector.print_report()

        # Export metrics
        metrics_file = self.output_dir / "baseline_report.json"
        self.collector.export_json(metrics_file)
        logger.info("baseline_complete", report_file=str(metrics_file))

        return {
            "baseline_results": all_results,
            "summaries": self.collector.get_all_summaries(),
        }


async def run_baseline_from_config(
    search_queries: List[str] = None,
    doc_ids: List[int] = None,
    runs: int = 3,
) -> None:
    """Run baseline tests with optional default queries and documents.

    Args:
        search_queries: Queries to test (uses defaults if not provided)
        doc_ids: Document IDs to test (uses defaults if not provided)
        runs: Number of test runs
    """
    # Default test queries
    if search_queries is None:
        search_queries = [
            "بیمه",  # Insurance
            "قرارداد",  # Contract
            "مالیات",  # Tax
            "کار",  # Labor/Work
            "حقوق",  # Rights/Law
            "دولت",  # Government
            "قانون",  # Law
            "جرم",  # Crime
        ]

    # Default document IDs (would need to be obtained from database in real scenario)
    if doc_ids is None:
        doc_ids = list(range(1, 11))  # First 10 documents as sample

    tester = BaselinePerformanceTester()
    await tester.run_baseline(search_queries, doc_ids, runs)


if __name__ == "__main__":
    asyncio.run(run_baseline_from_config(runs=2))
