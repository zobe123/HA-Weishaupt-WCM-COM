"""Regression tests for WTC operation phase decoding."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "weishaupt_wcm_com"
    / "operation_phase.py"
)
SPEC = spec_from_file_location("weishaupt_operation_phase", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
operation_phase = module_from_spec(SPEC)
SPEC.loader.exec_module(operation_phase)


class FormatOperationPhaseTest(unittest.TestCase):
    """Verify documented phases and dynamic controller displays."""

    def test_documented_burner_phases(self) -> None:
        """All fixed I10 burner phase values use the documented labels."""
        expected = {
            0: "Brenner aus",
            1: "Ruhestandskontrolle Gebläse",
            2: "Vorspüldrehzahl erreichen",
            3: "Countdown der Vorspülzeit",
            4: "Zünddrehzahl erreichen",
            5: "Flammenbildungszeit",
            6: "Brenner in Betrieb, Regelung aktiv",
            7: "Gasventilkontrolle V1",
            8: "Gasventilkontrolle V2",
            9: "Nachspüldrehzahl erreichen und Nachspülen",
        }

        self.assertEqual(
            {value: operation_phase.format_operation_phase(value) for value in expected},
            expected,
        )

    def test_dynamic_prepurge_countdown(self) -> None:
        """A dynamic value without flame is remaining pre-purge time."""
        self.assertEqual(
            operation_phase.format_operation_phase(16),
            "Vorspülzeit – noch 16 s",
        )

    def test_observed_flame_formation_values(self) -> None:
        """Observed values 16 and 17 with flame are tenths of a second."""
        self.assertEqual(
            operation_phase.format_operation_phase(16, flame_on=True),
            "Flammenbildungszeit 1.6 s",
        )
        self.assertEqual(
            operation_phase.format_operation_phase(17, flame_on=True),
            "Flammenbildungszeit 1.7 s",
        )

    def test_unknown_value_remains_visible(self) -> None:
        """Unexpected values must retain their raw value for diagnosis."""
        self.assertEqual(
            operation_phase.format_operation_phase(255),
            "Unbekannte Betriebsphase (255)",
        )


if __name__ == "__main__":
    unittest.main()
