from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .coordinator import ElectroCarsCoordinator
from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator: ElectroCarsCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    for car in coordinator.data:
        if "telematics" in car and car["telematics"]:
            entities.append(ElectroCarTrackerEntity(coordinator, str(car["id"])))

    async_add_entities(entities)

class ElectroCarTrackerEntity(CoordinatorEntity, TrackerEntity):
    def __init__(self, coordinator: ElectroCarsCoordinator, car_id: str) -> None:
        super().__init__(coordinator)
        self.car_id = car_id
        car = next((c for c in coordinator.data if str(c["id"]) == car_id), None)
        if car:
            model = car.get("model", {}).get("name", "Модель неизвестна")
            brand = car.get("brand", {}).get("name", "Бренд неизвестен")
            numberplate = car.get("numberplate", "Без номера")
            self._attr_name = f"{brand} {model} ({numberplate})"
        else:
            self._attr_name = f"Машина {car_id}"
        self._attr_unique_id = f"{car_id}_tracker"

    @property
    def latitude(self) -> float | None:
        car = next((c for c in self.coordinator.data if str(c["id"]) == self.car_id), None)
        if car and "telematics" in car and car["telematics"]:
            return car["telematics"][0].get("lat")
        return None

    @property
    def longitude(self) -> float | None:
        car = next((c for c in self.coordinator.data if str(c["id"]) == self.car_id), None)
        if car and "telematics" in car and car["telematics"]:
            return car["telematics"][0].get("lng")
        return None

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def icon(self) -> str:
        return "mdi:car"
