"""Static contract checks for the bundled time-program panel."""

import ast
import json
from pathlib import Path
import shutil
import subprocess
import textwrap
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
        self.assertIn('vol.In((0, 1, 2))', backend)
        self.assertIn('circuit_0: "WTC-HC1 / FS1"', panel)
        self.assertIn("this._info.program_buses.hot_water", panel)
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

    def test_panel_and_card_escape_hostile_rendered_values(self) -> None:
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node.js is required for the frontend test")
        panel = COMPONENT / "frontend" / "weishaupt-time-program-panel.js"
        script = textwrap.dedent(
            r"""
            const fs = require("node:fs");
            const vm = require("node:vm");

            const registry = new Map();
            globalThis.HTMLElement = class {
              attachShadow() {
                this.shadowRoot = {
                  innerHTML: "",
                  querySelector: () => null,
                  querySelectorAll: () => [],
                };
              }
            };
            globalThis.customElements = {
              define: (name, constructor) => registry.set(name, constructor),
              get: (name) => registry.get(name),
            };
            globalThis.window = {};

            const panelPath = process.argv[1];
            vm.runInThisContext(fs.readFileSync(panelPath, "utf8"), {
              filename: panelPath,
            });

            const hostile = '$&<img src=x onerror="globalThis.xss=1">\'&';
            const escaped =
              "$&amp;&lt;img src=x onerror=&quot;globalThis.xss=1&quot;&gt;&#39;&amp;";

            for (const elementName of [
              "weishaupt-time-program-panel",
              "weishaupt-time-program-card",
            ]) {
              const Element = customElements.get(elementName);
              const element = new Element();
              element.localName = elementName;
              element._config = { title: hostile };
              element._info = {
                allow_write: true,
                circuits: { "0": { active_program: "heating_1", mode: hostile } },
                program_buses: { hot_water: 0, circulation: 0 },
                circulation_supported: true,
                external_gas_meter: {
                  name: hostile,
                  state: hostile,
                  unit: hostile,
                },
              };
              element._target = { circuit: 0, program: "heating_1" };
              element._status = hostile;
              element._targets = () => [
                { circuit: 0, program: hostile, label: hostile },
              ];

              if (element._t("load_failed", { error: hostile }) !== `Loading failed: ${hostile}`) {
                throw new Error(`${elementName} changed replacement-like message text`);
              }

              element._render();
              const html = element.shadowRoot.innerHTML;
              if (html.includes(hostile) || html.includes("<img")) {
                throw new Error(`${elementName} rendered hostile markup`);
              }
              if (!html.includes(escaped)) {
                throw new Error(`${elementName} did not render escaped hostile text`);
              }
            }
            """
        )
        result = subprocess.run(
            [node, "-e", script, str(panel)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
