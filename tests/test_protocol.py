"""Regression tests for WCM-COM telegram identity and write scaling."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import ast
import unittest


ROOT = Path(__file__).parents[1]
PROTOCOL_PATH = (
    ROOT / "custom_components" / "weishaupt_wcm_com" / "protocol.py"
)
CONST_PATH = ROOT / "custom_components" / "weishaupt_wcm_com" / "const.py"

SPEC = spec_from_file_location("weishaupt_protocol", PROTOCOL_PATH)
assert SPEC is not None and SPEC.loader is not None
protocol = module_from_spec(SPEC)
SPEC.loader.exec_module(protocol)


def load_parameters() -> list[dict]:
    """Read PARAMETERS without importing Home Assistant."""

    module = ast.parse(CONST_PATH.read_text(encoding="utf-8"))
    parameters: list[dict] = []
    for node in module.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "PARAMETERS"
            for target in node.targets
        ):
            parameters.extend(ast.literal_eval(node.value))
        elif (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and isinstance(node.value.func.value, ast.Name)
            and node.value.func.value.id == "PARAMETERS"
            and node.value.func.attr == "extend"
        ):
            parameters.extend(ast.literal_eval(node.value.args[0]))
    if parameters:
        return parameters
    raise AssertionError("PARAMETERS not found")


def load_constant(name: str):
    """Read one literal constant without importing Home Assistant."""

    module = ast.parse(CONST_PATH.read_text(encoding="utf-8"))
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not found")


class ProtocolTest(unittest.TestCase):
    """Verify protocol discriminators and wire-value conversion."""

    def test_parameter_274_has_one_capability_selected_definition(self) -> None:
        """The WebUI exposes one parameter-274 interpretation per bus."""

        parameters = {item["name"]: item for item in load_parameters()}
        self.assertEqual(parameters["HK1 User Betriebsart"]["request_group"], 2)
        self.assertEqual(parameters["HK2 User Betriebsart"]["request_group"], 2)
        self.assertEqual(protocol.user_mode_kind(0, 1), "hk")
        self.assertEqual(protocol.user_mode_kind(0x40, 1), "ww")

    def test_holiday_select_aliases_resolve_by_unique_wire_address(self) -> None:
        """Localized select names must resolve to their raw metadata."""

        parameters = load_parameters()
        for circuit in (1, 2):
            parameter = protocol.resolve_parameter_metadata(
                parameters,
                name=f"HK{circuit} Urlaubstemperaturniveau",
                parameter_id=317,
                bus=circuit,
                module_type=6,
            )
            self.assertEqual(parameter["name"], f"HK{circuit} Holiday Temp Level")
            self.assertEqual(protocol.parameter_group(parameter), 1)

    def test_exact_name_resolves_operating_mode(self) -> None:

        parameters = load_parameters()
        parameter = protocol.resolve_parameter_metadata(
            parameters,
            name="HK1 User Betriebsart",
            parameter_id=274,
            bus=1,
            module_type=6,
        )
        self.assertEqual(parameter["name"], "HK1 User Betriebsart")

    def test_response_resolution_is_limited_to_request_group(self) -> None:
        parameters = [
            {"id": 1, "name": "first", "bus": 1, "modultyp": 6, "request_group": 1},
            {"id": 1, "name": "second", "bus": 1, "modultyp": 6, "request_group": 2},
        ]
        self.assertEqual(
            protocol.resolve_response_parameter([parameters[1]], [6, 1, 1, 1, 0, 0, 7, 0])["name"],
            "second",
        )

    def test_request_group_identities_are_unique(self) -> None:

        identities: dict[tuple[int, int, int, int], str] = {}
        for item in load_parameters():
            if item.get("virtual"):
                continue
            identity = (
                item["id"],
                item.get("bus", 0),
                item.get("modultyp", item.get("destination", 10)),
                item.get("page", "default"),
                protocol.parameter_group(item),
            )
            self.assertNotIn(
                identity,
                identities,
                f"{item['name']} collides with {identities.get(identity)}",
            )
            identities[identity] = item["name"]

    def test_temperature_write_uses_tenths(self) -> None:
        scale = protocol.write_scale("temperature", 5)
        self.assertEqual(protocol.encode_value(22.5, scale), 225)

    def test_percent_write_uses_tenths(self) -> None:
        scale = protocol.write_scale("percent", 319)
        self.assertEqual(protocol.encode_value(100, scale), 1000)

    def test_optimization_minutes_use_15_minute_blocks(self) -> None:
        scale = protocol.write_scale("minutes", 272)
        self.assertEqual(protocol.encode_value(30, scale), 2)
        self.assertEqual(protocol.display_scale(272), 15.0)

    def test_negative_temperature_uses_signed_bytes(self) -> None:
        encoded = protocol.encode_value(-4, protocol.write_scale("temp_delta", 3103))
        telegram = protocol.build_telegram(
            module_type=10,
            bus=0,
            command=protocol.WRITE_COMMAND,
            parameter_id=3103,
            telegram_type=protocol.GENERIC_TELEGRAM,
            value=encoded,
        )
        self.assertEqual(telegram, [10, 0, 2, 3103, 0, 1, 216, 255])

    def test_builder_preserves_explicit_generic_type(self) -> None:
        telegram = protocol.build_telegram(
            module_type=6,
            bus=1,
            command=protocol.WRITE_COMMAND,
            parameter_id=274,
            telegram_type=protocol.GENERIC_TELEGRAM,
            value=11,
        )
        self.assertEqual(telegram, [6, 1, 2, 274, 0, 1, 11, 0])

    def test_frost_limit_is_integer_and_slope_is_tenths(self) -> None:
        self.assertEqual(protocol.write_scale("integer_temperature", 702), 1)
        self.assertEqual(protocol.write_scale("ratio_tenths", 270), 10)

    def test_phantom_solar_parameter_is_absent(self) -> None:
        names = {item["name"] for item in load_parameters()}
        self.assertNotIn("HK1 User Sollwert Solar", names)
        self.assertNotIn("HK2 User Sollwert Solar", names)

    def test_browser_groups_never_become_telegram_types(self) -> None:
        parameters = load_parameters()
        self.assertFalse(any("protocol" in item for item in parameters))
        groups = protocol.split_request_groups(
            [item for item in parameters if item.get("page") == "hk_user"]
        )
        self.assertGreaterEqual(len(groups), 6)
        for group in groups:
            for item in group:
                telegram = protocol.build_telegram(
                    module_type=item.get("modultyp", 10),
                    bus=item.get("bus", 0),
                    command=protocol.READ_COMMAND,
                    parameter_id=item["id"],
                )
                self.assertEqual(telegram[5], protocol.STANDARD_TELEGRAM)

    def test_original_webui_parameters_are_modelled(self) -> None:
        identities = {(item["id"], item.get("bus", 0)) for item in load_parameters()}
        for circuit in (1, 2):
            for parameter_id in (19, 650, 2418, 306, 2414, 2588):
                self.assertIn((parameter_id, circuit), identities)

    def test_all_three_fs_circuits_share_the_core_parameter_set(self) -> None:
        parameters = load_parameters()
        identities = {
            (item["id"], item.get("bus", 0), item.get("modultyp", 10))
            for item in parameters
            if not item.get("virtual")
        }
        fs_core = {
            2, 4, 5, 8, 16, 17, 270, 272, 274, 278, 306, 321, 702,
            2414, 2419, 2580, 2586,
        }
        for bus in (0, 1, 2):
            for parameter_id in fs_core:
                with self.subTest(bus=bus, parameter_id=parameter_id):
                    self.assertIn((parameter_id, bus, 6), identities)

    def test_fs1_does_not_gain_em_only_parameters(self) -> None:
        identities = {
            (item["id"], item.get("bus", 0), item.get("modultyp", 10))
            for item in load_parameters()
            if not item.get("virtual")
        }
        for parameter_id in (15, 857, 1257, 65019):
            self.assertNotIn((parameter_id, 0, 12), identities)

    def test_live_no_value_markers_are_parameter_specific(self) -> None:
        parameters = {item["name"]: item for item in load_parameters()}
        self.assertEqual(
            parameters["WTC HK1 Config HK Type"]["wire_scale"],
            256,
        )
        self.assertEqual(
            parameters["WTC HK1 Expert Raumthermostat"]["no_value"],
            32768,
        )
        for circuit in (1, 2):
            self.assertEqual(
                parameters[f"HK{circuit} User Vorverlegung"]["no_value"],
                32768,
            )
            self.assertEqual(
                parameters[f"HK{circuit} Expert Raumthermostat"]["no_value"],
                10,
            )
            self.assertEqual(
                parameters[f"HK{circuit} Expert Max Charge Time WW"]["no_value"],
                0,
            )

    def test_voltage_codes_match_original_webui(self) -> None:
        self.assertEqual(
            load_constant("HK_CONFIG_VOLTAGE_MAP"),
            {
                0: "Pumpenspannung: Manuell Aus",
                1: "Pumpenspannung: Manuell Ein",
                2: "Pumpenspannung: Automatik Aus",
                3: "Pumpenspannung: Automatik Ein",
            },
        )


if __name__ == "__main__":
    unittest.main()
