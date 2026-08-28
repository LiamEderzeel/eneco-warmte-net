"""Daily update coordinator: fetch the GDPR export, parse it, and push
district-heating readings into Home Assistant's long-term statistics for
the Energy Dashboard - as external statistics, since these are periodic
meter readings, not a live-polled entity.
"""

from __future__ import annotations

import io
import logging
from datetime import date, datetime

from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.config_entries import ConfigEntry
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
    TYPE_TO_STAT,
    UPDATE_INTERVAL,
)
from .parser import load_readings, resolve_series

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
            csv_bytes, new_token = await self.hass.async_add_executor_job(
                self.client.fetch_meterstanden_csv
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

        text = csv_bytes.decode("utf-8-sig")
        readings = load_readings(io.StringIO(text))

        for row_type, (slug, unit, unit_class) in TYPE_TO_STAT.items():
            series = resolve_series(readings.get(row_type, {}))
            if not series:
                _LOGGER.warning("No data found for %s", row_type)
                continue

            stats = [
                StatisticData(
                    start=dt_util.as_utc(
                        dt_util.start_of_local_day(date.fromisoformat(d))
                    ),
                    state=value,
                    sum=value,
                )
                for d, value in series
            ]
            async_add_external_statistics(
                self.hass,
                StatisticMetaData(
                    mean_type=StatisticMeanType.NONE,
                    has_sum=True,
                    name=f"Eneco {slug}",
                    source=DOMAIN,
                    statistic_id=f"{DOMAIN}:{slug}",
                    unit_class=unit_class,
                    unit_of_measurement=unit,
                ),
                stats,
            )

        return dt_util.utcnow()
