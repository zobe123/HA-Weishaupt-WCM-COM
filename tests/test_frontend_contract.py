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
        self.assertIn('vol.Optional("cache_only"', backend)
        self.assertIn('"cache_age_seconds"', backend)
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

    def test_panel_and_card_escape_every_dynamic_render_path(self) -> None:
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

            const attack = (field) =>
              `$&<img data-field="${field}" src=x onerror="globalThis.xss=1">'&`;
            const escape = (value) => String(value)
              .replaceAll("&", "&amp;")
              .replaceAll("<", "&lt;")
              .replaceAll(">", "&gt;")
              .replaceAll('"', "&quot;")
              .replaceAll("'", "&#39;");
            const attacks = Object.fromEntries([
              "title", "overviewLabel", "overviewSubtitle", "overviewError",
              "overviewBadge", "timelineStart", "timelineEnd", "modeSummary",
              "meterName", "meterState", "meterUnit", "status", "optionValue",
              "optionLabel",
            ].map((field) => [field, attack(field)]));
            const days = [
              "monday", "tuesday", "wednesday", "thursday", "friday",
              "saturday", "sunday",
            ];
            const hostileSchedule = Object.fromEntries(days.map((day) => [
              day, [[attacks.timelineStart, attacks.timelineEnd]],
            ]));

            const assertEscaped = (elementName, view, html, fields) => {
              if (html.includes("<img") || globalThis.xss) {
                throw new Error(`${elementName} ${view} rendered hostile markup`);
              }
              for (const field of fields) {
                if (!html.includes(escape(attacks[field]))) {
                  throw new Error(`${elementName} ${view} did not escape ${field}`);
                }
              }
            };

            for (const elementName of [
              "weishaupt-time-program-panel",
              "weishaupt-time-program-card",
            ]) {
              const Element = customElements.get(elementName);
              const element = new Element();
              element.localName = elementName;
              element._hass = { language: "en" };
              element._config = { title: attacks.title };
              element._info = {
                allow_write: true,
                circuits: {
                  "0": { active_program: null, mode: attacks.modeSummary },
                },
                program_buses: { hot_water: 0, circulation: 0 },
                circulation_supported: true,
                external_gas_meter: {
                  name: attacks.meterName,
                  state: attacks.meterState,
                  unit: attacks.meterUnit,
                },
              };

              element._view = "overview";
              element._overview = [
                {
                  circuit: 0,
                  program: null,
                  editorProgram: "heating_1",
                  label: attacks.overviewLabel,
                  subtitle: attacks.overviewSubtitle,
                  mode: attacks.overviewBadge,
                  kind: "heating",
                  schedule: null,
                  loading: false,
                  error: attacks.overviewError,
                  ageSeconds: null,
                },
                {
                  circuit: 1,
                  program: "heating_1",
                  editorProgram: "heating_1",
                  label: "Timeline",
                  subtitle: "Timeline",
                  mode: "program_1",
                  kind: "heating",
                  schedule: hostileSchedule,
                  loading: false,
                  error: "",
                  ageSeconds: 0,
                },
              ];
              element._render();
              assertEscaped(elementName, "overview", element.shadowRoot.innerHTML, [
                "title", "overviewLabel", "overviewSubtitle", "overviewError",
                "overviewBadge", "timelineStart", "timelineEnd",
              ]);

              element._view = "editor";
              element._target = { circuit: 0, program: "heating_1" };
              element._schedule = {};
              element._status = attacks.status;
              element._targets = () => [{
                circuit: 0,
                program: attacks.optionValue,
                label: attacks.optionLabel,
              }];
              element._render();
              assertEscaped(elementName, "editor", element.shadowRoot.innerHTML, [
                "title", "modeSummary", "meterName", "meterState", "meterUnit",
                "status", "optionValue", "optionLabel",
              ]);
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

    def test_overview_loads_active_programs_from_cache_and_groups_days(self) -> None:
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

            const schedule = Object.fromEntries([
              "monday", "tuesday", "wednesday", "thursday", "friday",
              "saturday", "sunday",
            ].map((day) => [day, [["06:00", "22:00"]]]));
            const requests = [];
            const Element = customElements.get("weishaupt-time-program-panel");
            const element = new Element();
            element.localName = "weishaupt-time-program-panel";
            element._hass = {
              language: "de",
              callWS: async (request) => {
                requests.push(request);
                if (!request.cache_only) {
                  throw new Error("fresh cache entries must not trigger live reads");
                }
                return {
                  schedule,
                  cache_age_seconds: 12,
                  cache_fresh: true,
                };
              },
            };
            element._info = {
              entry_id: "entry",
              allow_write: true,
              circulation_supported: false,
              circuits: {
                "0": { active_program: null, mode: "summer" },
                "1": { active_program: "heating_1", mode: "program_1" },
                "2": { active_program: "heating_1", mode: "program_1" },
              },
              program_buses: { hot_water: 0, circulation: 0 },
              external_gas_meter: {
                name: "HIDDEN GAS METER",
                state: "1234",
                unit: "m³",
              },
            };

            (async () => {
              await element._loadOverview();
              const html = element.shadowRoot.innerHTML;
              for (const text of [
                "WTC-HK1 / FS1", "HK2 Radiatoren / FS2", "HK3 FBH / FS3",
                "Warmwasser", "Sommer ⛱️", "Mo–So", "06:00–22:00",
              ]) {
                if (!html.includes(text)) throw new Error(`overview misses ${text}`);
              }
              const mondayNoon = new Date(2026, 10, 2, 12, 0);
              const mondayNight = new Date(2026, 10, 2, 23, 0);
              const program = { program: "heating_1", mode: "program_1", schedule };
              if (element._overviewBadge(program, mondayNoon) !== "P1 aktiv ☀️") {
                throw new Error("active heating interval misses sun symbol");
              }
              if (element._overviewBadge(program, mondayNight) !== "P1 aktiv 🌙") {
                throw new Error("reduced heating interval misses moon symbol");
              }
              for (const [mode, expected] of [
                ["normal", "Normal ☀️"], ["reduced", "Absenk 🌙"],
                ["standby", "Standby ⏻"], ["summer", "Sommer ⛱️"],
                ["control_center", "Wie Leitstelle"],
              ]) {
                if (element._overviewBadge({ program: null, mode }, mondayNoon) !== expected) {
                  throw new Error(`wrong badge for ${mode}`);
                }
              }
              if (html.includes("HIDDEN GAS METER") || html.includes("mode-pills")) {
                throw new Error("overview still renders removed summary content");
              }
              if (requests.length !== 3 || requests.some((request) => !request.cache_only)) {
                throw new Error(`unexpected overview requests: ${JSON.stringify(requests)}`);
              }
              if (requests.some((request) => request.heating_circuit === 0 && request.program?.startsWith("heating_"))) {
                throw new Error("inactive heating circuit was queried");
              }
            })().catch((error) => {
              console.error(error);
              process.exitCode = 1;
            });
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
