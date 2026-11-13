"""Update coordinator: fetch daily district-heating usage and push it into
Home Assistant's long-term statistics for the Energy Dashboard, as external
statistics.
"""

from __future__ import annotations

import logging
from datetime import date, datetime

from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import EnecoApiError, EnecoAuthError, EnecoClient
from .const import (
    CONF_API_KEY,
    CONF_CUSTOMER_ID,
    CONF_SESSION_TOKEN,
    DOMAIN,
    FIRST_MONTH,
    STAT_SLUG,
    UPDATE_INTERVAL,
)
from .parser import cumulative

_LOGGER = logging.getLogger(__name__)

type EnecoConfigEntry = ConfigEntry[EnecoCoordinator]


class EnecoCoordinator(DataUpdateCoordinator[datetime]):
    """Fetches, parses, and pushes Eneco meter readings once per cycle."""

    config_entry: EnecoConfigEntry

    def __init__(self, hass: HomeAssistant, entry: EnecoConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = EnecoClient(
            entry.data[CONF_CUSTOMER_ID],
            entry.data[CONF_API_KEY],
            entry.data[CONF_SESSION_TOKEN],
        )

    async def _async_update_data(self) -> datetime:
        try:
            daily, new_token = await self.hass.async_add_executor_job(
                self.client.fetch_daily_usage, FIRST_MONTH
            )
        except EnecoAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except EnecoApiError as err:
            raise UpdateFailed(str(err)) from err

        # Persist the renewed cookie every cycle, regardless of what
        # happens below - this is what keeps the session alive.
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={**self.config_entry.data, CONF_SESSION_TOKEN: new_token},
        )

        stats = [
            StatisticData(
                start=dt_util.as_utc(dt_util.start_of_local_day(date.fromisoformat(d))),
                state=total,
                sum=total,
            )
            for d, total in cumulative(daily)
        ]
        if not stats:
            _LOGGER.warning("No usage data returned")
            return dt_util.utcnow()

        async_add_external_statistics(
            self.hass,
            StatisticMetaData(
                mean_type=StatisticMeanType.NONE,
                has_sum=True,
                name=f"Eneco {STAT_SLUG}",
                source=DOMAIN,
                statistic_id=f"{DOMAIN}:{STAT_SLUG}",
                unit_class="energy",
                unit_of_measurement=UnitOfEnergy.GIGA_JOULE,
            ),
            stats,
        )

        return dt_util.utcnow()
