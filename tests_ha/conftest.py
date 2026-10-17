"""Shared fixtures for Home Assistant behavior tests."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow loading the integration from custom_components."""

    yield


@pytest.fixture(autouse=True)
def skip_dependency_setup_for_flow_tests():
    """Load config flows without setting up unrelated frontend dependencies."""

    with patch(
        "homeassistant.config_entries.async_process_deps_reqs", AsyncMock()
    ):
        yield
