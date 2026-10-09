"""Dependency-light helpers for WCM-COM CoCo telegrams."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping, Sequence
from typing import Any


READ_COMMAND = 1
WRITE_COMMAND = 2
STANDARD_TELEGRAM = 0
GENERIC_TELEGRAM = 1


def parameter_group(parameter: Mapping[str, Any]) -> int:
    """Return the WebUI update group used to sequence parameter requests.

    The eighth ``OBJTELEGRAMM`` constructor argument is an internal browser
    update group.  It is not transmitted in the CoCo telegram.  Standard read
    telegrams always use type 0 in field five.
    """

    return int(parameter.get("request_group", 0))


def split_request_groups(
    parameters: Sequence[Mapping[str, Any]],
) -> list[list[Mapping[str, Any]]]:
    """Split parameters like the original WebUI: page, bus, then group."""

    groups: OrderedDict[tuple[str, int, int], list[Mapping[str, Any]]] = OrderedDict()
    for parameter in parameters:
        key = (
            str(parameter.get("page", "default")),
            int(parameter.get("bus", 0)),
            parameter_group(parameter),
        )
        groups.setdefault(key, []).append(parameter)
    return list(groups.values())


def resolve_response_parameter(
    requested_parameters: Sequence[Mapping[str, Any]],
    message: Sequence[Any],
) -> Mapping[str, Any] | None:
    """Resolve a response only within the request group that produced it."""

    if len(message) < 6:
        return None
    module_type = int(message[0])
    bus = int(message[1])
    parameter_id = int(message[3])
    candidates = [
        parameter
        for parameter in requested_parameters
        if int(parameter["id"]) == parameter_id
        and int(parameter.get("bus", 0)) == bus
        and int(parameter.get("modultyp", parameter.get("destination", 10)))
        == module_type
    ]
    return candidates[0] if len(candidates) == 1 else None


def user_mode_kind(capability_flags: int | None, bus: int) -> str | None:
    """Return which parameter-274 interpretation the original WebUI enables."""

    if capability_flags is None:
        return None
    if int(capability_flags) & 0x0040 and int(bus) != 0:
        return "ww"
    return "hk"


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
    combination. Parameters sharing the same address must use an exact name;
    request-group context resolves them while processing a response.
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

    if parameter_type in ("temperature", "temp_delta", "ratio_tenths"):
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
    telegram_type: int = STANDARD_TELEGRAM,
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
        int(telegram_type),
        int(value) & 0xFF,
        (int(value) >> 8) & 0xFF,
    ]
