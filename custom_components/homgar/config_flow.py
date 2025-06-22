"""Config flow for HomGar integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .api import HomgarApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional("area_code", default="31"): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HomGar."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await self._validate_input(user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def _validate_input(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate the user input allows us to connect."""
        api = HomgarApiClient(
            email=data[CONF_EMAIL],
            password=data[CONF_PASSWORD],
            area_code=data.get("area_code", "31"),
        )

        try:
            await self.hass.async_add_executor_job(api.ensure_logged_in)
        except Exception as err:
            _LOGGER.error("Failed to connect to HomGar API: %s", err)
            if "401" in str(err) or "403" in str(err):
                raise InvalidAuth from err
            raise CannotConnect from err

        return {"title": f"HomGar ({data[CONF_EMAIL]})"}


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
