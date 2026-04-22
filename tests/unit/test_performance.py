"""Tests for performance monitoring and profiling."""

import json
import time
from pathlib import Path

from law_agent.performance.metrics import (
    MetricsCollector,
    PerformanceMetrics,
    PerformanceTimer,
)
from law_agent.performance.profiler import Profiler, profile_function


class TestProfiler:
    """Tests for Profiler class."""

    def test_profiler_context_manager(self, tmp_path: Path) -> None:
        """Test profiler as context manager."""
        with Profiler("test", tmp_path):
            # Do some work
            sum(range(1000))

        # Check stats file was created
        stats_file = tmp_path / "test.prof"
        assert stats_file.exists()

    def test_profile_function_decorator(self) -> None:
        """Test profile_function decorator."""

        @profile_function()
        def slow_function():
            time.sleep(0.01)
            return 42

        result = slow_function()
        assert result == 42


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics dataclass."""

    def test_metrics_creation(self) -> None:
        """Test creating performance metrics."""
        metric = PerformanceMetrics(
            timestamp="2024-01-01T00:00:00",
            operation="test_op",
            duration_ms=100.5,
            status="success",
        )

        assert metric.operation == "test_op"
        assert metric.duration_ms == 100.5
        assert metric.status == "success"

    def test_metrics_with_metadata(self) -> None:
        """Test metrics with additional metadata."""
        metric = PerformanceMetrics(
            timestamp="2024-01-01T00:00:00",
            operation="search",
            duration_ms=50.0,
            status="success",
            metadata={"query": "test", "results": 10},
        )

        assert metric.metadata["query"] == "test"
        assert metric.metadata["results"] == 10


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    def test_record_metric(self, tmp_path: Path) -> None:
        """Test recording a metric."""
        collector = MetricsCollector(tmp_path / "test_metrics.jsonl")

        metric = PerformanceMetrics(
            timestamp="2024-01-01T00:00:00",
            operation="test",
            duration_ms=100.0,
            status="success",
        )

        collector.record(metric)
        assert len(collector.metrics) == 1

    def test_get_summary_empty(self) -> None:
        """Test getting summary for non-existent operation."""
        collector = MetricsCollector()
        summary = collector.get_summary("nonexistent")
        assert summary == {}

    def test_get_summary_statistics(self, tmp_path: Path) -> None:
        """Test getting summary statistics."""
        collector = MetricsCollector(tmp_path / "test_metrics.jsonl")

        # Record multiple metrics
        for i in range(5):
            metric = PerformanceMetrics(
                timestamp="2024-01-01T00:00:00",
                operation="search",
                duration_ms=100.0 + i * 10,
                status="success",
            )
            collector.record(metric)

        summary = collector.get_summary("search")
        assert summary["count"] == 5
        assert summary["min_ms"] == 100.0
        assert summary["max_ms"] == 140.0
        assert "mean_ms" in summary
        assert "median_ms" in summary

    def test_export_json(self, tmp_path: Path) -> None:
        """Test exporting metrics as JSON."""
        collector = MetricsCollector(tmp_path / "test_metrics.jsonl")

        metric = PerformanceMetrics(
            timestamp="2024-01-01T00:00:00",
            operation="test",
            duration_ms=100.0,
            status="success",
        )
        collector.record(metric)

        export_file = tmp_path / "export.json"
        collector.export_json(export_file)

        assert export_file.exists()
        with open(export_file) as f:
            data = json.load(f)
        assert data["total_metrics"] == 1
        assert "summaries" in data


class TestPerformanceTimer:
    """Tests for PerformanceTimer context manager."""

    def test_timer_success(self, tmp_path: Path) -> None:
        """Test timer with successful operation."""
        collector = MetricsCollector(tmp_path / "test_metrics.jsonl")

        with PerformanceTimer("test_op", collector):
            time.sleep(0.01)

        assert len(collector.metrics) == 1
        assert collector.metrics[0].operation == "test_op"
        assert collector.metrics[0].status == "success"
        assert collector.metrics[0].duration_ms >= 10

    def test_timer_with_exception(self, tmp_path: Path) -> None:
        """Test timer records error status on exception."""
        collector = MetricsCollector(tmp_path / "test_metrics.jsonl")

        try:
            with PerformanceTimer("failing_op", collector):
                raise ValueError("Test error")
        except ValueError:
            pass

        assert len(collector.metrics) == 1
        assert collector.metrics[0].status == "error"

    def test_timer_with_metadata(self, tmp_path: Path) -> None:
        """Test timer with metadata."""
        collector = MetricsCollector(tmp_path / "test_metrics.jsonl")

        metadata = {"query": "test", "results": 5}
        with PerformanceTimer("search", collector, metadata):
            pass

        assert collector.metrics[0].metadata == metadata

    def test_timer_without_collector(self) -> None:
        """Test timer works without collector."""
        with PerformanceTimer("test_op"):
            time.sleep(0.01)
        # Should not raise any errors


class TestMetricsCollectorSummaries:
    """Tests for getting summaries of multiple operations."""

    def test_get_all_summaries(self, tmp_path: Path) -> None:
        """Test getting summaries for all operations."""
        collector = MetricsCollector(tmp_path / "test_metrics.jsonl")

        # Record metrics for multiple operations
        for op in ["search", "fetch"]:
            for i in range(3):
                metric = PerformanceMetrics(
                    timestamp="2024-01-01T00:00:00",
                    operation=op,
                    duration_ms=100.0 + i,
                    status="success",
                )
                collector.record(metric)

        summaries = collector.get_all_summaries()
        assert "search" in summaries
        assert "fetch" in summaries
        assert summaries["search"]["count"] == 3
        assert summaries["fetch"]["count"] == 3
