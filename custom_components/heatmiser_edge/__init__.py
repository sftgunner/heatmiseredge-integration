"""The heatmiser_edge component."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import DOMAIN
from .heatmiser_edge import *

# List of platforms to support. There should be a matching .py file for each,
# eg <cover.py> and <sensor.py>
# PLATFORMS = [Platform.CLIMATE, Platform.NUMBER]
PLATFORMS = [Platform.CLIMATE, Platform.NUMBER, Platform.TIME]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up heatmiser edge from a config entry."""
    # Store an instance of the "connecting" class that does the work of speaking
    # with your actual devices.
    # hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub.Hub(hass, entry.data["host"])

    register_store = heatmiser_edge_register_store(entry.data["host"],entry.data["port"],entry.data["modbus_id"])

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = register_store

    await register_store.async_update() # Make sure values are all up to date

    # This creates each HA object for each platform your device requires.
    # It's done by calling the `async_setup_entry` function in each platform module.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok