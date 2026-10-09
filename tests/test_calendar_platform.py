"""Regression tests for the device-backed calendar platform."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, Mock


ROOT = Path(__file__).parents[1] / "custom_components" / "weishaupt_wcm_com"
PACKAGE = "weishaupt_calendar_testpkg"


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
calendar_component = types.ModuleType("homeassistant.components.calendar")
config_entries_module = types.ModuleType("homeassistant.config_entries")
core_module = types.ModuleType("homeassistant.core")
const_module = types.ModuleType("homeassistant.const")
helpers = types.ModuleType("homeassistant.helpers")
entity_platform_module = types.ModuleType("homeassistant.helpers.entity_platform")
util_module = types.ModuleType("homeassistant.util")
dt_module = types.ModuleType("homeassistant.util.dt")


class CalendarEntity:
    hass = None
    entity_id = None


@dataclass
class CalendarEvent:
    start: datetime
    end: datetime
    summary: str
    description: str | None = None
    uid: str | None = None


calendar_component.CalendarEntity = CalendarEntity
calendar_component.CalendarEvent = CalendarEvent
config_entries_module.ConfigEntry = object
core_module.HomeAssistant = object
const_module.CONF_SCAN_INTERVAL = "scan_interval"
entity_platform_module.AddEntitiesCallback = object
dt_module.now = lambda: datetime.now().astimezone()
util_module.dt = dt_module

for module in (
    homeassistant,
    components,
    calendar_component,
    config_entries_module,
    core_module,
    const_module,
    helpers,
    entity_platform_module,
    util_module,
    dt_module,
):
    sys.modules[module.__name__] = module

load_module(f"{PACKAGE}.const", ROOT / "const.py")
load_module(f"{PACKAGE}.time_program", ROOT / "time_program.py")
calendar_module = load_module(f"{PACKAGE}.calendar", ROOT / "calendar.py")


class CalendarPlatformTest(unittest.TestCase):
    """Verify entity count and weekly event expansion."""

    def test_platform_creates_ten_program_calendars(self) -> None:
        manager = Mock()
        hass = Mock()
        hass.data = {
            "weishaupt_wcm_com": {
                "entry-1": {"time_program_manager": manager}
            }
        }
        entry = Mock(entry_id="entry-1")
        added = []

        asyncio.run(
            calendar_module.async_setup_entry(
                hass, entry, lambda entities: added.extend(entities)
            )
        )

        self.assertEqual(len(added), 10)
        self.assertEqual(len({entity._attr_unique_id for entity in added}), 10)

    def test_calendar_expands_weekly_intervals(self) -> None:
        manager = Mock()
        manager.async_get = AsyncMock(
            return_value={
                day: (("06:00", "08:00"),) if day == "monday" else ()
                for day in calendar_module.WEEKDAYS
            }
        )
        entity = calendar_module.WeishauptTimeProgramCalendar(
            manager, 1, "heating_1"
        )
        start = datetime.fromisoformat("2026-10-05T00:00:00+02:00")
        end = datetime.fromisoformat("2026-10-12T00:00:00+02:00")

        events = asyncio.run(entity.async_get_events(Mock(), start, end))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].start.isoformat(), "2026-10-05T06:00:00+02:00")
        self.assertEqual(events[0].end.isoformat(), "2026-10-05T08:00:00+02:00")
        self.assertEqual(events[0].summary, "HK1 Heizprogramm 1")


if __name__ == "__main__":
    unittest.main()
