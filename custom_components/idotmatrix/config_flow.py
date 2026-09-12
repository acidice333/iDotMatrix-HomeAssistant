"""Config flow for iDotMatrix integration."""
from __future__ import annotations

import logging
import re
from typing import Any, TYPE_CHECKING

import voluptuous as vol

from homeassistant import config_entries
if TYPE_CHECKING:
    from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_DISPLAY_MODE,
    DEFAULT_NAME,
    DISPLAY_MODE_DESIGN,
    DISPLAY_MODE_OPTIONS,
    DOMAIN,
    CONF_MAC,
)

_LOGGER = logging.getLogger(__name__)

def normalize_address(value: str) -> str:
    """Use one identity for colon, dash, compact, and mixed-case MAC input."""
    compact = re.sub(r"[:-]", "", str(value).strip())
    if not re.fullmatch(r"[0-9a-fA-F]{12}", compact):
        raise vol.Invalid("Enter a valid Bluetooth MAC address")
    return ":".join(compact[i:i + 2] for i in range(0, 12, 2)).upper()


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for iDotMatrix."""

    VERSION = 1

    async def _async_claim_address(self, address):
        """Reject duplicates, including entries made with older address formats."""
        await self.async_set_unique_id(address)
        for entry in self._async_current_entries():
            try:
                matches = normalize_address(entry.data.get(CONF_MAC, "")) == address
            except vol.Invalid:
                continue
            if matches:
                from homeassistant.data_entry_flow import AbortFlow
                raise AbortFlow("already_configured")
        self._abort_if_unique_id_configured()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                address = normalize_address(user_input[CONF_MAC])
            except vol.Invalid:
                errors[CONF_MAC] = "invalid_address"
            else:
                await self._async_claim_address(address)
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, DEFAULT_NAME),
                    data={CONF_MAC: address, CONF_NAME: user_input.get(CONF_NAME, DEFAULT_NAME)},
                )

        from homeassistant.components import bluetooth
        
        # Look for devices
        options = {}
        for service_info in bluetooth.async_discovered_service_info(self.hass):
             if service_info.name and str(service_info.name).startswith("IDM-"):
                 options[normalize_address(service_info.address)] = f"{service_info.name} ({service_info.address})"

        if not options:
            # Fallback to manual entry
            schema = vol.Schema({
                vol.Required(CONF_MAC): str,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            })
        else:
            # Show list
            schema = vol.Schema({
                vol.Required(CONF_MAC): vol.In(list(options.keys())),
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )


    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle bluetooth discovery."""
        await self._async_claim_address(normalize_address(discovery_info.address))
        
        self.discovery_info = discovery_info
        self.context["title_placeholders"] = {"name": discovery_info.name}
        
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        if user_input is not None:
             name = self.discovery_info.name or DEFAULT_NAME
             return self.async_create_entry(
                title=name,
                data={
                    CONF_MAC: normalize_address(self.discovery_info.address),
                    CONF_NAME: name,
                },
            )

        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": self.discovery_info.name},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle iDotMatrix options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(CONF_DISPLAY_MODE, DISPLAY_MODE_DESIGN)
        schema = vol.Schema(
            {
                vol.Required(CONF_DISPLAY_MODE, default=current): vol.In(
                    DISPLAY_MODE_OPTIONS
                )
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
