"""Binary sensor platform for Tap Electric."""

import logging
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the binary sensors."""
    coordinators = hass.data[DOMAIN][entry.entry_id]["coordinators"]

    entities = []
    for charger_id, coordinator in coordinators.items():
        if coordinator.data:
            entities.append(TapElectricOnlineSensor(coordinator, charger_id))

    async_add_entities(entities)


class TapElectricOnlineSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for charger online status."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_has_entity_name = True

    def __init__(self, coordinator, charger_id):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.charger_id = charger_id
        self._attr_unique_id = f"tapelectric_{charger_id}_online"
        self._attr_name = "Online"

    @property
    def device_info(self):
        """Return device information to link to the device registry."""
        data = self.coordinator.data or {}
        return {
            "identifiers": {(DOMAIN, self.charger_id)},
            "name": data.get("name") or f"Tap Charger {self.charger_id}",
            "manufacturer": "Tap Electric",
            "serial_number": self.charger_id,
        }

    @property
    def is_on(self):
        """Return true if the charger is online."""
        data = self.coordinator.data or {}
        return data.get("online") is True
