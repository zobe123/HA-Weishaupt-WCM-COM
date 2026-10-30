"""Regression tests for user-facing entity help attributes."""

from importlib.util import module_from_spec, spec_from_file_location
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


if __name__ == "__main__":
    unittest.main()
