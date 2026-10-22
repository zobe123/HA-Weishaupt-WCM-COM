"""Behavior tests for WTC boiler profiles."""

import logging
from unittest.mock import AsyncMock, Mock

import pytest

from homeassistant.components.number import NumberDeviceClass
from homeassistant.const import UnitOfTemperature
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.weishaupt_wcm_com import (
    _filter_disabled_entity_parameters,
    _remove_inactive_heating_circuit_entities,
    _remove_inactive_profile_entities,
)

from custom_components.weishaupt_wcm_com.const import (
    BOILER_PROFILE_WTC_G,
    BOILER_PROFILE_WTC_OB,
    BOILER_PROFILES,
    HEATING_CIRCUIT_PROBE_PARAMETERS,
    detected_heating_circuit_buses,
    parameters_for_profile,
    DOMAIN,
    PARAMETERS,
)
from custom_components.weishaupt_wcm_com.number import WeishauptExpertNumber
from custom_components.weishaupt_wcm_com.weishaupt_api import (
    combine_wtc_ob_counters,
)
from custom_components.weishaupt_wcm_com.sensor import (
    WeishauptSensor,
    scale_profile_value,
)


def test_only_documented_heat_generator_profiles_are_offered() -> None:
    assert BOILER_PROFILES == (BOILER_PROFILE_WTC_G, BOILER_PROFILE_WTC_OB)


def test_heating_circuit_probe_detects_only_answering_fs_buses() -> None:
    assert len(HEATING_CIRCUIT_PROBE_PARAMETERS) == 6
    assert detected_heating_circuit_buses(
        {
            "Heating Circuit 0 Version High": 1,
            "Heating Circuit 0 Version Low": 2,
            "Heating Circuit 2 Version High": 0,
        }
    ) == {0, 2}
    assert detected_heating_circuit_buses({}) == set()


def test_profile_parameter_sets_do_not_cross_poll() -> None:
    gas_ids = {parameter["id"] for parameter in parameters_for_profile("wtc_g")}
    oil_ids = {parameter["id"] for parameter in parameters_for_profile("wtc_ob")}

    assert 3158 in gas_ids and 3197 not in gas_ids
    assert 3197 in oil_ids and 3158 not in oil_ids
    assert 319 in gas_ids and 345 in gas_ids and 4148 not in gas_ids
    assert 4148 in oil_ids and 319 not in oil_ids and 345 not in oil_ids


def test_detected_heating_circuits_filter_parameter_set() -> None:
    parameters = parameters_for_profile("wtc_ob", {0, 2})
    names = {parameter["name"] for parameter in parameters}
    assert any(name.startswith("WTC HK1 ") for name in names)
    assert not any(name.startswith("HK1 ") for name in names)
    assert any(name.startswith("HK2 ") for name in names)


def test_oil_high_low_words_match_original_webui() -> None:
    oil_parts = {
        parameter["id"]: parameter["name"]
        for parameter in PARAMETERS
        if parameter.get("profile") == "wtc_ob" and parameter.get("internal")
    }
    assert oil_parts[3792] == "WTC-OB Ölzähler High"
    assert oil_parts[3793] == "WTC-OB Ölzähler Low"
    assert oil_parts[3197] == "WTC-OB Schaltspiele High"
    assert oil_parts[3196] == "WTC-OB Schaltspiele Low"
    assert oil_parts[3199] == "WTC-OB Betriebsstunden High"
    assert oil_parts[3198] == "WTC-OB Betriebsstunden Low"

    data = {
        "WTC-OB Schaltspiele High": 12,
        "WTC-OB Schaltspiele Low": 345,
        "WTC-OB Betriebsstunden High": 6,
        "WTC-OB Betriebsstunden Low": 789,
        "WTC-OB Ölzähler High": 3,
        "WTC-OB Ölzähler Low": 210,
    }

    combine_wtc_ob_counters(data)

    assert data["Schaltspielzahl Brenner"] == 12345
    assert data["Betriebsstunden Brenner"] == 6789
    assert data["Ölzähler"] == 3210


def test_webui_profile_scaling() -> None:
    assert scale_profile_value("hours_100", 123) == 12300
    assert scale_profile_value("hours_10", 12) == 120
    assert scale_profile_value("power_tenths", 456) == 45.6


async def test_profile_switch_removes_only_inactive_registry_entities(hass) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="WCM-COM")
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    gas_sensor = registry.async_get_or_create(
        "sensor", DOMAIN, "weishaupt_gasventil_1", config_entry=entry
    )
    gas_number = registry.async_get_or_create(
        "number",
        DOMAIN,
        "weishaupt_expert_max_power_heating_number",
        config_entry=entry,
    )
    common_sensor = registry.async_get_or_create(
        "sensor", DOMAIN, "weishaupt_zeit_seit_letzter_wartung", config_entry=entry
    )
    oil_sensor = registry.async_get_or_create(
        "sensor", DOMAIN, "weishaupt_magnetventil_1", config_entry=entry
    )

    _remove_inactive_profile_entities(hass, parameters_for_profile("wtc_ob"))

    assert registry.async_get(gas_sensor.entity_id) is None
    assert registry.async_get(gas_number.entity_id) is None
    assert registry.async_get(common_sensor.entity_id) is not None
    assert registry.async_get(oil_sensor.entity_id) is not None


async def test_disabled_entity_parameters_are_not_polled(hass) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="WCM-COM")
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    flame = registry.async_get_or_create(
        "sensor", DOMAIN, "weishaupt_flamme", config_entry=entry,
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    pump = registry.async_get_or_create(
        "sensor", DOMAIN, "weishaupt_pumpe", config_entry=entry,
    )
    parameters = [
        next(item for item in PARAMETERS if item["name"] == name)
        for name in ("Status", "Flamme", "Pumpe")
    ]

    filtered = _filter_disabled_entity_parameters(hass, entry, parameters)

    assert {item["name"] for item in filtered} == {"Status", "Pumpe"}
    assert registry.async_get(flame.entity_id) is not None
    assert registry.async_get(pump.entity_id) is not None


async def test_inactive_heating_circuit_registry_entries_are_removed(hass) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="WCM-COM")
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    hk1 = registry.async_get_or_create(
        "sensor", DOMAIN, "weishaupt_hk1_raumtemperatur", config_entry=entry
    )
    hk2 = registry.async_get_or_create(
        "sensor", DOMAIN, "weishaupt_hk2_raumtemperatur", config_entry=entry
    )

    _remove_inactive_heating_circuit_entities(hass, {0, 2})

    assert registry.async_get(hk1.entity_id) is None
    assert registry.async_get(hk2.entity_id) is not None


@pytest.mark.parametrize(
    ("name", "parameter_id", "minimum", "maximum", "unit", "invalid"),
    (
        (
            "Expert Spec Level Heating Mode",
            3102,
            8,
            85,
            UnitOfTemperature.CELSIUS,
            86,
        ),
        ("Expert Corr Outside Sensor", 3103, -4, 4, "K", -5),
    ),
)
async def test_p18_p20_write_unscaled_and_reject_out_of_range(
    hass, name, parameter_id, minimum, maximum, unit, invalid
) -> None:
    coordinator = DataUpdateCoordinator(
        hass,
        logging.getLogger(__name__),
        config_entry=None,
        name="test-profile-number",
    )
    coordinator.async_set_updated_data({name: 60 if parameter_id == 3102 else 0})
    coordinator.async_request_refresh = AsyncMock()
    api = Mock()
    entity = WeishauptExpertNumber(
        coordinator,
        api,
        name,
        parameter_id=parameter_id,
        min_value=minimum,
        max_value=maximum,
        step=1,
        unit=unit,
        allow_write=True,
    )
    entity.hass = hass

    if parameter_id == 3102:
        assert entity.native_value == 60
        assert entity.native_unit_of_measurement == UnitOfTemperature.CELSIUS
        assert entity.device_class == NumberDeviceClass.TEMPERATURE
        await entity.async_set_native_value(60)
        api.write_parameter.assert_called_once_with(3102, 0, 10, 60)
    else:
        assert entity.native_value == 0
        assert entity.native_unit_of_measurement == "K"
        assert entity.device_class is None

    with pytest.raises(ServiceValidationError):
        await entity.async_set_native_value(invalid)


async def test_p18_p20_sensor_units_and_device_classes(hass) -> None:
    coordinator = DataUpdateCoordinator(
        hass,
        logging.getLogger(__name__),
        config_entry=None,
        name="test-profile-sensor",
    )
    coordinator.async_set_updated_data(
        {
            "Expert Spec Level Heating Mode": 60,
            "Expert Corr Outside Sensor": 0,
        }
    )
    api = Mock()
    by_id = {parameter["id"]: parameter for parameter in PARAMETERS}
    p18 = WeishauptSensor(
        coordinator, api, by_id[3102], UnitOfTemperature.CELSIUS
    )
    p20 = WeishauptSensor(coordinator, api, by_id[3103], "K")

    assert p18.native_value == 60
    assert p18.native_unit_of_measurement == UnitOfTemperature.CELSIUS
    assert p18.device_class == "temperature"
    assert p20.native_value == 0
    assert p20.native_unit_of_measurement == "K"
    assert p20.device_class is None


async def test_missing_sensor_value_is_unavailable(hass) -> None:
    coordinator = DataUpdateCoordinator(
        hass,
        logging.getLogger(__name__),
        config_entry=None,
        name="test-missing-sensor",
    )
    coordinator.async_set_updated_data({})
    parameter = next(item for item in PARAMETERS if item["id"] == 118)
    entity = WeishauptSensor(
        coordinator, Mock(), parameter, UnitOfTemperature.CELSIUS
    )

    assert entity.native_value is None
    assert entity.available is False
