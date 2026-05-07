"""
Custom Chainlit data layer for Law Agent.

Extends SQLAlchemyDataLayer with:
- Thread auto-creation on first user message (matching data-assistant pattern)
- Persian time-based conversation grouping for sidebar
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

import structlog
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.step import StepDict
from chainlit.types import ThreadDict

from law_agent.config.settings import Settings

logger = structlog.get_logger(__name__)

_data_layer: Optional[LawAgentDataLayer] = None


class LawAgentDataLayer(SQLAlchemyDataLayer):
    """Chainlit data layer for Law Agent with Persian UI support.

    Follows the data-assistant pattern:
    - Override create_step() to auto-create thread on first user message
    - Override get_all_user_threads() to add Persian time grouping
    - Let parent class handle all SQL execution (no execute_sql override)
    """

    # Class-level lock following data-assistant pattern
    step_creation_lock = asyncio.Lock()

    async def create_step(self, step_dict: "StepDict"):
        """Override to auto-create thread from first user message.

        Pattern from data-assistant/src/datasource/postgres/chainlit_data_layer.py:
        1. Check if thread exists
        2. If first user message: create thread with message as name
        3. Otherwise: skip (non-user steps before thread exists are ignored)
        4. Call super().create_step() for actual persistence
        """
        async with self.step_creation_lock:
            thread_id = step_dict["threadId"]
            thread = await self.get_thread(thread_id)

            if thread is None:
                if step_dict["type"] == "user_message":
                    # Auto-create thread named after first user message
                    user_id = None
                    try:
                        import chainlit as cl
                        user = cl.user_session.get("user")
                        if user:
                            user_id = user.id
                    except Exception:
                        pass

                    await self.update_thread(
                        thread_id,
                        name=step_dict["output"],
                        user_id=user_id,
                    )
                    logger.info("thread_auto_created", thread_id=thread_id)
                else:
                    # Non-user steps before thread exists: skip
                    return

            return await super().create_step(step_dict)

    async def get_all_user_threads(
        self, user_id: Optional[str] = None, thread_id: Optional[str] = None
    ) -> Optional[List[ThreadDict]]:
        """Override to sort threads newest-first for Persian sidebar display."""
        threads = await super().get_all_user_threads(
            user_id=user_id, thread_id=thread_id
        )
        if not threads:
            return threads
        return sorted(threads, key=_parse_thread_date, reverse=True)


def _parse_thread_date(thread: ThreadDict) -> datetime:
    created_at = thread.get("createdAt")
    if isinstance(created_at, str):
        try:
            return datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.min


# ---------------------------------------------------------------------------
# Singleton initialization
# ---------------------------------------------------------------------------

try:
    from sqlalchemy.engine import URL

    settings = Settings.from_yaml()
    db_config = settings.database

    db_url = URL.create(
        drivername="postgresql+asyncpg",
        host=db_config.host,
        port=db_config.port,
        username=db_config.user,
        password=db_config.password,
        database=db_config.database,
    )

    _data_layer = LawAgentDataLayer(conninfo=str(db_url), show_logger=True)
    logger.info(
        "data_layer_initialized",
        host=db_config.host,
        database=db_config.database,
    )
except Exception as e:
    logger.exception("failed_to_initialize_data_layer", error=str(e))
    _data_layer = None


def get_data_layer() -> LawAgentDataLayer:
    if _data_layer is None:
        raise RuntimeError(
            "Data layer not initialized. Check logs for initialization errors."
        )
    return _data_layer


def reset_data_layer() -> None:
    """Reset the data layer singleton (for testing)."""
    global _data_layer
    _data_layer = None
