"""Static regression checks for config-entry behavior and compatibility."""

import ast
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "weishaupt_wcm_com"


class ConfigContractTest(unittest.TestCase):
    """Keep authentication, identity and compatibility metadata aligned."""

    def test_config_flow_parses_and_supports_reauthentication(self) -> None:
        source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        methods = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        self.assertIn("async_step_reauth", methods)
        self.assertIn("async_step_reauth_confirm", methods)
        self.assertIn("await self.async_set_unique_id", source)
        self.assertIn("self._abort_if_unique_id_configured()", source)
        self.assertIn("TextSelectorType.PASSWORD", source)
        self.assertIn("VERSION = 5", source)

    def test_setup_maps_authentication_failure_to_home_assistant(self) -> None:
        source = (COMPONENT / "__init__.py").read_text(encoding="utf-8")

        self.assertIn("from homeassistant.const import CONF_HOST", source)
        self.assertIn("except WeishauptAuthenticationError as err:", source)
        self.assertIn("raise ConfigEntryAuthFailed", source)
        self.assertIn('update_kwargs["unique_id"] = normalize_host(host)', source)

    def test_manifest_and_minimum_versions_match_used_apis(self) -> None:
        manifest = json.loads(
            (COMPONENT / "manifest.json").read_text(encoding="utf-8")
        )
        hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertEqual(manifest["integration_type"], "hub")
        self.assertEqual(manifest["version"], "1.4.3b1")
        self.assertEqual(hacs["homeassistant"], "2023.12.0")
        self.assertIn("Python 3.11 or higher", readme)


if __name__ == "__main__":
    unittest.main()
