"""Regression tests for time-program caching and narrow startup retry."""

import asyncio
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).parents[1] / "custom_components" / "weishaupt_wcm_com"
PACKAGE = "weishaupt_time_program_manager_testpkg"


package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = package

time_program = types.ModuleType(f"{PACKAGE}.time_program")
time_program.encode_day = lambda intervals: tuple(intervals)
sys.modules[time_program.__name__] = time_program

api_module = types.ModuleType(f"{PACKAGE}.weishaupt_api")


class WeishauptCommunicationError(Exception):
    """Test transport error."""


api_module.WeishauptAPI = object
api_module.WeishauptCommunicationError = WeishauptCommunicationError
sys.modules[api_module.__name__] = api_module

spec = spec_from_file_location(
    f"{PACKAGE}.time_program_manager", ROOT / "time_program_manager.py"
)
assert spec is not None and spec.loader is not None
manager_module = module_from_spec(spec)
sys.modules[spec.name] = manager_module
spec.loader.exec_module(manager_module)


class FakeHass:
    """Execute jobs inline like Home Assistant's executor bridge."""

    async def async_add_executor_job(self, function, *args):
        return function(*args)


class TimeProgramManagerTest(unittest.TestCase):
    """Retry only the observed incomplete-read failure."""

    def test_retries_one_omitted_parameter_once(self) -> None:
        class Api:
            calls = 0

            def read_time_program(self, _circuit, _program):
                self.calls += 1
                if self.calls == 1:
                    raise WeishauptCommunicationError(
                        "WCM-COM omitted time-program parameter 6754"
                    )
                return {"monday": (("06:00", "08:00"),)}

        api = Api()
        manager = manager_module.TimeProgramManager(FakeHass(), api)
        result = asyncio.run(manager.async_get(2, "circulation"))

        self.assertEqual(api.calls, 2)
        self.assertEqual(result["monday"], (("06:00", "08:00"),))

    def test_other_communication_errors_are_not_retried(self) -> None:
        class Api:
            calls = 0

            def read_time_program(self, _circuit, _program):
                self.calls += 1
                raise WeishauptCommunicationError("server busy")

        api = Api()
        manager = manager_module.TimeProgramManager(FakeHass(), api)

        with self.assertRaisesRegex(WeishauptCommunicationError, "server busy"):
            asyncio.run(manager.async_get(1, "heating_1"))
        self.assertEqual(api.calls, 1)

    def test_stale_schedule_remains_available_without_device_io(self) -> None:
        clock = [100.0]
        original_monotonic = manager_module.monotonic
        manager_module.monotonic = lambda: clock[0]

        class Api:
            calls = 0

            def read_time_program(self, _circuit, _program):
                self.calls += 1
                return {"monday": (("06:00", "22:00"),)}

        try:
            api = Api()
            manager = manager_module.TimeProgramManager(
                FakeHass(), api, cache_seconds=300
            )
            asyncio.run(manager.async_get(0, "heating_1"))
            clock[0] = 700.0

            snapshot = manager.cached(0, "heating_1")

            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            self.assertFalse(snapshot["fresh"])
            self.assertEqual(snapshot["age_seconds"], 600.0)
            self.assertEqual(
                snapshot["schedule"]["monday"], (("06:00", "22:00"),)
            )
            self.assertEqual(api.calls, 1)
        finally:
            manager_module.monotonic = original_monotonic

    def test_force_refresh_replaces_a_fresh_cache_entry(self) -> None:
        class Api:
            calls = 0

            def read_time_program(self, _circuit, _program):
                self.calls += 1
                return {"revision": self.calls}

        api = Api()
        manager = manager_module.TimeProgramManager(FakeHass(), api)

        first = asyncio.run(manager.async_get(1, "heating_1"))
        refreshed = asyncio.run(
            manager.async_get(1, "heating_1", force_refresh=True)
        )

        self.assertEqual(first["revision"], 1)
        self.assertEqual(refreshed["revision"], 2)
        self.assertEqual(api.calls, 2)

    def test_concurrent_refreshes_share_one_controller_read(self) -> None:
        class YieldingHass:
            async def async_add_executor_job(self, function, *args):
                await asyncio.sleep(0)
                return function(*args)

        class Api:
            calls = 0

            def read_time_program(self, _circuit, _program):
                self.calls += 1
                return {"revision": self.calls}

        async def refresh_twice(manager):
            return await asyncio.gather(
                manager.async_get(1, "heating_1", force_refresh=True),
                manager.async_get(1, "heating_1", force_refresh=True),
            )

        api = Api()
        manager = manager_module.TimeProgramManager(YieldingHass(), api)
        results = asyncio.run(refresh_twice(manager))

        self.assertEqual(results, [{"revision": 1}, {"revision": 1}])
        self.assertEqual(api.calls, 1)


if __name__ == "__main__":
    unittest.main()
