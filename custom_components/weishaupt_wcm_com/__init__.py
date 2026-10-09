"""Weishaupt WCM-COM integration.

Uses a DataUpdateCoordinator to ensure that only a single
request to the WCM-COM device is executed per update interval.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    CONF_ALLOW_WRITE,
    DEFAULT_ALLOW_WRITE,
    CONF_ADVANCED_LOGGING,
    DEFAULT_ADVANCED_LOGGING,
    PARAMETERS,
)
from .weishaupt_api import WeishauptAPI
from .time_program_manager import TimeProgramManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor", "select", "number", "calendar"]

OBSOLETE_ENTITY_UNIQUE_IDS = {
    "sensor": {
        "weishaupt_hk1_user_sollwert_solar",
        "weishaupt_hk2_user_sollwert_solar",
        "weishaupt_hk1_user_betriebsart_hk",
        "weishaupt_hk1_user_betriebsart_ww",
        "weishaupt_hk2_user_betriebsart_hk",
        "weishaupt_hk2_user_betriebsart_ww",
    },
    "number": {
        "weishaupt_hk1_user_sollwert_solar_number",
        "weishaupt_hk2_user_sollwert_solar_number",
    },
    "select": {
        "weishaupt_hk1_user_op_mode_hk_select",
        "weishaupt_hk1_user_op_mode_ww_select",
        "weishaupt_hk2_user_op_mode_hk_select",
        "weishaupt_hk2_user_op_mode_ww_select",
    },
}


def _remove_obsolete_entities(hass: HomeAssistant, data: dict) -> None:
    """Remove invalid and unsupported conditional registry entries."""

    registry = er.async_get(hass)
    unique_ids_by_platform = {
        platform: set(unique_ids)
        for platform, unique_ids in OBSOLETE_ENTITY_UNIQUE_IDS.items()
    }
    for parameter in PARAMETERS:
        if not parameter.get("conditional") or parameter["name"] in data:
            continue
        slug = parameter["name"].lower().replace(" ", "_")
        unique_ids_by_platform["sensor"].add(f"weishaupt_{slug}")
        unique_ids_by_platform["number"].add(f"weishaupt_{slug}_number")
        if parameter["name"].endswith("Expert Raumthermostat"):
            hk = 1 if parameter["name"].startswith("HK1") else 2
            unique_ids_by_platform["select"].add(
                f"weishaupt_hk{hk}_expert_room_thermostat_select"
            )

    for platform, unique_ids in unique_ids_by_platform.items():
        for unique_id in unique_ids:
            entity_id = registry.async_get_entity_id(platform, DOMAIN, unique_id)
            if entity_id is not None:
                registry.async_remove(entity_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Weishaupt WCM-COM from a config entry."""

    # Prefer legacy connection values accidentally stored in options by <=1.2.10,
    # while the corrected options flow persists them in entry.data.
    host: str | None = entry.options.get("host", entry.data.get("host"))
    username: str | None = entry.options.get("username", entry.data.get("username"))
    password: str | None = entry.options.get("password", entry.data.get("password"))

    # Read scan interval, write flag and advanced logging from options (or use defaults)
    scan_interval: int = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    allow_write: bool = entry.options.get(CONF_ALLOW_WRITE, DEFAULT_ALLOW_WRITE)
    advanced_logging: bool = entry.options.get(CONF_ADVANCED_LOGGING, DEFAULT_ADVANCED_LOGGING)

    api = WeishauptAPI(host, username, password, advanced_logging=advanced_logging)

    async def async_update_data() -> dict:
        """Fetch the latest data from the WCM-COM API.

        This function is executed by the DataUpdateCoordinator in an executor
        thread and must not block the event loop.
        """

        try:
            await hass.async_add_executor_job(api.update)
            return api.data
        except Exception as err:  # pragma: no cover  # pylint: disable=broad-except
            raise UpdateFailed(f"Error communicating with WCM-COM: {err}") from err

    coordinator = DataUpdateCoordinator[
        dict
    ](
        hass,
        _LOGGER,
        name="weishaupt_wcm_com",
        update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),
    )

    # First refresh before entities are created
    await coordinator.async_config_entry_first_refresh()
    _remove_obsolete_entities(hass, coordinator.data or {})

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "time_program_manager": TimeProgramManager(hass, api),
        "allow_write": allow_write,
        "advanced_logging": advanced_logging,
    }

    # Register services only once per integration domain
    if not hass.services.has_service(DOMAIN, "set_holiday_date"):
        _register_services(hass)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


def _register_services(hass: HomeAssistant) -> None:
    """Register integration-level services (called once)."""

    async def async_set_holiday_date(call: ServiceCall) -> None:
        """Set HK1/HK2 holiday start/end date via raw Day/Month/Year parameters.

        Fields are mapped as:
        - HKx Holiday Start: IDs 283/284/285 (Day/Month/Year)
        - HKx Holiday End:   IDs 286/287/288 (Day/Month/Year)

        Year is encoded as (calendar year - 2000).
        A null/empty date resets Year to 0 and Day/Month to 1 ("not set").
        """

        heating_circuit = int(call.data.get("heating_circuit", 1))
        target = str(call.data.get("target", "start")).lower()
        date_str = call.data.get("date")

        if heating_circuit not in (1, 2):
            raise HomeAssistantError(
                f"Invalid heating_circuit={heating_circuit}; expected 1 or 2"
            )
        if target not in ("start", "end"):
            raise HomeAssistantError(
                f"Invalid target={target}; expected 'start' or 'end'"
            )

        # Determine parameter IDs for the selected HK/target
        if target == "start":
            base_id = 283
        else:
            base_id = 286

        day_id = base_id
        month_id = base_id + 1
        year_id = base_id + 2

        bus = heating_circuit
        modultyp = 6

        # Resolve the requested config entry. Never guess when multiple devices exist.
        domain_data = hass.data.get(DOMAIN, {})
        if not domain_data:
            raise HomeAssistantError(f"No loaded {DOMAIN} config entry found")

        config_entry_id = call.data.get("config_entry_id")
        if config_entry_id:
            entry_data = domain_data.get(config_entry_id)
            if entry_data is None:
                raise HomeAssistantError(
                    f"Unknown or unloaded config_entry_id: {config_entry_id}"
                )
        elif len(domain_data) == 1:
            entry_data = next(iter(domain_data.values()))
        else:
            raise HomeAssistantError(
                "config_entry_id is required when multiple WCM-COM entries are loaded"
            )

        if not entry_data.get("allow_write", False):
            raise HomeAssistantError(
                "Weishaupt WCM-COM integration is in read-only mode."
            )

        api: WeishauptAPI = entry_data["api"]
        coordinator: DataUpdateCoordinator = entry_data["coordinator"]

        # Parse date / reset logic
        if not date_str:
            # Reset: Year=0, Day=1, Month=1 (WebUI semantics for "not set")
            day = 1
            month = 1
            year_raw = 0
        else:
            from datetime import datetime

            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                raise HomeAssistantError(
                    f"Invalid date '{date_str}'; expected YYYY-MM-DD"
                ) from None

            day = dt.day
            month = dt.month
            year_raw = dt.year - 2000
            if year_raw < 0 or year_raw > 99:
                raise HomeAssistantError(
                    f"Year {dt.year} is outside the supported range 2000-2099"
                )

        _LOGGER.debug(
            "set_holiday_date: HK%s %s -> %s (Day=%s, Month=%s, YearRaw=%s)",
            heating_circuit,
            target,
            date_str or "<not set>",
            day,
            month,
            year_raw,
        )

        # Write all three fields under one API lock so no poll can observe a
        # half-updated date. Year is written last and activates the date.
        writes = [
            (day_id, bus, modultyp, day),
            (month_id, bus, modultyp, month),
            (year_id, bus, modultyp, year_raw),
        ]
        await hass.async_add_executor_job(api.write_parameters, writes)

        # Refresh coordinator so that HKx Holiday Start/End sensors update
        await coordinator.async_request_refresh()

    def resolve_writable_entry(call: ServiceCall) -> dict:
        """Resolve a loaded writable config entry without guessing."""

        domain_data = hass.data.get(DOMAIN, {})
        if not domain_data:
            raise HomeAssistantError(f"No loaded {DOMAIN} config entry found")
        config_entry_id = call.data.get("config_entry_id")
        if config_entry_id:
            entry_data = domain_data.get(config_entry_id)
            if entry_data is None:
                raise HomeAssistantError(
                    f"Unknown or unloaded config_entry_id: {config_entry_id}"
                )
        elif len(domain_data) == 1:
            entry_data = next(iter(domain_data.values()))
        else:
            raise HomeAssistantError(
                "config_entry_id is required when multiple WCM-COM entries are loaded"
            )
        if not entry_data.get("allow_write", False):
            raise HomeAssistantError(
                "Weishaupt WCM-COM integration is in read-only mode."
            )
        return entry_data

    async def async_set_time_program_day(call: ServiceCall) -> None:
        """Replace all three intervals of one time-program day."""

        entry_data = resolve_writable_entry(call)
        intervals = []
        for slot in range(1, 4):
            start = call.data.get(f"start_{slot}")
            end = call.data.get(f"end_{slot}")
            if bool(start) != bool(end):
                raise HomeAssistantError(
                    f"Time window {slot} requires both start and end"
                )
            if start and end:
                intervals.append((start, end))

        try:
            await entry_data["time_program_manager"].async_set_day(
                int(call.data["heating_circuit"]),
                str(call.data["program"]),
                str(call.data["day"]),
                intervals,
            )
        except (ValueError, KeyError) as err:
            raise HomeAssistantError(str(err)) from err

    async def async_copy_time_program_day(call: ServiceCall) -> None:
        """Copy one source day to one or more target days."""

        entry_data = resolve_writable_entry(call)
        target_days = call.data["target_days"]
        if isinstance(target_days, str):
            target_days = [target_days]
        try:
            await entry_data["time_program_manager"].async_copy_day(
                int(call.data["source_heating_circuit"]),
                str(call.data["source_program"]),
                str(call.data["source_day"]),
                int(call.data["target_heating_circuit"]),
                str(call.data["target_program"]),
                list(target_days),
            )
        except (ValueError, KeyError) as err:
            raise HomeAssistantError(str(err)) from err

    async def async_clear_time_program_days(call: ServiceCall) -> None:
        """Disable all intervals on one or more program days."""

        entry_data = resolve_writable_entry(call)
        days = call.data["days"]
        if isinstance(days, str):
            days = [days]
        try:
            for day in days:
                await entry_data["time_program_manager"].async_set_day(
                    int(call.data["heating_circuit"]),
                    str(call.data["program"]),
                    str(day),
                    [],
                )
        except (ValueError, KeyError) as err:
            raise HomeAssistantError(str(err)) from err

    hass.services.async_register(DOMAIN, "set_holiday_date", async_set_holiday_date)
    hass.services.async_register(
        DOMAIN, "set_time_program_day", async_set_time_program_day
    )
    hass.services.async_register(
        DOMAIN, "copy_time_program_day", async_copy_time_program_day
    )
    hass.services.async_register(
        DOMAIN, "clear_time_program_days", async_clear_time_program_days
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and entry.entry_id in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update.

    Called when options (e.g. scan interval) are changed in the UI.
    """

    scan_interval: int = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    allow_write: bool = entry.options.get(CONF_ALLOW_WRITE, DEFAULT_ALLOW_WRITE)
    advanced_logging: bool = entry.options.get(CONF_ADVANCED_LOGGING, DEFAULT_ADVANCED_LOGGING)

    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not entry_data:
        return

    coordinator: DataUpdateCoordinator | None = entry_data.get("coordinator")
    if coordinator is None:
        return

    # Reload the entry so that entities pick up changed options (e.g. allow_write)
    await hass.config_entries.async_reload(entry.entry_id)

    _LOGGER.info(
        "Reloaded config entry %s after options update (scan_interval=%s, allow_write=%s, advanced_logging=%s)",
        entry.entry_id,
        scan_interval,
        allow_write,
        advanced_logging,
    )
