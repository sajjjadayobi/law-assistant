"""
Pytest configuration and shared fixtures for all tests.

This file is automatically loaded by pytest and provides:
- Shared test configuration
- Common fixtures for unit and integration tests
- Database setup/teardown (to be added in Task 2.7)
"""

import pytest


@pytest.fixture(scope="session")
def test_config():
    """Load test configuration (to be implemented in Task 2.7)."""
    pass


@pytest.fixture
def mock_logger(monkeypatch):
    """Provide a mock logger for tests that need logging."""
    pass
