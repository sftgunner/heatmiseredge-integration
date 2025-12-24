"""The heatmiser_edge component."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import Platform, CONF_HOST, CONF_PORT
import voluptuous as vol
from homeassistant.helpers import device_registry as dr
# from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import DeviceInfo

from .const import *
from .heatmiser_edge import *

# List of platforms to support. There should be a matching .py file for each,
# eg <cover.py> and <sensor.py>
# PLATFORMS = [Platform.CLIMATE, Platform.NUMBER]
PLATFORMS_THERMOSTAT = [Platform.CLIMATE, Platform.NUMBER, Platform.TIME, Platform.BUTTON, Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SELECT]
PLATFORMS_TIMER = [Platform.SWITCH, Platform.NUMBER, Platform.TIME, Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SELECT]
PLATFORMS_ALL = [Platform.CLIMATE, Platform.SWITCH, Platform.NUMBER, Platform.TIME, Platform.BUTTON, Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SELECT]

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up is called when Home Assistant is loading our component."""
    # Important that the service action is registered in this function to ensure that it still responds with a helpful error if no config entry is set up
    
    # TODO: Add service to force register to be refreshed
    # TODO: Add service to bulk write to multiple registers at once
    
    async def write_register(call: ServiceCall) -> None:
        """Handle the service call to write a register."""
        _LOGGER.debug(f"[DEBUG] write_register service called with data: {call.data}")
        # if not call.target:
        #     raise ValueError("No target device specified")
            
        device_registry = dr.async_get(hass)
        
        # Handle both device_id and device formats
        # device_ids = []
        # if "device_id" in call.target:
        #     device_ids.append(call.target["device_id"])
        # elif "device" in call.target:
        #     device_ids.extend(call.target["device"])
        
        device_ids = call.data.get("device_id")
        
        for device_id in device_ids:
            _LOGGER.debug(f"[DEBUG] Processing device_id: {device_id}")
            
            device_entry = device_registry.async_get(device_id)
            if not device_entry:
                raise ValueError(f"Device {device_id} not found")
                
            # Find the config entry for this device
            config_entry_id = next(iter(device_entry.config_entries))
            register_store = hass.data[DOMAIN].get(config_entry_id)
            
            if not register_store:
                raise ValueError(f"Device {device_id} is not a Heatmiser Edge device")
            
            register = call.data.get("register")
            if register < 50 or register > 217:
                raise ValueError("Register must be between 50 and 217 (schedule area)")
            
            value = call.data.get("value")
            
            refresh_values_after_writing = call.data.get("refresh_values_after_writing",False)
            
            _LOGGER.debug(f"[DEBUG] Service call to write register {register} with value {value} for device {device_id}")
            
            await register_store.write_register(register, value, refresh_values_after_writing)
            
    async def write_register_range(call: ServiceCall) -> None:
        """Handle the service call to write a range of registers."""
        _LOGGER.debug(f"[DEBUG] write_register_range service called with data: {call.data}")
        # if not call.target:
        #     raise ValueError("No target device specified")
            
        device_registry = dr.async_get(hass)
        
        device_ids = call.data.get("device_id")
        
        for device_id in device_ids:
            _LOGGER.debug(f"[DEBUG] Processing device_id: {device_id}")
            
            device_entry = device_registry.async_get(device_id)
            if not device_entry:
                raise ValueError(f"Device {device_id} not found")
                
            # Find the config entry for this device
            config_entry_id = next(iter(device_entry.config_entries))
            register_store = hass.data[DOMAIN].get(config_entry_id)
            
            if not register_store:
                raise ValueError(f"Device {device_id} is not a Heatmiser Edge device")
            
            start_register = call.data.get("register")
            if start_register < 50 or start_register > 217:
                raise ValueError("Start register must be between 50 and 217 (schedule area)")
            
            valuesString = call.data.get("values")
            values = valuesString.split(",")
            values = [int(v) for v in values]
            # if not isinstance(values, list) or not all(isinstance(v, int) for v in values):
            #     raise ValueError("Values must be a list of integers")
            
            refresh_values_after_writing = call.data.get("refresh_values_after_writing",False)
            
            if start_register + len(values) - 1 > 217:
                raise ValueError("Register range exceeds schedule area (max register 217)")
            
            _LOGGER.debug(f"[DEBUG] Service call to write registers starting at {start_register} with values {values} for device {device_id}")
            
            await register_store.write_register_range(start_register, values, refresh_values_after_writing)

    # Register the service
    hass.services.async_register(
        DOMAIN,
        "write_register",
        write_register
        # Schema seems to be more trouble than it's worth, keeps complaining about device_id
        # schema=vol.Schema({
        #     vol.Required("device_id"): None,
        #     vol.Required("register"): int,
        #     vol.Required("value"): int,
        # })
    )

    hass.services.async_register(
        DOMAIN,
        "write_register_range",
        write_register_range
        # Schema seems to be more trouble than it's worth, keeps complaining about device_id
        # schema=vol.Schema({
        #     vol.Required("device_id"): None,
        #     vol.Required("register"): int,
        #     vol.Required("value"): int,
        # })
    )

    # Return boolean to indicate that initialization was successful.
    return True


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