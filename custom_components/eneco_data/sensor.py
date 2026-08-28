"""Diagnostic sensor for Eneco Data.

The actual heat readings are pushed as external recorder statistics
(see coordinator.py), not entity state - this is the one real entity
the integration owns. It exists to (a) keep the coordinator's polling
timer alive (DataUpdateCoordinator only refreshes while it has at least
one listener) and (b) give the user visible confirmation that the daily
import is actually running.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EnecoConfigEntry, EnecoCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnecoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([EnecoLastImportSensor(entry.runtime_data, entry.entry_id)])


class EnecoLastImportSensor(CoordinatorEntity[EnecoCoordinator], SensorEntity):
    """Timestamp of the last successful import cycle."""

    _attr_has_entity_name = True
    _attr_translation_key = "last_import"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: EnecoCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_last_import"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Eneco Data",
        )

    @property
    def native_value(self):
        return self.coordinator.data
