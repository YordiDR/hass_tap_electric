"""The Tap Electric integration."""

import logging
import json
import asyncio
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.exceptions import HomeAssistantError, ConfigEntryNotReady

from .const import DOMAIN, CONF_API_KEY, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
from .coordinator import TapElectricChargerCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_REMOTE_START = "remote_start"
PLATFORMS = ["sensor", "binary_sensor", "button"]

# Fixed Schema: connector_id is an integer, nfc_uid is a string
SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required("connector_id"): vol.Coerce(int),
        vol.Optional("nfc_uid"): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tap Electric from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    api_key = entry.data[CONF_API_KEY]
    update_interval = entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    session = async_get_clientsession(hass)

    # 1. Discovery phase: get all chargers once
    discovery_url = "https://api.tapelectric.app/api/v1/chargers"
    headers = {"X-Api-Key": api_key}

    try:
        async with session.get(discovery_url, headers=headers) as resp:
            if resp.status != 200:
                _LOGGER.error("Discovery failed. HTTP %s", resp.status)
                raise ConfigEntryNotReady
            chargers_list = await resp.json()
    except Exception as err:
        _LOGGER.error("Failed to connect to Tap Electric API for discovery: %s", err)
        raise ConfigEntryNotReady

    # 2. Setup coordinators per charger
    coordinators = {}
    for charger in chargers_list:
        _LOGGER.debug("Setting up charger: %s", charger)
        charger_id = charger.get("id")
        if not charger_id:
            continue

        coordinator = TapElectricChargerCoordinator(
            hass, session, api_key, charger_id, update_interval
        )
        await coordinator.async_config_entry_first_refresh()
        coordinators[charger_id] = coordinator

    hass.data[DOMAIN][entry.entry_id] = {"coordinators": coordinators}

    # 3. Setup platforms (sensors, binary_sensors)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 4. Define and register the remote start service
    async def handle_remote_start(call: ServiceCall):
        """Handle the remote start service call."""
        device_id = call.data["device_id"]
        connector_id = call.data["connector_id"]  # Integer
        nfc_uid = call.data.get("nfc_uid")  # String or None

        device_registry = dr.async_get(hass)
        device = device_registry.async_get(device_id)
        if not device:
            raise HomeAssistantError(f"Device with ID {device_id} not found.")

        charger_id = None
        for identifier in device.identifiers:
            if identifier[0] == DOMAIN:
                charger_id = identifier[1]
                break

        if not charger_id:
            raise HomeAssistantError("No valid Tap Electric device selected.")

        coordinator = coordinators.get(charger_id)
        if not coordinator:
            raise HomeAssistantError(f"Coordinator for charger {charger_id} not found.")

        await coordinator.async_request_refresh()

        charger_data = coordinator.data
        if not charger_data:
            raise HomeAssistantError(f"Charger data for {charger_id} is empty.")

        status = None
        for conn in charger_data.get("connectors", []):
            if conn.get("id") == connector_id or str(conn.get("id")) == str(
                connector_id
            ):
                status = conn.get("status")
                break

        if not status:
            raise HomeAssistantError(
                f"Connector {connector_id} not found on charger {charger_id}."
            )

        allowed_statuses = ["PREPARING", "FINISHING", "SUSPENDEDEVSE"]
        if status not in allowed_statuses:
            raise HomeAssistantError(
                f"Connector is in invalid state to start: {status}"
            )

        url_post = f"https://api.tapelectric.app/api/v1/chargers/{charger_id}/ocpp"

        # connectorId is serialized as integer, idTag as string
        inner_dict = {"connectorId": connector_id}
        if nfc_uid:
            inner_dict["idTag"] = str(nfc_uid)

        payload = {
            "action": "RemoteStartTransaction",
            "ocppVersion": "ocpp1.6",
            "data": json.dumps(inner_dict),
        }

        headers_post = {"Content-Type": "application/json", "X-Api-Key": api_key}

        async with session.post(
            url_post, json=payload, headers=headers_post
        ) as resp_post:
            if resp_post.status != 200:
                error_msg = await resp_post.text()
                raise HomeAssistantError(
                    f"Failed to start charging session: {error_msg}"
                )

        async def _delayed_refresh():
            await asyncio.sleep(3)
            await coordinator.async_request_refresh()

        # Schedule task in background so service call completes immediately
        hass.async_create_task(_delayed_refresh())

    hass.services.async_register(
        DOMAIN, SERVICE_REMOTE_START, handle_remote_start, schema=SERVICE_SCHEMA
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.services.async_remove(DOMAIN, SERVICE_REMOTE_START)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
