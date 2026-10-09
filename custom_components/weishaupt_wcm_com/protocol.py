"""Dependency-light helpers for WCM-COM CoCo telegrams."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


READ_COMMAND = 1
WRITE_COMMAND = 2


def parameter_protocol(parameter: Mapping[str, Any]) -> int:
    """Return the documented TEL_PROT value for a parameter."""

    return int(parameter.get("protocol", 0))


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
