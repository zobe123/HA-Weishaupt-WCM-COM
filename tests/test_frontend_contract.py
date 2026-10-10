"""Static contract checks for the bundled time-program panel."""

import ast
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "weishaupt_wcm_com"


class FrontendContractTest(unittest.TestCase):
    """Keep backend registration and the shipped custom element aligned."""

    def test_frontend_python_parses(self) -> None:
        ast.parse((COMPONENT / "frontend.py").read_text(encoding="utf-8"))

    def test_panel_element_and_file_match_registration(self) -> None:
        backend = (COMPONENT / "frontend.py").read_text(encoding="utf-8")
        panel = (
            COMPONENT / "frontend" / "weishaupt-time-program-panel.js"
        ).read_text(encoding="utf-8")
        self.assertIn('PANEL_ELEMENT = "weishaupt-time-program-panel"', backend)
        self.assertIn('CARD_ELEMENT = "weishaupt-time-program-card"', backend)
        self.assertIn('PANEL_FILE = "weishaupt-time-program-panel.js"', backend)
        self.assertIn(
            'customElements.define("weishaupt-time-program-panel"', panel
        )
        self.assertIn(
            'customElements.define("weishaupt-time-program-card"', panel
        )
        self.assertIn("frontend.add_extra_js_url", backend)
        self.assertIn("frontend.remove_extra_js_url", backend)
        self.assertIn('sidebar_title="WCM-COM"', backend)
        self.assertNotIn('sidebar_title="Weishaupt Zeitprogramme"', backend)

    def test_time_program_options_are_translated(self) -> None:
        for language in ("de", "en"):
            translation = json.loads(
                (COMPONENT / "translations" / f"{language}.json").read_text(
                    encoding="utf-8"
                )
            )
            fields = translation["options"]["step"]["init"]["data"]
            for option in (
                "show_time_program_panel",
                "expose_time_program_calendars",
                "external_gas_meter_entity",
            ):
                self.assertIn(option, fields)

    def test_manifest_loads_panel_dependencies(self) -> None:
        manifest = json.loads(
            (COMPONENT / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            set(manifest["dependencies"]),
            {"http", "panel_custom", "websocket_api"},
        )


if __name__ == "__main__":
    unittest.main()
