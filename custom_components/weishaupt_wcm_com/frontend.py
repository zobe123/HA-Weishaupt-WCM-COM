"""Frontend panel and WebSocket API for WCM-COM weekly programs."""

from __future__ import annotations

from pathlib import Path

import voluptuous as vol

from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .localization import SELECT_OPTION_KEYS
from .time_program import (
    PROGRAM_NAMES,
    active_heating_program,
    circulation_supported,
    validate_program,
)

PANEL_URL_PATH = "weishaupt-time-programs"
PANEL_STATIC_URL = "/weishaupt_wcm_com_frontend"
PANEL_ELEMENT = "weishaupt-time-program-panel"
CARD_ELEMENT = "weishaupt-time-program-card"
PANEL_FILE = "weishaupt-time-program-panel.js"
DATA_FRONTEND = f"{DOMAIN}_frontend"


def _module_url() -> str:
    """Return a cache-busted URL for the bundled panel/card module."""

    module_path = Path(__file__).parent / "frontend" / PANEL_FILE
    return f"{PANEL_STATIC_URL}/{PANEL_FILE}?v={int(module_path.stat().st_mtime)}"


def _resolve_entry(hass: HomeAssistant, entry_id: str | None) -> tuple[str, dict]:
    """Resolve one loaded integration entry without guessing among several."""

    entries = hass.data.get(DOMAIN, {})
    if entry_id:
        if entry_id not in entries:
            raise ValueError(f"Unknown or unloaded config entry: {entry_id}")
        return entry_id, entries[entry_id]
    if len(entries) != 1:
        raise ValueError("entry_id is required when multiple WCM-COM entries are loaded")
    return next(iter(entries.items()))


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/time_programs/info",
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def websocket_time_program_info(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    """Return available editors and active operating modes."""

    try:
        entry_id, entry_data = _resolve_entry(hass, msg.get("entry_id"))
    except ValueError as err:
        connection.send_error(msg["id"], "not_found", str(err))
        return

    data = entry_data["coordinator"].data or {}
    gas_meter_entity = entry_data.get("external_gas_meter_entity") or None
    gas_meter = None
    if gas_meter_entity and (state := hass.states.get(gas_meter_entity)) is not None:
        gas_meter = {
            "entity_id": gas_meter_entity,
            "name": state.name,
            "state": state.state,
            "unit": state.attributes.get("unit_of_measurement"),
        }
    circuits = {}
    for circuit in (1, 2):
        raw_mode = data.get(f"HK{circuit} User Betriebsart")
        circuits[str(circuit)] = {
            "mode": SELECT_OPTION_KEYS["heating_operating_mode"].get(
                raw_mode, f"code_{raw_mode}"
            ),
            "active_program": active_heating_program(data, circuit),
        }

    connection.send_result(
        msg["id"],
        {
            "entry_id": entry_id,
            "allow_write": bool(entry_data.get("allow_write", False)),
            "circulation_supported": circulation_supported(data),
            "external_gas_meter": gas_meter,
            "circuits": circuits,
            "program_names": PROGRAM_NAMES,
        },
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/time_programs/get",
        vol.Optional("entry_id"): str,
        vol.Required("heating_circuit"): vol.All(vol.Coerce(int), vol.In((1, 2))),
        vol.Required("program"): str,
    }
)
@websocket_api.async_response
async def websocket_time_program_get(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    """Load one weekly program on demand."""

    try:
        entry_id, entry_data = _resolve_entry(hass, msg.get("entry_id"))
        program = validate_program(msg["program"])
        circuit = int(msg["heating_circuit"])
        if program in ("hot_water", "circulation"):
            circuit = 1
        schedule = await entry_data["time_program_manager"].async_get(
            circuit, program
        )
    except (ValueError, KeyError) as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    except Exception as err:  # pragma: no cover - surfaced to the panel
        connection.send_error(msg["id"], "home_assistant_error", str(err))
        return

    connection.send_result(
        msg["id"],
        {
            "entry_id": entry_id,
            "heating_circuit": circuit,
            "program": program,
            "schedule": {
                day: [list(interval) for interval in intervals]
                for day, intervals in schedule.items()
            },
        },
    )


async def async_register_frontend(
    hass: HomeAssistant,
    entry_id: str,
    *,
    show_panel: bool,
) -> None:
    """Register the optional panel, dashboard card and WebSocket API."""

    frontend_data = hass.data.setdefault(DATA_FRONTEND, {})
    if not frontend_data.get("commands"):
        websocket_api.async_register_command(hass, websocket_time_program_info)
        websocket_api.async_register_command(hass, websocket_time_program_get)
        frontend_data["commands"] = True

    if not frontend_data.get("static_path"):
        frontend_dir = Path(__file__).parent / "frontend"
        await hass.http.async_register_static_paths(
            [StaticPathConfig(PANEL_STATIC_URL, str(frontend_dir), False)]
        )
        frontend_data["static_path"] = True

    frontend_data.setdefault("entries", {})[entry_id] = bool(show_panel)

    module_url = _module_url()
    previous_module_url = frontend_data.get("module_url")
    if previous_module_url != module_url:
        if previous_module_url:
            frontend.remove_extra_js_url(hass, previous_module_url)
        frontend.add_extra_js_url(hass, module_url)
        frontend_data["module_url"] = module_url

    any_panel = any(frontend_data["entries"].values())
    if any_panel and not frontend.async_panel_exists(hass, PANEL_URL_PATH):
        await panel_custom.async_register_panel(
            hass=hass,
            frontend_url_path=PANEL_URL_PATH,
            webcomponent_name=PANEL_ELEMENT,
            module_url=module_url,
            sidebar_title="Weishaupt Zeitprogramme",
            sidebar_icon="mdi:calendar-clock",
            require_admin=True,
            embed_iframe=False,
        )
    elif not any_panel and frontend.async_panel_exists(hass, PANEL_URL_PATH):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)


def async_unregister_frontend(hass: HomeAssistant, entry_id: str) -> None:
    """Remove entry-specific frontend state and unused registrations."""

    frontend_data = hass.data.get(DATA_FRONTEND, {})
    entries = frontend_data.get("entries", {})
    entries.pop(entry_id, None)

    if not any(entries.values()) and frontend.async_panel_exists(hass, PANEL_URL_PATH):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)

    if not entries and (module_url := frontend_data.pop("module_url", None)):
        frontend.remove_extra_js_url(hass, module_url)
