"""Regression tests for WCM-COM weekly time programs."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest


PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "weishaupt_wcm_com"
    / "time_program.py"
)
SPEC = spec_from_file_location("weishaupt_time_program", PATH)
assert SPEC is not None and SPEC.loader is not None
time_program = module_from_spec(SPEC)
SPEC.loader.exec_module(time_program)


class TimeProgramTest(unittest.TestCase):
    """Verify IDs, byte order and schedule validation."""

    def test_original_webui_parameter_ids(self) -> None:
        self.assertEqual(
            time_program.parameter_ids("heating_1", "monday"),
            (5136, 5137, 5138),
        )
        self.assertEqual(
            time_program.parameter_ids("heating_1", "sunday"),
            (5232, 5233, 5234),
        )
        self.assertEqual(
            time_program.parameter_ids("hot_water", "monday"),
            (5904, 5905, 5906),
        )
        self.assertEqual(
            time_program.parameter_ids("circulation", "monday"),
            (6672, 6673, 6674),
        )

    def test_start_is_high_byte_and_end_is_low_byte(self) -> None:
        encoded = time_program.encode_interval("06:15", "08:30")
        self.assertEqual(encoded, (25 << 8) | 34)
        self.assertEqual(time_program.decode_interval(encoded), ("06:15", "08:30"))

    def test_disabled_slots_are_filled(self) -> None:
        values = time_program.encode_day([("06:00", "08:00")])
        self.assertEqual(values[1:], (32896, 32896))
        self.assertEqual(
            time_program.decode_day(values),
            (("06:00", "08:00"),),
        )

    def test_midnight_end_is_supported(self) -> None:
        value = time_program.encode_interval("22:00", "24:00")
        self.assertEqual(time_program.decode_interval(value), ("22:00", "24:00"))

    def test_non_quarter_hour_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "15-minute"):
            time_program.encode_interval("06:10", "08:00")

    def test_overlap_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "overlap"):
            time_program.encode_day(
                [("06:00", "09:00"), ("08:45", "10:00")]
            )

    def test_more_than_three_intervals_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "at most three"):
            time_program.encode_day(
                [
                    ("00:00", "01:00"),
                    ("02:00", "03:00"),
                    ("04:00", "05:00"),
                    ("06:00", "07:00"),
                ]
            )

    def test_invalid_wire_value_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid WCM"):
            time_program.decode_interval((100 << 8) | 101)

    def test_active_heating_program_mapping(self) -> None:
        self.assertEqual(
            time_program.active_heating_program(
                {"WTC HK1 User Betriebsart": 11}, 0
            ),
            "heating_1",
        )
        self.assertEqual(
            time_program.active_heating_program(
                {"HK1 User Betriebsart": 12}, 1
            ),
            "heating_2",
        )
        self.assertEqual(
            time_program.active_heating_program(
                {"HK2 User Betriebsart": "Programm 3"}, 2
            ),
            "heating_3",
        )
        self.assertIsNone(
            time_program.active_heating_program(
                {"HK2 User Betriebsart": 15}, 2
            )
        )

    def test_circulation_requires_a_real_measurement(self) -> None:
        self.assertFalse(
            time_program.circulation_supported(
                {
                    "HK1 Zirkulationstemperatur": None,
                    "HK2 Zirkulationstemperatur": None,
                }
            )
        )
        self.assertTrue(
            time_program.circulation_supported(
                {"HK2 Zirkulationstemperatur": 42.0}
            )
        )

    def test_program_bus_routing_uses_detected_wtc_and_circulation_buses(self) -> None:
        data = {
            "WTC HK1 User Mode Kind": "hk",
            "HK1 User Mode Kind": "hk",
            "HK1 Zirkulationstemperatur": 41.5,
        }

        self.assertEqual(
            time_program.resolve_time_program_bus({0, 1}, data, 0, "heating_1"),
            0,
        )
        self.assertEqual(
            time_program.resolve_time_program_bus({0, 1}, data, 1, "hot_water"),
            0,
        )
        self.assertEqual(
            time_program.resolve_time_program_bus(
                {0, 1}, data, 0, "circulation"
            ),
            1,
        )

    def test_explicit_hot_water_controller_wins_over_wtc_fallback(self) -> None:
        data = {
            "WTC HK1 User Mode Kind": "hk",
            "HK1 User Mode Kind": "ww",
        }
        self.assertEqual(
            time_program.domestic_hot_water_program_bus({0, 1}, data),
            1,
        )

    def test_inactive_or_unknown_heating_bus_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "was not detected"):
            time_program.resolve_time_program_bus({0}, {}, 1, "heating_1")
        with self.assertRaisesRegex(ValueError, "0, 1 or 2"):
            time_program.resolve_time_program_bus({0}, {}, 3, "heating_1")


if __name__ == "__main__":
    unittest.main()
