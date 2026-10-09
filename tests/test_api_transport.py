"""Transport-level regression tests for the synchronous WCM-COM API."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import Mock, patch
import sys
import types
import unittest

import requests


ROOT = Path(__file__).parents[1] / "custom_components" / "weishaupt_wcm_com"
PACKAGE = "weishaupt_transport_testpkg"


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

const = types.ModuleType(f"{PACKAGE}.const")
const.PARAMETERS = [
    {
        "id": 274,
        "name": "HK1 User Betriebsart WW",
        "type": "value",
        "bus": 1,
        "modultyp": 6,
        "protocol": 3,
    }
]
const.ERROR_CODE_MAP = {}
const.WARNING_CODE_MAP = {}
sys.modules[const.__name__] = const

protocol = load_module(f"{PACKAGE}.protocol", ROOT / "protocol.py")
temperature = load_module(f"{PACKAGE}.temperature", ROOT / "temperature.py")
api_module = load_module(f"{PACKAGE}.weishaupt_api", ROOT / "weishaupt_api.py")


def json_response(telegram: list[list[int]]) -> Mock:
    """Return a minimal requests-like successful JSON response."""

    response = Mock()
    response.text = "json"
    response.json.return_value = {"telegramm": telegram}
    response.raise_for_status.return_value = None
    response.status_code = 200
    return response


class ApiTransportTest(unittest.TestCase):
    """Verify transport errors, protocol matching and write behavior."""

    def test_read_uses_and_matches_protocol(self) -> None:
        response = json_response([[6, 1, 1, 274, 0, 3, 11, 0]])
        with patch.object(api_module.requests, "post", return_value=response) as post:
            api = api_module.WeishauptAPI("wcm.test")
            data = api.get_data()

        self.assertEqual(data["HK1 User Betriebsart WW"], 11)
        self.assertIn('[[6, 1, 1, 274, 0, 3, 0, 0]]', post.call_args.kwargs["data"])

    def test_failed_update_raises_and_preserves_last_data(self) -> None:
        api = api_module.WeishauptAPI("wcm.test")
        api._data = {"existing": 42}

        with (
            patch.object(
                api_module.requests,
                "post",
                side_effect=requests.exceptions.Timeout("timeout"),
            ),
            patch.object(api_module.time, "sleep"),
        ):
            with self.assertRaises(api_module.WeishauptCommunicationError):
                api.update()

        self.assertEqual(api.data, {"existing": 42})

    def test_server_busy_write_raises(self) -> None:
        response = Mock()
        response.text = "<HTML>Sorry, the server is busy.</HTML>"

        with patch.object(api_module.requests, "post", return_value=response):
            api = api_module.WeishauptAPI("wcm.test")
            with self.assertRaises(api_module.WeishauptCommunicationError):
                api.write_parameter(274, 1, 6, 11, 3)

    def test_batch_write_keeps_protocols_and_order(self) -> None:
        response = json_response([])
        with patch.object(api_module.requests, "post", return_value=response) as post:
            api = api_module.WeishauptAPI("wcm.test")
            api.write_parameters(
                [
                    (283, 1, 6, 1, 0),
                    (284, 1, 6, 8, 0),
                    (285, 1, 6, 26, 0),
                ]
            )

        payloads = [call.kwargs["data"] for call in post.call_args_list]
        self.assertIn('[[6, 1, 2, 283, 0, 0, 1, 0]]', payloads[0])
        self.assertIn('[[6, 1, 2, 284, 0, 0, 8, 0]]', payloads[1])
        self.assertIn('[[6, 1, 2, 285, 0, 0, 26, 0]]', payloads[2])


if __name__ == "__main__":
    unittest.main()
