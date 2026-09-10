"""Sensor platform for Tap Electric."""

import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensors."""
    coordinators = hass.data[DOMAIN][entry.entry_id]["coordinators"]

    entities = []
    for charger_id, coordinator in coordinators.items():
        if not coordinator.data:
            continue

        entities.append(TapElectricChargerStatusSensor(coordinator, charger_id))
        entities.append(TapElectricConnectorCountSensor(coordinator, charger_id))

        for connector in coordinator.data.get("connectors", []):
            conn_id = connector.get("id")
            if conn_id is not None:
                entities.append(
                    TapElectricConnectorStatusSensor(coordinator, charger_id, conn_id)
                )

    async_add_entities(entities)


class TapElectricBaseSensor(CoordinatorEntity, SensorEntity):
    """Base sensor class for Tap Electric."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, charger_id):
        """Initialize the base sensor."""
        super().__init__(coordinator)
        self.charger_id = charger_id

    @property
    def device_info(self):
        """Return device information."""
        data = self.coordinator.data or {}
        return {
            "identifiers": {(DOMAIN, self.charger_id)},
            "name": data.get("name") or f"Tap Charger {self.charger_id}",
            "manufacturer": "Tap Electric",
        }


class TapElectricChargerStatusSensor(TapElectricBaseSensor):
    """Sensor for general charger status."""

    def __init__(self, coordinator, charger_id):
        """Initialize the status sensor."""
        super().__init__(coordinator, charger_id)
        self._attr_unique_id = f"tapelectric_{charger_id}_status"
        self._attr_name = "Charger Status"
        self._attr_icon = "mdi:ev-station"

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        data = self.coordinator.data or {}
        return data.get("status", "UNKNOWN")


class TapElectricConnectorCountSensor(TapElectricBaseSensor):
    """Sensor for the number of connectors."""

    def __init__(self, coordinator, charger_id):
        """Initialize the connector count sensor."""
        super().__init__(coordinator, charger_id)
        self._attr_unique_id = f"tapelectric_{charger_id}_connector_count"
        self._attr_name = "Connectors"
        self._attr_icon = "mdi:numeric"

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        data = self.coordinator.data or {}
        return len(data.get("connectors", []))


class TapElectricConnectorStatusSensor(TapElectricBaseSensor):
    """Sensor for individual connector status."""

    def __init__(self, coordinator, charger_id, connector_id):
        """Initialize the individual connector sensor."""
        super().__init__(coordinator, charger_id)
        self.connector_id = connector_id
        self._attr_unique_id = (
            f"tapelectric_{charger_id}_connector_{connector_id}_status"
        )
        self._attr_name = f"Connector {connector_id} Status"
        self._attr_icon = "mdi:ev-plug-type2"

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        data = self.coordinator.data or {}
        connectors = data.get("connectors", [])
        for conn in connectors:
            if str(conn.get("id")) == str(self.connector_id):
                return conn.get("status", "UNKNOWN")
        return "UNKNOWN"
