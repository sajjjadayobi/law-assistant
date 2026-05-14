"""Health check functions for Docker and monitoring system integration."""

from __future__ import annotations

import httpx
import structlog

from law_assistant.config.settings import get_settings
from law_assistant.database.connection import check_connection

logger = structlog.get_logger(__name__)


async def check_database_health() -> dict[str, str]:
    try:
        ok = check_connection()
        if ok:
            return {"status": "healthy", "message": "Database connection successful"}
        return {"status": "unhealthy", "message": "Database query failed"}
    except Exception as exc:
        logger.warning("database_health_check_failed", error=str(exc))
        return {"status": "unhealthy", "message": str(exc)}


async def check_phoenix_health() -> dict[str, str]:
    settings = get_settings()
    endpoint = settings.observability.phoenix_endpoint
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{endpoint}/healthz")
            if resp.status_code < 400:
                return {"status": "healthy", "message": "Phoenix connection successful"}
            return {"status": "degraded", "message": f"Phoenix returned {resp.status_code}"}
    except Exception as exc:
        logger.warning("phoenix_health_check_failed", error=str(exc))
        return {"status": "degraded", "message": str(exc)}


async def get_health_status() -> dict[str, object]:
    db = await check_database_health()
    phoenix = await check_phoenix_health()

    if db["status"] == "unhealthy":
        overall = "unhealthy"
    elif phoenix["status"] != "healthy":
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "status": overall,
        "components": {"database": db, "phoenix": phoenix},
    }


async def get_readiness() -> dict[str, object]:
    db = await check_database_health()
    return {
        "ready": db["status"] == "healthy",
        "status": db["status"],
        "details": db,
    }
