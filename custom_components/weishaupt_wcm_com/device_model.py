"""Stable device routing for boiler and heating-circuit entities."""

from __future__ import annotations

from typing import Any

from .const import DOMAIN


def device_descriptor(parameter_name: str) -> tuple[str, str]:
    """Return a stable registry identifier and the corrected display name.

    The legacy ``HK1`` and ``HK2`` prefixes are deliberately retained in
    parameter names and unique IDs.  They historically represented bus 1 and
    bus 2, so changing them would silently break existing dashboards.  Only
    their displayed circuit numbering is corrected here.
    """

    if parameter_name.startswith("WTC HK1 ") or parameter_name == "Kessel Config Version FS":
        return "weishaupt_wtc_hk1", "Weishaupt WCM-COM · WTC-HK1 / FS1"
    if parameter_name.startswith("HK1 "):
        return "weishaupt_hk1", "Weishaupt WCM-COM · HK2 Radiatoren / FS2"
    if parameter_name.startswith("HK2 "):
        return "weishaupt_hk2", "Weishaupt WCM-COM · HK3 FBH / FS3"
    return "weishaupt_kessel", "Weishaupt WCM-COM · WTC / Therme-Kessel"


def device_info(parameter_name: str, *, sw_version: str | None = None) -> dict[str, Any]:
    """Build Home Assistant device information without changing identifiers."""

    identifier, name = device_descriptor(parameter_name)
    info: dict[str, Any] = {
        "identifiers": {(DOMAIN, identifier)},
        "name": name,
        "manufacturer": "Weishaupt",
        "model": "WCM-COM",
    }
    if sw_version:
        info["sw_version"] = sw_version
    return info
