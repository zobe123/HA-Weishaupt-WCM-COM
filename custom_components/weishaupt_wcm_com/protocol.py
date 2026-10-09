"""Dependency-light helpers for WCM-COM CoCo telegrams."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


READ_COMMAND = 1
WRITE_COMMAND = 2


def parameter_protocol(parameter: Mapping[str, Any]) -> int:
    """Return the documented TEL_PROT value for a parameter."""

    return int(parameter.get("protocol", 0))


def resolve_parameter_metadata(
    parameters: Sequence[Mapping[str, Any]],
    *,
    name: str,
    parameter_id: int,
    bus: int,
    module_type: int,
) -> Mapping[str, Any]:
    """Resolve metadata by name first, then by a unique wire address.

    Some entities use a user-facing name that differs from the raw parameter
    name.  The fallback is intentionally limited to a unique ID/bus/module
    combination so parameters distinguished by TEL_PROT are never guessed.
    """

    candidates = [
        parameter
        for parameter in parameters
        if not parameter.get("virtual")
        and int(parameter["id"]) == int(parameter_id)
        and int(parameter.get("bus", 0)) == int(bus)
        and int(
            parameter.get("modultyp", parameter.get("destination", 10))
        )
        == int(module_type)
    ]

    named = [parameter for parameter in candidates if parameter["name"] == name]
    if len(named) == 1:
        return named[0]
    if len(candidates) == 1:
        return candidates[0]

    raise ValueError(
        f"Missing or ambiguous parameter metadata for {name} "
        f"(id={parameter_id}, bus={bus}, module_type={module_type})"
    )


def write_scale(parameter_type: str, parameter_id: int) -> float:
    """Return the multiplier from Home Assistant units to wire units."""

    if parameter_type in ("temperature", "temp_delta"):
        return 10.0
    if parameter_type == "percent" and parameter_id in (319, 345):
        return 10.0
    if parameter_id == 272:
        return 1.0 / 15.0
    return 1.0


def display_scale(parameter_id: int) -> float:
    """Return the multiplier from decoded API values to Home Assistant units."""

    if parameter_id == 272:
        return 15.0
    return 1.0


def encode_value(value: float, scale: float = 1.0) -> int:
    """Encode a Home Assistant value as the signed 16-bit wire integer."""

    encoded = int(round(float(value) * scale))
    if not -32768 <= encoded <= 65535:
        raise ValueError(f"Encoded WCM-COM value out of 16-bit range: {encoded}")
    return encoded


def build_telegram(
    *,
    module_type: int,
    bus: int,
    command: int,
    parameter_id: int,
    protocol: int = 0,
    index: int = 0,
    value: int = 0,
) -> list[int]:
    """Build one CoCo telegram using the original WebUI field order."""

    return [
        int(module_type),
        int(bus),
        int(command),
        int(parameter_id),
        int(index),
        int(protocol),
        int(value) & 0xFF,
        (int(value) >> 8) & 0xFF,
    ]
