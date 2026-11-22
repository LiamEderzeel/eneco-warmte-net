"""Config flow for Eneco Data."""

from __future__ import annotations

from datetime import date
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback

from .api import (
    EnecoAccountError,
    EnecoApiError,
    EnecoApiKeyError,
    EnecoAuthError,
    EnecoClient,
)
from .const import (
    CONF_ACCOUNT_ID,
    CONF_API_KEY,
    CONF_CUSTOMER_ID,
    CONF_HEAT_PRICE,
    CONF_SESSION_TOKEN,
    DEFAULT_ACCOUNT_ID,
    DOMAIN,
)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CUSTOMER_ID): str,
        vol.Required(CONF_ACCOUNT_ID, default=DEFAULT_ACCOUNT_ID): str,
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_SESSION_TOKEN): str,
    }
)

STEP_REAUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_SESSION_TOKEN): str,
    }
)


def account_id(entry: ConfigEntry) -> str:
    """Account number: options win over the original setup data."""
    return str(
        entry.options.get(
            CONF_ACCOUNT_ID, entry.data.get(CONF_ACCOUNT_ID, DEFAULT_ACCOUNT_ID)
        )
    )


async def _validate(
    hass, customer_id: str, api_key: str, session_token: str, account: str
) -> dict[str, str]:
    """Try one fetch. Returns an errors dict (empty on success)."""
    client = EnecoClient(customer_id, api_key, session_token, account)
    try:
        await hass.async_add_executor_job(
            client.fetch_daily_usage, date.today().replace(day=1)
        )
    except EnecoApiKeyError:
        return {"base": "invalid_api_key"}
    except EnecoAuthError:
        return {"base": "invalid_auth"}
    except EnecoAccountError:
        return {"base": "invalid_account"}
    except EnecoApiError:
        return {"base": "cannot_connect"}
    return {}


class EnecoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eneco Data."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> EnecoOptionsFlow:
        return EnecoOptionsFlow()

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
                user_input[CONF_ACCOUNT_ID],
            )
            if not errors:
                return self.async_create_entry(title="Eneco Data", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_SCHEMA, user_input
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a fresh session token and, if it changed, the apikey."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            errors = await _validate(
                self.hass,
                reauth_entry.data[CONF_CUSTOMER_ID],
                user_input[CONF_API_KEY],
                user_input[CONF_SESSION_TOKEN],
                account_id(reauth_entry),
            )
            if not errors:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data={**reauth_entry.data, **user_input},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                STEP_REAUTH_SCHEMA,
                user_input or {CONF_API_KEY: reauth_entry.data[CONF_API_KEY]},
            ),
            errors=errors,
        )


class EnecoOptionsFlow(OptionsFlowWithReload):
    """Account number and the optional price used for the cost statistic."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            user_input[CONF_ACCOUNT_ID] = str(user_input[CONF_ACCOUNT_ID]).strip()
            return self.async_create_entry(data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ACCOUNT_ID, default=account_id(self.config_entry)
                ): str,
                vol.Required(
                    CONF_HEAT_PRICE,
                    default=self.config_entry.options.get(CONF_HEAT_PRICE, 0.0),
                ): vol.All(vol.Coerce(float), vol.Range(min=0)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
