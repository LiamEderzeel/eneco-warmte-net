"""Tests for the Eneco Data config flow."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.eneco_data.api import EnecoApiError, EnecoAuthError
from custom_components.eneco_data.const import (
    CONF_API_KEY,
    CONF_CUSTOMER_ID,
    CONF_SESSION_TOKEN,
    DOMAIN,
)


USER_INPUT = {
    CONF_CUSTOMER_ID: "12345678",
    CONF_API_KEY: "test-api-key",
    CONF_SESSION_TOKEN: "test-session-token",
}

FETCH_TARGET = "custom_components.eneco_data.config_flow.EnecoClient.fetch_daily_usage"


async def test_user_flow_success(recorder_mock, enable_custom_integrations, hass):
    with patch(FETCH_TARGET, return_value=({}, "renewed-token")):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Eneco Data"
    assert result["data"] == USER_INPUT


async def test_user_flow_invalid_auth(recorder_mock, enable_custom_integrations, hass):
    with patch(FETCH_TARGET, side_effect=EnecoAuthError("expired")):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(recorder_mock, enable_custom_integrations, hass):
    with patch(FETCH_TARGET, side_effect=EnecoApiError("boom")):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_reauth_flow_updates_token(
    recorder_mock, enable_custom_integrations, hass, mock_config_entry
):
    mock_config_entry.add_to_hass(hass)

    with patch(FETCH_TARGET, return_value=({}, "brand-new-token")):
        result = await mock_config_entry.start_reauth_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_SESSION_TOKEN: "brand-new-token"}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_SESSION_TOKEN] == "brand-new-token"
