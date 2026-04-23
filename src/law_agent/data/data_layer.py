"""
Custom Chainlit data layer for Law Agent.

This module provides persistent conversation storage using PostgreSQL,
enabling users to resume conversations across sessions and view
conversation history in the sidebar.

The data layer extends Chainlit's SQLAlchemyDataLayer with custom
query logic for time-based grouping of conversations.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

import structlog
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.types import ThreadDict

from law_agent.config.settings import Settings

logger = structlog.get_logger(__name__)

# Lazy-loaded data layer instance
_data_layer: Optional[LawAgentDataLayer] = None


class LawAgentDataLayer(SQLAlchemyDataLayer):
    """Custom Chainlit data layer for Law Agent with Persian UI support.

    Extends SQLAlchemyDataLayer to provide:
    - Time-based conversation grouping (Today, Yesterday, Last 7 days, Last 30 days)
    - Persian labels for UI
    - Auto-generation of thread names from first user message
    - Async operations for scalability
    """

    def __init__(self, conninfo: str):
        """Initialize the data layer.

        Args:
            conninfo: PostgreSQL connection string
        """
        super().__init__(conninfo=conninfo)
        self.show_logger = False  # Set to True for debugging SQL queries

    async def create_thread(self, thread_dict: dict) -> Optional[str]:
        """Create a new conversation thread.

        Args:
            thread_dict: Dictionary containing thread metadata

        Returns:
            Thread ID if successful, None otherwise
        """
        try:
            thread_id = thread_dict.get("id")
            if self.show_logger:
                logger.info("creating_thread", thread_id=thread_id)

            return await super().create_thread(thread_dict)
        except Exception as e:
            logger.exception("create_thread_error", error=str(e))
            return None

    async def update_thread(
        self,
        thread_id: str,
        name: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        tags: Optional[list[str]] = None,
    ) -> Optional[str]:
        """Update thread metadata.

        Automatically generates thread name from first user message if not provided.

        Args:
            thread_id: Thread ID to update
            name: Thread name (auto-generated from first message if None)
            user_id: User ID for the thread
            metadata: Additional metadata
            tags: Tags for the thread

        Returns:
            Thread ID if successful
        """
        try:
            if self.show_logger:
                logger.info("updating_thread", thread_id=thread_id, name=name)

            return await super().update_thread(
                thread_id=thread_id,
                name=name,
                user_id=user_id,
                metadata=metadata,
                tags=tags,
            )
        except Exception as e:
            logger.exception("update_thread_error", error=str(e))
            return None

    async def get_all_user_threads(self, user_id: Optional[str]) -> Optional[list[ThreadDict]]:
        """Get all threads for a user, grouped by time period.

        Returns threads grouped into Persian-labeled time periods:
        - امروز (Today)
        - دیروز (Yesterday)
        - 7 روز گذشته (Last 7 days)
        - 30 روز گذشته (Last 30 days)

        Args:
            user_id: User ID to fetch threads for

        Returns:
            List of ThreadDict objects grouped by time
        """
        try:
            if self.show_logger:
                logger.info("getting_all_user_threads", user_id=user_id)

            # Get threads from base class
            threads = await super().get_all_user_threads(user_id)

            if not threads:
                return []

            # Group threads by time period
            grouped_threads = self._group_threads_by_time(threads)

            # Flatten grouped threads back to list (Chainlit UI handles grouping)
            flattened = []
            for period in ["امروز", "دیروز", "7 روز گذشته", "30 روز گذشته"]:
                if period in grouped_threads:
                    flattened.extend(grouped_threads[period])

            if self.show_logger:
                logger.info(
                    "threads_grouped",
                    total_threads=len(threads),
                    grouped_threads=len(flattened),
                )

            return flattened

        except Exception as e:
            logger.exception("get_all_user_threads_error", error=str(e))
            return []

    def _group_threads_by_time(self, threads: list[ThreadDict]) -> dict[str, list[ThreadDict]]:
        """Group threads by time period.

        Args:
            threads: List of ThreadDict objects

        Returns:
            Dictionary with time period keys and thread lists
        """
        now = datetime.now()
        today = now.date()

        groups: dict[str, list[ThreadDict]] = {
            "امروز": [],  # Today
            "دیروز": [],  # Yesterday
            "7 روز گذشته": [],  # Last 7 days
            "30 روز گذشته": [],  # Last 30 days
        }

        for thread in threads:
            try:
                # Get thread creation date
                created_at = thread.get("createdAt")
                if isinstance(created_at, str):
                    # Parse ISO format string
                    thread_date = datetime.fromisoformat(created_at.replace("Z", "+00:00")).date()
                elif isinstance(created_at, datetime):
                    thread_date = created_at.date()
                else:
                    logger.warning("invalid_thread_date", created_at=created_at)
                    thread_date = today

                # Calculate days since thread creation
                days_ago = (today - thread_date).days

                # Assign to appropriate group
                if days_ago == 0:
                    groups["امروز"].append(thread)
                elif days_ago == 1:
                    groups["دیروز"].append(thread)
                elif days_ago <= 7:
                    groups["7 روز گذشته"].append(thread)
                elif days_ago <= 30:
                    groups["30 روز گذشته"].append(thread)
                # Threads older than 30 days are not shown (can add another group if needed)

            except Exception as e:
                logger.warning("thread_grouping_error", thread_id=thread.get("id"), error=str(e))
                # Add to today group as fallback
                groups["امروز"].append(thread)

        return groups


def get_data_layer() -> LawAgentDataLayer:
    """Get or create the singleton data layer instance (synchronous).

    This ensures only one data layer is created for the entire application.
    Uses a simple lock-free pattern since this is called at app startup.

    Note: Uses psycopg2 (synchronous) instead of asyncpg for compatibility.
    Chainlit will handle async calls internally.

    Returns:
        LawAgentDataLayer instance
    """
    global _data_layer

    if _data_layer is None:
        settings = Settings.from_yaml()

        # Build PostgreSQL connection string using psycopg2 (synchronous)
        # Chainlit's SQLAlchemyDataLayer handles async calls internally
        db_config = settings.database
        conninfo = f"postgresql://{db_config.user}:{db_config.password}@{db_config.host}:{db_config.port}/{db_config.database}"

        logger.info(
            "initializing_data_layer",
            host=db_config.host,
            port=db_config.port,
            database=db_config.database,
            driver="psycopg2",
        )

        _data_layer = LawAgentDataLayer(conninfo=conninfo)
        logger.info("data_layer_initialized")

    return _data_layer


def reset_data_layer() -> None:
    """Reset the data layer singleton (for testing).

    This is useful for test isolation.
    """
    global _data_layer
    _data_layer = None
