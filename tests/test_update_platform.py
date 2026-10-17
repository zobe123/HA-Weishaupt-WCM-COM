"""Regression tests for the WCM-COM firmware update entity."""

import asyncio
from datetime import timedelta
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock
from enum import IntFlag


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
update_component = types.ModuleType("homeassistant.components.update")
config_entries_module = types.ModuleType("homeassistant.config_entries")
const_module = types.ModuleType("homeassistant.const")
core_module = types.ModuleType("homeassistant.core")
helpers = types.ModuleType("homeassistant.helpers")
device_registry_module = types.ModuleType("homeassistant.helpers.device_registry")
entity_platform_module = types.ModuleType("homeassistant.helpers.entity_platform")
coordinator_module = types.ModuleType("homeassistant.helpers.update_coordinator")


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


class UpdateFailed(Exception):
    """Minimal coordinator update error."""


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


update_component.UpdateEntity = UpdateEntity
update_component.UpdateEntityFeature = UpdateEntityFeature
config_entries_module.ConfigEntry = object
const_module.EntityCategory = EntityCategory
core_module.HomeAssistant = object
device_registry_module.DeviceInfo = DeviceInfo
entity_platform_module.AddEntitiesCallback = object
coordinator_module.CoordinatorEntity = CoordinatorEntity
coordinator_module.DataUpdateCoordinator = DataUpdateCoordinator
coordinator_module.UpdateFailed = UpdateFailed

for module in (
    homeassistant,
    components,
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
update_module = load_module(f"{PACKAGE}.update", ROOT / "update.py")


class UpdatePlatformTest(unittest.TestCase):
    """Verify firmware discovery, metadata and read-only behavior."""

    def test_setup_checks_once_and_creates_daily_read_only_entity(self) -> None:
        api = Mock()
        api.check_firmware_update.return_value = {
            "installed_version": "376-09 C",
            "latest_version": "376-09 C",
            "update_available": False,
        }
        hass = Mock()
        hass.data = {"weishaupt_wcm_com": {"entry-1": {"api": api}}}

        async def run_executor(function, *args):
            return function(*args)

        hass.async_add_executor_job = run_executor
        added = []
        asyncio.run(
            update_module.async_setup_entry(
                hass,
                Mock(entry_id="entry-1"),
                lambda entities: added.extend(entities),
            )
        )

        api.check_firmware_update.assert_called_once_with()
        self.assertEqual(len(added), 1)
        entity = added[0]
        self.assertEqual(entity.installed_version, "376-09 C")
        self.assertEqual(entity.latest_version, "376-09 C")
        self.assertEqual(entity._attr_unique_id, "weishaupt_wcm_com_firmware")
        self.assertEqual(entity._attr_supported_features, UpdateEntityFeature(0))
        self.assertTrue(entity.available)
        self.assertEqual(entity.coordinator.update_interval, timedelta(hours=24))
        self.assertEqual(
            entity.device_info["identifiers"],
            {("weishaupt_wcm_com", "weishaupt_kessel")},
        )
        self.assertEqual(entity.device_info["sw_version"], "376-09 C")

    def test_vendor_failure_does_not_block_integration_platform_setup(self) -> None:
        api = Mock()
        api.check_firmware_update.side_effect = RuntimeError("vendor unavailable")
        hass = Mock()
        hass.data = {"weishaupt_wcm_com": {"entry-1": {"api": api}}}

        async def run_executor(function, *args):
            return function(*args)

        hass.async_add_executor_job = run_executor
        added = []
        asyncio.run(
            update_module.async_setup_entry(
                hass,
                Mock(entry_id="entry-1"),
                lambda entities: added.extend(entities),
            )
        )

        self.assertEqual(len(added), 1)
        self.assertFalse(added[0].available)
        self.assertEqual(
            added[0].coordinator.data["check_error"], "vendor unavailable"
        )


if __name__ == "__main__":
    unittest.main()
