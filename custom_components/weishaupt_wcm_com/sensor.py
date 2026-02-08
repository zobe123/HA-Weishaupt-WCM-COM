"""Sensor platform for the Weishaupt WCM-COM integration.

All sensors are backed by a shared DataUpdateCoordinator which performs
exactly one request to the WCM-COM device per update interval.
"""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.const import UnitOfTemperature, UnitOfTime, PERCENTAGE
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
    HK_CONFIG_PUMP_MAP,
    HK_CONFIG_VOLTAGE_MAP,
    HK_CONFIG_HK_TYPE_MAP,
    HK_CONFIG_REGELVARIANTE_MAP,
    HK_CONFIG_EXT_ROOM_SENSOR_MAP,
    EXPERT_BOILER_ADDRESS_MAP,
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
        # Interne Rohwerte (z. B. High/Low-Bytes für Versionsnummern)
        # sollen keine eigenen Sensoren bekommen.
        if param.get("internal"):
            continue

        sensor_name = param["name"]
        p_type = param["type"]
        unit = None
        if p_type == "temperature":
            unit = UnitOfTemperature.CELSIUS
        elif p_type == "temp_delta":
            unit = "K"
        elif p_type == "days":
            unit = UnitOfTime.DAYS
        elif p_type == "percent":
            unit = PERCENTAGE
        elif p_type == "hours_1000":
            unit = UnitOfTime.HOURS
        elif p_type == "minutes":
            unit = UnitOfTime.MINUTES

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
        # Sichtbarer Name der Entität in HA (z.B. "Außentemperatur",
        # "Heizkreis 1 Solltemperatur"). Wir setzen ihn explizit, damit
        # nicht der Gerätename (z.B. "Weishaupt Kessel") angezeigt wird.
        self._attr_name = self._sensor_name
        self._attr_native_unit_of_measurement = unit

        # Nutze ein konsistentes Unique-ID-Schema, das deinem Wunschpattern
        # entspricht: weishaupt_<slug>
        # Beispiel: weishaupt_hk1_gemischte_außentemperatur
        self._attr_unique_id = f"weishaupt_{slug}"

        # Expert-/Fachmann-Werte als Diagnose-Entities kennzeichnen,
        # damit sie im Gerät in einem eigenen Abschnitt erscheinen.
        if slug.startswith("expert_"):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

        # Firmware-/Versionsanzeigen als Diagnose-Entities behandeln
        if self._sensor_name in (
            "Kessel Config Version FS",
            "HK1 Config Version FS",
            "HK2 Config Version FS",
            "HK1 Config Version EM",
            "HK2 Config Version EM",
        ):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_icon = "mdi:chip"

        # HK-Konfigurations-Sensoren: eigene Icons
        if self._sensor_name in ("HK1 Config Pump", "HK2 Config Pump"):
            self._attr_icon = "mdi:pump"
        elif self._sensor_name in ("HK1 Config Voltage", "HK2 Config Voltage"):
            self._attr_icon = "mdi:flash-triangle-outline"
        elif self._sensor_name in ("HK1 Config HK Type", "HK2 Config HK Type"):
            self._attr_icon = "mdi:radiator"
        elif self._sensor_name in ("HK1 Config Regelvariante", "HK2 Config Regelvariante"):
            self._attr_icon = "mdi:chart-bell-curve"
        elif self._sensor_name in ("HK1 Config Ext Room Sensor", "HK2 Config Ext Room Sensor"):
            self._attr_icon = "mdi:home-thermometer-outline"

        # Kessel-/HK-Prozesswerte: Icons, wo es eindeutig ist
        if self._sensor_name == "Status":
            self._attr_icon = "mdi:alert-circle-outline"
        elif self._sensor_name == "Außentemperatur":
            self._attr_icon = "mdi:thermometer"
        elif self._sensor_name == "Warmwassertemperatur":
            self._attr_icon = "mdi:thermometer-water"
        elif self._sensor_name == "Flamme":
            self._attr_icon = "mdi:fire"
        elif self._sensor_name == "Heizung":
            self._attr_icon = "mdi:radiator"
        elif self._sensor_name == "Warmwasser":
            self._attr_icon = "mdi:water-thermometer"
        elif self._sensor_name == "Kesseltemperatur":
            self._attr_icon = "mdi:thermometer"
        elif self._sensor_name == "Betriebsphase":
            self._attr_icon = "mdi:cog-play"
        elif self._sensor_name == "Puffer Oben":
            self._attr_icon = "mdi:thermometer-lines"
        elif self._sensor_name == "Laststellung":
            self._attr_icon = "mdi:chart-line"
        elif self._sensor_name == "Gedämpfte Außentemperatur":
            self._attr_icon = "mdi:thermometer"
        elif self._sensor_name == "Schaltspielzahl Brenner":
            self._attr_icon = "mdi:counter"
        elif self._sensor_name == "Betriebsstunden Brenner":
            self._attr_icon = "mdi:clock-time-eight-outline"
        elif self._sensor_name == "Zeit seit letzter Wartung":
            self._attr_icon = "mdi:calendar-clock"

        elif self._sensor_name in ("HK1 Gemischte Außentemperatur", "HK2 Gemischte Außentemperatur"):
            self._attr_icon = "mdi:thermometer"
        elif self._sensor_name in ("HK1 Raumtemperatur", "HK2 Raumtemperatur"):
            self._attr_icon = "mdi:home-thermometer"
        elif self._sensor_name in ("HK1 Vorlauftemperatur", "HK2 Vorlauftemperatur"):
            self._attr_icon = "mdi:thermometer"
        elif self._sensor_name in ("HK1 Warmwassertemperatur", "HK2 Warmwassertemperatur"):
            self._attr_icon = "mdi:thermometer-water"
        elif self._sensor_name in ("HK1 Zirkulationstemperatur", "HK2 Zirkulationstemperatur"):
            self._attr_icon = "mdi:pipe"
        elif self._sensor_name in ("HK1 Solltemperatur", "HK2 Solltemperatur", "HK1 Solltemperatur System", "HK2 Solltemperatur System"):
            self._attr_icon = "mdi:thermostat"

        # Entity-ID wird von Home Assistant aus name/unique_id generiert.
        # Wir erzwingen sie NICHT manuell, um Probleme mit Umlauten
        # und zukünftigen Slug-Regeln zu vermeiden.

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for grouping sensors (Kessel, HK1, HK2)."""

        slug = self._sensor_name.lower().replace(" ", "_")

        data = self.coordinator.data or {}
        sw_version: str | None = None

        # FS/EM-Versionen auf die jeweiligen Geräte mappen:
        # - Kessel: EM-Version (falls vorhanden)
        # - HK1/HK2: FS-Version des jeweiligen Heizkreises
        if slug.startswith("hk1_"):
            ident = "weishaupt_hk1"
            name = "Weishaupt Heizkreis 1"
            fs = data.get("HK1 Config Version FS")
            em = data.get("HK1 Config Version EM")
            if fs and em:
                sw_version = f"FS {fs}, EM {em}"
            elif fs:
                sw_version = f"FS {fs}"
            elif em:
                sw_version = f"EM {em}"
        elif slug.startswith("hk2_"):
            ident = "weishaupt_hk2"
            name = "Weishaupt Heizkreis 2"
            fs = data.get("HK2 Config Version FS")
            em = data.get("HK2 Config Version EM")
            if fs and em:
                sw_version = f"FS {fs}, EM {em}"
            elif fs:
                sw_version = f"FS {fs}"
            elif em:
                sw_version = f"EM {em}"
        else:
            # Kessel + Fachmann-Werte im selben Gerät "Weishaupt Kessel" bündeln
            ident = "weishaupt_kessel"
            name = "Weishaupt Kessel"
            fs = data.get("Kessel Config Version FS")
            em = None  # Bus 0 EM ist bei dir N/V
            if fs and em:
                sw_version = f"FS {fs}, EM {em}"
            elif fs:
                sw_version = f"FS {fs}"  # z.B. "FS 327.30"

        info_kwargs = {
            "identifiers": {(DOMAIN, ident)},
            "name": name,
            "manufacturer": "Weishaupt",
            "model": "WCM-COM",
        }

        # Firmware-Version nur setzen, wenn wir einen String haben
        if isinstance(sw_version, str) and sw_version:
            info_kwargs["sw_version"] = sw_version

        return DeviceInfo(**info_kwargs)

    @property
    def native_value(self):
        """Return the state of the sensor based on the latest data."""

        data = self.coordinator.data or {}

        try:
            value = data.get(self._sensor_name)
            if value is None:
                _LOGGER.debug("Data for %s not found – sensor set to unavailable", self._sensor_name)
                self._attr_available = False
                return None

            # Wir haben einen Wert gefunden -> Sensor ist verfügbar
            self._attr_available = True

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

            # HK-Konfigurations-Sensoren: Codes auf lesbare Texte abbilden
            if self._sensor_name in ("HK1 Config Pump", "HK2 Config Pump"):
                return HK_CONFIG_PUMP_MAP.get(value, f"Pumpe (Code {value})")

            if self._sensor_name in ("HK1 Config Voltage", "HK2 Config Voltage"):
                return HK_CONFIG_VOLTAGE_MAP.get(value, f"Spannung (Code {value})")

            if self._sensor_name in ("HK1 Config HK Type", "HK2 Config HK Type"):
                return HK_CONFIG_HK_TYPE_MAP.get(value, f"HK-Typ (Code {value})")

            if self._sensor_name in ("HK1 Config Regelvariante", "HK2 Config Regelvariante"):
                return HK_CONFIG_REGELVARIANTE_MAP.get(value, f"Regelvariante (Code {value})")

            if self._sensor_name in ("HK1 Config Ext Room Sensor", "HK2 Config Ext Room Sensor"):
                return HK_CONFIG_EXT_ROOM_SENSOR_MAP.get(value, f"Externer Raumfühler (Code {value})")

            # Fachmann-Adresse (P12 / ID 376) als 1/A/B/C/D/E darstellen
            if self._sensor_name == "Expert Boiler Address":
                return EXPERT_BOILER_ADDRESS_MAP.get(value, f"Adresse (Code {value})")

            # Fachmann-Prozentwerte übernehmen wir 1:1 (0-100 %)
            if self._sensor_name in (
                "Expert Max Power Heating",
                "Expert Max Power WW",
            ):
                return value

            param_type = next(
                (p["type"] for p in PARAMETERS if p["name"] == self._sensor_name),
                None,
            )

            if param_type == "binary":
                return "Ein" if value else "Aus"

            if param_type in ("value", "temperature", "days", "percent", "minutes") or param_type is None:
                return value

            if param_type in ("value_1000", "hours_1000"):
                return value * 1000

            # Fallback: return the raw value
            return value

        except Exception as err:  # pragma: no cover  # pylint: disable=broad-except
            _LOGGER.error(
                "Error updating sensor %s from coordinator data: %s",
                self._sensor_name,
                err,
            )
            return None
