"""Script to run load tests and generate reports."""

import argparse
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class LoadTestRunner:
    """Runs load tests and generates reports."""

    def __init__(
        self,
        host: str = "http://localhost:8000",
        output_dir: Path = Path("./load_test_results"),
    ):
        """Initialize load test runner.

        Args:
            host: Target host URL
            output_dir: Directory for test results
        """
        self.host = host
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)

    def run_scenario(
        self,
        scenario_name: str,
        num_users: int,
        spawn_rate: int,
        duration: int = 300,
    ) -> bool:
        """Run a load test scenario.

        Args:
            scenario_name: Name of the scenario
            num_users: Number of concurrent users
            spawn_rate: Users spawned per second
            duration: Test duration in seconds

        Returns:
            True if test completed successfully
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.output_dir / f"{scenario_name}_{timestamp}_results.html"
        self.output_dir / f"{scenario_name}_{timestamp}_stats.json"

        logger.info(
            "load_test_starting",
            scenario=scenario_name,
            users=num_users,
            spawn_rate=spawn_rate,
            duration=duration,
        )

        cmd = [
            "locust",
            "-f",
            "tests/load/locustfile.py",
            f"--host={self.host}",
            f"--users={num_users}",
            f"--spawn-rate={spawn_rate}",
            f"--run-time={duration}s",
            f"--html={results_file}",
            "--csv=" + str(self.output_dir / f"{scenario_name}_{timestamp}"),
            "--headless",
            "--quiet",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 60)

            if result.returncode == 0:
                logger.info(
                    "load_test_complete",
                    scenario=scenario_name,
                    results_file=str(results_file),
                )
                return True
            else:
                logger.error(
                    "load_test_failed",
                    scenario=scenario_name,
                    error=result.stderr,
                )
                return False
        except subprocess.TimeoutExpired:
            logger.error("load_test_timeout", scenario=scenario_name)
            return False
        except Exception as e:
            logger.error("load_test_error", scenario=scenario_name, error=str(e))
            return False

    def run_all_scenarios(self) -> dict[str, bool]:
        """Run all predefined load test scenarios.

        Returns:
            Dictionary mapping scenario names to success status
        """
        scenarios = {
            "light": {"users": 10, "spawn_rate": 1, "duration": 300},
            "medium": {"users": 50, "spawn_rate": 5, "duration": 600},
            "heavy": {"users": 100, "spawn_rate": 10, "duration": 900},
        }

        results = {}

        for scenario_name, config in scenarios.items():
            success = self.run_scenario(
                scenario_name,
                num_users=config["users"],
                spawn_rate=config["spawn_rate"],
                duration=config["duration"],
            )
            results[scenario_name] = success

            # Wait between scenarios
            if success:
                time.sleep(10)

        return results

    def generate_report(self) -> None:
        """Generate summary report from all test results."""
        logger.info("generating_load_test_report")

        report = {
            "timestamp": datetime.now().isoformat(),
            "test_host": self.host,
            "results_directory": str(self.output_dir),
            "test_runs": [],
        }

        # Find all result files
        for html_file in self.output_dir.glob("*_results.html"):
            scenario_name = html_file.stem.split("_")[0]
            report["test_runs"].append(
                {
                    "scenario": scenario_name,
                    "results_file": html_file.name,
                }
            )

        # Save report
        report_file = self.output_dir / "load_test_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        logger.info("report_generated", report_file=str(report_file))

        # Print summary
        self.print_summary(report)

    def print_summary(self, report: dict[str, Any]) -> None:
        """Print test summary to console.

        Args:
            report: Report dictionary
        """
        print("\n" + "=" * 80)
        print("LOAD TEST SUMMARY")
        print("=" * 80)
        print(f"Timestamp: {report['timestamp']}")
        print(f"Target: {report['test_host']}")
        print(f"Results Directory: {report['results_directory']}")
        print("\nTest Runs:")

        for run in report["test_runs"]:
            print(f"  - {run['scenario']}: {run['results_file']}")

        print("\nView detailed results:")
        print(f"  HTML reports in: {report['results_directory']}")

        print("=" * 80 + "\n")


def main():
    """Main entry point for load testing."""
    parser = argparse.ArgumentParser(description="Run load tests for Law Agent")
    parser.add_argument(
        "--host",
        default="http://localhost:8000",
        help="Target host URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./load_test_results"),
        help="Output directory for results",
    )
    parser.add_argument(
        "--scenario",
        choices=["light", "medium", "heavy", "all"],
        default="light",
        help="Load test scenario to run",
    )
    parser.add_argument(
        "--users",
        type=int,
        help="Number of users (overrides scenario)",
    )
    parser.add_argument(
        "--spawn-rate",
        type=int,
        help="Users spawned per second (overrides scenario)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=300,
        help="Test duration in seconds (default: 300)",
    )

    args = parser.parse_args()

    runner = LoadTestRunner(host=args.host, output_dir=args.output_dir)

    if args.scenario == "all":
        runner.run_all_scenarios()
    elif args.users and args.spawn_rate:
        # Custom scenario
        runner.run_scenario(
            "custom",
            num_users=args.users,
            spawn_rate=args.spawn_rate,
            duration=args.duration,
        )
    else:
        # Predefined scenario
        scenario_config = {
            "light": {"users": 10, "spawn_rate": 1},
            "medium": {"users": 50, "spawn_rate": 5},
            "heavy": {"users": 100, "spawn_rate": 10},
        }

        config = scenario_config[args.scenario]
        runner.run_scenario(
            args.scenario,
            num_users=config["users"],
            spawn_rate=config["spawn_rate"],
            duration=args.duration,
        )

    runner.generate_report()


if __name__ == "__main__":
    main()
