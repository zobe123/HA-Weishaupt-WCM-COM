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


def unauthorized_response() -> Mock:
    """Return a minimal HTTP 401 response."""

    response = Mock()
    response.text = "Unauthorized"
    response.status_code = 401
    response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "401 Client Error: Unauthorized"
    )
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

    def test_wtc_hk1_readback_uses_bus_zero_and_heating_mode(self) -> None:
        parameters = [
            {
                "id": 104,
                "name": "WTC HK1 User Capability Flags",
                "type": "value",
                "bus": 0,
                "modultyp": 6,
                "request_group": 0,
                "page": "hk_user",
                "internal": True,
            },
            {
                "id": 274,
                "name": "WTC HK1 User Betriebsart",
                "type": "value",
                "bus": 0,
                "modultyp": 6,
                "request_group": 2,
                "page": "hk_user",
            },
        ]

        def respond(*args, **kwargs):
            request = json.loads(kwargs["data"])["telegramm"]
            messages = []
            for telegram in request:
                value = 0x40 if telegram[3] == 104 else 5
                messages.append([6, 0, 1, telegram[3], 0, 0, value, 0])
            return json_response(messages)

        with (
            patch.object(api_module, "PARAMETERS", parameters),
            patch.object(api_module.requests, "post", side_effect=respond) as post,
        ):
            data = api_module.WeishauptAPI("wcm.test").get_data()

        payloads = [json.loads(call.kwargs["data"])["telegramm"] for call in post.call_args_list]
        telegrams = [telegram for payload in payloads for telegram in payload]
        self.assertIn([6, 0, 1, 274, 0, 0, 0, 0], telegrams)
        self.assertEqual(data["WTC HK1 User Betriebsart"], 5)
        self.assertEqual(data["WTC HK1 User Mode Kind"], "hk")

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

    def test_authentication_failure_is_not_retried(self) -> None:
        with (
            patch.object(
                api_module.requests,
                "post",
                return_value=unauthorized_response(),
            ) as post,
            patch.object(api_module.time, "sleep") as sleep,
        ):
            with self.assertRaises(api_module.WeishauptAuthenticationError):
                api_module.WeishauptAPI("wcm.test", "user", "wrong").get_data()

        self.assertEqual(post.call_count, 1)
        sleep.assert_not_called()

    def test_firmware_authentication_failure_is_specific(self) -> None:
        with patch.object(
            api_module.requests,
            "post",
            return_value=unauthorized_response(),
        ) as post:
            with self.assertRaises(api_module.WeishauptAuthenticationError):
                api_module.WeishauptAPI(
                    "wcm.test", "user", "wrong"
                ).check_firmware_update()

        self.assertEqual(post.call_count, 1)

    def test_write_authentication_failure_is_specific(self) -> None:
        with patch.object(
            api_module.requests,
            "post",
            return_value=unauthorized_response(),
        ) as post:
            with self.assertRaises(api_module.WeishauptAuthenticationError):
                api_module.WeishauptAPI(
                    "wcm.test", "user", "wrong"
                ).write_parameter(274, 1, 6, 11)

        self.assertEqual(post.call_count, 1)

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

    def test_bus_zero_high_byte_enum_is_scaled_to_its_option_code(self) -> None:
        parameters = [
            {
                "id": 16,
                "name": "WTC HK1 Config HK Type",
                "type": "value",
                "bus": 0,
                "modultyp": 6,
                "wire_scale": 256,
            },
            {
                "id": 2588,
                "name": "WTC HK1 Expert Raumthermostat",
                "type": "value",
                "bus": 0,
                "modultyp": 6,
                "no_value": 32768,
            },
        ]
        response = json_response(
            [[6, 0, 1, 16, 0, 0, 0, 4], [6, 0, 1, 2588, 0, 0, 0, 128]]
        )
        with (
            patch.object(api_module, "PARAMETERS", parameters),
            patch.object(api_module.requests, "post", return_value=response),
        ):
            data = api_module.WeishauptAPI("wcm.test").get_data()

        self.assertEqual(data["WTC HK1 Config HK Type"], 4)
        self.assertNotIn("WTC HK1 Expert Raumthermostat", data)

    def test_server_busy_write_raises(self) -> None:
        response = Mock()
        response.text = "<HTML>Sorry, the server is busy.</HTML>"

        with patch.object(api_module.requests, "post", return_value=response):
            api = api_module.WeishauptAPI("wcm.test")
            with self.assertRaises(api_module.WeishauptCommunicationError):
                api.write_parameter(274, 1, 6, 11)

    def test_firmware_check_uses_webui_telegrams_and_reports_current(self) -> None:
        responses = [
            json_response([[0, 0, 1, 20015, 0, 1, 9, "376-09 C"]]),
            json_response([]),
            json_response([[0, 0, 1, 20117, 0, 1, 0, 0]]),
            json_response([[0, 0, 1, 20117, 0, 1, 1, 0]]),
        ]
        with (
            patch.object(api_module.requests, "post", side_effect=responses) as post,
            patch.object(api_module.time, "sleep"),
        ):
            result = api_module.WeishauptAPI("wcm.test").check_firmware_update()

        self.assertEqual(
            result,
            {
                "installed_version": "376-09 C",
                "latest_version": "376-09 C",
                "update_available": False,
            },
        )
        telegrams = [
            json.loads(call.kwargs["data"])["telegramm"][0]
            for call in post.call_args_list
        ]
        self.assertEqual(
            telegrams,
            [
                [0, 0, 1, 20015, 0, 1, 0, 0],
                [0, 0, 2, 20116, 0, 0, 1, 0],
                [0, 0, 1, 20117, 0, 1, 0, 0],
                [0, 0, 1, 20117, 0, 1, 0, 0],
            ],
        )

    def test_firmware_check_reports_available_version(self) -> None:
        responses = [
            json_response([[0, 0, 1, 20015, 0, 1, 9, "376-09 C"]]),
            json_response([]),
            json_response([[0, 0, 1, 20117, 0, 1, 2, "377-01 A"]]),
        ]
        with patch.object(api_module.requests, "post", side_effect=responses):
            result = api_module.WeishauptAPI("wcm.test").check_firmware_update()

        self.assertEqual(result["installed_version"], "376-09 C")
        self.assertEqual(result["latest_version"], "377-01 A")
        self.assertTrue(result["update_available"])

    def test_firmware_server_error_is_isolated_as_communication_error(self) -> None:
        responses = [
            json_response([[0, 0, 1, 20015, 0, 1, 9, "376-09 C"]]),
            json_response([]),
            json_response([[0, 0, 1, 20117, 0, 1, 3, 0]]),
        ]
        with patch.object(api_module.requests, "post", side_effect=responses):
            with self.assertRaisesRegex(
                api_module.WeishauptCommunicationError,
                "firmware server returned an error",
            ):
                api_module.WeishauptAPI("wcm.test").check_firmware_update()

    def test_batch_write_uses_standard_type_and_keeps_order(self) -> None:
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
        self.assertIn('[[6, 1, 2, 283, 0, 0, 1, 0]]', payloads[0])
        self.assertIn('[[6, 1, 2, 284, 0, 0, 8, 0]]', payloads[1])
        self.assertIn('[[6, 1, 2, 285, 0, 0, 26, 0]]', payloads[2])

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
        write_types = []

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
            write_types.append(telegram[5])
            state[telegram[3]] = telegram[6] + 256 * telegram[7]
            return json_response([])

        values = ((24 << 8) | 32, (48 << 8) | 52, 32896)
        with patch.object(api_module.requests, "post", side_effect=respond):
            api_module.WeishauptAPI("wcm.test").write_time_program_day(
                1, "heating_1", "monday", values
            )

        self.assertEqual(commands, [1, 2, 2, 2, 1])
        self.assertEqual(write_types, [protocol.STANDARD_TELEGRAM] * 3)
        self.assertEqual(tuple(state[parameter_id] for parameter_id in ids), values)

    def test_time_program_write_rejects_invalid_original_before_writing(self) -> None:
        ids = (5136, 5137, 5138)
        original = {ids[0]: 257, ids[1]: 32896, ids[2]: 32896}
        values = ((24 << 8) | 32, (48 << 8) | 52, 32896)
        api = api_module.WeishauptAPI("wcm.test")

        with (
            patch.object(api, "_read_raw_parameters_unlocked", return_value=original),
            patch.object(api, "_write_parameter_unlocked") as write,
        ):
            with self.assertRaisesRegex(
                api_module.WeishauptCommunicationError,
                "original day is invalid",
            ):
                api.write_time_program_day(1, "heating_1", "monday", values)

        write.assert_not_called()

    def test_time_program_failed_verification_restores_and_verifies_original(self) -> None:
        ids = (5136, 5137, 5138)
        original_values = ((24 << 8) | 32, 32896, 32896)
        requested_values = ((28 << 8) | 36, 32896, 32896)
        original = dict(zip(ids, original_values))
        mismatched = dict(zip(ids, (requested_values[0], 0, 32896)))
        api = api_module.WeishauptAPI("wcm.test")

        with (
            patch.object(
                api,
                "_read_raw_parameters_unlocked",
                side_effect=[original, mismatched, original],
            ),
            patch.object(api, "_write_parameter_unlocked") as write,
        ):
            with self.assertRaisesRegex(
                api_module.WeishauptCommunicationError,
                "verification failed after writing",
            ):
                api.write_time_program_day(
                    1, "heating_1", "monday", requested_values
                )

        self.assertEqual(
            [call.args for call in write.call_args_list],
            [
                *(zip(ids, (1,) * 3, (6,) * 3, requested_values)),
                *(zip(ids, (1,) * 3, (6,) * 3, original_values)),
            ],
        )

    def test_time_program_failed_rollback_reports_compound_error(self) -> None:
        ids = (5136, 5137, 5138)
        original_values = ((24 << 8) | 32, 32896, 32896)
        requested_values = ((28 << 8) | 36, 32896, 32896)
        original = dict(zip(ids, original_values))
        mismatched = dict(zip(ids, (requested_values[0], 0, 32896)))
        api = api_module.WeishauptAPI("wcm.test")

        with (
            patch.object(
                api,
                "_read_raw_parameters_unlocked",
                side_effect=[original, mismatched, mismatched],
            ),
            patch.object(api, "_write_parameter_unlocked"),
        ):
            with self.assertRaisesRegex(
                api_module.WeishauptCommunicationError,
                "rollback could not be verified",
            ):
                api.write_time_program_day(
                    1, "heating_1", "monday", requested_values
                )


if __name__ == "__main__":
    unittest.main()
