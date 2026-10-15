"""Contracts for language-neutral entities and complete DE/EN catalogs."""

from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "weishaupt_wcm_com"
PACKAGE = "weishaupt_localization_testpkg"


def load_module(name: str, path: Path):
    spec = spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


package = types.ModuleType(PACKAGE)
package.__path__ = [str(COMPONENT)]
sys.modules[PACKAGE] = package
const = load_module(f"{PACKAGE}.const", COMPONENT / "const.py")
localization = load_module(
    f"{PACKAGE}.localization", COMPONENT / "localization.py"
)


def leaf_paths(value, prefix=()):
    """Return every leaf path so catalogs can be compared exactly."""

    if isinstance(value, dict):
        paths = set()
        for key, child in value.items():
            paths.update(leaf_paths(child, (*prefix, key)))
        return paths
    return {prefix}


class LocalizationContractTest(unittest.TestCase):
    """Ensure localization cannot silently regress to hard-coded German."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.catalogs = {
            language: json.loads(
                (COMPONENT / "translations" / f"{language}.json").read_text(
                    encoding="utf-8"
                )
            )
            for language in ("de", "en")
        }

    def test_catalogs_have_identical_leaf_keys(self) -> None:
        self.assertEqual(
            leaf_paths(self.catalogs["de"]),
            leaf_paths(self.catalogs["en"]),
        )

    def test_every_public_parameter_has_sensor_and_number_name(self) -> None:
        for parameter in const.PARAMETERS:
            if parameter.get("internal"):
                continue
            key = localization.parameter_translation_key(parameter)
            for language, catalog in self.catalogs.items():
                with self.subTest(language=language, parameter=parameter["name"]):
                    self.assertTrue(
                        catalog["entity"]["sensor"][key]["name"].strip()
                    )
                    self.assertTrue(
                        catalog["entity"]["number"][key]["name"].strip()
                    )

    def test_select_states_cover_every_neutral_option(self) -> None:
        for slug, translation_key in localization.SELECT_TRANSLATION_KEYS.items():
            # The WTC-integrated bus-0 circuit is always a heating circuit.
            # Bus 1/2 can be heating or hot-water depending on capabilities.
            hot_water = slug in ("hk1_user_op_mode", "hk2_user_op_mode")
            for language, catalog in self.catalogs.items():
                states = catalog["entity"]["select"][translation_key]["state"]
                possible = set(
                    localization.select_option_map(
                        translation_key,
                        hot_water=hot_water,
                    ).values()
                )
                with self.subTest(language=language, select=translation_key):
                    self.assertTrue(possible <= states.keys())

    def test_entity_platforms_do_not_set_hard_coded_names(self) -> None:
        for filename in ("sensor.py", "number.py", "select.py", "calendar.py"):
            source = (COMPONENT / filename).read_text(encoding="utf-8")
            with self.subTest(filename=filename):
                self.assertNotIn("_attr_name =", source)

    def test_diagnostics_documents_correct_physical_bus_mapping(self) -> None:
        source = (COMPONENT / "diagnostics.py").read_text(encoding="utf-8")
        self.assertIn('"0": "WTC-HK1 / FS1"', source)
        self.assertIn('"1": "EM-HK2 / radiators"', source)
        self.assertIn('"2": "EM-HK3 / underfloor heating"', source)
        self.assertNotIn("password", source.lower())

    def test_wtc_hc1_sensor_has_explicit_heating_mode_readback(self) -> None:
        source = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
        self.assertIn('self._sensor_name.startswith("WTC HK1")', source)
        self.assertIn('SELECT_OPTION_KEYS["heating_operating_mode"]', source)

    def test_user_visible_surfaces_exist_in_both_languages(self) -> None:
        for language, catalog in self.catalogs.items():
            with self.subTest(language=language):
                self.assertEqual(len(catalog["exceptions"]), 10)
                self.assertEqual(len(catalog["services"]), 4)
                self.assertIn("user", catalog["config"]["step"])
                self.assertIn("init", catalog["options"]["step"])


if __name__ == "__main__":
    unittest.main()
