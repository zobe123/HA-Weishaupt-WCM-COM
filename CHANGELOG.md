# Changelog

Release notes are written for Home Assistant and HACS: short headings, concise
bullet points, and no raw commit list. Before creating a version tag, replace
`Unreleased` with the exact version number used by the tag.

## [1.4.4]

### Fixed

- Show a translated message when setup is aborted because the WCM-COM is
  already configured.
- Move legacy connection settings out of config-entry options so updated
  credentials cannot be shadowed by stale values.
- Schedule exactly one reload after successful reauthentication or options
  changes.
- Close the options dialog immediately after saving instead of waiting for the
  slow WCM-COM config-entry reload to finish.
- Keep connection validation synchronous only when host or credentials were
  actually changed; the required integration reload then continues in the
  background.

### Improved

- Skip the WCM-COM connection check when only operational options change.
- Explain that changed connection settings are verified and that a new IP
  address can take a few minutes to respond.

### Tests

- Add behavioral Home Assistant config-flow coverage for duplicate setup,
  authentication failures, legacy migration and reload scheduling.
- Distinguish options-only updates from connection reconfiguration in the
  Home Assistant flow tests.
- Verify that an options update returns while its scheduled reload is still
  running.

## [1.4.3]

### Improved

- Trigger Home Assistant's reauthentication flow immediately when WCM-COM
  rejects stored credentials, and distinguish invalid credentials from an
  unreachable controller during setup and reconfiguration.
- Prevent duplicate config entries for the same normalized host and migrate
  existing entries to the same stable config-entry identity.
- Mask password inputs in setup, reauthentication and options forms.
- Declare the integration as a hub and align the documented Home Assistant and
  Python minimum versions with the APIs used by the integration.

## [1.4.2]

### New

- Added a read-only WCM-COM firmware update entity showing the installed and
  latest version reported by the official Weishaupt update service.
- Check for new device firmware once per day and on manual entity refresh,
  serialized with normal polling to protect the WCM-COM web server.

### Safety

- Firmware installation is intentionally not exposed because the controller
  update process can reset network settings.

## [1.4.1]

### Fixed

- Use the WCM-COM standard telegram type for all parameter writes so changes
  are persisted by controllers that reject generic write telegrams.
- Validate the saved time-program day before changing it and verify that an
  automatic rollback restored the exact original values after a failed write.
- Group domestic-hot-water controls, temperatures and schedules with the
  boiler instead of the room-heating circuits, while preserving stable IDs.
- Hide the duplicate FS2/FS3 hot-water setpoint controls from normal UI
  surfaces without deleting their history or automation access.
- Disable technical FS hot-water control/readback duplicates, omit unsupported
  zero/unknown temperature sensors and label calendars as time programs.

## [1.4.0]

### Fixed

- Corrected the physical bus mapping: bus 0 is WTC-HC1 / FS1, bus 1 is HC2
  radiators, and bus 2 is HC3 underfloor heating.
- Added a dedicated readable and writable WTC-HC1 operating-mode entity that
  sends parameter 274 exclusively to bus 0 / FS module 6.
- Separated WTC/boiler process values from the integrated WTC heating circuit
  in Home Assistant's device view.
- Gave FS1 the same supported configuration, setpoint, optimisation, frost,
  room and holiday entities as FS2/FS3, while keeping EM-only values on the
  two extension-module circuits.
- Decoded the WTC-integrated heating-circuit type with its bus-0 high-byte
  wire format and suppresses unsupported FS1 expert controls cleanly.
- Kept global burner, boiler, domestic-hot-water and plant values on the
  dedicated WTC / boiler device.
- Shortened the four Home Assistant device names so their distinguishing
  circuit or boiler label remains fully visible on narrow mobile screens.
- Removed repeated circuit names from entities shown inside a circuit device;
  the device supplies the context while entity rows stay short and readable.
- Hid redundant read-only sensor counterparts of writable controls from normal
  UI surfaces without deleting their stable IDs, history or automation access.

### Compatibility

- Preserved every existing bus-1/bus-2 unique ID and device identifier; only
  their displayed physical circuit names change.
- Added regression coverage for bus-0 readback, all operating-mode options,
  the bus-0 write target, FS-core symmetry, EM separation and legacy IDs.

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
