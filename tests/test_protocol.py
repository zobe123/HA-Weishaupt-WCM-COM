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
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == "PARAMETERS" for target in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("PARAMETERS not found")


class ProtocolTest(unittest.TestCase):
    """Verify protocol discriminators and wire-value conversion."""

    def test_hk_and_hot_water_modes_have_distinct_protocols(self) -> None:
        """Parameter 274 must be separated by TEL_PROT like the original WebUI."""

        parameters = {item["name"]: item for item in load_parameters()}
        self.assertEqual(parameters["HK1 User Betriebsart HK"]["protocol"], 2)
        self.assertEqual(parameters["HK1 User Betriebsart WW"]["protocol"], 3)
        self.assertEqual(parameters["HK2 User Betriebsart HK"]["protocol"], 2)
        self.assertEqual(parameters["HK2 User Betriebsart WW"]["protocol"], 3)

    def test_non_virtual_wire_identities_are_unique(self) -> None:
        """No two values may collapse onto the same complete telegram address."""

        identities: dict[tuple[int, int, int, int], str] = {}
        for item in load_parameters():
            if item.get("virtual"):
                continue
            identity = (
                item["id"],
                item.get("bus", 0),
                item.get("modultyp", item.get("destination", 10)),
                protocol.parameter_protocol(item),
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
            protocol=0,
            value=encoded,
        )
        self.assertEqual(telegram, [10, 0, 2, 3103, 0, 0, 216, 255])

    def test_write_telegram_preserves_protocol(self) -> None:
        telegram = protocol.build_telegram(
            module_type=6,
            bus=1,
            command=protocol.WRITE_COMMAND,
            parameter_id=274,
            protocol=3,
            value=11,
        )
        self.assertEqual(telegram, [6, 1, 2, 274, 0, 3, 11, 0])


if __name__ == "__main__":
    unittest.main()
