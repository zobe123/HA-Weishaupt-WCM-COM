# Changelog

Release notes are written for Home Assistant and HACS: short headings, concise
bullet points, and no raw commit list. Before creating a version tag, replace
`Unreleased` with the exact version number used by the tag.

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
