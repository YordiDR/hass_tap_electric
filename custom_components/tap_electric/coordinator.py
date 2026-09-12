"""DataUpdateCoordinator for Tap Electric."""

import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class TapElectricChargerCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from a single Tap Electric charger."""

    def __init__(self, hass, session, api_key, charger_id, update_interval):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{charger_id}",
            update_interval=timedelta(seconds=update_interval),
        )
        self.session = session
        self.api_key = api_key
        self.charger_id = charger_id

    async def _async_update_data(self):
        """Fetch data from API endpoint for this specific charger."""
        url = f"https://api.tapelectric.app/api/v1/chargers/{self.charger_id}"
        headers = {"X-Api-Key": self.api_key}

        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    error_msg = await response.text()
                    raise UpdateFailed(f"Error fetching charger data: {error_msg}")

                return await response.json()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")