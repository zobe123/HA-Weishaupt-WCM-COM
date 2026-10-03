"""Temperature value normalization for WCM-COM telegrams."""

from collections.abc import Mapping


INVALID_TEMPERATURE_SENTINEL = -3276.8
CIRCULATION_TEMPERATURE_PARAMETER_ID = 1257
CIRCULATION_TEMPERATURE_SENTINEL = -100.0


def normalize_temperature_value(
    *,
    parameter_id: int,
    parameter_name: str,
    value: float,
    previous_values: Mapping[str, object],
) -> tuple[object, bool]:
    """Return a usable value and whether an unexpected value should be logged."""

    is_expected_sentinel = value == INVALID_TEMPERATURE_SENTINEL or (
        parameter_id == CIRCULATION_TEMPERATURE_PARAMETER_ID
        and value == CIRCULATION_TEMPERATURE_SENTINEL
    )

    if is_expected_sentinel:
        return previous_values.get(parameter_name), False

    if value < -50 or value > 150:
        return previous_values.get(parameter_name), True

    return value, False
