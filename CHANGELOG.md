# Changelog

Release notes are written for Home Assistant and HACS: short headings, concise
bullet points, and no raw commit list. Before creating a version tag, replace
`Unreleased` with the exact version number used by the tag.

## [1.3.0]

### New

- Added complete German and English translations for setup, options, entities,
  entity states, calendars, actions, errors and the weekly-program editor.
- Added language-neutral internal entity and select-option keys so more
  languages can be added without changing Python code.

### Improved

- Existing entity unique IDs remain unchanged, preserving entity registry,
  history, dashboards and automations during the language migration.
- Entity and enum labels now follow each Home Assistant user's selected
  language instead of being hard-coded in German.
- Direct action calls using the previous German select labels remain accepted
  for backward compatibility.

### Quality

- Added localization-contract tests for complete and structurally identical
  German and English catalogs.

## [1.2.16b2]

### New

- Added an integration-provided weekly time-program panel with program/day
  selection, copy helpers and staged apply/discard controls.
- Added the same editor as a Lovelace card so it can sit beside the heating
  program selectors.
- Added options for the sidebar panel, Home Assistant calendar entities and an
  optional existing gas-meter entity.

### Improved

- Replaced the ten raw program calendars with active HK1/HK2 heating calendars
  and one global hot-water calendar.
- Circulation remains editable as an optional program but is exposed as a
  calendar only when the controller reports a usable circulation signal.
- The panel loads only the selected program to avoid parallel request bursts
  against the WCM-COM web server.
- A narrowly scoped retry handles a time-program value omitted once by the
  controller during the initial request burst.

## [1.2.15]

### New

- Added ten Home Assistant calendars for the HK1/HK2 heating, hot-water and
  circulation weekly programs.
- Added actions to set, copy and clear complete program days.

### Improved

- Time programs are loaded only when needed and cached to protect the small
  WCM-COM web server.
- Every changed day is validated, written atomically, read back and restored
  automatically if verification fails.
- Pump-voltage codes `0` to `3` now have their correct WebUI labels, including
  `Automatik Ein` for code `3`.

### Quality

- Added protocol, transaction, calendar and validation regression tests.

## [1.2.14]

### Fixed

- Hide unsupported heating-circuit settings instead of exposing unusable entities.
- Remove obsolete entity-registry entries for unsupported settings automatically.

### Quality

- Added regression coverage for controller-specific no-value markers.
