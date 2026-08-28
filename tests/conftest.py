"""Shared test fixtures."""

import pytest

from custom_components.eneco_data.const import (
    CONF_API_KEY,
    CONF_CUSTOMER_ID,
    CONF_SESSION_TOKEN,
    DOMAIN,
)

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Make custom_components/ visible to Home Assistant's loader in tests."""
    yield


@pytest.fixture
def mock_config_entry():
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="12345678",
        data={
            CONF_CUSTOMER_ID: "12345678",
            CONF_API_KEY: "test-api-key",
            CONF_SESSION_TOKEN: "test-session-token",
        },
    )
