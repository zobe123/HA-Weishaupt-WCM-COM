"""Regression tests for functional Home Assistant device grouping."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).parents[1] / "custom_components" / "weishaupt_wcm_com"
PACKAGE = "weishaupt_device_model_testpkg"

package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = package


def load_module(name: str, path: Path):
    spec = spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


load_module(f"{PACKAGE}.const", ROOT / "const.py")
device_model = load_module(f"{PACKAGE}.device_model", ROOT / "device_model.py")


class DeviceModelTest(unittest.TestCase):
    """Keep boiler and circuit assignment stable and understandable."""

    def test_heating_values_remain_on_their_circuit(self) -> None:
        self.assertEqual(
            device_model.device_descriptor("WTC HK1 User Steilheit"),
            ("weishaupt_wtc_hk1", "HK1 · WTC / FS1"),
        )
        self.assertEqual(
            device_model.device_descriptor("HK1 Raumtemperatur"),
            ("weishaupt_hk1", "HK2 · Radiatoren / FS2"),
        )
        self.assertEqual(
            device_model.device_descriptor("HK2 Vorlauftemperatur"),
            ("weishaupt_hk2", "HK3 · FBH / FS3"),
        )

    def test_hot_water_values_route_to_boiler_regardless_of_bus_prefix(self) -> None:
        for parameter_name in (
            "WTC HK1 User Normal WW Soll",
            "HK1 User Absenk WW Soll",
            "HK2 Warmwassertemperatur",
            "HK1 Zirkulationstemperatur",
            "HK2 Expert Max Charge Time WW",
        ):
            with self.subTest(parameter_name=parameter_name):
                self.assertEqual(
                    device_model.device_descriptor(parameter_name),
                    ("weishaupt_kessel", "Therme / Kessel"),
                )

    def test_dynamic_hot_water_mode_routes_to_boiler(self) -> None:
        self.assertEqual(
            device_model.device_descriptor(
                "HK2 User Betriebsart", hot_water=True
            ),
            ("weishaupt_kessel", "Therme / Kessel"),
        )

    def test_only_fs2_fs3_hot_water_setpoints_are_duplicate_controls(self) -> None:
        for parameter_name in (
            "HK1 User Normal WW Soll",
            "HK1 User Absenk WW Soll",
            "HK2 User Normal WW Soll",
            "HK2 User Absenk WW Soll",
        ):
            self.assertTrue(
                device_model.is_duplicate_hot_water_control(parameter_name)
            )
        self.assertFalse(
            device_model.is_duplicate_hot_water_control(
                "WTC HK1 User Normal WW Soll"
            )
        )
        self.assertFalse(
            device_model.is_duplicate_hot_water_control("HK1 User Normal VL Soll")
        )

    def test_every_hot_water_setpoint_readback_is_a_duplicate(self) -> None:
        for prefix in ("WTC HK1", "HK1", "HK2"):
            for level in ("Normal", "Absenk"):
                self.assertTrue(
                    device_model.is_hot_water_readback_duplicate(
                        f"{prefix} User {level} WW Soll"
                    )
                )
        self.assertFalse(
            device_model.is_hot_water_readback_duplicate(
                "WTC HK1 User Normal Raumtemperatur"
            )
        )


if __name__ == "__main__":
    unittest.main()
