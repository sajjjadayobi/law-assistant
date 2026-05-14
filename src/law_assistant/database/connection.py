"""Database connection management and session handling.

This module provides:
- Singleton SQLAlchemy engine with connection pooling
- Thread-local session management via scoped_session
- Context managers for explicit session cleanup
- Connection health checks

Usage:
    from law_assistant.database import get_session

    with get_session() as session:
        document = session.query(Document).get(123)
"""

import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import structlog
from sqlalchemy import create_engine, pool, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from law_assistant.config.settings import get_settings

logger = structlog.get_logger(__name__)

# Global engine and session factory (initialized lazily)
_engine = None
_session_factory = None
_scoped_session = None


def _get_engine() -> Engine:
    """Get or create the SQLAlchemy engine.

    Creates a singleton engine with connection pooling configured from settings.
    Lazy initialization allows tests to override settings.

    Returns:
        Engine: SQLAlchemy Engine instance
    """
    global _engine

    if _engine is not None:
        return _engine

    settings = get_settings()
    db_config = settings.database

    # Build PostgreSQL connection URL
    # Use environment variables for password if available (for security)
    password = os.getenv("DB_PASSWORD", db_config.password)

    url = (
        f"postgresql+psycopg2://"
        f"{db_config.user}:{password}@"
        f"{db_config.host}:{db_config.port}/"
        f"{db_config.database}"
    )

    # Create engine with connection pooling
    _engine = create_engine(
        url,
        poolclass=pool.QueuePool,
        pool_size=db_config.pool_size,
        max_overflow=db_config.max_overflow,
        pool_pre_ping=True,  # Test connections before using (prevents "connection lost" errors)
        echo=db_config.echo,  # Log all SQL queries if enabled
    )

    logger.info(
        "database_engine_created",
        host=db_config.host,
        port=db_config.port,
        database=db_config.database,
        pool_size=db_config.pool_size,
        max_overflow=db_config.max_overflow,
    )

    return _engine


def _get_session_factory() -> sessionmaker[Session]:
    """Get or create the session factory.

    Returns:
        sessionmaker: Configured session factory
    """
    global _session_factory

    if _session_factory is not None:
        return _session_factory

    engine = _get_engine()
    _session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    return _session_factory


def _get_scoped_session() -> scoped_session[Session]:
    """Get or create the scoped session registry.

    Scoped sessions provide thread-local sessions for multi-threaded environments.
    Each thread gets its own session, preventing cross-request data leaks.

    Returns:
        scoped_session: Thread-local session registry
    """
    global _scoped_session

    if _scoped_session is not None:
        return _scoped_session

    session_factory = _get_session_factory()
    _scoped_session = scoped_session(session_factory)

    return _scoped_session


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager for database sessions.

    Yields a thread-local session and ensures cleanup on exit.

    Example:
        with get_session() as session:
            documents = session.query(Document).all()

    Yields:
        Session: SQLAlchemy Session instance

    Note:
        Always use this within a context manager (with statement).
        Automatic cleanup prevents connection leaks.
    """
    scoped = _get_scoped_session()
    session = scoped()

    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.exception("session_error", error=str(e))
        raise
    finally:
        session.close()


def get_connection() -> Any:
    """Get a raw database connection.

    Use this for raw SQL queries that don't fit the ORM model.

    Returns:
        Connection: Raw psycopg2 connection

    Note:
        Remember to close the connection when done, or use it in a with statement.
    """
    engine = _get_engine()
    return engine.raw_connection()


def check_connection() -> bool:
    """Check if database is reachable.

    Performs a simple query to verify connectivity.

    Returns:
        bool: True if database is accessible, False otherwise
    """
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("database_connection_check_passed")
        return True
    except Exception as e:
        logger.exception("database_connection_check_failed", error=str(e))
        return False


def dispose_engine() -> None:
    """Dispose of the engine and close all connections.

    Use this for cleanup in tests or when shutting down.
    Also resets the global singletons so next call creates fresh ones.
    """
    global _engine, _session_factory, _scoped_session

    if _scoped_session is not None:
        _scoped_session.remove()
        _scoped_session = None

    if _engine is not None:
        _engine.dispose()
        _engine = None

    _session_factory = None

    logger.info("database_engine_disposed")
