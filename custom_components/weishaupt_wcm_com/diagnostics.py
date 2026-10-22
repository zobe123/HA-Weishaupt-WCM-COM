"""Diagnostics support for Weishaupt WCM-COM."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return bus-aware diagnostics without credentials or write capability."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator_data = entry_data["coordinator"].data or {}
    parameters = entry_data["parameters"]
    bus_parameters = [
        {
            "name": parameter["name"],
            "parameter": parameter["id"],
            "bus": parameter.get("bus", 0),
            "module": parameter.get(
                "modultyp", parameter.get("destination", 10)
            ),
        }
        for parameter in parameters
        if "bus" in parameter
        and (
            parameter["name"].startswith("WTC HK1 ")
            or parameter["name"].startswith("HK1 ")
            or parameter["name"].startswith("HK2 ")
        )
    ]

    return {
        "entry_state": entry.state.value,
        "requested_boiler_profile": entry_data["requested_profile"],
        "active_boiler_profile": entry_data["active_profile"],
        "detected_heating_circuit_buses": sorted(
            entry_data["active_heating_circuits"]
        ),
        "bus_mapping": {
            "0": "WTC-HK1 / FS1",
            "1": "HK2 radiators / FS2 + EM2",
            "2": "HK3 underfloor heating / FS3 + EM3",
        },
        "bus_parameters": bus_parameters,
        "coordinator_data": coordinator_data,
    }
