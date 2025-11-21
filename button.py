"""Button platform for Electro Cars integration."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .coordinator import ElectroCarsCoordinator
from .util import build_device_info

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: ElectroCarsCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for car in coordinator.data:
        device_info = build_device_info(car)

        if not car.get("telematics"):
            continue

        imei = str(car["telematics"][0].get("imei"))
        if not imei:
            continue

        commands = await coordinator.api.get_commands(imei)
        if not commands:
            continue

        created = set()
        for cmd in commands:
            if cmd["fleet_view_group"] == 1:
                # Diagnostic or configuration command, skip creating buttons
                continue

            command_id = cmd["command"]
            title = cmd["title"]

            if command_id in created:
                continue

            # Create button for command
            entities.append(ElectroCarButton(
                coordinator,
                imei,
                command_id,
                title,
                device_info,
            ))
            created.add(command_id)

            if cmd.get("reverse") and cmd["reverse"] not in created:
                # Create button for reverse command
                reverse_command_id = cmd["reverse"]
                reverse_title = f"Отмена: {title}"
                entities.append(ElectroCarButton(
                    coordinator,
                    imei,
                    reverse_command_id,
                    reverse_title,
                    device_info,
                ))
                created.add(reverse_command_id)

    async_add_entities(entities)

class ElectroCarButton(ButtonEntity):
    def __init__(self, coordinator: ElectroCarsCoordinator, imei: str, command_id: int, title: str, device_info: DeviceInfo) -> None:
        self.coordinator = coordinator
        self._imei = imei
        self._command_id = command_id
        self._attr_name = title
        self._attr_unique_id = f"{imei}_{command_id}_command"
        self._attr_device_info = device_info

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.api.send_command(self._imei, self._command_id)
