"""Regression tests for user-facing entity help attributes."""

from importlib.util import module_from_spec, spec_from_file_location
import ast
from pathlib import Path
import sys
import unittest


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "weishaupt_wcm_com"
    / "entity_help.py"
)
SPEC = spec_from_file_location("weishaupt_entity_help_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
ENTITY_HELP = module_from_spec(SPEC)
sys.modules[SPEC.name] = ENTITY_HELP
SPEC.loader.exec_module(ENTITY_HELP)
entity_help_attributes = ENTITY_HELP.entity_help_attributes


class EntityHelpTest(unittest.TestCase):
    """Verify localized, evidence-backed help metadata."""

    def test_german_heating_circuit_help(self) -> None:
        """Original WebUI menu references remain visible in German setups."""

        attributes = entity_help_attributes(
            "HK2 Config HK Type",
            language="de",
            value_range="Fußbodenheizung, Radiator",
        )

        self.assertEqual(
            attributes,
            {
                "parameter": "P316",
                "description": "Legt den angeschlossenen Heizkreistyp fest.",
                "value_range": "Fußbodenheizung, Radiator",
                "documentation_basis": "Weishaupt-Handbuch / originale WCM-COM-WebUI",
            },
        )

    def test_english_global_expert_help(self) -> None:
        """Global WTC expert parameters expose concise English help."""

        attributes = entity_help_attributes(
            "Expert Corr Outside Sensor",
            language="en-GB",
            value_range="-4–4 K; step 1 K",
        )

        self.assertEqual(attributes["parameter"], "P20")
        self.assertEqual(
            attributes["description"],
            "Correction applied to the measured outdoor temperature.",
        )
        self.assertEqual(attributes["value_range"], "-4–4 K; step 1 K")

    def test_switch_on_optimization_explains_wire_conversion(self) -> None:
        """The scaled P503 display documents its 15-minute wire blocks."""

        attributes = entity_help_attributes(
            "WTC HK1 Expert Ein Opti MAX",
            language="de-DE",
            value_range="0–240 min; step 15 min",
        )

        self.assertEqual(attributes["parameter"], "P503")
        self.assertIn("15-Minuten-Blöcke", attributes["notice"])

    def test_unknown_entity_gets_no_unverified_help(self) -> None:
        """Unsupported entities must not receive guessed documentation."""

        self.assertEqual(entity_help_attributes("Unknown", language="de"), {})

    def test_every_public_catalog_entity_has_documented_help(self) -> None:
        """Every entity produced from PARAMETERS has a description."""

        const_path = MODULE_PATH.with_name("const.py")
        tree = ast.parse(const_path.read_text(encoding="utf-8"))
        parameters: list[dict] = []
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "PARAMETERS"
                for target in node.targets
            ):
                parameters.extend(ast.literal_eval(node.value))
            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and isinstance(node.value.func.value, ast.Name)
                and node.value.func.value.id == "PARAMETERS"
                and node.value.func.attr == "extend"
            ):
                parameters.extend(ast.literal_eval(node.value.args[0]))

        missing = sorted(
            {
                parameter["name"]
                for parameter in parameters
                if not parameter.get("internal")
                and not entity_help_attributes(
                    parameter["name"],
                    language="de",
                    parameter=parameter,
                ).get("description")
            }
        )
        self.assertEqual(missing, [])

    def test_transport_identity_is_exposed(self) -> None:
        """Physical WCM identity accompanies the human menu reference."""

        attributes = entity_help_attributes(
            "HK2 Config HK Type",
            language="de",
            parameter={"id": 2419, "bus": 2, "modultyp": 6},
        )
        self.assertEqual(attributes["parameter"], "P316")
        self.assertEqual(attributes["wcm_parameter"], 2419)
        self.assertEqual(attributes["wcm_bus"], 2)
        self.assertEqual(attributes["wcm_module"], 6)


if __name__ == "__main__":
    unittest.main()
