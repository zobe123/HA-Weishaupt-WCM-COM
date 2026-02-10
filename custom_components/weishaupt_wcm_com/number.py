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
            max_value=180,
            step=1,
            scale=1.0,
            unit=UnitOfTime.MINUTES,
            allow_write=allow_write,
        )
    )

    # Frostheizgrenze (ID 702) – Fachmann / Heizung, -20..0 °C
    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "HK1 Expert Frostheizgrenze",
            parameter_id=702,
            min_value=-20.0,
            max_value=0.0,
            step=1.0,
            scale=1.0,
            unit=UnitOfTemperature.CELSIUS,
            bus=1,
            modultyp=6,
            allow_write=allow_write,
        )
    )

    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "HK2 Expert Frostheizgrenze",
            parameter_id=702,
            min_value=-20.0,
            max_value=0.0,
            step=1.0,
            scale=1.0,
            unit=UnitOfTemperature.CELSIUS,
            bus=2,
            modultyp=6,
            allow_write=allow_write,
        )
    )

    # Ein Opti MAX (ID 272) – Fachmann / Heizung, 0..240 Minuten in 15er-Schritten
    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "HK1 Expert Ein Opti MAX",
            parameter_id=272,
            min_value=0.0,
            max_value=240.0,
            step=15.0,
            scale=1.0,
            unit=UnitOfTime.MINUTES,
            bus=1,
            modultyp=6,
            allow_write=allow_write,
        )
    )

    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "HK2 Expert Ein Opti MAX",
            parameter_id=272,
            min_value=0.0,
            max_value=240.0,
            step=15.0,
            scale=1.0,
            unit=UnitOfTime.MINUTES,
            bus=2,
            modultyp=6,
            allow_write=allow_write,
        )
    )

    # HK1/HK2 User heating parameters (Form_Heizung_Benutzer)
    # HK1 (Bus=1)
    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "HK1 User Normal Raumtemperatur",
            parameter_id=5,
            min_value=10.0,
            max_value=35.0,
            step=0.5,
            scale=1.0,
            unit=UnitOfTemperature.CELSIUS,
            allow_write=allow_write,
        )
    )

    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "HK1 User Absenk Raumtemperatur",
            parameter_id=8,
            min_value=10.0,
            max_value=35.0,
            step=0.5,
            scale=1.0,
            unit=UnitOfTemperature.CELSIUS,
            allow_write=allow_write,
        )
    )

    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "HK1 User Normal VL Soll",
            parameter_id=297,
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
            "HK1 User Absenk VL Soll",
            parameter_id=298,
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
            "HK1 User Steilheit",
            parameter_id=270,
            min_value=2.5,
            max_value=40.0,
            step=0.5,
            scale=1.0,
            unit=None,
            allow_write=allow_write,
        )
    )

    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "HK1 User Raumfrosttemperatur",
            parameter_id=2580,
            min_value=4.0,
            max_value=35.0,
            step=0.5,
            scale=1.0,
            unit=UnitOfTemperature.CELSIUS,
            allow_write=allow_write,
        )
    )

    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "HK1 User SoWi Umschaltung",
            parameter_id=278,
            min_value=8.0,
            max_value=30.0,
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
            "HK1 User Sollwert Solar",
            parameter_id=129,
            min_value=0.0,
            max_value=10.0,
            step=0.1,
            scale=1.0,
            unit=UnitOfTemperature.CELSIUS,
            allow_write=allow_write,
        )
    )

    # HK2 (Bus=2)
    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "HK2 User Normal Raumtemperatur",
            parameter_id=5,
            min_value=10.0,
            max_value=35.0,
            step=0.5,
            scale=1.0,
            unit=UnitOfTemperature.CELSIUS,
            allow_write=allow_write,
        )
    )

    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "HK2 User Absenk Raumtemperatur",
            parameter_id=8,
            min_value=10.0,
            max_value=35.0,
            step=0.5,
            scale=1.0,
            unit=UnitOfTemperature.CELSIUS,
            allow_write=allow_write,
        )
    )

    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "HK2 User Normal VL Soll",
            parameter_id=297,
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
            "HK2 User Absenk VL Soll",
            parameter_id=298,
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
            "HK2 User Steilheit",
            parameter_id=270,
            min_value=2.5,
            max_value=40.0,
            step=0.5,
            scale=1.0,
            unit=None,
            allow_write=allow_write,
        )
    )

    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "HK2 User Raumfrosttemperatur",
            parameter_id=2580,
            min_value=4.0,
            max_value=35.0,
            step=0.5,
            scale=1.0,
            unit=UnitOfTemperature.CELSIUS,
            allow_write=allow_write,
        )
    )

    numbers.append(
        WeishauptExpertNumber(
            coordinator,
            api,
            "HK2 User SoWi Umschaltung",
            parameter_id=278,
            min_value=8.0,
            max_value=30.0,
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
            "HK2 User Sollwert Solar",
            parameter_id=129,
            min_value=0.0,
            max_value=10.0,
            step=0.1,
            scale=1.0,
            unit=UnitOfTemperature.CELSIUS,
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
        bus: int = 0,
        modultyp: int = 10,
    ) -> None:
        """Initialize the expert number entity."""

        CoordinatorEntity.__init__(self, coordinator)
        WeishauptBaseEntity.__init__(self, api)

        self._sensor_name = sensor_name
        self._parameter_id = parameter_id
        self._scale = float(scale) if scale else 1.0
        self._allow_write = allow_write
        self._bus = bus
        self._modultyp = modultyp

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
        name = sensor_name

        # Fachmann / Heizung
        if "Frostheizgrenze" in name:
            self._attr_icon = "mdi:snowflake-thermometer"
        elif "Ein Opti MAX" in name:
            self._attr_icon = "mdi:clock-outline"

        # Allgemeine Expert-Parameter
        elif "Corr Outside Sensor" in name:
            self._attr_icon = "mdi:thermometer-minus"
        elif "Spec Level Heating Mode" in name:
            self._attr_icon = "mdi:thermometer"
        elif "Min VL Target" in name or "Max VL Target" in name:
            self._attr_icon = "mdi:thermometer"
        elif "Switch Diff VL" in name:
            self._attr_icon = "mdi:thermometer-lines"
        elif "Power" in name:
            self._attr_icon = "mdi:gauge"
        elif "Pulse Lock" in name or "Charge Time" in name:
            self._attr_icon = "mdi:clock-outline"

        # HK1/HK2 User Heizparameter (Form_Heizung_Benutzer)
        elif "HK1 User Normal Raumtemperatur" in name or "HK2 User Normal Raumtemperatur" in name:
            self._attr_icon = "mdi:home-thermometer"
        elif "HK1 User Absenk Raumtemperatur" in name or "HK2 User Absenk Raumtemperatur" in name:
            self._attr_icon = "mdi:home-thermometer-outline"
        elif "HK1 User Normal VL Soll" in name or "HK2 User Normal VL Soll" in name:
            self._attr_icon = "mdi:thermostat"
        elif "HK1 User Absenk VL Soll" in name or "HK2 User Absenk VL Soll" in name:
            # etwas abgesetzter Thermostat für den Absenk-Bereich
            self._attr_icon = "mdi:thermostat-box-outline"
        elif "HK1 User Steilheit" in name or "HK2 User Steilheit" in name:
            self._attr_icon = "mdi:chart-bell-curve"
        elif "HK1 User Raumfrosttemperatur" in name or "HK2 User Raumfrosttemperatur" in name:
            self._attr_icon = "mdi:snowflake-thermometer"
        elif "HK1 User SoWi Umschaltung" in name or "HK2 User SoWi Umschaltung" in name:
            self._attr_icon = "mdi:weather-sunny-alert"
        elif "HK1 User Sollwert Solar" in name or "HK2 User Sollwert Solar" in name:
            self._attr_icon = "mdi:solar-power"

        # Fallback: generisches Tuning-Icon für sonstige Slider
        else:
            self._attr_icon = "mdi:tune-variant"

    @property
    def device_info(self):
        """Attach numbers to the appropriate device (boiler or HK1/HK2)."""

        name = self._sensor_name or ""
        slug = name.lower().replace(" ", "_")

        if slug.startswith("hk1_"):
            ident = "weishaupt_hk1"
            dev_name = "Weishaupt Heizkreis 1"
        elif slug.startswith("hk2_"):
            ident = "weishaupt_hk2"
            dev_name = "Weishaupt Heizkreis 2"
        else:
            ident = "weishaupt_kessel"
            dev_name = "Weishaupt Kessel"

        return {
            "identifiers": {(DOMAIN, ident)},
            "name": dev_name,
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

        # Für globale Expert-Parameter bleibt bus=0/modultyp=10, für
        # Heizkreis-spezifische Parameter (z.B. Frostheizgrenze/Opti MAX)
        # werden bus/modultyp über den Konstruktor gesetzt.
        await self.hass.async_add_executor_job(
            self.api.write_parameter,
            self._parameter_id,
            self._bus,
            self._modultyp,
            code,
        )

        # Nach dem Schreiben den Coordinator aktualisieren
        await self.coordinator.async_request_refresh()
