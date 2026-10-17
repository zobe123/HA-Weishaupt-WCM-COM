"""Firmware update platform for Weishaupt WCM-COM."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN
from .device_model import device_info
from .weishaupt_api import WeishauptAPI

_LOGGER = logging.getLogger(__name__)
FIRMWARE_SCAN_INTERVAL = timedelta(hours=24)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the read-only WCM-COM firmware update entity."""

    api: WeishauptAPI = hass.data[DOMAIN][entry.entry_id]["api"]

    async def async_update_firmware() -> dict[str, str | bool]:
        try:
            return await hass.async_add_executor_job(api.check_firmware_update)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("WCM-COM firmware check failed: %s", err)
            return {
                "installed_version": "",
                "latest_version": "",
                "update_available": False,
                "check_error": str(err),
            }

    coordinator = DataUpdateCoordinator[dict[str, str | bool]](
        hass,
        _LOGGER,
        name="weishaupt_wcm_com_firmware",
        update_method=async_update_firmware,
        update_interval=FIRMWARE_SCAN_INTERVAL,
    )
    async_add_entities([WeishauptFirmwareUpdateEntity(coordinator)])
    entry.async_create_background_task(
        hass,
        coordinator.async_config_entry_first_refresh(),
        "weishaupt_wcm_com_firmware_check",
    )


class WeishauptFirmwareUpdateEntity(CoordinatorEntity, UpdateEntity):
    """Show installed and available WCM-COM firmware versions."""

    _attr_unique_id = "weishaupt_wcm_com_firmware"
    _attr_translation_key = "wcm_com_firmware"
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:update"
    _attr_supported_features = UpdateEntityFeature(0)

    @property
    def available(self) -> bool:
        """Keep a vendor-server failure isolated to this one entity."""

        return bool(self.installed_version and self.latest_version)

    @property
    def installed_version(self) -> str | None:
        """Return the installed firmware version."""

        value = (self.coordinator.data or {}).get("installed_version")
        return str(value) if value else None

    @property
    def latest_version(self) -> str | None:
        """Return the latest firmware version reported by Weishaupt."""

        value = (self.coordinator.data or {}).get("latest_version")
        return str(value) if value else None

    @property
    def device_info(self) -> DeviceInfo:
        """Attach the firmware entity to the boiler/WCM-COM device."""

        return DeviceInfo(
            **device_info("WCM-COM Firmware", sw_version=self.installed_version)
        )
