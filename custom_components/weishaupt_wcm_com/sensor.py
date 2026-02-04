"""Sensor platform for the Weishaupt WCM-COM integration.

All sensors are backed by a shared DataUpdateCoordinator which performs
exactly one request to the WCM-COM device per update interval.
"""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    NAME_PREFIX,
    PARAMETERS,
    ERROR_CODE_KEY,
    OPERATION_MODE_MAP,
    OPERATION_PHASE_MAP,
)
from .base_entity import WeishauptBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform for a config entry."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DataUpdateCoordinator = entry_data["coordinator"]
    api = entry_data["api"]

    sensors: list[WeishauptSensor] = []
    for param in PARAMETERS:
        sensor_name = param["name"]
        unit = UnitOfTemperature.CELSIUS if param["type"] == "temperature" else None
        sensors.append(WeishauptSensor(coordinator, api, sensor_name, unit))

    async_add_entities(sensors)


class WeishauptSensor(CoordinatorEntity, WeishauptBaseEntity, SensorEntity):
    """Representation of a Weishaupt Sensor using shared coordinator data."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api,
        sensor_name: str,
        unit,
    ) -> None:
        """Initialize the sensor."""

        CoordinatorEntity.__init__(self, coordinator)
        WeishauptBaseEntity.__init__(self, api)

        self._sensor_name = sensor_name
        # Slug für Übersetzungs-Key und eindeutige IDs
        slug = self._sensor_name.lower().replace(" ", "_")

        # Use a translation_key derived from the parameter name so that
        # translations/en.json and translations/de.json define the visible
        # label. Keys are lowercase and underscore separated.
        self._attr_translation_key = slug
        # Wir verwenden Übersetzungen + has_entity_name, damit HA
        # den übersetzten Namen pro Entity verwendet.
        self._attr_has_entity_name = True
        self._attr_native_unit_of_measurement = unit

        # Nutze ein konsistentes Unique-ID-Schema, das deinem Wunschpattern
        # entspricht: weishaupt_<slug>
        # Beispiel: weishaupt_hk1_gemischte_außentemperatur
        self._attr_unique_id = f"weishaupt_{slug}"

        # Erzwinge einheitliche entity_ids nach dem Schema:
        #   sensor.weishaupt_<slug>
        # Beispiel: sensor.weishaupt_hk1_gemischte_außentemperatur
        self.entity_id = f"sensor.weishaupt_{slug}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for grouping sensors (Kessel, HK1, HK2)."""

        slug = self._sensor_name.lower().replace(" ", "_")

        if slug.startswith("hk1_"):
            ident = "weishaupt_hk1"
            name = "Weishaupt HK1"
        elif slug.startswith("hk2_"):
            ident = "weishaupt_hk2"
            name = "Weishaupt HK2"
        else:
            ident = "weishaupt_kessel"
            name = "Weishaupt Kessel"

        return DeviceInfo(
            identifiers={(DOMAIN, ident)},
            name=name,
            manufacturer="Weishaupt",
            model="WCM-COM",
        )

    @property
    def native_value(self):
        """Return the state of the sensor based on the latest data."""

        data = self.coordinator.data or {}

        try:
            value = data.get(self._sensor_name)
            if value is None:
                _LOGGER.debug("Data for %s not found", self._sensor_name)
                return None

            # Special handling for certain sensors
            if self._sensor_name == ERROR_CODE_KEY:
                # Map error codes to human readable text
                return self.api.process_codes(value)

            if self._sensor_name == "Betriebsmodus":
                return OPERATION_MODE_MAP.get(
                    value,
                    f"Unbekannter Modus ({value})",
                )

            if self._sensor_name == "Betriebsphase":
                return OPERATION_PHASE_MAP.get(
                    value,
                    f"Unbekannte Phase ({value})",
                )

            param_type = next(
                (p["type"] for p in PARAMETERS if p["name"] == self._sensor_name),
                None,
            )

            if param_type == "binary":
                return "Ein" if value else "Aus"

            if param_type in ("value", "temperature") or param_type is None:
                return value

            # Fallback: return the raw value
            return value

        except Exception as err:  # pragma: no cover  # pylint: disable=broad-except
            _LOGGER.error(
                "Error updating sensor %s from coordinator data: %s",
                self._sensor_name,
                err,
            )
            return None
