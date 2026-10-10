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


if __name__ == "__main__":
    unittest.main()
