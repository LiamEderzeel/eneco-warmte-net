"""Tests for the Eneco Data coordinator."""

from unittest.mock import patch

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.eneco_data.api import (
    EnecoApiError,
    EnecoApiKeyError,
    EnecoAuthError,
)
from custom_components.eneco_data.coordinator import EnecoCoordinator

DAILY = {"2026-11-01": 0.05, "2026-11-02": 0.1}

FETCH_TARGET = "custom_components.eneco_data.coordinator.EnecoClient.fetch_daily_usage"
ADD_STATS_TARGET = "custom_components.eneco_data.coordinator.async_add_external_statistics"


async def test_update_pushes_external_statistics(hass, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    coordinator = EnecoCoordinator(hass, mock_config_entry)

    with (
        patch(FETCH_TARGET, return_value=(DAILY, "renewed-token")),
        patch(ADD_STATS_TARGET) as mock_add_stats,
    ):
        await coordinator._async_update_data()

    mock_add_stats.assert_called_once()
    _, metadata, stats = mock_add_stats.call_args.args
    assert metadata["statistic_id"] == "eneco_data:heat_gj_daily"
    assert [round(s["sum"], 2) for s in stats] == [0.05, 0.15]


async def test_update_persists_renewed_token(hass, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    coordinator = EnecoCoordinator(hass, mock_config_entry)

    with (
        patch(FETCH_TARGET, return_value=(DAILY, "renewed-token")),
        patch(ADD_STATS_TARGET),
    ):
        await coordinator._async_update_data()

    assert mock_config_entry.data["session_token"] == "renewed-token"


async def test_update_raises_config_entry_auth_failed(hass, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    coordinator = EnecoCoordinator(hass, mock_config_entry)

    with patch(FETCH_TARGET, side_effect=EnecoAuthError("expired")):
        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()


async def test_update_raises_update_failed(hass, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    coordinator = EnecoCoordinator(hass, mock_config_entry)

    with patch(FETCH_TARGET, side_effect=EnecoApiError("boom")):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_update_pushes_cost_statistic_when_price_set(hass, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry, options={"heat_price": 40.0}
    )
    coordinator = EnecoCoordinator(hass, mock_config_entry)

    with (
        patch(FETCH_TARGET, return_value=(DAILY, "renewed-token")),
        patch(ADD_STATS_TARGET) as mock_add_stats,
    ):
        await coordinator._async_update_data()

    assert mock_add_stats.call_count == 2
    _, metadata, stats = mock_add_stats.call_args_list[1].args
    assert metadata["statistic_id"] == "eneco_data:heat_cost"
    assert metadata["unit_of_measurement"] == hass.config.currency
    assert [round(s["sum"], 2) for s in stats] == [2.0, 6.0]


async def test_update_uses_account_id_from_options(hass, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(mock_config_entry, options={"account_id": "2"})
    coordinator = EnecoCoordinator(hass, mock_config_entry)

    assert coordinator.client._account_id == "2"


async def test_update_rejected_api_key_triggers_reauth(hass, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    coordinator = EnecoCoordinator(hass, mock_config_entry)

    with patch(FETCH_TARGET, side_effect=EnecoApiKeyError("401")):
        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()
