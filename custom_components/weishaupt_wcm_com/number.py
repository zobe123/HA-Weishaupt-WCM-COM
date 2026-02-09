"""Number platform for Weishaupt WCM-COM expert parameters.

Currently used for:
- Expert Corr Outside Sensor (P20, ID 3103) as a -4..+4 K slider.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.const import UnitOfTemperature, UnitOfTime, PERCENTAGE
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
    allow_write: bool = entry_data.get("allow_write", False)

    numbers: list[WeishauptExpertNumber] = []

    # Expert Spec Level Heating Mode (P18 / ID 3102) – Sonderniveau Heizbetrieb
    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "Expert Spec Level Heating Mode",
            parameter_id=3102,
            min_value=8,
            max_value=85,
            step=1,
            scale=1.0,
            unit=UnitOfTemperature.CELSIUS,
            allow_write=allow_write,
        )
    )

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
            scale=1.0,
            unit=UnitOfTemperature.CELSIUS,
            allow_write=allow_write,
        )
    )

    # Expert Min/Max VL Target (P30/P31 / ID 31/39) – Min/Max Vorlauf-Solltemp.
    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "Expert Min VL Target",
            parameter_id=31,
            min_value=8.0,
            max_value=85.0,
            step=1.0,
            scale=1.0,
            unit=UnitOfTemperature.CELSIUS,
            allow_write=allow_write,
        )
    )

    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "Expert Max VL Target",
            parameter_id=39,
            min_value=8.0,
            max_value=85.0,
            step=1.0,
            scale=1.0,
            unit=UnitOfTemperature.CELSIUS,
            allow_write=allow_write,
        )
    )

    # Expert Switch Diff VL (P32 / ID 34) – Schaltdifferenz Vorlauf
    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "Expert Switch Diff VL",
            parameter_id=34,
            min_value=-7.0,
            max_value=7.0,
            step=1.0,
            scale=1.0,
            unit=UnitOfTemperature.CELSIUS,
            allow_write=allow_write,
        )
    )

    # Expert Burner Pulse Lock (P34 / ID 323) – Brenner-Taktsperre in Minuten
    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "Expert Burner Pulse Lock",
            parameter_id=323,
            min_value=1,
            max_value=15,
            step=1,
            scale=1.0,
            unit=UnitOfTime.MINUTES,
            allow_write=allow_write,
        )
    )

    # Expert Max Power Heating / WW (P37/P38 / ID 319/345) – Prozentwerte
    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "Expert Max Power Heating",
            parameter_id=319,
            min_value=20.0,
            max_value=100.0,
            step=1.0,
            scale=1.0,
            unit=PERCENTAGE,
            allow_write=allow_write,
        )
    )

    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "Expert Max Power WW",
            parameter_id=345,
            min_value=20.0,
            max_value=100.0,
            step=1.0,
            scale=1.0,
            unit=PERCENTAGE,
            allow_write=allow_write,
        )
    )

    # Expert Max Charge Time WW (P52 / ID 384) – max. WW-Ladezeit in Minuten
    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "Expert Max Charge Time WW",
            parameter_id=384,
            min_value=10,
            max_value=60,
            step=1,
            scale=1.0,
            unit=UnitOfTime.MINUTES,
            allow_write=allow_write,
        )
    )

    async_add_entities(numbers)


class WeishauptExpertNumber(CoordinatorEntity, WeishauptBaseEntity, NumberEntity):
    """Number entity for expert parameters (slider-based configuration)."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api,
        sensor_name: str,
        parameter_id: int,
        min_value: float,
        max_value: float,
        step: float,
        scale: float = 1.0,
        unit: str | None = None,
        allow_write: bool = False,
    ) -> None:
        """Initialize the expert number entity."""

        CoordinatorEntity.__init__(self, coordinator)
        WeishauptBaseEntity.__init__(self, api)

        self._sensor_name = sensor_name
        self._parameter_id = parameter_id
        self._scale = float(scale) if scale else 1.0
        self._allow_write = allow_write

        slug = self._sensor_name.lower().replace(" ", "_")
        self._attr_translation_key = slug
        self._attr_name = self._sensor_name
        self._attr_unique_id = f"weishaupt_{slug}_number"

        self._attr_native_min_value = float(min_value)
        self._attr_native_max_value = float(max_value)
        self._attr_native_step = float(step)

        # Einheit optional setzen
        if unit is not None:
            self._attr_native_unit_of_measurement = unit

        # Icon je nach Parameter leicht variieren
        if "Corr Outside Sensor" in sensor_name:
            self._attr_icon = "mdi:thermometer-minus"
        elif "Spec Level Heating Mode" in sensor_name:
            self._attr_icon = "mdi:thermometer"
        elif "Power" in sensor_name:
            self._attr_icon = "mdi:gauge"
        elif "Pulse Lock" in sensor_name or "Charge Time" in sensor_name:
            self._attr_icon = "mdi:clock-outline"
        else:
            self._attr_icon = "mdi:tune-variant"

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
            return float(value) / self._scale
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Handle value changes from Home Assistant."""

        if not self._allow_write:
            from homeassistant.exceptions import HomeAssistantError
            raise HomeAssistantError("Weishaupt WCM-COM integration is in read-only mode.")

        # Clamp to allowed range just in case
        value = max(self._attr_native_min_value, min(self._attr_native_max_value, value))

        # Skalierten Rohwert berechnen (DIV=10 etc. analog zur WebApp-Logik)
        code = int(round(value * self._scale))

        # Expert-Parameter sind globale WG‑Parameter (Modultyp 10, Bus 0)
        self.api.write_parameter(parameter_id=self._parameter_id, bus=0, modultyp=10, code=code)

        # Nach dem Schreiben den Coordinator aktualisieren
        await self.coordinator.async_request_refresh()
