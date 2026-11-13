"""Config flow for Eneco Data."""

from __future__ import annotations

from datetime import date
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .api import EnecoApiError, EnecoAuthError, EnecoClient
from .const import CONF_API_KEY, CONF_CUSTOMER_ID, CONF_SESSION_TOKEN, DOMAIN

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CUSTOMER_ID): str,
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_SESSION_TOKEN): str,
    }
)

STEP_REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_SESSION_TOKEN): str})


async def _validate(
    hass, customer_id: str, api_key: str, session_token: str
) -> dict[str, str]:
    """Try one fetch. Returns an errors dict (empty on success)."""
    client = EnecoClient(customer_id, api_key, session_token)
    try:
        await hass.async_add_executor_job(client.fetch_daily_usage, date.today().replace(day=1))
    except EnecoAuthError:
        return {"base": "invalid_auth"}
    except EnecoApiError:
        return {"base": "cannot_connect"}
    return {}


class EnecoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eneco Data."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_CUSTOMER_ID])
            self._abort_if_unique_id_configured()

            errors = await _validate(
                self.hass,
                user_input[CONF_CUSTOMER_ID],
                user_input[CONF_API_KEY],
                user_input[CONF_SESSION_TOKEN],
            )
            if not errors:
                return self.async_create_entry(title="Eneco Data", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            errors = await _validate(
                self.hass,
                reauth_entry.data[CONF_CUSTOMER_ID],
                reauth_entry.data[CONF_API_KEY],
                user_input[CONF_SESSION_TOKEN],
            )
            if not errors:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data={**reauth_entry.data, **user_input},
                )

        return self.async_show_form(
            step_id="reauth_confirm", data_schema=STEP_REAUTH_SCHEMA, errors=errors
        )
