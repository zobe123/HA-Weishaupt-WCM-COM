"""Regression tests for WCM-COM firmware entities."""

import asyncio
from datetime import timedelta
from enum import IntFlag
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock


ROOT = Path(__file__).parents[1] / "custom_components" / "weishaupt_wcm_com"
PACKAGE = "weishaupt_update_testpkg"


def load_module(name: str, path: Path):
    spec = spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = package

homeassistant = types.ModuleType("homeassistant")
components = types.ModuleType("homeassistant.components")
sensor_component = types.ModuleType("homeassistant.components.sensor")
update_component = types.ModuleType("homeassistant.components.update")
config_entries_module = types.ModuleType("homeassistant.config_entries")
const_module = types.ModuleType("homeassistant.const")
core_module = types.ModuleType("homeassistant.core")
helpers = types.ModuleType("homeassistant.helpers")
device_registry_module = types.ModuleType("homeassistant.helpers.device_registry")
entity_platform_module = types.ModuleType("homeassistant.helpers.entity_platform")
coordinator_module = types.ModuleType("homeassistant.helpers.update_coordinator")


class SensorEntity:
    """Minimal Home Assistant sensor stub."""


class UpdateEntity:
    """Minimal Home Assistant update stub."""


class UpdateEntityFeature(IntFlag):
    """Minimal Home Assistant update feature flags."""

    INSTALL = 1


class EntityCategory:
    DIAGNOSTIC = "diagnostic"


class DeviceInfo(dict):
    """Minimal DeviceInfo stub."""


class CoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator


class DataUpdateCoordinator:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, hass, logger, *, name, update_method, update_interval):
        self.hass = hass
        self.name = name
        self.update_method = update_method
        self.update_interval = update_interval
        self.data = None

    async def async_config_entry_first_refresh(self):
        self.data = await self.update_method()


sensor_component.SensorEntity = SensorEntity
update_component.UpdateEntity = UpdateEntity
update_component.UpdateEntityFeature = UpdateEntityFeature
config_entries_module.ConfigEntry = object
const_module.EntityCategory = EntityCategory
core_module.HomeAssistant = object
device_registry_module.DeviceInfo = DeviceInfo
entity_platform_module.AddEntitiesCallback = object
coordinator_module.CoordinatorEntity = CoordinatorEntity
coordinator_module.DataUpdateCoordinator = DataUpdateCoordinator

for module in (
    homeassistant,
    components,
    sensor_component,
    update_component,
    config_entries_module,
    const_module,
    core_module,
    helpers,
    device_registry_module,
    entity_platform_module,
    coordinator_module,
):
    sys.modules[module.__name__] = module

const = types.ModuleType(f"{PACKAGE}.const")
const.DOMAIN = "weishaupt_wcm_com"
sys.modules[const.__name__] = const
load_module(f"{PACKAGE}.device_model", ROOT / "device_model.py")
api_module = types.ModuleType(f"{PACKAGE}.weishaupt_api")
api_module.WeishauptAPI = object
sys.modules[api_module.__name__] = api_module
firmware_module = load_module(f"{PACKAGE}.firmware", ROOT / "firmware.py")
update_module = load_module(f"{PACKAGE}.update", ROOT / "update.py")


def create_test_coordinator(api: Mock, *, allow_online_check: bool):
    """Create a firmware coordinator with a synchronous executor stub."""

    hass = Mock()

    async def run_executor(function, *args):
        return function(*args)

    hass.async_add_executor_job = run_executor
    coordinator = firmware_module.create_firmware_coordinator(
        hass,
        api,
        allow_online_check=allow_online_check,
    )
    hass.data = {
        "weishaupt_wcm_com": {
            "entry-1": {"firmware_coordinator": coordinator}
        }
    }
    return hass, coordinator


class FirmwarePlatformTest(unittest.TestCase):
    """Verify the shared firmware coordinator and both entity types."""

    def test_read_only_refresh_exposes_installed_version_sensor(self) -> None:
        api = Mock()
        api.get_firmware_version.return_value = "376-09 C"
        hass, coordinator = create_test_coordinator(
            api, allow_online_check=False
        )

        asyncio.run(coordinator.async_config_entry_first_refresh())

        api.get_firmware_version.assert_called_once_with()
        api.check_firmware_update.assert_not_called()
        sensor = firmware_module.WeishauptInstalledFirmwareSensor(coordinator)
        self.assertEqual(sensor.native_value, "376-09 C")
        self.assertTrue(sensor.available)
        self.assertEqual(
            sensor._attr_unique_id, "weishaupt_wcm_com_installed_firmware"
        )
        self.assertEqual(
            sensor.device_info["identifiers"],
            {("weishaupt_wcm_com", "weishaupt_kessel")},
        )

        added = []
        asyncio.run(
            update_module.async_setup_entry(
                hass,
                Mock(entry_id="entry-1"),
                lambda entities: added.extend(entities),
            )
        )
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0].installed_version, "376-09 C")
        self.assertIsNone(added[0].latest_version)

    def test_opted_in_refresh_populates_update_entity(self) -> None:
        api = Mock()
        api.check_firmware_update.return_value = {
            "installed_version": "376-09 C",
            "latest_version": "376-09 C",
            "update_available": False,
        }
        hass, coordinator = create_test_coordinator(
            api, allow_online_check=True
        )

        asyncio.run(coordinator.async_config_entry_first_refresh())

        api.check_firmware_update.assert_called_once_with()
        added = []
        asyncio.run(
            update_module.async_setup_entry(
                hass,
                Mock(entry_id="entry-1"),
                lambda entities: added.extend(entities),
            )
        )
        entity = added[0]
        self.assertEqual(entity.installed_version, "376-09 C")
        self.assertEqual(entity.latest_version, "376-09 C")
        self.assertEqual(entity._attr_supported_features, UpdateEntityFeature(0))
        self.assertEqual(coordinator.update_interval, timedelta(hours=24))
        self.assertTrue(entity.available)

    def test_vendor_failure_isolated_to_firmware_entities(self) -> None:
        api = Mock()
        api.check_firmware_update.side_effect = RuntimeError("vendor unavailable")
        _, coordinator = create_test_coordinator(api, allow_online_check=True)

        asyncio.run(coordinator.async_config_entry_first_refresh())

        sensor = firmware_module.WeishauptInstalledFirmwareSensor(coordinator)
        entity = update_module.WeishauptFirmwareUpdateEntity(coordinator)
        self.assertFalse(sensor.available)
        self.assertFalse(entity.available)
        self.assertEqual(coordinator.data["check_error"], "vendor unavailable")


if __name__ == "__main__":
    unittest.main()
