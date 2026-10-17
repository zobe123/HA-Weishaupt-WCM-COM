"""Stable device routing for boiler and heating-circuit entities."""

from __future__ import annotations

from typing import Any

from .const import DOMAIN


HOT_WATER_MARKERS = ("Warmwasser", "Zirkulation")


def is_hot_water_parameter(parameter_name: str) -> bool:
    """Return whether a parameter belongs to domestic hot water."""

    return (
        "WW" in parameter_name.split()
        or any(marker in parameter_name for marker in HOT_WATER_MARKERS)
    )


def is_duplicate_hot_water_control(parameter_name: str) -> bool:
    """Return whether an FS2/FS3 control duplicates the canonical FS1 one."""

    return (
        parameter_name.startswith(("HK1 ", "HK2 "))
        and parameter_name.endswith(("Normal WW Soll", "Absenk WW Soll"))
    )


def is_hot_water_readback_duplicate(parameter_name: str) -> bool:
    """Return whether a sensor only mirrors a writable hot-water control."""

    return parameter_name.endswith(("Normal WW Soll", "Absenk WW Soll"))


def device_descriptor(
    parameter_name: str, *, hot_water: bool = False
) -> tuple[str, str]:
    """Return a stable registry identifier and the corrected display name.

    The legacy ``HK1`` and ``HK2`` prefixes are deliberately retained in
    parameter names and unique IDs.  They historically represented bus 1 and
    bus 2, so changing them would silently break existing dashboards.  Only
    their displayed circuit numbering is corrected here.
    """

    if hot_water or is_hot_water_parameter(parameter_name):
        return "weishaupt_kessel", "Therme / Kessel"
    if parameter_name.startswith("WTC HK1 ") or parameter_name == "Kessel Config Version FS":
        return "weishaupt_wtc_hk1", "HK1 · WTC / FS1"
    if parameter_name.startswith("HK1 "):
        return "weishaupt_hk1", "HK2 · Radiatoren / FS2"
    if parameter_name.startswith("HK2 "):
        return "weishaupt_hk2", "HK3 · FBH / FS3"
    return "weishaupt_kessel", "Therme / Kessel"


def device_info(
    parameter_name: str,
    *,
    sw_version: str | None = None,
    hot_water: bool = False,
) -> dict[str, Any]:
    """Build Home Assistant device information without changing identifiers."""

    identifier, name = device_descriptor(parameter_name, hot_water=hot_water)
    info: dict[str, Any] = {
        "identifiers": {(DOMAIN, identifier)},
        "name": name,
        "manufacturer": "Weishaupt",
        "model": "WCM-COM",
    }
    if sw_version:
        info["sw_version"] = sw_version
    return info
