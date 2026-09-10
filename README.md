# Integration for Tap Electric EVSE in Home Assistant

This integration requires a Tap Electric API key. You can create this in the account settings.
After setting up the integration by providing the API key, all chargers & connectors will be discovered.
You'll get basic info about the charger (serial number, status, online status, amount of connectors and the status of each connector).
There is also a "tap_electric.remote_start" service which can be used to remotely start a charging session with a specific NFC UID (optional).
