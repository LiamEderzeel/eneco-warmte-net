"""Tests for the Eneco Data coordinator."""

from unittest.mock import patch

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.eneco_data.api import EnecoApiError, EnecoAuthError
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
