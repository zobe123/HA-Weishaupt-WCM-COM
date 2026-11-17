"""Registry migrations for renamed parameters."""

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.weishaupt_wcm_com import (
    _filter_disabled_entity_parameters,
    _migrate_renamed_unique_ids,
)
from custom_components.weishaupt_wcm_com.const import DOMAIN, PARAMETERS


async def test_flue_gas_rename_keeps_entity_id_and_settings(hass) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="WCM-COM")
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "weishaupt_kesseltemperatur",
        config_entry=entry,
        suggested_object_id="therme_kessel_boiler_temperature",
        disabled_by=er.RegistryEntryDisabler.USER,
    )

    _migrate_renamed_unique_ids(hass)
    _migrate_renamed_unique_ids(hass)  # idempotent on every setup

    migrated = registry.async_get(old.entity_id)
    assert migrated is not None
    assert migrated.entity_id == "sensor.therme_kessel_boiler_temperature"
    assert migrated.unique_id == "weishaupt_abgastemperatur"
    assert migrated.disabled_by is er.RegistryEntryDisabler.USER
    assert registry.async_get_entity_id(
        "sensor", DOMAIN, "weishaupt_kesseltemperatur"
    ) is None

    # The migrated, user-disabled entity is still excluded from polling.
    polled = _filter_disabled_entity_parameters(hass, entry, PARAMETERS)
    assert "Abgastemperatur" not in {parameter["name"] for parameter in polled}


async def test_flue_gas_rename_leaves_existing_new_entity_alone(hass) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="WCM-COM")
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old = registry.async_get_or_create(
        "sensor", DOMAIN, "weishaupt_kesseltemperatur", config_entry=entry
    )
    new = registry.async_get_or_create(
        "sensor", DOMAIN, "weishaupt_abgastemperatur", config_entry=entry
    )

    _migrate_renamed_unique_ids(hass)

    assert registry.async_get(old.entity_id).unique_id == "weishaupt_kesseltemperatur"
    assert registry.async_get(new.entity_id).unique_id == "weishaupt_abgastemperatur"
