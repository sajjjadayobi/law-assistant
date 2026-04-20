"""Database query optimization utilities."""

from typing import Any

import structlog
from sqlalchemy import text

from .connection import get_connection

logger = structlog.get_logger(__name__)


class DatabaseOptimizer:
    """Utilities for optimizing database queries and performance."""

    @staticmethod
    def create_indexes() -> dict[str, bool]:
        """Create missing indexes for performance optimization.

        Returns:
            Dictionary mapping index name to creation success status
        """
        indexes = {
            "idx_documents_doc_type": """
                CREATE INDEX IF NOT EXISTS idx_documents_doc_type
                ON documents(doc_type)
            """,
            "idx_documents_date": """
                CREATE INDEX IF NOT EXISTS idx_documents_date
                ON documents(date)
            """,
            "idx_documents_tags": """
                CREATE INDEX IF NOT EXISTS idx_documents_tags
                ON documents USING GIN(tags)
            """,
            "idx_relations_src": """
                CREATE INDEX IF NOT EXISTS idx_relations_src
                ON relations(src_doc_id)
            """,
            "idx_relations_dst": """
                CREATE INDEX IF NOT EXISTS idx_relations_dst
                ON relations(dst_doc_id)
            """,
            "idx_relations_type": """
                CREATE INDEX IF NOT EXISTS idx_relations_type
                ON relations(relation_type)
            """,
        }

        results = {}
        conn = get_connection()

        try:
            for index_name, create_stmt in indexes.items():
                try:
                    conn.execute(text(create_stmt))
                    conn.commit()
                    results[index_name] = True
                    logger.info("index_created", index=index_name)
                except Exception as e:
                    results[index_name] = False
                    logger.warning(
                        "index_creation_failed",
                        index=index_name,
                        error=str(e),
                    )
        finally:
            conn.close()

        return results

    @staticmethod
    def analyze_table(table_name: str) -> bool:
        """Run ANALYZE on a table to update statistics.

        Args:
            table_name: Name of table to analyze

        Returns:
            True if successful, False otherwise
        """
        conn = get_connection()

        try:
            conn.execute(text(f"ANALYZE {table_name}"))
            conn.commit()
            logger.info("table_analyzed", table=table_name)
            return True
        except Exception as e:
            logger.warning("table_analysis_failed", table=table_name, error=str(e))
            return False
        finally:
            conn.close()

    @staticmethod
    def get_index_stats() -> dict[str, Any]:
        """Get statistics about indexes and their usage.

        Returns:
            Dictionary with index statistics
        """
        query = """
            SELECT
                schemaname,
                tablename,
                indexname,
                idx_scan,
                idx_tup_read,
                idx_tup_fetch,
                pg_size_pretty(pg_relation_size(indexrelid)) as index_size
            FROM pg_stat_user_indexes
            ORDER BY idx_scan DESC
        """

        conn = get_connection()
        try:
            result = conn.execute(text(query))
            rows = result.fetchall()

            stats = []
            for row in rows:
                stats.append(
                    {
                        "schema": row[0],
                        "table": row[1],
                        "index": row[2],
                        "scans": row[3],
                        "tuples_read": row[4],
                        "tuples_fetched": row[5],
                        "size": row[6],
                    }
                )

            logger.info("index_stats_retrieved", count=len(stats))
            return {"indexes": stats}
        except Exception as e:
            logger.warning("index_stats_failed", error=str(e))
            return {}
        finally:
            conn.close()

    @staticmethod
    def get_table_stats() -> dict[str, Any]:
        """Get statistics about tables.

        Returns:
            Dictionary with table statistics
        """
        query = """
            SELECT
                schemaname,
                tablename,
                n_live_tup,
                n_dead_tup,
                last_vacuum,
                last_analyze,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        """

        conn = get_connection()
        try:
            result = conn.execute(text(query))
            rows = result.fetchall()

            stats = []
            for row in rows:
                stats.append(
                    {
                        "schema": row[0],
                        "table": row[1],
                        "live_rows": row[2],
                        "dead_rows": row[3],
                        "last_vacuum": row[4],
                        "last_analyze": row[5],
                        "total_size": row[6],
                    }
                )

            logger.info("table_stats_retrieved", count=len(stats))
            return {"tables": stats}
        except Exception as e:
            logger.warning("table_stats_failed", error=str(e))
            return {}
        finally:
            conn.close()

    @staticmethod
    def get_slow_queries(limit: int = 10) -> list[dict[str, Any]]:
        """Get slowest queries from pg_stat_statements.

        Args:
            limit: Number of slow queries to return

        Returns:
            List of slow query information
        """
        query = """
            SELECT
                query,
                calls,
                total_time,
                mean_time,
                max_time,
                rows,
                100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS cache_hit_ratio
            FROM pg_stat_statements
            WHERE query NOT LIKE '%pg_stat_statements%'
            ORDER BY mean_time DESC
            LIMIT %s
        """

        conn = get_connection()
        try:
            result = conn.execute(text(query), {"limit": limit})
            rows = result.fetchall()

            slow_queries = []
            for row in rows:
                slow_queries.append(
                    {
                        "query": row[0][:100],  # First 100 chars
                        "calls": row[1],
                        "total_time_ms": round(row[2], 2),
                        "mean_time_ms": round(row[3], 2),
                        "max_time_ms": round(row[4], 2),
                        "rows_returned": row[5],
                        "cache_hit_ratio": round(row[6], 2) if row[6] else None,
                    }
                )

            logger.info("slow_queries_retrieved", count=len(slow_queries))
            return slow_queries
        except Exception as e:
            logger.warning("slow_queries_failed", error=str(e))
            return []
        finally:
            conn.close()

    @staticmethod
    def explain_query(query_str: str) -> dict[str, Any]:
        """Get EXPLAIN ANALYZE output for a query.

        Args:
            query_str: SQL query to analyze

        Returns:
            EXPLAIN output as dictionary
        """
        explain_query_str = f"EXPLAIN (ANALYZE, BUFFERS, VERBOSE) {query_str}"

        conn = get_connection()
        try:
            result = conn.execute(text(explain_query_str))
            rows = result.fetchall()

            plan = "\n".join([row[0] for row in rows])
            logger.info("query_explained", query=query_str[:50])
            return {"plan": plan}
        except Exception as e:
            logger.warning("query_explain_failed", error=str(e))
            return {}
        finally:
            conn.close()

    @staticmethod
    def get_missing_indexes() -> list[dict[str, str]]:
        """Identify potentially missing indexes based on sequential scans.

        Returns:
            List of tables with high sequential scan counts
        """
        query = """
            SELECT
                schemaname,
                tablename,
                seq_scan,
                seq_tup_read,
                idx_scan
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
            AND seq_scan > 100
            AND seq_scan > idx_scan
            ORDER BY seq_tup_read DESC
        """

        conn = get_connection()
        try:
            result = conn.execute(text(query))
            rows = result.fetchall()

            missing = []
            for row in rows:
                missing.append(
                    {
                        "schema": row[0],
                        "table": row[1],
                        "sequential_scans": row[2],
                        "tuples_read": row[3],
                        "index_scans": row[4],
                        "recommendation": f"Consider adding index on {row[1]} (seq_scan={row[2]} >> idx_scan={row[4]})",
                    }
                )

            logger.info("missing_indexes_identified", count=len(missing))
            return missing
        except Exception as e:
            logger.warning("missing_indexes_check_failed", error=str(e))
            return []
        finally:
            conn.close()

    @staticmethod
    def reset_stats() -> bool:
        """Reset PostgreSQL statistics (pg_stat_statements).

        Returns:
            True if successful
        """
        conn = get_connection()
        try:
            conn.execute(text("SELECT pg_stat_statements_reset()"))
            conn.commit()
            logger.info("stats_reset")
            return True
        except Exception as e:
            logger.warning("stats_reset_failed", error=str(e))
            return False
        finally:
            conn.close()


class QueryOptimizer:
    """Utilities for optimizing application-level queries."""

    @staticmethod
    def paginate(
        query_results: list[Any],
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Any], dict[str, int]]:
        """Paginate query results.

        Args:
            query_results: Results from database query
            page: Page number (1-indexed)
            page_size: Number of results per page

        Returns:
            Tuple of (paginated results, pagination metadata)
        """
        total = len(query_results)
        start = (page - 1) * page_size
        end = start + page_size

        paginated = query_results[start:end]

        metadata = {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,
            "has_next": end < total,
            "has_prev": page > 1,
        }

        logger.debug(
            "results_paginated",
            page=page,
            page_size=page_size,
            total=total,
        )

        return paginated, metadata

    @staticmethod
    def batch_fetch(
        ids: list[int],
        fetch_fn,
        batch_size: int = 100,
    ) -> list[Any]:
        """Fetch multiple items in batches to optimize performance.

        Args:
            ids: List of IDs to fetch
            fetch_fn: Async function that takes list of IDs and returns results
            batch_size: Number of IDs to fetch per batch

        Returns:
            Combined list of fetched items
        """
        results = []

        for i in range(0, len(ids), batch_size):
            batch = ids[i : i + batch_size]
            logger.debug("batch_fetching", batch_num=i // batch_size, batch_size=len(batch))
            batch_results = fetch_fn(batch)
            if batch_results:
                results.extend(batch_results)

        return results

    @staticmethod
    def get_optimization_report() -> dict[str, Any]:
        """Generate comprehensive optimization report.

        Returns:
            Dictionary with optimization recommendations
        """
        optimizer = DatabaseOptimizer()

        report = {
            "timestamp": None,
            "indexes": optimizer.get_index_stats(),
            "tables": optimizer.get_table_stats(),
            "slow_queries": optimizer.get_slow_queries(10),
            "missing_indexes": optimizer.get_missing_indexes(),
        }

        logger.info("optimization_report_generated")
        return report
