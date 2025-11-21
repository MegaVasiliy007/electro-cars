"""Config flow for Electro Cars integration."""

from __future__ import annotations

from typing import Any
import voluptuous as vol
import logging

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN
from .api import ElectroCarsAPI

_LOGGER = logging.getLogger(__name__)

class ElectroCarsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Electro Cars."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._api: ElectroCarsAPI | None = None
        self._phone: str | None = None
        self._refresh_token: str | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step: ask for phone and send SMS."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required("phone"): str,
                    }
                ),
            )

        phone = user_input.get("phone", "").strip()
        if not phone:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required("phone"): str,
                    }
                ),
                errors={"base": "unknown"},
            )

        if self._api is None:
            self._api = ElectroCarsAPI()

        try:
            await self._api.send_sms(phone)
        except Exception:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required("phone"): str,
                    }
                ),
                errors={"base": "sms_failed"},
            )

        self._phone = phone
        return await self.async_step_code()

    async def async_step_code(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the SMS code step."""
        if user_input is None:
            return self.async_show_form(
                step_id="code",
                data_schema=vol.Schema(
                    {
                        vol.Required("code"): str,
                    }
                ),
            )

        code = user_input.get("code", "").strip()
        if not code:
            return self.async_show_form(
                step_id="code",
                data_schema=vol.Schema(
                    {
                        vol.Required("code"): str,
                    }
                ),
                errors={"base": "invalid_code"},
            )

        if self._api is None:
            self._api = ElectroCarsAPI()

        try:
            tokens = await self._api.login_with_code(code)
        except Exception as err:
            _LOGGER.exception("Error during SMS code login: %s", err)
            return self.async_show_form(
                step_id="code",
                data_schema=vol.Schema(
                    {
                        vol.Required("code"): str,
                    }
                ),
                errors={"base": "invalid_code"},
            )

        # After successful login, use the refresh token returned by the API
        if not tokens or "refresh_token" not in tokens:
            _LOGGER.error("Login succeeded but no refresh_token was returned: %s", tokens)
            return self.async_show_form(
                step_id="code",
                data_schema=vol.Schema(
                    {
                        vol.Required("code"): str,
                    }
                ),
                errors={"base": "unknown"},
            )

        self._refresh_token = tokens["refresh_token"]

        if not self._refresh_token:
            return self.async_show_form(
                step_id="code",
                data_schema=vol.Schema(
                    {
                        vol.Required("code"): str,
                    }
                ),
                errors={"base": "unknown"},
            )

        data = {
            "refresh_token": self._refresh_token,
        }
        if self._phone:
            data["phone"] = self._phone

        return self.async_create_entry(title="Electro Cars", data=data)
