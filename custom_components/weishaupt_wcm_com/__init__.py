"""Weishaupt WCM-COM integration.

Uses a DataUpdateCoordinator to ensure that only a single
request to the WCM-COM device is executed per update interval.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    CONF_ALLOW_WRITE,
    DEFAULT_ALLOW_WRITE,
    CONF_ADVANCED_LOGGING,
    DEFAULT_ADVANCED_LOGGING,
)
from .weishaupt_api import WeishauptAPI

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor", "select", "number"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Weishaupt WCM-COM from a config entry."""

    host: str | None = entry.data.get("host")
    username: str | None = entry.data.get("username")
    password: str | None = entry.data.get("password")

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

    # Read scan interval, write flag and advanced logging from options (or use defaults)
    scan_interval: int = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    allow_write: bool = entry.options.get(CONF_ALLOW_WRITE, DEFAULT_ALLOW_WRITE)
    advanced_logging: bool = entry.options.get(CONF_ADVANCED_LOGGING, DEFAULT_ADVANCED_LOGGING)

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

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
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
            _LOGGER.error("set_holiday_date: invalid heating_circuit=%s", heating_circuit)
            return
        if target not in ("start", "end"):
            _LOGGER.error("set_holiday_date: invalid target=%s", target)
            return

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

        # Lookup a coordinating API instance (any entry for this domain)
        domain_data = hass.data.get(DOMAIN, {})
        if not domain_data:
            _LOGGER.error("set_holiday_date: no %s data found in hass.data", DOMAIN)
            return

        # Use the first config entry's API/coordinator
        entry_data = next(iter(domain_data.values()))
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
                _LOGGER.error("set_holiday_date: invalid date '%s' (expected YYYY-MM-DD)", date_str)
                return

            day = dt.day
            month = dt.month
            year_raw = dt.year - 2000
            if year_raw < 0 or year_raw > 99:
                _LOGGER.error("set_holiday_date: year %s out of encodable range (2000-2099)", dt.year)
                return

        _LOGGER.debug(
            "set_holiday_date: HK%s %s -> %s (Day=%s, Month=%s, YearRaw=%s)",
            heating_circuit,
            target,
            date_str or "<not set>",
            day,
            month,
            year_raw,
        )

        # Perform writes in executor (three parameters: day, month, year)
        await hass.async_add_executor_job(api.write_parameter, day_id, bus, modultyp, day)
        await hass.async_add_executor_job(api.write_parameter, month_id, bus, modultyp, month)
        await hass.async_add_executor_job(api.write_parameter, year_id, bus, modultyp, year_raw)

        # Refresh coordinator so that HKx Holiday Start/End sensors update
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, "set_holiday_date", async_set_holiday_date)


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
