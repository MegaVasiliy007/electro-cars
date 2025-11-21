import aiohttp
import async_timeout
import logging
from typing import Optional

_LOGGER = logging.getLogger(__name__)

AUTH_BASE = "https://fleet-gateway.technotrek.ru/api/auth"
FLEET_BASE = "https://fleet-api.technotrek.ru"
APP_ID = "7542fd74-47bd-4652-b422-6ef7d610582e"

class ElectroCarsAPI:
    def __init__(self, entry: Optional["ConfigEntry"] = None):
        self._access_token = None
        self._refresh_token = None
        self._phone = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._entry = entry

    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

    async def initialize(self, hass, entry):
        self._session = aiohttp.ClientSession()
        self._entry = entry
        self._phone = entry.data.get("phone")
        self._refresh_token = entry.data.get("refresh_token")
        self._hass = hass
        if self._refresh_token and not self._access_token:
            await self.refresh_access_token(hass)

        # Здесь можно вставить загрузку refresh_token из storage и авто-обновление access_token
        # Пока просто заглушка

    async def send_sms(self, phone: str) -> bool:
        await self._ensure_session()
        self._phone = phone
        payload = {"phone_number": phone}
        async with async_timeout.timeout(10):
            async with self._session.post(f"{AUTH_BASE}/send-code", json=payload, headers={"x-app-id": APP_ID}) as resp:
                if resp.status == 200:
                    _LOGGER.debug("SMS code sent to %s", phone)
                    return True
                text = await resp.text()
                _LOGGER.warning("Failed to send SMS: %s", text)
                return False

    async def login_with_code(self, code: str) -> Optional[dict[str, str]]:
        await self._ensure_session()
        payload = {
            "phone_number": self._phone,
            "code": code
        }
        async with async_timeout.timeout(10):
            async with self._session.post(f"{AUTH_BASE}/token/sms", json=payload, headers={"x-app-id": APP_ID}) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    self._access_token = data["access_token"]
                    cookies = resp.cookies
                    if "refresh_token" in cookies:
                        self._refresh_token = cookies["refresh_token"].value
                    else:
                        _LOGGER.error("Missing refresh_token in response cookies")
                        return None
                    _LOGGER.info("Login successful for %s", self._phone)
                    return {
                        "access_token": self._access_token,
                        "refresh_token": self._refresh_token
                    }
                text = await resp.text()
                _LOGGER.warning("Login failed: %s", text)
                _LOGGER.error("Login failed response body: %s", text)
                return None

    async def refresh_access_token(self, hass) -> bool:
        await self._ensure_session()
        async with async_timeout.timeout(10):
            async with self._session.post(
                f"{AUTH_BASE}/refresh",
                cookies={"refresh_token": self._refresh_token},
                headers={"x-app-id": APP_ID}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    access = data.get("access_token")
                    if not access:
                        _LOGGER.error("Refresh token response missing access_token: %s", data)
                        return False
                    self._access_token = access
                    # Extract and store new refresh_token from cookies if available
                    cookies = resp.cookies
                    if "refresh_token" in cookies:
                        self._refresh_token = cookies["refresh_token"].value
                        if self._entry:
                            async def _save_refresh_token():
                                new_data = {**self._entry.data, "refresh_token": self._refresh_token}
                                hass.config_entries.async_update_entry(
                                    self._entry,
                                    data=new_data,
                                )

                            hass.async_create_task(_save_refresh_token())
                    else:
                        _LOGGER.warning("Refresh response did not include a new refresh_token.")
                    _LOGGER.info("Access token refreshed")
                    return True
                text = await resp.text()
                _LOGGER.error("Failed to refresh token: %s", text)
                return False

    async def get_cars(self) -> Optional[list]:
        await self._ensure_session()
        headers = {"Authorization": f"Bearer {self._access_token}"}
        async with async_timeout.timeout(10):
            async with self._session.get(f"{FLEET_BASE}/car?limit=100&offset=0&filter=%5B%5D", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["result"]["items"]
                elif resp.status == 401:
                    _LOGGER.warning("Access token invalid, trying to refresh...")
                    if await self.refresh_access_token(self._hass):
                        return await self.get_cars()
                text = await resp.text()
                _LOGGER.error("Failed to get cars: %s", text)
                return None

    async def get_commands(self, imei: str) -> Optional[list]:
        """Get list of available commands for a specific device."""
        await self._ensure_session()
        headers = {"Authorization": f"Bearer {self._access_token}"}
        async with async_timeout.timeout(10):
            async with self._session.get(f"{FLEET_BASE}/telematics/devices/{imei}/commands", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["result"]
                elif resp.status == 500:
                    _LOGGER.warning("Access token invalid, trying to refresh...")
                    if await self.refresh_access_token(self._hass):
                        return await self.get_commands(imei)
                text = await resp.text()
                _LOGGER.error("Failed to get commands: %s", text)
                return None

    async def send_command(self, imei: str, command: int) -> bool:
        """Send a specific command to the device."""
        await self._ensure_session()
        headers = {"Authorization": f"Bearer {self._access_token}"}
        payload = {"command": command}
        async with async_timeout.timeout(10):
            async with self._session.post(f"{FLEET_BASE}/telematics/devices/{imei}/commands", headers=headers, json=payload) as resp:
                if resp.status == 200:
                    _LOGGER.info("Command %s sent successfully to device %s", command, imei)
                    return True
                elif resp.status == 500:
                    _LOGGER.warning("Access token invalid, trying to refresh...")
                    if await self.refresh_access_token(self._hass):
                        return await self.send_command(imei, command)
                text = await resp.text()
                _LOGGER.error("Failed to send command: %s", text)
                return False

    async def close(self):
        if self._session:
            await self._session.close()
