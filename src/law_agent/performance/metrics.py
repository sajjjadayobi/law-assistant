"""Performance metrics collection and reporting."""

import json
import statistics
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    timestamp: str
    operation: str
    duration_ms: float
    status: str  # "success" or "error"
    memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    metadata: dict[str, Any] = None

    def __post_init__(self) -> None:
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}


class MetricsCollector:
    """Collects and analyzes performance metrics."""

    def __init__(self, output_file: Optional[Path] = None):
        """Initialize metrics collector.

        Args:
            output_file: File to save metrics (default: metrics.jsonl)
        """
        self.output_file = output_file or Path("metrics.jsonl")
        self.metrics: list[PerformanceMetrics] = []
        self._operation_times: dict[str, list[float]] = defaultdict(list)

    def record(self, metric: PerformanceMetrics) -> None:
        """Record a metric.

        Args:
            metric: Performance metric to record
        """
        self.metrics.append(metric)
        self._operation_times[metric.operation].append(metric.duration_ms)

        # Append to file for persistence
        with open(self.output_file, "a") as f:
            json_str = json.dumps(asdict(metric))
            f.write(json_str + "\n")

        logger.debug(
            "metric_recorded",
            operation=metric.operation,
            duration_ms=round(metric.duration_ms, 2),
            status=metric.status,
        )

    def get_summary(self, operation: str) -> dict[str, float]:
        """Get summary statistics for an operation.

        Args:
            operation: Operation name to summarize

        Returns:
            Dictionary with min, max, mean, median, p95, p99 durations
        """
        times = self._operation_times.get(operation, [])
        if not times:
            return {}

        sorted_times = sorted(times)
        n = len(sorted_times)

        return {
            "count": n,
            "min_ms": min(times),
            "max_ms": max(times),
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "stdev_ms": statistics.stdev(times) if n > 1 else 0.0,
            "p95_ms": sorted_times[int(n * 0.95)] if n > 20 else sorted_times[-1],
            "p99_ms": sorted_times[int(n * 0.99)] if n > 100 else sorted_times[-1],
        }

    def get_all_summaries(self) -> dict[str, dict[str, float]]:
        """Get summary statistics for all operations.

        Returns:
            Dictionary mapping operation names to their summaries
        """
        summaries = {}
        for operation in self._operation_times:
            summaries[operation] = self.get_summary(operation)
        return summaries

    def print_report(self) -> None:
        """Print formatted performance report."""
        summaries = self.get_all_summaries()

        print("\n" + "=" * 80)
        print("PERFORMANCE METRICS REPORT")
        print("=" * 80)
        print(f"Report generated: {datetime.now().isoformat()}")
        print(f"Total metrics collected: {len(self.metrics)}")
        print("\n" + "-" * 80)

        for operation, stats in sorted(summaries.items()):
            if not stats:
                continue

            print(f"\n{operation}:")
            print(f"  Count:       {stats['count']}")
            print(f"  Min:         {stats['min_ms']:.2f}ms")
            print(f"  Max:         {stats['max_ms']:.2f}ms")
            print(f"  Mean:        {stats['mean_ms']:.2f}ms")
            print(f"  Median:      {stats['median_ms']:.2f}ms")
            print(f"  StdDev:      {stats['stdev_ms']:.2f}ms")
            print(f"  P95:         {stats['p95_ms']:.2f}ms")
            print(f"  P99:         {stats['p99_ms']:.2f}ms")

        print("\n" + "=" * 80)

    def export_json(self, filepath: Path) -> None:
        """Export metrics as JSON.

        Args:
            filepath: Output file path
        """
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_metrics": len(self.metrics),
            "summaries": self.get_all_summaries(),
            "metrics": [asdict(m) for m in self.metrics],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info("metrics_exported", filepath=str(filepath))


class PerformanceTimer:
    """Context manager for timing operations."""

    def __init__(
        self,
        operation: str,
        collector: Optional[MetricsCollector] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """Initialize timer.

        Args:
            operation: Name of operation being timed
            collector: Metrics collector to record to
            metadata: Additional metadata to attach
        """
        self.operation = operation
        self.collector = collector
        self.metadata = metadata or {}
        self.start_time = 0.0

    def __enter__(self) -> "PerformanceTimer":
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Stop timing and record metric."""
        elapsed_ms = (time.time() - self.start_time) * 1000
        status = "error" if exc_type else "success"

        metric = PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            operation=self.operation,
            duration_ms=elapsed_ms,
            status=status,
            metadata=self.metadata,
        )

        if self.collector:
            self.collector.record(metric)

        logger.debug(
            "timer_complete",
            operation=self.operation,
            duration_ms=round(elapsed_ms, 2),
            status=status,
        )
