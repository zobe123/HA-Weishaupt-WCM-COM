"""Weishaupt WCM-COM integration.

Uses a DataUpdateCoordinator to ensure that only a single
request to the WCM-COM device is executed per update interval.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, CONF_ALLOW_WRITE, DEFAULT_ALLOW_WRITE
from .weishaupt_api import WeishauptAPI

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor", "select", "number"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Weishaupt WCM-COM from a config entry."""

    host: str | None = entry.data.get("host")
    username: str | None = entry.data.get("username")
    password: str | None = entry.data.get("password")

    api = WeishauptAPI(host, username, password)

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

    # Read scan interval and write flag from options (or use defaults)
    scan_interval: int = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    allow_write: bool = entry.options.get(CONF_ALLOW_WRITE, DEFAULT_ALLOW_WRITE)

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
    }

    entry.async_on_unload(entry.add_update_listener(update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


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

    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not entry_data:
        return

    coordinator: DataUpdateCoordinator | None = entry_data.get("coordinator")
    if coordinator is None:
        return

    coordinator.update_interval = timedelta(seconds=scan_interval)
    entry_data["allow_write"] = allow_write

    _LOGGER.info(
        "Updated options for entry %s: scan_interval=%s, allow_write=%s",
        entry.entry_id,
        scan_interval,
        allow_write,
    )
