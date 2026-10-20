"""Shared firmware coordinator and installed-version sensor."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .device_model import device_info
from .weishaupt_api import WeishauptAPI

_LOGGER = logging.getLogger(__name__)
FIRMWARE_SCAN_INTERVAL = timedelta(hours=24)


def create_firmware_coordinator(
    hass: HomeAssistant,
    api: WeishauptAPI,
    *,
    allow_online_check: bool,
) -> DataUpdateCoordinator[dict[str, str | bool]]:
    """Create the coordinator shared by firmware sensor and update entity."""

    async def async_update_firmware() -> dict[str, str | bool]:
        try:
            if allow_online_check:
                return await hass.async_add_executor_job(api.check_firmware_update)
            installed_version = await hass.async_add_executor_job(
                api.get_firmware_version
            )
            return {
                "installed_version": installed_version,
                "latest_version": "",
                "update_available": False,
            }
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("WCM-COM firmware check failed: %s", err)
            return {
                "installed_version": "",
                "latest_version": "",
                "update_available": False,
                "check_error": str(err),
            }

    return DataUpdateCoordinator[dict[str, str | bool]](
        hass,
        _LOGGER,
        name="weishaupt_wcm_com_firmware",
        update_method=async_update_firmware,
        update_interval=FIRMWARE_SCAN_INTERVAL,
    )


class WeishauptInstalledFirmwareSensor(CoordinatorEntity, SensorEntity):
    """Show the locally installed WCM-COM firmware version."""

    _attr_unique_id = "weishaupt_wcm_com_installed_firmware"
    _attr_translation_key = "wcm_com_installed_firmware"
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:chip"

    @property
    def native_value(self) -> str | None:
        """Return the locally installed firmware version."""

        value = (self.coordinator.data or {}).get("installed_version")
        return str(value) if value else None

    @property
    def available(self) -> bool:
        """Return whether the installed version was read successfully."""

        return self.native_value is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Attach the sensor to the boiler/WCM-COM device."""

        return DeviceInfo(
            **device_info("WCM-COM Firmware", sw_version=self.native_value)
        )
