"""Tests for the Eneco Data coordinator."""

from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.eneco_data.api import EnecoApiError, EnecoAuthError
from custom_components.eneco_data.coordinator import EnecoCoordinator

FIXTURE_CSV = (Path(__file__).parent / "fixtures" / "meterstanden.csv").read_bytes()

FETCH_TARGET = "custom_components.eneco_data.coordinator.EnecoClient.fetch_meterstanden_csv"
ADD_STATS_TARGET = "custom_components.eneco_data.coordinator.async_add_external_statistics"


async def test_update_pushes_external_statistics(hass, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    coordinator = EnecoCoordinator(hass, mock_config_entry)

    with (
        patch(FETCH_TARGET, return_value=(FIXTURE_CSV, "renewed-token")),
        patch(ADD_STATS_TARGET) as mock_add_stats,
    ):
        await coordinator._async_update_data()

    assert mock_add_stats.call_count == 2
    statistic_ids = {
        call.args[1]["statistic_id"] for call in mock_add_stats.call_args_list
    }
    assert statistic_ids == {"eneco_data:heat_gj", "eneco_data:heat_m3"}


async def test_update_persists_renewed_token(hass, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    coordinator = EnecoCoordinator(hass, mock_config_entry)

    with (
        patch(FETCH_TARGET, return_value=(FIXTURE_CSV, "renewed-token")),
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
