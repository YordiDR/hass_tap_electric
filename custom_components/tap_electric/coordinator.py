"""DataUpdateCoordinator for Tap Electric."""

import logging
import json
from datetime import datetime, timedelta, timezone
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def _parse_timestamp(msg: dict) -> datetime:
    """Safely parse the requestedAt timestamp for sorting."""
    ts_str = msg.get("requestedAt")
    
    # Fallback to the timestamp inside the request payload if requestedAt is missing
    if not ts_str:
        try:
            payload = json.loads(msg.get("requestPayload", "{}"))
            ts_str = payload.get("timestamp")
        except (json.JSONDecodeError, TypeError):
            pass

    if ts_str:
        try:
            # Replace Z with +00:00 for broader Python version compatibility
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            pass

    # Fallback to the earliest possible time if parsing fails
    return datetime.min.replace(tzinfo=timezone.utc)


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
        base_url = f"https://api.tapelectric.app/api/v1/chargers/{self.charger_id}"
        ocpp_url = f"{base_url}/ocpp"
        headers = {"X-Api-Key": self.api_key}

        try:
            # 1. Fetch base charger data
            async with self.session.get(base_url, headers=headers) as response:
                if response.status != 200:
                    error_msg = await response.text()
                    raise UpdateFailed(f"Error fetching charger data: {error_msg}")
                data = await response.json()

            # 2. Fetch StartTransaction messages
            params_start = {"limit": 10, "offset": 0, "action": "StartTransaction"}
            async with self.session.get(ocpp_url, headers=headers, params=params_start) as resp_start:
                start_messages = await resp_start.json() if resp_start.status == 200 else []

            # 3. Fetch StopTransaction messages
            params_stop = {"limit": 10, "offset": 0, "action": "StopTransaction"}
            async with self.session.get(ocpp_url, headers=headers, params=params_stop) as resp_stop:
                stop_messages = await resp_stop.json() if resp_stop.status == 200 else []

            # Parse StopTransaction IDs into a fast lookup set
            stopped_transaction_ids = set()
            for stop_msg in stop_messages:
                try:
                    req_payload = json.loads(stop_msg.get("requestPayload", "{}"))
                    if "transactionId" in req_payload:
                        stopped_transaction_ids.add(req_payload["transactionId"])
                except (json.JSONDecodeError, TypeError):
                    continue

            # Sort the start messages descending by time (newest first)
            start_messages.sort(key=_parse_timestamp, reverse=True)

            # Determine active sessions per connector
            active_sessions = {}
            for start_msg in start_messages:
                try:
                    req_payload = json.loads(start_msg.get("requestPayload", "{}"))
                    connector_id = req_payload.get("connectorId")

                    # Because the list is sorted newest-first, we only need to evaluate the first hit per connector.
                    if connector_id is not None and connector_id not in active_sessions:
                        resp_payload_raw = start_msg.get("responsePayload")
                        transaction_id = None
                        
                        if resp_payload_raw:
                            resp_payload = json.loads(resp_payload_raw)
                            # StartTransaction responsePayload format is usually: [3, "MessageID", {"transactionId": 12345}]
                            if isinstance(resp_payload, list) and len(resp_payload) >= 3:
                                transaction_id = resp_payload[2].get("transactionId")

                        # The session is active if it was assigned a transaction ID and it hasn't been stopped.
                        active_sessions[connector_id] = bool(
                            transaction_id and transaction_id not in stopped_transaction_ids
                        )
                except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                    continue

            # Append the calculated sessions into the coordinator's parsed data
            data["active_sessions"] = active_sessions

            return data

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")