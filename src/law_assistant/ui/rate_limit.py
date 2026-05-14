"""Rate limiting utilities for per-user daily request quotas."""

from datetime import date
from typing import Any

import asyncpg
import structlog
from sqlalchemy.ext.asyncio import AsyncEngine

logger = structlog.get_logger(__name__)

_table_initialized = False


async def ensure_rate_limits_table(engine: AsyncEngine) -> None:
    """Create rate_limits table if it doesn't exist.

    Called lazily on first use to ensure the table is ready for rate-limit checks.
    """
    sql = """
    CREATE TABLE IF NOT EXISTS rate_limits (
        user_id  TEXT        NOT NULL,
        day      DATE        NOT NULL DEFAULT CURRENT_DATE,
        count    INT         NOT NULL DEFAULT 0,
        PRIMARY KEY (user_id, day)
    );
    CREATE INDEX IF NOT EXISTS idx_rate_limits_user_id ON rate_limits(user_id);
    """

    try:
        async with engine.begin() as conn:
            await conn.exec_driver_sql(sql)
        logger.info("rate_limits table initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize rate_limits table: {e}")


async def check_and_increment(engine: AsyncEngine, user_id: str, limit: int) -> bool:
    """Check if user has requests remaining today, then increment.

    Args:
        engine: SQLAlchemy async engine
        user_id: User identifier (email)
        limit: Max requests allowed per day

    Returns:
        True if request allowed (count <= limit), False if limit exceeded
    """
    global _table_initialized

    # Lazy initialization of the rate_limits table on first use
    if not _table_initialized:
        try:
            await ensure_rate_limits_table(engine)
            _table_initialized = True
        except Exception as e:
            logger.warning(f"Failed to initialize rate_limits table: {e}")

    today = date.today()

    try:
        async with engine.begin() as conn:
            raw_conn = await conn.get_raw_connection()
            async_conn: asyncpg.Connection = raw_conn.driver_connection

            result: Any = await async_conn.fetchval(
                """
                INSERT INTO rate_limits (user_id, day, count)
                VALUES ($1, $2, 1)
                ON CONFLICT (user_id, day) DO UPDATE
                    SET count = count + 1
                RETURNING count
                """,
                user_id,
                today,
            )

            count: int = result or 0
            allowed = count <= limit
            if not allowed:
                logger.warning(
                    "rate_limit_exceeded",
                    user_id=user_id,
                    count=count,
                    limit=limit,
                )
            return allowed
    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        return True  # Allow on error (fail open)
