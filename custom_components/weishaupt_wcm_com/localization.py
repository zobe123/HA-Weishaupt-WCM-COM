"""Language-neutral keys for entities and controller enum values."""

from __future__ import annotations

from typing import Any


_VIRTUAL_PARAMETER_KEYS = {
    "Kessel Config Version FS": "boiler_firmware_fs",
    "HK1 Config Version FS": "hc1_firmware_fs",
    "HK2 Config Version FS": "hc2_firmware_fs",
    "HK1 Config Version EM": "hc1_firmware_em",
    "HK2 Config Version EM": "hc2_firmware_em",
    "System Date": "system_date",
    "System Time": "system_time",
    "HK1 Holiday Start": "hc1_holiday_start",
    "HK1 Holiday End": "hc1_holiday_end",
    "HK1 Urlaubstemperaturniveau": "hc1_holiday_temperature_level",
    "HK2 Holiday Start": "hc2_holiday_start",
    "HK2 Holiday End": "hc2_holiday_end",
    "HK2 Urlaubstemperaturniveau": "hc2_holiday_temperature_level",
    "DST Start": "daylight_saving_start",
    "DST End": "daylight_saving_end",
}


def parameter_translation_key(parameter: dict[str, Any]) -> str:
    """Return a stable, language-neutral translation key for a parameter."""

    parameter_id = int(parameter["id"])
    if parameter_id == 0:
        return _VIRTUAL_PARAMETER_KEYS[str(parameter["name"])]
    bus = int(parameter.get("bus", 0))
    module = int(parameter.get("modultyp", parameter.get("destination", 10)))
    return f"parameter_b{bus}_m{module}_p{parameter_id}"


SELECT_TRANSLATION_KEYS = {
    "hk1_config_hk_type": "hc1_type",
    "hk1_config_regelvariante": "hc1_control_variant",
    "hk1_config_ext_room_sensor": "hc1_external_room_sensor",
    "hk2_config_hk_type": "hc2_type",
    "hk2_config_regelvariante": "hc2_control_variant",
    "hk2_config_ext_room_sensor": "hc2_external_room_sensor",
    "hk1_user_op_mode": "hc1_operating_mode",
    "hk2_user_op_mode": "hc2_operating_mode",
    "hk1_expert_reduced_mode": "hc1_reduced_mode",
    "hk2_expert_reduced_mode": "hc2_reduced_mode",
    "hk1_expert_room_thermostat": "hc1_room_thermostat",
    "hk2_expert_room_thermostat": "hc2_room_thermostat",
    "hk1_urlaubstemperaturniveau": "hc1_holiday_temperature_level",
    "hk2_urlaubstemperaturniveau": "hc2_holiday_temperature_level",
}


SELECT_OPTION_KEYS = {
    "hc_type": {
        0: "not_available",
        1: "external_room_sensor",
        2: "internal_room_sensor",
        3: "not_available",
        4: "inside_boiler",
    },
    "control_variant": {
        0: "floor_warming",
        1: "underfloor_heating",
        2: "radiator_60",
        3: "radiator_75",
        4: "convector",
        5: "universal",
    },
    "external_room_sensor": {
        0: "constant_flow",
        1: "weather_compensated",
        2: "weather_and_room_compensated",
        3: "room_compensated",
    },
    "heating_operating_mode": {
        11: "program_1",
        12: "program_2",
        13: "program_3",
        1: "standby",
        5: "summer",
        4: "reduced",
        3: "normal",
        255: "control_center",
    },
    "hot_water_operating_mode": {
        11: "hot_water_program",
        1: "standby",
        4: "reduced",
        3: "normal",
        255: "control_center",
    },
    "reduced_mode": {0: "frost_protection", 1: "reduced_operation"},
    "room_thermostat": {
        0: "off",
        1: "day_on",
        2: "one_kelvin",
        3: "two_kelvin",
        4: "three_kelvin",
    },
    "holiday_temperature_level": {
        0: "frost_protection",
        1: "reduced_temperature",
    },
}


def select_option_map(translation_key: str, *, hot_water: bool = False) -> dict[int, str]:
    """Return neutral option values for a translated select entity."""

    if translation_key.endswith("_type"):
        family = "hc_type"
    elif translation_key.endswith("_control_variant"):
        family = "control_variant"
    elif translation_key.endswith("_external_room_sensor"):
        family = "external_room_sensor"
    elif translation_key.endswith("_operating_mode"):
        family = "hot_water_operating_mode" if hot_water else "heating_operating_mode"
    elif translation_key.endswith("_reduced_mode"):
        family = "reduced_mode"
    elif translation_key.endswith("_room_thermostat"):
        family = "room_thermostat"
    elif translation_key.endswith("_holiday_temperature_level"):
        family = "holiday_temperature_level"
    else:
        raise KeyError(f"Unknown select translation key: {translation_key}")
    return SELECT_OPTION_KEYS[family]


SENSOR_ENUM_MAPS: dict[str, dict[int, str]] = {
    "HK1 Config Pump": {0: "stepped"},
    "HK2 Config Pump": {0: "stepped"},
    "HK1 Config Voltage": {
        0: "manual_off",
        1: "manual_on",
        2: "automatic_off",
        3: "automatic_on",
    },
    "HK2 Config Voltage": {
        0: "manual_off",
        1: "manual_on",
        2: "automatic_off",
        3: "automatic_on",
    },
    "HK1 Config HK Type": SELECT_OPTION_KEYS["hc_type"],
    "HK2 Config HK Type": SELECT_OPTION_KEYS["hc_type"],
    "HK1 Config Regelvariante": SELECT_OPTION_KEYS["control_variant"],
    "HK2 Config Regelvariante": SELECT_OPTION_KEYS["control_variant"],
    "HK1 Config Ext Room Sensor": SELECT_OPTION_KEYS["external_room_sensor"],
    "HK2 Config Ext Room Sensor": SELECT_OPTION_KEYS["external_room_sensor"],
    "HK1 Expert Reduziertbetrieb": SELECT_OPTION_KEYS["reduced_mode"],
    "HK2 Expert Reduziertbetrieb": SELECT_OPTION_KEYS["reduced_mode"],
    "HK1 Expert Raumthermostat": SELECT_OPTION_KEYS["room_thermostat"],
    "HK2 Expert Raumthermostat": SELECT_OPTION_KEYS["room_thermostat"],
}

BINARY_SENSOR_NAMES = {
    "Flamme",
    "Heizung",
    "Warmwasser",
    "Pumpe",
    "Gasventil 1",
    "Gasventil 2",
}


def operation_phase_key(value: object, *, flame_on: bool = False) -> str:
    """Return a translatable state key for parameter 373."""

    if isinstance(value, bool) or not isinstance(value, int):
        return f"unknown_{value}"
    if 0 <= value <= 9:
        return f"phase_{value}"
    if 10 <= value <= 60:
        prefix = "flame_formation" if flame_on else "pre_purge_remaining"
        return f"{prefix}_{value}"
    return f"unknown_{value}"


def error_code_key(value: object) -> str:
    """Return a stable state key while preserving an unknown raw code."""

    try:
        code = int(value)
    except (TypeError, ValueError):
        return f"unknown_{value}"
    return "normal" if code == 0 else f"code_{code}"
