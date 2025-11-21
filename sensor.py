from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import ElectroCarsCoordinator
from .util import build_device_info

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(key="battery", name="Уровень заряда", native_unit_of_measurement="%", icon="mdi:battery", device_class="battery", state_class="measurement"),
    SensorEntityDescription(key="power_reserve", name="Запас хода", native_unit_of_measurement="km", icon="mdi:car-electric", state_class="measurement"),
    SensorEntityDescription(key="temp_from_remote_control", name="Температура в салоне", native_unit_of_measurement="°C", icon="mdi:thermometer", device_class="temperature", state_class="measurement"),
    SensorEntityDescription(key="odometer", name="Пробег", native_unit_of_measurement="km", icon="mdi:counter", device_class="distance", state_class="total_increasing"),
    SensorEntityDescription(key="gsm_level", name="Уровень GSM", native_unit_of_measurement="%", icon="mdi:signal", state_class="measurement", entity_category=EntityCategory.DIAGNOSTIC),
    SensorEntityDescription(key="board_network_voltage", name="Бортовое напряжение", native_unit_of_measurement="V", icon="mdi:car-battery", device_class="voltage", state_class="measurement"),
    SensorEntityDescription(key="lat", name="Широта", native_unit_of_measurement="°", icon="mdi:map-marker", state_class="measurement"),
    SensorEntityDescription(key="lng", name="Долгота", native_unit_of_measurement="°", icon="mdi:map-marker", state_class="measurement"),
    SensorEntityDescription(key="battery_capacity", name="Емкость батареи", native_unit_of_measurement="кВт⋅ч", icon="mdi:battery-high", state_class="measurement"),
    SensorEntityDescription(key="last_online", name="Последний онлайн", icon="mdi:clock-time-four-outline", entity_category=EntityCategory.DIAGNOSTIC),
    SensorEntityDescription(key="battery_temp", name="Температура батареи", native_unit_of_measurement="°C", icon="mdi:thermometer", device_class="temperature", state_class="measurement"),
    SensorEntityDescription(key="update_interval", name="Интервал обновления данных", icon="mdi:timer-cog", entity_category=EntityCategory.DIAGNOSTIC),
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ElectroCarsCoordinator = hass.data[DOMAIN][entry.entry_id]

    if not coordinator.data:
        _LOGGER.warning("No cars received from API, skipping sensor setup.")
        return

    entities = []
    for car in coordinator.data:
        telematics = car.get("telematics", [{}])[0]
        car_id = str(car["id"])
        device_info = build_device_info(car)

        for description in SENSOR_TYPES:
            # Try telematics first, then fallback to main car data
            value = telematics.get(description.key, car.get(description.key))
            if value is not None:
                entities.append(ElectroCarSensor(
                    coordinator=coordinator,
                    car_id=car_id,
                    description=description,
                    device_info=device_info,
                ))

    async_add_entities(entities)

class ElectroCarSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: ElectroCarsCoordinator, car_id, description, device_info):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.car_id = car_id
        self.entity_description = description
        self._attr_name = description.name
        self._attr_unique_id = f"{car_id}_{description.key}"
        self._attr_device_info = device_info

    @property
    def icon(self) -> str | None:
        """Return icon based on state."""
        if self.entity_description.device_class in ("door", "lock"):
            return "mdi:door-closed" if self.native_value == "Закрыта" or self.native_value == "Заблокировано" else "mdi:door-open"
        if isinstance(self.native_value, bool):
            return "mdi:check-circle" if self.native_value else "mdi:close-circle"
        return self.entity_description.icon

    @property
    def native_value(self):
        car = next((car for car in self.coordinator.data if str(car["id"]) == self.car_id), None)
        if car:
            telematics = car.get("telematics", [{}])[0]
            value = telematics.get(self.entity_description.key, car.get(self.entity_description.key))

            if self.entity_description.device_class == "door":
                return "Закрыта" if not value else "Открыта"

            if self.entity_description.device_class == "lock":
                return "Заблокировано" if value else "Разблокировано"

            if self.entity_description.device_class == "battery":
                return int(value) if value is not None else None

            if self.entity_description.key == "last_online" and value:
                from datetime import datetime
                from homeassistant.util import dt as dt_util

                dt = datetime.utcfromtimestamp(value)
                local_dt = dt_util.as_local(dt)
                return local_dt.strftime("%Y-%m-%d %H:%M:%S")

            return value
        if self.entity_description.key == "update_interval":
            interval = self.coordinator.update_interval
            if interval:
                seconds = interval.total_seconds()
                if seconds <= 300:
                    return "5 минут"
                if seconds <= 600:
                    return "10 минут"
                return "1 час"
            return "Неизвестно"
        return None