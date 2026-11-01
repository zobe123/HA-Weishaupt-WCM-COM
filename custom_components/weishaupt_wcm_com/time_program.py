"""Helpers for WCM-COM weekly time programs.

The controller stores every interval as one 16-bit value. The high byte is
the start and the low byte is the end in 15-minute steps. ``128/128`` marks
an unused interval.
"""

from __future__ import annotations

from datetime import time
from typing import Iterable


WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)

PROGRAM_OFFSETS = {
    "heating_1": 0,
    "heating_2": 256,
    "heating_3": 512,
    "hot_water": 768,
    "circulation": 1536,
}

ACTIVE_HEATING_PROGRAMS = {
    11: "heating_1",
    12: "heating_2",
    13: "heating_3",
    "Programm 1": "heating_1",
    "Programm 2": "heating_2",
    "Programm 3": "heating_3",
}

HEATING_CIRCUIT_BUSES = (0, 1, 2)

DISABLED_QUARTER = 128
DISABLED_INTERVAL = (DISABLED_QUARTER << 8) | DISABLED_QUARTER


def validate_heating_circuit_bus(heating_circuit: int) -> int:
    """Return a physical WCM-FS bus or raise a useful error."""

    bus = int(heating_circuit)
    if bus not in HEATING_CIRCUIT_BUSES:
        raise ValueError("Heating-circuit bus must be 0, 1 or 2")
    return bus


def heating_circuit_prefix(heating_circuit: int) -> str:
    """Return the coordinator-data prefix for one physical WCM-FS bus."""

    bus = validate_heating_circuit_bus(heating_circuit)
    return "WTC HK1" if bus == 0 else f"HK{bus}"


def active_heating_program(data: dict, heating_circuit: int) -> str | None:
    """Return the selected weekly heating program, if one is active."""

    value = data.get(f"{heating_circuit_prefix(heating_circuit)} User Betriebsart")
    return ACTIVE_HEATING_PROGRAMS.get(value)


def circulation_supported(data: dict) -> bool:
    """Return whether the controller exposes a usable circulation signal.

    WCM devices retain a factory circulation schedule even when no circulation
    pump is configured. A real circulation measurement is therefore a safer
    capability signal than the mere presence of the time-program parameters.
    """

    return any(
        data.get(f"{heating_circuit_prefix(bus)} Zirkulationstemperatur")
        is not None
        for bus in HEATING_CIRCUIT_BUSES
    )


def _active_buses(active_buses) -> tuple[int, ...]:
    """Normalize discovered buses without silently accepting unknown values."""

    buses = tuple(
        sorted({validate_heating_circuit_bus(bus) for bus in active_buses})
    )
    if not buses:
        raise ValueError("No active heating-circuit bus is available")
    return buses


def domestic_hot_water_program_bus(active_buses, data: dict) -> int:
    """Return the FS bus that owns the domestic-hot-water program.

    An FS explicitly configured as the hot-water controller wins.  Otherwise
    the integrated WTC-HK1/FS1 on bus 0 is authoritative when present, matching
    the original WCM-COM WebUI and the canonical hot-water controls.
    """

    buses = _active_buses(active_buses)
    for bus in buses:
        prefix = heating_circuit_prefix(bus)
        if data.get(f"{prefix} User Mode Kind") == "ww":
            return bus
    if 0 in buses:
        return 0
    return buses[0]


def circulation_program_bus(active_buses, data: dict) -> int:
    """Return the FS bus with the detected circulation installation."""

    buses = _active_buses(active_buses)
    for bus in buses:
        prefix = heating_circuit_prefix(bus)
        if data.get(f"{prefix} Zirkulationstemperatur") is not None:
            return bus
    return domestic_hot_water_program_bus(buses, data)


def resolve_time_program_bus(
    active_buses,
    data: dict,
    requested_bus: int,
    program: str,
) -> int:
    """Resolve one program to its detected physical FS bus."""

    buses = _active_buses(active_buses)
    program = validate_program(program)
    if program == "hot_water":
        return domestic_hot_water_program_bus(buses, data)
    if program == "circulation":
        return circulation_program_bus(buses, data)

    bus = validate_heating_circuit_bus(requested_bus)
    if bus not in buses:
        raise ValueError(f"Heating-circuit bus {bus} was not detected")
    return bus


def validate_program(program: str) -> str:
    """Return a normalized program key or raise a useful error."""

    normalized = str(program).lower()
    if normalized not in PROGRAM_OFFSETS:
        raise ValueError(
            f"Unsupported time program '{program}'; expected one of "
            f"{', '.join(PROGRAM_OFFSETS)}"
        )
    return normalized


def validate_weekday(day: str) -> str:
    """Return a normalized weekday key or raise a useful error."""

    normalized = str(day).lower()
    if normalized not in WEEKDAYS:
        raise ValueError(
            f"Unsupported weekday '{day}'; expected one of {', '.join(WEEKDAYS)}"
        )
    return normalized


def parameter_ids(program: str, day: str) -> tuple[int, int, int]:
    """Return the three WCM parameter IDs for one program day."""

    program = validate_program(program)
    day = validate_weekday(day)
    base = 5136 + WEEKDAYS.index(day) * 16 + PROGRAM_OFFSETS[program]
    return base, base + 1, base + 2


def request_groups(program: str) -> tuple[tuple[int, ...], ...]:
    """Return parameter IDs in the same three groups as the original WebUI."""

    validate_program(program)
    return (
        tuple(
            parameter_id
            for day in WEEKDAYS[:2]
            for parameter_id in parameter_ids(program, day)
        ),
        tuple(
            parameter_id
            for day in WEEKDAYS[2:4]
            for parameter_id in parameter_ids(program, day)
        ),
        tuple(
            parameter_id
            for day in WEEKDAYS[4:]
            for parameter_id in parameter_ids(program, day)
        ),
    )


def _quarter(value: time | str) -> int:
    """Encode a time as a quarter-hour index."""

    if isinstance(value, str):
        parts = value.split(":")
        if len(parts) not in (2, 3):
            raise ValueError(f"Invalid time '{value}'; expected HH:MM")
        try:
            hour, minute = int(parts[0]), int(parts[1])
        except ValueError as err:
            raise ValueError(f"Invalid time '{value}'; expected HH:MM") from err
    elif isinstance(value, time):
        hour, minute = value.hour, value.minute
    else:
        raise ValueError(f"Invalid time value: {value!r}")

    if hour == 24 and minute == 0:
        return 96
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError(f"Time outside supported range: {value}")
    if minute % 15:
        raise ValueError(f"Time must use 15-minute steps: {value}")
    return hour * 4 + minute // 15


def format_quarter(quarter: int) -> str:
    """Format a quarter-hour index as HH:MM (including 24:00)."""

    if not 0 <= int(quarter) <= 96:
        raise ValueError(f"Quarter-hour index outside supported range: {quarter}")
    hour, part = divmod(int(quarter), 4)
    return f"{hour:02d}:{part * 15:02d}"


def encode_interval(start: time | str, end: time | str) -> int:
    """Encode and validate one active interval."""

    start_quarter = _quarter(start)
    end_quarter = _quarter(end)
    if start_quarter >= end_quarter:
        raise ValueError(f"Interval end must be after start: {start}-{end}")
    if start_quarter == 96:
        raise ValueError("An interval cannot start at 24:00")
    return (start_quarter << 8) | end_quarter


def decode_interval(value: int) -> tuple[str, str] | None:
    """Decode one wire value into an interval, or ``None`` when disabled."""

    raw = int(value)
    start_quarter = (raw >> 8) & 0xFF
    end_quarter = raw & 0xFF
    if start_quarter == DISABLED_QUARTER and end_quarter == DISABLED_QUARTER:
        return None
    if not 0 <= start_quarter <= 95 or not 1 <= end_quarter <= 96:
        raise ValueError(f"Invalid WCM time-program value: {raw}")
    if start_quarter >= end_quarter:
        raise ValueError(f"Invalid WCM interval order: {raw}")
    return format_quarter(start_quarter), format_quarter(end_quarter)


def encode_day(
    intervals: Iterable[tuple[time | str, time | str]],
) -> tuple[int, int, int]:
    """Validate and encode up to three non-overlapping daily intervals."""

    encoded = [encode_interval(start, end) for start, end in intervals]
    if len(encoded) > 3:
        raise ValueError("A WCM time program supports at most three intervals per day")

    decoded = [decode_interval(value) for value in encoded]
    for previous, current in zip(decoded, decoded[1:]):
        assert previous is not None and current is not None
        if _quarter(current[0]) < _quarter(previous[1]):
            raise ValueError("Time-program intervals must not overlap")

    return tuple(encoded + [DISABLED_INTERVAL] * (3 - len(encoded)))  # type: ignore[return-value]


def decode_day(values: Iterable[int]) -> tuple[tuple[str, str], ...]:
    """Decode the three WCM values for a day."""

    raw_values = tuple(values)
    if len(raw_values) != 3:
        raise ValueError("Exactly three WCM interval values are required")
    intervals = [decode_interval(value) for value in raw_values]
    active = tuple(interval for interval in intervals if interval is not None)
    # Reuse the encoder for ordering/overlap validation.
    encode_day(active)
    return active
