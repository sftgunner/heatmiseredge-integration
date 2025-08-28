"""The heatmiser_edge component."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import *
from .heatmiser_edge import *

# List of platforms to support. There should be a matching .py file for each,
# eg <cover.py> and <sensor.py>
# PLATFORMS = [Platform.CLIMATE, Platform.NUMBER]
PLATFORMS_THERMOSTAT = [Platform.CLIMATE, Platform.NUMBER, Platform.TIME, Platform.BUTTON, Platform.SENSOR, Platform.BINARY_SENSOR]
PLATFORMS_TIMER = [Platform.SWITCH, Platform.BINARY_SENSOR, Platform.NUMBER, Platform.SENSOR]
PLATFORMS_ALL = [Platform.CLIMATE, Platform.NUMBER, Platform.TIME, Platform.BUTTON, Platform.SENSOR, Platform.BINARY_SENSOR,Platform.SWITCH]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up heatmiser edge from a config entry."""
    # Store an instance of the "connecting" class that does the work of speaking
    # with your actual devices.
    # hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub.Hub(hass, entry.data["host"])

    # Create the register store that will hold the values read from the device
    # NB this is initialised in heatmiser_edge.py
    register_store = heatmiser_edge_register_store(entry.data["host"],entry.data["port"],entry.data["modbus_id"])

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = register_store

    await register_store.async_update() # Make sure values are all up to date in the register store

    # This creates each HA object for each platform your device requires.
    # It's done by calling the `async_setup_entry` function in each platform module.

    # Detect whether a thermostat or a timer
    if register_store.device_type == DEVICE_TYPE_THERMOSTAT:
        # Thermostat - room temperature would be greater than 1
        _LOGGER.debug(f"Detecting device {entry.data['host']} channel {entry.data['modbus_id']} as being a thermostat")
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS_THERMOSTAT)
    elif register_store.device_type == DEVICE_TYPE_TIMER:
        # Timer - thermostat on/off mode can only be 1 or 0
        _LOGGER.debug(f"Detecting device {entry.data['host']} channel {entry.data['modbus_id']} as being a timer")
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS_TIMER)
    else:
        _LOGGER.error(f"Unable to detect device type for {entry.data['host']} channel {entry.data['modbus_id']}. Not loading any platforms")
        return False
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    # if entry.data["device_type"] == DEVICE_TYPE_TIMER:
    #     unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS_TIMER)
    # else:
    #     unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS_THERMOSTAT)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS_ALL) # This is a bit of a hack, should ideally only unload the platforms used by a given entry

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok