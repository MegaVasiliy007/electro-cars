from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import ElectroCarsCoordinator
from .util import build_device_info

_LOGGER = logging.getLogger(__name__)

BINARY_SENSOR_TYPES: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(key="charging", name="Зарядка", device_class="battery_charging"),
    BinarySensorEntityDescription(key="locked", name="Замок", device_class="lock"),
    BinarySensorEntityDescription(key="door_fl", name="Передняя левая дверь", device_class="door"),
    BinarySensorEntityDescription(key="door_fr", name="Передняя правая дверь", device_class="door"),
    BinarySensorEntityDescription(key="door_rl", name="Задняя левая дверь", device_class="door"),
    BinarySensorEntityDescription(key="door_rr", name="Задняя правая дверь", device_class="door"),
    BinarySensorEntityDescription(key="trunk", name="Багажник", device_class="door"),
    BinarySensorEntityDescription(key="moving", name="Движение", device_class="moving"),
    BinarySensorEntityDescription(key="eco", name="Эко режим"),
    BinarySensorEntityDescription(key="auto_main_battery_heating", name="Автоподогрев батареи"),
    BinarySensorEntityDescription(key="auto_board_battery_recharge", name="Автозаряд бортовой батареи"),
    BinarySensorEntityDescription(key="ignition", name="Двигатель", icon="mdi:engine", device_class="running"),
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ElectroCarsCoordinator = hass.data[DOMAIN][entry.entry_id]

    if not coordinator.data:
        _LOGGER.warning("No cars received from API, skipping binary sensor setup.")
        return

    entities = []
    for car in coordinator.data:
        telematics = car.get("telematics", [{}])[0]
        car_id = str(car["id"])
        device_info = build_device_info(car)

        for description in BINARY_SENSOR_TYPES:
            value = telematics.get(description.key, car.get(description.key))
            if value is not None:
                entities.append(ElectroCarBinarySensor(
                    coordinator=coordinator,
                    car_id=car_id,
                    description=description,
                    device_info=device_info,
                ))

    async_add_entities(entities)

class ElectroCarBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator: ElectroCarsCoordinator, car_id, description, device_info):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.car_id = car_id
        self.entity_description = description
        self._attr_name = description.name
        self._attr_unique_id = f"{car_id}_{description.key}"
        self._attr_device_info = device_info

    @property
    def is_on(self) -> bool | None:
        car = next((car for car in self.coordinator.data if str(car["id"]) == self.car_id), None)
        if car:
            telematics = car.get("telematics", [{}])[0]
            value = telematics.get(self.entity_description.key, car.get(self.entity_description.key))
            if self.entity_description.key == "locked":
                return not bool(value)
            return bool(value)
        return None