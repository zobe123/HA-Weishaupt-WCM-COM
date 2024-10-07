"""Weishaupt WCM-COM integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, CONF_SCAN_INTERVAL
from .weishaupt_api import WeishauptAPI

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Weishaupt WCM-COM from a config entry."""
    host = entry.data.get("host")
    username = entry.data.get("username")
    password = entry.data.get("password")

    api = WeishauptAPI(host, username, password)

    # Initiale Datenabfrage mit await in einem Thread
    await hass.async_add_executor_job(api.update)

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "scan_interval": scan_interval,
    }

    entry.async_on_unload(entry.add_update_listener(update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    # Aktualisieren Sie das Abfrageintervall
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    hass.data[DOMAIN][entry.entry_id]["scan_interval"] = scan_interval
    _LOGGER.info(f"Updated scan interval to {scan_interval} seconds for entry {entry.entry_id}")
