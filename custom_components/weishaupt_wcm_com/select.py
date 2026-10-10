"""Select platform for Weishaupt WCM-COM HK1 configuration.

This exposes read/write dropdowns for:
- HK1 Config HK Type (id 16)
- HK1 Config Regelvariante (id 2419)
- HK1 Config Ext Room Sensor (id 321)

Initially only HK1 is supported; HK2 can be added later using the same pattern.
"""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    PARAMETERS,
    HK_CONFIG_HK_TYPE_MAP,
    HK_CONFIG_REGELVARIANTE_MAP,
    HK_CONFIG_EXT_ROOM_SENSOR_MAP,
    HK_USER_OPERATION_MODE_MAP,
    WW_USER_OPERATION_MODE_MAP,
    HOLIDAY_TEMP_LEVEL_MAP,
    HK_REDUCED_MODE_MAP,
    HK_ROOM_THERMOSTAT_MAP,
)
from .base_entity import WeishauptBaseEntity
from .protocol import resolve_parameter_metadata
from .localization import SELECT_TRANSLATION_KEYS, select_option_map

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities for HK1 configuration."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DataUpdateCoordinator = entry_data["coordinator"]
    api = entry_data["api"]
    allow_write: bool = entry_data.get("allow_write", False)

    selects: list[WeishauptHK1ConfigSelect] = []

    # HK1 uses bus=1 in PARAMETERS; we use the sensor names as keys
    # HK1
    selects.append(
        WeishauptHKConfigSelect(
            coordinator,
            api,
            "HK1 Config HK Type",
            "hk1_config_hk_type",
            HK_CONFIG_HK_TYPE_MAP,
            parameter_id=16,
            bus=1,
            modultyp=6,
            allow_write=allow_write,
        )
    )

    selects.append(
        WeishauptHKConfigSelect(
            coordinator,
            api,
            "HK1 Config Regelvariante",
            "hk1_config_regelvariante",
            HK_CONFIG_REGELVARIANTE_MAP,
            parameter_id=2419,
            bus=1,
            modultyp=6,
            allow_write=allow_write,
        )
    )

    selects.append(
        WeishauptHKConfigSelect(
            coordinator,
            api,
            "HK1 Config Ext Room Sensor",
            "hk1_config_ext_room_sensor",
            HK_CONFIG_EXT_ROOM_SENSOR_MAP,
            parameter_id=321,
            bus=1,
            modultyp=6,
            allow_write=allow_write,
        )
    )

    # HK2
    selects.append(
        WeishauptHKConfigSelect(
            coordinator,
            api,
            "HK2 Config HK Type",
            "hk2_config_hk_type",
            HK_CONFIG_HK_TYPE_MAP,
            parameter_id=16,
            bus=2,
            modultyp=6,
            allow_write=allow_write,
        )
    )

    selects.append(
        WeishauptHKConfigSelect(
            coordinator,
            api,
            "HK2 Config Regelvariante",
            "hk2_config_regelvariante",
            HK_CONFIG_REGELVARIANTE_MAP,
            parameter_id=2419,
            bus=2,
            modultyp=6,
            allow_write=allow_write,
        )
    )

    selects.append(
        WeishauptHKConfigSelect(
            coordinator,
            api,
            "HK2 Config Ext Room Sensor",
            "hk2_config_ext_room_sensor",
            HK_CONFIG_EXT_ROOM_SENSOR_MAP,
            parameter_id=321,
            bus=2,
            modultyp=6,
            allow_write=allow_write,
        )
    )

    # Parameter 274 has exactly one meaning per bus. The capability flags
    # decide whether the WebUI exposes it as heating or hot-water mode.
    for hk in (1, 2):
        mode_kind = (coordinator.data or {}).get(f"HK{hk} User Mode Kind")
        if mode_kind in ("hk", "ww"):
            selects.append(
                WeishauptHKConfigSelect(
                    coordinator, api, f"HK{hk} User Betriebsart",
                    f"hk{hk}_user_op_mode",
                    HK_USER_OPERATION_MODE_MAP if mode_kind == "hk" else WW_USER_OPERATION_MODE_MAP,
                    parameter_id=274, bus=hk, modultyp=6,
                    allow_write=allow_write,
                    hot_water_mode=mode_kind == "ww",
                )
            )

        for name, slug, mapping, parameter_id in (
            (f"HK{hk} Expert Reduziertbetrieb", f"hk{hk}_expert_reduced_mode", HK_REDUCED_MODE_MAP, 306),
            (f"HK{hk} Expert Raumthermostat", f"hk{hk}_expert_room_thermostat", HK_ROOM_THERMOSTAT_MAP, 2588),
        ):
            if name in (coordinator.data or {}):
                selects.append(
                    WeishauptHKConfigSelect(
                        coordinator, api, name, slug, mapping,
                        parameter_id=parameter_id, bus=hk, modultyp=6,
                        allow_write=allow_write,
                    )
                )

    # HK1 holiday temperature level (P142 / ID 317)
    selects.append(
        WeishauptHKConfigSelect(
            coordinator,
            api,
            "HK1 Urlaubstemperaturniveau",
            "hk1_urlaubstemperaturniveau",
            HOLIDAY_TEMP_LEVEL_MAP,
            parameter_id=317,
            bus=1,
            modultyp=6,
            allow_write=allow_write,
        )
    )

    # HK2 holiday temperature level (P142 / ID 317, bus=2)
    selects.append(
        WeishauptHKConfigSelect(
            coordinator,
            api,
            "HK2 Urlaubstemperaturniveau",
            "hk2_urlaubstemperaturniveau",
            HOLIDAY_TEMP_LEVEL_MAP,
            parameter_id=317,
            bus=2,
            modultyp=6,
            allow_write=allow_write,
        )
    )

    async_add_entities(selects)


class WeishauptHKConfigSelect(CoordinatorEntity, WeishauptBaseEntity, SelectEntity):
    """Select entity for HK1/HK2 configuration parameters."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api,
        sensor_name: str,
        slug: str,
        value_map: dict[int, str],
        parameter_id: int,
        bus: int,
        modultyp: int,
        allow_write: bool = False,
        hot_water_mode: bool = False,
    ) -> None:
        """Initialize the select entity."""

        CoordinatorEntity.__init__(self, coordinator)
        WeishauptBaseEntity.__init__(self, api)

        self._sensor_name = sensor_name
        self._attr_unique_id = f"weishaupt_{slug}_select"
        self._value_map = value_map
        self._parameter_id = parameter_id
        self._bus = bus
        self._modultyp = modultyp
        self._allow_write = allow_write
        self._attr_has_entity_name = True
        self._attr_translation_key = SELECT_TRANSLATION_KEYS[slug]
        self._option_map = select_option_map(
            self._attr_translation_key,
            hot_water=hot_water_mode,
        )

        parameter = resolve_parameter_metadata(
            PARAMETERS,
            name=sensor_name,
            parameter_id=parameter_id,
            bus=bus,
            module_type=modultyp,
        )
        self._data_name = str(parameter["name"])

        # Schönerer Anzeigename ohne "Config"-Präfix + passende Icons
        if sensor_name == "HK1 Config HK Type":
            self._attr_icon = "mdi:radiator"
        elif sensor_name == "HK1 Config Regelvariante":
            self._attr_icon = "mdi:chart-bell-curve"
        elif sensor_name == "HK1 Config Ext Room Sensor":
            self._attr_icon = "mdi:home-thermometer-outline"
        elif sensor_name == "HK2 Config HK Type":
            self._attr_icon = "mdi:radiator"
        elif sensor_name == "HK2 Config Regelvariante":
            self._attr_icon = "mdi:chart-bell-curve"
        elif sensor_name == "HK2 Config Ext Room Sensor":
            self._attr_icon = "mdi:home-thermometer-outline"
        elif sensor_name.endswith("User Betriebsart"):
            self._attr_icon = (
                "mdi:water-thermometer"
                if hot_water_mode
                else "mdi:home-thermometer"
            )
        elif sensor_name == "HK1 Urlaubstemperaturniveau":
            self._attr_icon = "mdi:snowflake"
        elif sensor_name == "HK2 Urlaubstemperaturniveau":
            self._attr_icon = "mdi:snowflake"

        self._attr_options = list(dict.fromkeys(self._option_map.values()))

    @property
    def device_info(self):
        """Attach to the HK1/HK2 device group."""

        slug = self._sensor_name.lower().replace(" ", "_")

        if slug.startswith("hk1_"):
            ident = "weishaupt_hk1"
            name = "Weishaupt WCM-COM · HK1"
        elif slug.startswith("hk2_"):
            ident = "weishaupt_hk2"
            name = "Weishaupt WCM-COM · HK2"
        else:
            ident = "weishaupt_kessel"
            name = "Weishaupt WCM-COM · WTC"

        return {
            "identifiers": {(DOMAIN, ident)},
            "name": name,
            "manufacturer": "Weishaupt",
            "model": "WCM-COM",
        }

    @staticmethod
    def _extract_option_label(text: str) -> str:
        """Strip the left label part (before ":") from a mapped string."""
        if not isinstance(text, str):
            return str(text)
        if ":" in text:
            return text.split(":", 1)[1].strip()
        return text

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option based on coordinator data."""

        data = self.coordinator.data or {}
        value = data.get(self._data_name)
        if value is None:
            return None

        if isinstance(value, str):
            for code, legacy_label in self._value_map.items():
                if value in (legacy_label, self._extract_option_label(legacy_label)):
                    return self._option_map.get(code)
            return value if value in self._attr_options else None

        # Fallback: roher Code → Mapping benutzen
        if isinstance(value, int):
            return self._option_map.get(value)

        return None

    async def async_select_option(self, option: str) -> None:
        """Handle user selection by sending a write telegram to WCM-COM."""

        if not self._allow_write:
            from homeassistant.exceptions import HomeAssistantError
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="read_only",
            )

        # Finde den passenden Roh-Code für das gewählte Label
        code = next(
            (raw for raw, key in self._option_map.items() if key == option),
            None,
        )
        # Keep direct calls using the pre-1.3 option labels working.
        if code is None:
            code = next(
                (
                    raw
                    for raw, text in self._value_map.items()
                    if option in (text, self._extract_option_label(text))
                ),
                None,
            )

        if code is None:
            _LOGGER.warning("Unknown option '%s' for %s", option, self._sensor_name)
            return

        _LOGGER.debug(
            "Setting %s (id=%s, bus=%s, modultyp=%s) to code %s",
            self._sensor_name,
            self._parameter_id,
            self._bus,
            self._modultyp,
            code,
        )

        # Schreiben über die API (synchron, im Executor)
        await self.hass.async_add_executor_job(
            self.api.write_parameter,
            self._parameter_id,
            self._bus,
            self._modultyp,
            code,
        )

        # Nach dem Schreiben direkt ein Update anstoßen
        await self.coordinator.async_request_refresh()
