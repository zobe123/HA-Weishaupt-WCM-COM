"""Regression tests for WCM-COM temperature sentinel handling."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "weishaupt_wcm_com"
    / "temperature.py"
)
SPEC = spec_from_file_location("weishaupt_temperature", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
temperature = module_from_spec(SPEC)
SPEC.loader.exec_module(temperature)


class NormalizeTemperatureValueTest(unittest.TestCase):
    """Verify expected sentinels stay quiet without hiding real outliers."""

    def test_circulation_sentinel_without_previous_value(self) -> None:
        value, should_warn = temperature.normalize_temperature_value(
            parameter_id=1257,
            parameter_name="HK1 Zirkulationstemperatur",
            value=-100.0,
            previous_values={},
        )

        self.assertIsNone(value)
        self.assertFalse(should_warn)

    def test_circulation_sentinel_uses_previous_value(self) -> None:
        value, should_warn = temperature.normalize_temperature_value(
            parameter_id=1257,
            parameter_name="HK2 Zirkulationstemperatur",
            value=-100.0,
            previous_values={"HK2 Zirkulationstemperatur": 42.5},
        )

        self.assertEqual(value, 42.5)
        self.assertFalse(should_warn)

    def test_minus_100_remains_unexpected_for_other_parameters(self) -> None:
        value, should_warn = temperature.normalize_temperature_value(
            parameter_id=15,
            parameter_name="HK1 Vorlauftemperatur",
            value=-100.0,
            previous_values={},
        )

        self.assertIsNone(value)
        self.assertTrue(should_warn)

    def test_global_invalid_sentinel_stays_quiet(self) -> None:
        value, should_warn = temperature.normalize_temperature_value(
            parameter_id=15,
            parameter_name="HK1 Vorlauftemperatur",
            value=-3276.8,
            previous_values={},
        )

        self.assertIsNone(value)
        self.assertFalse(should_warn)

    def test_valid_temperature_is_unchanged(self) -> None:
        value, should_warn = temperature.normalize_temperature_value(
            parameter_id=15,
            parameter_name="HK1 Vorlauftemperatur",
            value=37.4,
            previous_values={},
        )

        self.assertEqual(value, 37.4)
        self.assertFalse(should_warn)


if __name__ == "__main__":
    unittest.main()
