"""Profiling utilities for identifying performance bottlenecks."""

import cProfile
import pstats
import time
import functools
from pathlib import Path
from typing import Any, Callable, TypeVar, Optional
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class Profiler:
    """Context manager for profiling code execution."""

    def __init__(self, name: str = "profile", output_dir: Optional[Path] = None):
        """Initialize profiler.

        Args:
            name: Name for the profile output file
            output_dir: Directory to save profile results (default: ./profiles)
        """
        self.name = name
        self.output_dir = output_dir or Path("./profiles")
        self.output_dir.mkdir(exist_ok=True)
        self.profiler = cProfile.Profile()

    def __enter__(self) -> "Profiler":
        """Start profiling."""
        self.profiler.enable()
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Stop profiling and save results."""
        self.profiler.disable()
        elapsed = time.time() - self.start_time

        # Save stats to file
        stats_file = self.output_dir / f"{self.name}.prof"
        self.profiler.dump_stats(str(stats_file))

        # Print summary to console
        stats = pstats.Stats(self.profiler)
        stats.sort_stats("cumulative")

        logger.info(
            "profiling_complete",
            name=self.name,
            elapsed_seconds=round(elapsed, 2),
            stats_file=str(stats_file),
        )

        # Print top 10 functions by cumulative time
        print(f"\nProfile: {self.name}")
        print(f"Elapsed time: {elapsed:.2f}s")
        print("\nTop 10 functions by cumulative time:")
        stats.print_stats(10)

    def print_stats(self, n: int = 10) -> None:
        """Print top N functions by cumulative time."""
        stats = pstats.Stats(self.profiler)
        stats.sort_stats("cumulative")
        stats.print_stats(n)


def profile_function(
    name: Optional[str] = None, output_dir: Optional[Path] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to profile a function.

    Args:
        name: Custom name for profile output (default: function name)
        output_dir: Directory for profile output

    Example:
        @profile_function()
        def my_slow_function():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            profile_name = name or func.__name__
            with Profiler(profile_name, output_dir):
                return func(*args, **kwargs)

        return wrapper

    return decorator
