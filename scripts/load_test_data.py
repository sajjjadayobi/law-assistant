#!/usr/bin/env python3
"""Load test data into the Law Agent database.

This script loads sample documents for testing. It can:
- Load test data from SQL file
- Load test data from Python fixtures
- Reset the database to clean state
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


def load_from_sql(db_name: str = "law_agent", sql_file: str | None = None) -> bool:
    """Load test data from SQL file.

    Args:
        db_name: Database name
        sql_file: Path to SQL file (defaults to load_test_data.sql)

    Returns:
        True if successful
    """
    if sql_file is None:
        sql_file = Path(__file__).parent / "load_test_data.sql"
    else:
        sql_file = Path(sql_file)

    if not sql_file.exists():
        logger.error("SQL file not found", path=sql_file)
        return False

    try:
        logger.info("Loading test data from SQL", path=sql_file)
        result = subprocess.run(
            ["psql", "-d", db_name, "-f", str(sql_file)],
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info("Test data loaded successfully", output=result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error("Failed to load test data", error=e.stderr)
        return False
    except FileNotFoundError:
        logger.error("psql command not found - ensure PostgreSQL is installed")
        return False


def reset_database(db_name: str = "law_agent") -> bool:
    """Reset database to clean state.

    Args:
        db_name: Database name

    Returns:
        True if successful
    """
    try:
        logger.info("Resetting database", db_name=db_name)

        # Drop and recreate database
        subprocess.run(
            ["dropdb", db_name],
            capture_output=True,
            check=False,
        )

        subprocess.run(
            ["createdb", db_name],
            capture_output=True,
            text=True,
            check=True,
        )

        logger.info("Database reset successfully", db_name=db_name)
        return True
    except FileNotFoundError:
        logger.error("PostgreSQL tools not found - ensure PostgreSQL is installed")
        return False
    except subprocess.CalledProcessError as e:
        logger.error("Failed to reset database", error=e.stderr)
        return False


def verify_data(db_name: str = "law_agent") -> bool:
    """Verify that test data was loaded correctly.

    Args:
        db_name: Database name

    Returns:
        True if data looks correct
    """
    try:
        logger.info("Verifying test data")

        # Count documents
        result = subprocess.run(
            [
                "psql",
                "-d",
                db_name,
                "-t",
                "-c",
                "SELECT COUNT(*) FROM documents;",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        doc_count = int(result.stdout.strip())

        # Count relations
        result = subprocess.run(
            [
                "psql",
                "-d",
                db_name,
                "-t",
                "-c",
                "SELECT COUNT(*) FROM relations;",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        rel_count = int(result.stdout.strip())

        logger.info(
            "Data verification complete",
            documents=doc_count,
            relations=rel_count,
        )

        if doc_count == 0:
            logger.warning("No documents found in database")
            return False

        return True
    except subprocess.CalledProcessError as e:
        logger.error("Failed to verify data", error=e.stderr)
        return False


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Load test data for Law Agent")
    parser.add_argument("--db", default="law_agent", help="Database name (default: law_agent)")
    parser.add_argument(
        "--sql-file",
        help="Path to SQL file (default: load_test_data.sql in script directory)",
    )
    parser.add_argument("--reset", action="store_true", help="Reset database before loading")
    parser.add_argument("--verify", action="store_true", help="Verify data after loading")

    args = parser.parse_args()

    logger.info("Starting test data load", db=args.db)

    if args.reset:
        if not reset_database(args.db):
            return 1

    if not load_from_sql(args.db, args.sql_file):
        return 1

    if args.verify:
        if not verify_data(args.db):
            return 1

    logger.info("✓ Test data load complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
