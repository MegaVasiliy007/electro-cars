from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


def build_device_info(car: dict) -> DeviceInfo:
    car_id = str(car["id"])
    return DeviceInfo(
        identifiers={(DOMAIN, car_id)},
        name=f"{car['brand']['name']} {car['model']['name']} ({car['numberplate']})",
        manufacturer=car["brand"]["name"],
        model=f"{car['model']['name']} - {car['modification']['name']} (VIN {car['vin']})",
    )
