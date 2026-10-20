"""Static compatibility metadata checks."""

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "weishaupt_wcm_com"


class ConfigContractTest(unittest.TestCase):
    """Keep authentication, identity and compatibility metadata aligned."""

    def test_manifest_and_minimum_versions_match_used_apis(self) -> None:
        manifest = json.loads(
            (COMPONENT / "manifest.json").read_text(encoding="utf-8")
        )
        hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertEqual(manifest["integration_type"], "hub")
        self.assertTrue(manifest["single_config_entry"])
        self.assertEqual(manifest["version"], "1.4.5b1")
        self.assertEqual(hacs["homeassistant"], "2023.12.0")
        self.assertIn("Python 3.11 or higher", readme)
        self.assertIn("Apache License 2.0", readme)

    def test_duplicate_abort_reason_is_translated(self) -> None:
        for language in ("de", "en"):
            translations = json.loads(
                (COMPONENT / "translations" / f"{language}.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertIn("already_configured", translations["config"]["abort"])
            self.assertIn("description", translations["options"]["step"]["init"])


if __name__ == "__main__":
    unittest.main()
