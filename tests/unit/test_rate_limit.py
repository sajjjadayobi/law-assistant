"""Tests for rate limiting functionality."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from law_agent.ui.rate_limit import check_and_increment, ensure_rate_limits_table


@pytest.mark.asyncio
async def test_ensure_rate_limits_table() -> None:
    """Test that ensure_rate_limits_table creates the table."""
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_conn
    mock_context.__aexit__.return_value = None
    mock_engine.begin.return_value = mock_context

    await ensure_rate_limits_table(mock_engine)

    # Verify exec_driver_sql was called
    mock_conn.exec_driver_sql.assert_called_once()
    sql_call = mock_conn.exec_driver_sql.call_args[0][0]
    assert "CREATE TABLE IF NOT EXISTS rate_limits" in sql_call


@pytest.mark.asyncio
async def test_check_and_increment_first_request() -> None:
    """Test that first request is allowed."""
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_conn
    mock_context.__aexit__.return_value = None
    mock_engine.begin.return_value = mock_context

    mock_raw_conn = MagicMock()
    mock_async_conn = AsyncMock()
    mock_conn.get_raw_connection = AsyncMock(return_value=mock_raw_conn)
    mock_raw_conn.driver_connection = mock_async_conn

    # Simulate first request: INSERT returns count=1
    mock_async_conn.fetchval.return_value = 1

    # Mock the table initialization to skip the first check
    with patch("law_agent.ui.rate_limit._table_initialized", True):
        result = await check_and_increment(mock_engine, "test@example.com", limit=30)

    assert result is True
    mock_async_conn.fetchval.assert_called_once()
    call_args = mock_async_conn.fetchval.call_args
    assert "INSERT INTO rate_limits" in call_args[0][0]
    assert call_args[0][1] == "test@example.com"
    assert call_args[0][2] == date.today()


@pytest.mark.asyncio
async def test_check_and_increment_at_limit() -> None:
    """Test that request at limit is allowed."""
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_conn
    mock_context.__aexit__.return_value = None
    mock_engine.begin.return_value = mock_context

    mock_raw_conn = MagicMock()
    mock_async_conn = AsyncMock()
    mock_conn.get_raw_connection = AsyncMock(return_value=mock_raw_conn)
    mock_raw_conn.driver_connection = mock_async_conn

    # Simulate 30th request: INSERT returns count=30
    mock_async_conn.fetchval.return_value = 30

    with patch("law_agent.ui.rate_limit._table_initialized", True):
        result = await check_and_increment(mock_engine, "test@example.com", limit=30)

    assert result is True


@pytest.mark.asyncio
async def test_check_and_increment_exceeds_limit() -> None:
    """Test that request exceeding limit is denied."""
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_conn
    mock_context.__aexit__.return_value = None
    mock_engine.begin.return_value = mock_context

    mock_raw_conn = MagicMock()
    mock_async_conn = AsyncMock()
    mock_conn.get_raw_connection = AsyncMock(return_value=mock_raw_conn)
    mock_raw_conn.driver_connection = mock_async_conn

    # Simulate 31st request: INSERT returns count=31
    mock_async_conn.fetchval.return_value = 31

    with patch("law_agent.ui.rate_limit._table_initialized", True):
        result = await check_and_increment(mock_engine, "test@example.com", limit=30)

    assert result is False


@pytest.mark.asyncio
async def test_check_and_increment_database_error() -> None:
    """Test that database error returns True (fail open)."""
    mock_engine = MagicMock()
    mock_engine.begin.side_effect = Exception("Database connection failed")

    with patch("law_agent.ui.rate_limit._table_initialized", True):
        result = await check_and_increment(mock_engine, "test@example.com", limit=30)

    # Fail open: return True on error
    assert result is True
