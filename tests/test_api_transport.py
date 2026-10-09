"""Transport-level regression tests for the synchronous WCM-COM API."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import Mock, patch
import json
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
        "name": "HK1 User Betriebsart",
        "type": "value",
        "bus": 1,
        "modultyp": 6,
        "request_group": 2,
        "page": "hk_user",
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

    def test_read_uses_standard_type_and_request_context(self) -> None:
        response = json_response([[6, 1, 1, 274, 0, 0, 11, 0]])
        with patch.object(api_module.requests, "post", return_value=response) as post:
            api = api_module.WeishauptAPI("wcm.test")
            data = api.get_data()

        self.assertEqual(data["HK1 User Betriebsart"], 11)
        self.assertIn('[[6, 1, 1, 274, 0, 0, 0, 0]]', post.call_args.kwargs["data"])

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

    def test_parameter_specific_no_value_marker_is_omitted(self) -> None:
        parameters = [
            {
                "id": 2418, "name": "HK1 User Vorverlegung", "type": "minutes",
                "bus": 1, "modultyp": 6, "request_group": 3,
                "page": "hk_user", "no_value": 32768,
            },
            {
                "id": 19, "name": "HK1 User Normal WW Soll", "type": "temperature",
                "bus": 1, "modultyp": 6, "request_group": 3, "page": "hk_user",
            },
        ]
        response = json_response(
            [[6, 1, 1, 2418, 0, 0, 0, 128], [6, 1, 1, 19, 0, 0, 244, 1]]
        )
        with (
            patch.object(api_module, "PARAMETERS", parameters),
            patch.object(api_module.requests, "post", return_value=response),
        ):
            data = api_module.WeishauptAPI("wcm.test").get_data()

        self.assertNotIn("HK1 User Vorverlegung", data)
        self.assertEqual(data["HK1 User Normal WW Soll"], 50.0)

    def test_server_busy_write_raises(self) -> None:
        response = Mock()
        response.text = "<HTML>Sorry, the server is busy.</HTML>"

        with patch.object(api_module.requests, "post", return_value=response):
            api = api_module.WeishauptAPI("wcm.test")
            with self.assertRaises(api_module.WeishauptCommunicationError):
                api.write_parameter(274, 1, 6, 11)

    def test_batch_write_uses_generic_type_and_keeps_order(self) -> None:
        response = json_response([])
        with patch.object(api_module.requests, "post", return_value=response) as post:
            api = api_module.WeishauptAPI("wcm.test")
            api.write_parameters(
                [
                    (283, 1, 6, 1),
                    (284, 1, 6, 8),
                    (285, 1, 6, 26),
                ]
            )

        payloads = [call.kwargs["data"] for call in post.call_args_list]
        self.assertIn('[[6, 1, 2, 283, 0, 1, 1, 0]]', payloads[0])
        self.assertIn('[[6, 1, 2, 284, 0, 1, 8, 0]]', payloads[1])
        self.assertIn('[[6, 1, 2, 285, 0, 1, 26, 0]]', payloads[2])

    def test_time_program_read_uses_webui_groups_and_byte_order(self) -> None:
        active = (24 << 8) | 32  # 06:00-08:00

        def respond(*args, **kwargs):
            payload = json.loads(kwargs["data"])
            response = []
            for telegram in payload["telegramm"]:
                parameter_id = telegram[3]
                value = active if parameter_id == 5136 else 32896
                response.append(
                    [6, 1, 1, parameter_id, 0, 0, value & 0xFF, value >> 8]
                )
            return json_response(response)

        with patch.object(api_module.requests, "post", side_effect=respond) as post:
            schedule = api_module.WeishauptAPI("wcm.test").read_time_program(
                1, "heating_1"
            )

        self.assertEqual(post.call_count, 3)
        self.assertEqual(schedule["monday"], (("06:00", "08:00"),))
        self.assertEqual(schedule["sunday"], ())

    def test_time_program_day_write_is_read_write_verify_transaction(self) -> None:
        ids = (5136, 5137, 5138)
        state = {parameter_id: 32896 for parameter_id in ids}
        commands = []

        def respond(*args, **kwargs):
            payload = json.loads(kwargs["data"])
            telegrams = payload["telegramm"]
            command = telegrams[0][2]
            commands.append(command)
            if command == protocol.READ_COMMAND:
                return json_response(
                    [
                        [
                            6,
                            1,
                            1,
                            telegram[3],
                            0,
                            0,
                            state[telegram[3]] & 0xFF,
                            state[telegram[3]] >> 8,
                        ]
                        for telegram in telegrams
                    ]
                )
            telegram = telegrams[0]
            state[telegram[3]] = telegram[6] + 256 * telegram[7]
            return json_response([])

        values = ((24 << 8) | 32, (48 << 8) | 52, 32896)
        with patch.object(api_module.requests, "post", side_effect=respond):
            api_module.WeishauptAPI("wcm.test").write_time_program_day(
                1, "heating_1", "monday", values
            )

        self.assertEqual(commands, [1, 2, 2, 2, 1])
        self.assertEqual(tuple(state[parameter_id] for parameter_id in ids), values)


if __name__ == "__main__":
    unittest.main()
