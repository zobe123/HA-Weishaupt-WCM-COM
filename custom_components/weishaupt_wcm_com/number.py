"""Number platform for Weishaupt WCM-COM expert parameters.

Currently used for:
- Expert Corr Outside Sensor (P20, ID 3103) as a -4..+4 K slider.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.config_entries import ConfigEntry

from .base_entity import WeishauptBaseEntity
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities for a config entry."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DataUpdateCoordinator = entry_data["coordinator"]
    api = entry_data["api"]

    numbers: list[WeishauptExpertNumber] = []

    # Expert Corr Outside Sensor (P20 / ID 3103) – Außentemperatur-Korrektur
    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "Expert Corr Outside Sensor",
            parameter_id=3103,
            min_value=-4,
            max_value=4,
            step=1,
        )
    )

    async_add_entities(numbers)


class WeishauptExpertNumber(CoordinatorEntity, WeishauptBaseEntity, NumberEntity):
    """Number entity for expert parameters (slider-based configuration)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_unit_of_measurement = UnitOfTemperature.KELVIN

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api,
        sensor_name: str,
        parameter_id: int,
        min_value: float,
        max_value: float,
        step: float,
    ) -> None:
        """Initialize the expert number entity."""

        CoordinatorEntity.__init__(self, coordinator)
        WeishauptBaseEntity.__init__(self, api)

        self._sensor_name = sensor_name
        self._parameter_id = parameter_id

        slug = self._sensor_name.lower().replace(" ", "_")
        self._attr_translation_key = slug
        self._attr_name = self._sensor_name
        self._attr_unique_id = f"weishaupt_{slug}_number"

        self._attr_native_min_value = float(min_value)
        self._attr_native_max_value = float(max_value)
        self._attr_native_step = float(step)

        # Klar machen, dass es sich um eine Korrektur handelt
        self._attr_icon = "mdi:thermometer-minus"

    @property
    def device_info(self):
        """Attach expert numbers to the boiler device."""

        return {
            "identifiers": {(DOMAIN, "weishaupt_kessel")},
            "name": "Weishaupt Kessel",
            "manufacturer": "Weishaupt",
            "model": "WCM-COM",
        }

    @property
    def native_value(self) -> float | None:
        """Return the current value from the coordinator data."""

        data = self.coordinator.data or {}
        value = data.get(self._sensor_name)

        if value is None:
            self._attr_available = False
            return None

        self._attr_available = True
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Handle value changes from Home Assistant."""

        # Clamp to allowed range just in case
        value = max(self._attr_native_min_value, min(self._attr_native_max_value, value))

        # P20 / ID 3103 is a global expert parameter; WebApp uses TEL_MTYPE_WG
        # which corresponds to the WG module type (10) on bus 0 in the CoCo telegrams.
        code = int(round(value))
        self.api.write_parameter(parameter_id=self._parameter_id, bus=0, modultyp=10, code=code)

        # Nach dem Schreiben den Coordinator aktualisieren
        await self.coordinator.async_request_refresh()
