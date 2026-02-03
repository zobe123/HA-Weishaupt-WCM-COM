"""Config flow for Weishaupt WCM-COM integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_SCAN_INTERVAL
from homeassistant.core import callback

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
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
        """Manage the Weishaupt options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        scan_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            DEFAULT_SCAN_INTERVAL,
        )

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=scan_interval,
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)
