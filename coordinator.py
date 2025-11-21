import datetime
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import ElectroCarsAPI

_LOGGER = logging.getLogger(__name__)

class ElectroCarsCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching data from ElectroCars API."""

    def __init__(self, hass, api: ElectroCarsAPI):
        self._last_active = datetime.datetime.now(datetime.timezone.utc)
        super().__init__(
            hass,
            _LOGGER,
            name="ElectroCarsCoordinator",
            update_interval=datetime.timedelta(hours=1),
            update_method=self._async_update_data,
        )
        self.api = api
        self.data = []

    async def _async_update_data(self):
        """Fetch data from ElectroCars API and adjust update interval."""
        cars = await self.api.get_cars()
        if cars:
            self.data = cars

            any_moving = any(car.get("telematics", [{}])[0].get("moving") for car in cars)
            any_charging = any(car.get("telematics", [{}])[0].get("charging") for car in cars)

            now = datetime.datetime.now(datetime.timezone.utc)
            if any_moving or any_charging:
                # If moving or charging, update every 5 minutes
                new_interval = datetime.timedelta(minutes=5)
                self._last_active = now
            else:
                # If stopped for more than 10 minutes, switch to 1 hour
                last_active = getattr(self, "_last_active", now)
                if (now - last_active) > datetime.timedelta(minutes=10):
                    new_interval = datetime.timedelta(hours=1)
                else:
                    new_interval = datetime.timedelta(minutes=10)

            if self.update_interval != new_interval:
                self.update_interval = new_interval

        return self.data