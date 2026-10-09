"""Regression tests for select metadata resolution and writes."""

import asyncio
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, Mock


ROOT = Path(__file__).parents[1] / "custom_components" / "weishaupt_wcm_com"
PACKAGE = "weishaupt_select_testpkg"


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
select_component = types.ModuleType("homeassistant.components.select")
const_module = types.ModuleType("homeassistant.const")
core_module = types.ModuleType("homeassistant.core")
config_entries_module = types.ModuleType("homeassistant.config_entries")
helpers = types.ModuleType("homeassistant.helpers")
coordinator_module = types.ModuleType("homeassistant.helpers.update_coordinator")
entity_platform_module = types.ModuleType("homeassistant.helpers.entity_platform")
exceptions_module = types.ModuleType("homeassistant.exceptions")


class SelectEntity:
    """Minimal Home Assistant select stub."""


class EntityCategory:
    CONFIG = "config"


class CoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator


class HomeAssistantError(Exception):
    """Minimal Home Assistant error stub."""


select_component.SelectEntity = SelectEntity
const_module.EntityCategory = EntityCategory
const_module.CONF_SCAN_INTERVAL = "scan_interval"
core_module.HomeAssistant = object
config_entries_module.ConfigEntry = object
coordinator_module.DataUpdateCoordinator = object
coordinator_module.CoordinatorEntity = CoordinatorEntity
entity_platform_module.AddEntitiesCallback = object
exceptions_module.HomeAssistantError = HomeAssistantError

for module in (
    homeassistant,
    components,
    select_component,
    const_module,
    core_module,
    config_entries_module,
    helpers,
    coordinator_module,
    entity_platform_module,
    exceptions_module,
):
    sys.modules[module.__name__] = module

base_entity = types.ModuleType(f"{PACKAGE}.base_entity")


class WeishauptBaseEntity:
    def __init__(self, api):
        self.api = api


base_entity.WeishauptBaseEntity = WeishauptBaseEntity
sys.modules[base_entity.__name__] = base_entity

load_module(f"{PACKAGE}.const", ROOT / "const.py")
load_module(f"{PACKAGE}.protocol", ROOT / "protocol.py")
select_module = load_module(f"{PACKAGE}.select", ROOT / "select.py")


class SelectPlatformTest(unittest.TestCase):
    """Verify select discovery, aliases and generic writes."""

    def test_platform_setup_creates_every_select(self) -> None:
        coordinator = Mock()
        coordinator.data = {
            "HK1 User Mode Kind": "hk",
            "HK2 User Mode Kind": "ww",
            "HK1 Expert Reduziertbetrieb": 1,
            "HK2 Expert Reduziertbetrieb": 0,
            "HK1 Expert Raumthermostat": 0,
            "HK2 Expert Raumthermostat": 1,
        }
        api = Mock()
        hass = Mock()
        hass.data = {
            "weishaupt_wcm_com": {
                "entry-1": {
                    "coordinator": coordinator,
                    "api": api,
                    "allow_write": False,
                }
            }
        }
        entry = Mock(entry_id="entry-1")
        added: list[object] = []

        asyncio.run(
            select_module.async_setup_entry(
                hass,
                entry,
                lambda entities: added.extend(entities),
            )
        )

        self.assertEqual(len(added), 14)

    def test_holiday_select_uses_raw_data_name(self) -> None:
        coordinator = Mock()
        coordinator.data = {"HK1 Holiday Temp Level": 1}
        entity = select_module.WeishauptHKConfigSelect(
            coordinator,
            Mock(),
            "HK1 Urlaubstemperaturniveau",
            "hk1_urlaubstemperaturniveau",
            {0: "Frostschutz", 1: "Absenktemperatur"},
            parameter_id=317,
            bus=1,
            modultyp=6,
            allow_write=True,
        )

        self.assertEqual(entity.current_option, "Absenktemperatur")

    def test_select_write_uses_generic_api_call(self) -> None:
        coordinator = Mock()
        coordinator.data = {"HK1 Holiday Temp Level": 0}
        coordinator.async_request_refresh = AsyncMock()
        api = Mock()
        entity = select_module.WeishauptHKConfigSelect(
            coordinator,
            api,
            "HK1 Urlaubstemperaturniveau",
            "hk1_urlaubstemperaturniveau",
            {0: "Frostschutz", 1: "Absenktemperatur"},
            parameter_id=317,
            bus=1,
            modultyp=6,
            allow_write=True,
        )

        async def run_executor(function, *args):
            return function(*args)

        entity.hass = Mock()
        entity.hass.async_add_executor_job = run_executor
        asyncio.run(entity.async_select_option("Absenktemperatur"))

        api.write_parameter.assert_called_once_with(317, 1, 6, 1)
        coordinator.async_request_refresh.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
