"""Behavior tests for the Home Assistant config and options flows."""

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.weishaupt_wcm_com import async_migrate_entry
from custom_components.weishaupt_wcm_com.const import (
    CONF_ADVANCED_LOGGING,
    CONF_ALLOW_WRITE,
    CONF_EXPOSE_TIME_PROGRAM_CALENDARS,
    CONF_EXTERNAL_GAS_METER_ENTITY,
    CONF_SHOW_TIME_PROGRAM_PANEL,
    DOMAIN,
)
from custom_components.weishaupt_wcm_com.weishaupt_api import (
    WeishauptAuthenticationError,
)


pytestmark = pytest.mark.asyncio


def _entry(**kwargs) -> MockConfigEntry:
    defaults = {
        "data": {
            CONF_HOST: "wcm-com.local",
            CONF_USERNAME: "",
            CONF_PASSWORD: "",
        },
        "unique_id": "wcm-com.local",
        "version": 6,
    }
    defaults.update(kwargs)
    return MockConfigEntry(
        domain=DOMAIN,
        title="Weishaupt WCM-COM",
        **defaults,
    )


async def _finish_user_flow(hass, user_input: dict) -> ConfigFlowResult:
    return await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data=user_input,
    )


async def test_duplicate_host_aborts_with_translated_reason(hass) -> None:
    """A normalized duplicate host aborts with the translated reason key."""

    _entry().add_to_hass(hass)

    result = await _finish_user_flow(
        hass,
        {CONF_HOST: " WCM-COM.LOCAL. ", CONF_USERNAME: "", CONF_PASSWORD: ""},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_flow_maps_401_to_invalid_auth(hass) -> None:
    """Authentication failures remain on the form with invalid_auth."""

    with patch(
        "custom_components.weishaupt_wcm_com.config_flow._async_validate_connection",
        AsyncMock(side_effect=WeishauptAuthenticationError),
    ):
        result = await _finish_user_flow(
            hass,
            {
                CONF_HOST: "wcm-com.local",
                CONF_USERNAME: "wrong",
                CONF_PASSWORD: "wrong",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_migration_moves_legacy_connection_options_to_data(hass) -> None:
    """Version 6 preserves effective legacy credentials and cleans options."""

    entry = _entry(
        version=5,
        data={
            CONF_HOST: "old.local",
            CONF_USERNAME: "old-user",
            CONF_PASSWORD: "old-password",
        },
        options={
            CONF_HOST: "WCM-COM.LOCAL.",
            CONF_USERNAME: "legacy-user",
            CONF_PASSWORD: "legacy-password",
            CONF_SCAN_INTERVAL: 90,
            CONF_ALLOW_WRITE: True,
        },
        unique_id=None,
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)

    assert entry.version == 6
    assert entry.unique_id == "wcm-com.local"
    assert entry.data[CONF_HOST] == "wcm-com.local"
    assert entry.data[CONF_USERNAME] == "legacy-user"
    assert entry.data[CONF_PASSWORD] == "legacy-password"
    assert entry.options == {CONF_SCAN_INTERVAL: 90, CONF_ALLOW_WRITE: True}


async def test_reauth_updates_credentials_and_schedules_one_reload(hass) -> None:
    """Successful reauthentication updates data and schedules one reload."""

    entry = _entry(
        options={
            CONF_USERNAME: "legacy-user",
            CONF_PASSWORD: "legacy-password",
            CONF_SCAN_INTERVAL: 60,
        }
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.weishaupt_wcm_com.config_flow._async_validate_connection",
            AsyncMock(),
        ),
        patch.object(
            hass.config_entries, "async_reload", AsyncMock(return_value=True)
        ) as reload_entry,
    ):
        form = await entry.start_reauth_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            form["flow_id"],
            {CONF_USERNAME: "new-user", CONF_PASSWORD: "new-password"},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_USERNAME] == "new-user"
    assert entry.data[CONF_PASSWORD] == "new-password"
    assert entry.options == {CONF_SCAN_INTERVAL: 60}
    reload_entry.assert_awaited_once_with(entry.entry_id)


async def test_options_update_schedules_one_reload(hass) -> None:
    """Connection and operational option changes schedule one reload total."""

    entry = _entry(
        options={
            CONF_SCAN_INTERVAL: 60,
            CONF_ALLOW_WRITE: False,
            CONF_ADVANCED_LOGGING: False,
            CONF_SHOW_TIME_PROGRAM_PANEL: True,
            CONF_EXPOSE_TIME_PROGRAM_CALENDARS: True,
            CONF_EXTERNAL_GAS_METER_ENTITY: "",
        }
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.weishaupt_wcm_com.config_flow._async_validate_connection",
            AsyncMock(),
        ),
        patch.object(
            hass.config_entries, "async_reload", AsyncMock(return_value=True)
        ) as reload_entry,
    ):
        form = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            form["flow_id"],
            {
                CONF_HOST: "wcm-com.local",
                CONF_USERNAME: "",
                CONF_PASSWORD: "",
                CONF_SCAN_INTERVAL: 90,
                CONF_ALLOW_WRITE: True,
                CONF_ADVANCED_LOGGING: False,
                CONF_SHOW_TIME_PROGRAM_PANEL: True,
                CONF_EXPOSE_TIME_PROGRAM_CALENDARS: True,
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SCAN_INTERVAL] == 90
    assert entry.options[CONF_ALLOW_WRITE] is True
    reload_entry.assert_awaited_once_with(entry.entry_id)
