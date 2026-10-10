"""Config flow for Weishaupt WCM-COM integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    CONF_ALLOW_WRITE,
    DEFAULT_ALLOW_WRITE,
    CONF_ADVANCED_LOGGING,
    DEFAULT_ADVANCED_LOGGING,
    CONF_SHOW_TIME_PROGRAM_PANEL,
    DEFAULT_SHOW_TIME_PROGRAM_PANEL,
    CONF_EXPOSE_TIME_PROGRAM_CALENDARS,
    DEFAULT_EXPOSE_TIME_PROGRAM_CALENDARS,
    CONF_EXTERNAL_GAS_METER_ENTITY,
    DEFAULT_EXTERNAL_GAS_METER_ENTITY,
)
from .weishaupt_api import WeishauptAPI

_LOGGER = logging.getLogger(__name__)

class WeishauptConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Weishaupt WCM-COM."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            username = user_input.get(CONF_USERNAME)
            password = user_input.get(CONF_PASSWORD)

            # Validierung der Verbindung
            api = WeishauptAPI(host, username, password)
            try:
                # Da get_data eine blockierende Methode ist, führen wir sie im Executor aus
                data = await self.hass.async_add_executor_job(api.get_data)
                if not data:
                    errors["base"] = "cannot_connect"
                else:
                    # Erfolgreiche Verbindung
                    return self.async_create_entry(title="Weishaupt WCM-COM", data=user_input)
            except Exception as e:
                _LOGGER.error(f"Error connecting to Weishaupt WCM-COM: {e}")
                errors["base"] = "cannot_connect"

        data_schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Optional(CONF_USERNAME): str,
            vol.Optional(CONF_PASSWORD): str,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return WeishauptOptionsFlowHandler(config_entry)

class WeishauptOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Weishaupt WCM-COM options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize Weishaupt options flow."""
        # In neueren HA-Versionen ist ``config_entry`` bereits als Property
        # im OptionsFlow-Basisobjekt vorhanden. Wir speichern daher unsere
        # Referenz unter einem eigenen Namen.
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the Weishaupt options (reconfigure connection)."""
        errors = {}

        if user_input is not None:
            connection_data = {
                CONF_HOST: user_input[CONF_HOST],
                CONF_USERNAME: user_input.get(CONF_USERNAME, ""),
                CONF_PASSWORD: user_input.get(CONF_PASSWORD, ""),
            }
            api = WeishauptAPI(
                connection_data[CONF_HOST],
                connection_data[CONF_USERNAME],
                connection_data[CONF_PASSWORD],
            )
            try:
                data = await self.hass.async_add_executor_job(api.get_data)
                if not data:
                    errors["base"] = "cannot_connect"
                else:
                    self.hass.config_entries.async_update_entry(
                        self._config_entry,
                        data=connection_data,
                    )
                    options_data = {
                        CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                        CONF_ALLOW_WRITE: user_input[CONF_ALLOW_WRITE],
                        CONF_ADVANCED_LOGGING: user_input[CONF_ADVANCED_LOGGING],
                        CONF_SHOW_TIME_PROGRAM_PANEL: user_input[
                            CONF_SHOW_TIME_PROGRAM_PANEL
                        ],
                        CONF_EXPOSE_TIME_PROGRAM_CALENDARS: user_input[
                            CONF_EXPOSE_TIME_PROGRAM_CALENDARS
                        ],
                        CONF_EXTERNAL_GAS_METER_ENTITY: user_input.get(
                            CONF_EXTERNAL_GAS_METER_ENTITY, ""
                        ),
                    }
                    return self.async_create_entry(title="", data=options_data)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error("Error validating updated WCM-COM connection: %s", err)
                errors["base"] = "cannot_connect"

        # Aktuelle Werte aus Entry / Optionen als Default
        source = user_input or self._config_entry.options
        host = source.get(CONF_HOST, self._config_entry.data.get(CONF_HOST, ""))
        username = source.get(CONF_USERNAME, self._config_entry.data.get(CONF_USERNAME, ""))
        password = source.get(CONF_PASSWORD, self._config_entry.data.get(CONF_PASSWORD, ""))

        scan_interval = source.get(
            CONF_SCAN_INTERVAL,
            DEFAULT_SCAN_INTERVAL,
        )
        allow_write = source.get(
            CONF_ALLOW_WRITE,
            DEFAULT_ALLOW_WRITE,
        )
        advanced_logging = source.get(
            CONF_ADVANCED_LOGGING,
            DEFAULT_ADVANCED_LOGGING,
        )
        show_time_program_panel = source.get(
            CONF_SHOW_TIME_PROGRAM_PANEL,
            DEFAULT_SHOW_TIME_PROGRAM_PANEL,
        )
        expose_time_program_calendars = source.get(
            CONF_EXPOSE_TIME_PROGRAM_CALENDARS,
            DEFAULT_EXPOSE_TIME_PROGRAM_CALENDARS,
        )
        external_gas_meter_entity = source.get(
            CONF_EXTERNAL_GAS_METER_ENTITY,
            DEFAULT_EXTERNAL_GAS_METER_ENTITY,
        )

        gas_meter_key = vol.Optional(CONF_EXTERNAL_GAS_METER_ENTITY)
        if external_gas_meter_entity:
            gas_meter_key = vol.Optional(
                CONF_EXTERNAL_GAS_METER_ENTITY,
                description={"suggested_value": external_gas_meter_entity},
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=host): str,
                vol.Optional(CONF_USERNAME, default=username): str,
                vol.Optional(CONF_PASSWORD, default=password): str,
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=scan_interval,
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
                vol.Required(
                    CONF_ALLOW_WRITE,
                    default=allow_write,
                ): bool,
                vol.Required(
                    CONF_ADVANCED_LOGGING,
                    default=advanced_logging,
                ): bool,
                vol.Required(
                    CONF_SHOW_TIME_PROGRAM_PANEL,
                    default=show_time_program_panel,
                ): bool,
                vol.Required(
                    CONF_EXPOSE_TIME_PROGRAM_CALENDARS,
                    default=expose_time_program_calendars,
                ): bool,
                gas_meter_key: selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )
