"""Config flow for Tap Electric integration."""

import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, CONF_API_KEY, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL

class TapElectricConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tap Electric."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(
                title="Tap Electric", 
                data=user_input
            )

        # Define the schema with both API key and the configurable update interval
        data_schema = vol.Schema({
            vol.Required(CONF_API_KEY): str,
            vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): int,
        })

        return self.async_show_form(
            step_id="user", 
            data_schema=data_schema
        )