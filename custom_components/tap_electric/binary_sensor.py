"""Binary sensor platform for Tap Electric."""

import logging
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ACTIVE_STATUSES = {"CHARGING", "SUSPENDEDEV", "SUSPENDEDEVSE"}

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the binary sensors."""
    coordinators = hass.data[DOMAIN][entry.entry_id]["coordinators"]

    entities = []
    for charger_id, coordinator in coordinators.items():
        if coordinator.data:
            entities.append(TapElectricOnlineSensor(coordinator, charger_id))

            for connector in coordinator.data.get("connectors", []):
                conn_id = connector.get("id")
                if conn_id is not None:
                    entities.append(
                        TapElectricConnectorSessionSensor(coordinator, charger_id, conn_id)
                    )

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
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        charger_id_str = str(self.charger_id)
        data = self.coordinator.data or {}
        return DeviceInfo(
            identifiers={(DOMAIN, charger_id_str)},
            name=data.get("name") or f"Tap Charger {charger_id_str}",
            manufacturer="Tap Electric",
            serial_number=charger_id_str,
        )

    @property
    def is_on(self) -> bool:
        """Return true if the charger is online."""
        data = self.coordinator.data or {}
        return data.get("online") is True


class TapElectricConnectorSessionSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor representing an active charging session."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, charger_id: str, connector_id: int):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._charger_id = charger_id
        self._connector_id = connector_id
        
        self._attr_unique_id = f"tapelectric_{charger_id}_connector_{connector_id}_session"
        self._attr_name = f"Connector {connector_id} session active"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        charger_id_str = str(self._charger_id)
        data = self.coordinator.data or {}
        return DeviceInfo(
            identifiers={(DOMAIN, charger_id_str)},
            name=data.get("name") or f"Tap Charger {charger_id_str}",
            manufacturer="Tap Electric",
            serial_number=charger_id_str,
        )

    @property
    def is_on(self) -> bool:
        """Return true if the session is active based on connector status."""
        data = self.coordinator.data or {}
        connectors = data.get("connectors", [])

        for conn in connectors:
            if str(conn.get("id")) == str(self._connector_id):
                status = str(conn.get("status", "")).upper()
                return status in ACTIVE_STATUSES

        return False