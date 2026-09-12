"""Button platform for Tap Electric."""

import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the button platform."""
    coordinators = hass.data[DOMAIN][entry.entry_id]["coordinators"]

    entities = []
    for charger_id, coordinator in coordinators.items():
        entities.append(TapElectricRefreshButton(coordinator, charger_id))

    async_add_entities(entities)


class TapElectricRefreshButton(CoordinatorEntity, ButtonEntity):
    """Button to force a data refresh for the charger."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, charger_id):
        """Initialize the button."""
        super().__init__(coordinator)
        self.charger_id = charger_id
        
        self._attr_unique_id = f"tapelectric_{charger_id}_refresh"
        self._attr_name = "Refresh"
        self._attr_icon = "mdi:refresh"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information to link to the device registry."""
        charger_id_str = str(self.charger_id)
        data = self.coordinator.data or {}
        
        return DeviceInfo(
            identifiers={(DOMAIN, charger_id_str)},
            name=data.get("name") or f"Tap Charger {charger_id_str}",
            manufacturer="Tap Electric",
            serial_number=charger_id_str,
        )

    async def async_press(self) -> None:
        """Handle the button press by forcing a data update."""
        await self.coordinator.async_request_refresh()