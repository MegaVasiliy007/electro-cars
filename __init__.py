"""Sensor platform for Electro Cars integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .api import ElectroCarsAPI
from .coordinator import ElectroCarsCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = ElectroCarsAPI(entry)
    await api.initialize(hass, entry)
    coordinator = ElectroCarsCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "device_tracker", "binary_sensor", "button"])

    # async def handle_send_command(call):
    #     """Handle the service call to send a command."""
    #     imei = call.data.get("imei")
    #     command = call.data.get("command")
    #     if not imei or command is None:
    #         _LOGGER.error("Missing required parameters: imei and command")
    #         return
    #
    #     success = await coordinator.api.send_command(imei, command)
    #     if not success:
    #         _LOGGER.error("Failed to send command %s to device %s", command, imei)
    #
    # hass.services.async_register(
    #     DOMAIN,
    #     "send_command",
    #     handle_send_command,
    # )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: ElectroCarsCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.api.close()
    return await hass.config_entries.async_unload_platforms(entry, ["sensor", "device_tracker", "binary_sensor"])
