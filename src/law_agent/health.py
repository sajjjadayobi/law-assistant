"""
Health check endpoints and monitoring for the Law Agent application.

This module provides health check functionality for deployment monitoring:
- Application readiness check
- Database connectivity check
- Phoenix observability connectivity check
- Detailed status information
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from sqlalchemy import text

from law_agent.database.connection import _get_engine

logger = structlog.get_logger(__name__)


async def check_database_health() -> dict[str, Any]:
    """
    Check database connectivity and readiness.

    Returns:
        Dictionary with status and details
    """
    try:
        engine = _get_engine()
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            if result.fetchone():
                return {
                    "status": "healthy",
                    "component": "database",
                    "message": "Database connection successful",
                }
            else:
                return {
                    "status": "unhealthy",
                    "component": "database",
                    "message": "Database query returned no results",
                }
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        return {
            "status": "unhealthy",
            "component": "database",
            "message": f"Database connection failed: {str(e)}",
        }


async def check_phoenix_health() -> dict[str, Any]:
    """
    Check Phoenix observability platform connectivity.

    Returns:
        Dictionary with status and details
    """
    try:
        import httpx

        phoenix_url = "http://localhost:6006/health"
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(phoenix_url)
                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "component": "phoenix",
                        "message": "Phoenix connection successful",
                    }
                else:
                    return {
                        "status": "degraded",
                        "component": "phoenix",
                        "message": f"Phoenix returned status {response.status_code}",
                    }
        except Exception as e:
            return {
                "status": "degraded",
                "component": "phoenix",
                "message": f"Phoenix connection timeout or error: {str(e)}",
            }
    except ImportError:
        return {
            "status": "unknown",
            "component": "phoenix",
            "message": "httpx not available, skipping Phoenix check",
        }


async def get_health_status() -> dict[str, Any]:
    """
    Get comprehensive health status of the application.

    Returns:
        Dictionary with overall status and component details
    """
    try:
        # Check database and Phoenix in parallel
        db_check, phoenix_check = await asyncio.gather(
            check_database_health(),
            check_phoenix_health(),
            return_exceptions=True,
        )

        # Convert exceptions to error responses
        if isinstance(db_check, Exception):
            db_check = {
                "status": "unhealthy",
                "component": "database",
                "message": f"Error checking database: {str(db_check)}",
            }

        if isinstance(phoenix_check, Exception):
            phoenix_check = {
                "status": "degraded",
                "component": "phoenix",
                "message": f"Error checking phoenix: {str(phoenix_check)}",
            }

        # Determine overall status
        all_checks = [db_check, phoenix_check]
        statuses = [check["status"] for check in all_checks]

        if "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "degraded" in statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return {
            "status": overall_status,
            "components": {
                "database": db_check,
                "phoenix": phoenix_check,
            },
        }
    except Exception as e:
        logger.exception("health_check_failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": f"Health check failed: {str(e)}",
        }


async def get_readiness() -> dict[str, Any]:
    """
    Check if application is ready to serve requests.

    Returns:
        Dictionary with readiness status
    """
    health = await get_health_status()

    # Application is ready if database is healthy
    # (Phoenix being degraded is OK, but database is required)
    is_ready = health.get("components", {}).get("database", {}).get("status") == "healthy"

    return {
        "ready": is_ready,
        "status": health.get("status"),
        "details": health,
    }
