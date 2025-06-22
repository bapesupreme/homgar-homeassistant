"""Config flow for HomGar integration."""
from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .api import HomgarApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Constants
DEFAULT_AREA_CODE = "31"
MAX_AREA_CODE_LENGTH = 3
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional("area_code", default=DEFAULT_AREA_CODE): str,
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
            # Validate input format first
            validation_errors = self._validate_input_format(user_input)
            if validation_errors:
                errors.update(validation_errors)
            else:
                # Check for existing entries with same email
                await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
                self._abort_if_unique_id_configured()
                
                try:
                    info = await self._validate_api_connection(user_input)
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except InvalidAreaCode:
                    errors["area_code"] = "invalid_area_code"
                except Exception as err:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception during setup: %s", err)
                    errors["base"] = "unknown"
                else:
                    return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    def _validate_input_format(self, data: dict[str, Any]) -> dict[str, str]:
        """Validate input format before attempting API connection."""
        errors: dict[str, str] = {}
        
        # Validate email format
        email = data.get(CONF_EMAIL, "").strip()
        if not email:
            errors[CONF_EMAIL] = "email_required"
        elif not EMAIL_REGEX.match(email):
            errors[CONF_EMAIL] = "invalid_email"
        
        # Validate password
        password = data.get(CONF_PASSWORD, "")
        if not password:
            errors[CONF_PASSWORD] = "password_required"
        elif len(password) < 3:  # Basic length check
            errors[CONF_PASSWORD] = "password_too_short"
        
        # Validate area code
        area_code = data.get("area_code", "").strip()
        if area_code:
            if not area_code.isdigit():
                errors["area_code"] = "area_code_not_numeric"
            elif len(area_code) > MAX_AREA_CODE_LENGTH:
                errors["area_code"] = "area_code_too_long"
            elif len(area_code) == 0:
                errors["area_code"] = "area_code_empty"
        
        return errors

    async def _validate_api_connection(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate the user input allows us to connect to the API."""
        # Clean up the data
        clean_data = {
