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
from homeassistant.exceptions import ServiceValidationError, ConfigEntryNotReady
from homeassistant.components.modbus import async_get_unit
from modbus_connection import ModbusError, ModbusTcpParams

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
        
        device_ids = call.data.get("device")
        if isinstance(device_ids, str):
            device_ids = [device_ids]
        
        for device_id in device_ids:
            _LOGGER.debug(f"[DEBUG] Processing device_id: {device_id}")
            
            device_entry = device_registry.async_get(device_id)
            if not device_entry:
                raise ServiceValidationError(f"Device {device_id} not found")
                
            # Find the config entry for this device
            config_entry_id = next(iter(device_entry.config_entries))
            register_store = hass.data[DOMAIN].get(config_entry_id)
            
            if not register_store:
                raise ServiceValidationError(f"Device {device_id} is not a Heatmiser Edge device")
            
            register = call.data.get("register")
            if register < 50 or register > 217:
                raise ServiceValidationError("Register must be between 50 and 217 (schedule area)")
            
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
        
        device_ids = call.data.get("device")
        if isinstance(device_ids, str):
            device_ids = [device_ids]
        
        for device_id in device_ids:
            _LOGGER.debug(f"[DEBUG] Processing device_id: {device_id}")
            
            device_entry = device_registry.async_get(device_id)
            if not device_entry:
                raise ServiceValidationError(f"Device {device_id} not found")
                
            # Find the config entry for this device
            config_entry_id = next(iter(device_entry.config_entries))
            register_store = hass.data[DOMAIN].get(config_entry_id)
            
            if not register_store:
                raise ServiceValidationError(f"Device {device_id} is not a Heatmiser Edge device")
            
            start_register = call.data.get("register")
            if start_register < 50 or start_register > 217:
                raise ServiceValidationError("Start register must be between 50 and 217 (schedule area)")
            
            valuesString = call.data.get("values")
            values = valuesString.split(",")
            values = [int(v) for v in values]
            # if not isinstance(values, list) or not all(isinstance(v, int) for v in values):
            #     raise ValueError("Values must be a list of integers")
            
            refresh_values_after_writing = call.data.get("refresh_values_after_writing",False)
            
            if start_register + len(values) - 1 > 217:
                raise ServiceValidationError("Register range exceeds schedule area (max register 217)")
            
            _LOGGER.debug(f"[DEBUG] Service call to write registers starting at {start_register} with values {values} for device {device_id}")
            
            await register_store.write_register_range(start_register, values, refresh_values_after_writing)

    async def boost_thermostat_heating(call: ServiceCall) -> None:
        """Handle the service call to temporarily boost thermostat heating."""
        _LOGGER.debug(f"[DEBUG] boost_thermostat_heating service called with data: {call.data}")
        
        device_registry = dr.async_get(hass)
        device_ids = call.data.get("device")
        if isinstance(device_ids, str):
            device_ids = [device_ids]
        
        for device_id in device_ids:
            _LOGGER.debug(f"[DEBUG] Processing device_id: {device_id}")
            
            device_entry = device_registry.async_get(device_id)
            if not device_entry:
                raise ServiceValidationError(f"Device {device_id} not found")
                
            # Find the config entry for this device
            config_entry_id = next(iter(device_entry.config_entries))
            register_store = hass.data[DOMAIN].get(config_entry_id)
            
            # Check it has a register store (i.e. is a Heatmiser Edge device)
            if not register_store:
                raise ServiceValidationError(f"Device {device_id} is not a Heatmiser Edge device")
            
            # Check device is a thermostat
            if register_store.device_type != DEVICE_TYPE_THERMOSTAT:
                raise ServiceValidationError(f"Device {device_id} is not a thermostat")
            
            # Get service parameters
            temperature = call.data.get("temperature")
            duration_hours = call.data.get("duration_hours", 0)
            duration_minutes = call.data.get("duration_minutes", 0)
            frost_protection_override = call.data.get("frost_protection_override", False)
            
            # Check device is not in frost protection mode
            if not frost_protection_override:
                if register_store.registers[int(ThermostatRegisterAddresses.CURRENT_OPERATION_MODE_RD)] == int(PRESET_MODES.index("Frost protection")): # Frost protection mode 
                    raise ServiceValidationError(f"Device {device_id} is currently in frost protection mode. Boosting is not allowed in this mode unless 'frost_protection_override' is set to true.")
            
            # Validate parameters
            if not 5 <= temperature <= 35:
                raise ServiceValidationError("Temperature must be between 5 and 35 degrees Celsius")
            if not 0 <= duration_hours <= 99:
                raise ServiceValidationError("Duration hours must be between 0 and 99")
            if not 0 <= duration_minutes <= 59:
                raise ServiceValidationError("Duration minutes must be between 0 and 59")
            
            _LOGGER.info(f"Boosting thermostat {device_id} to {temperature}°C for {duration_hours}h{duration_minutes}m")
            
            try:
                # Step 1: Sync time to device
                await register_store.async_update_device_time()
                
                # Step 2: Update hold time register (HOLDTIME_HOUR_MIN)
                # High 8 bits = hours, low 8 bits = minutes
                hold_time_value = (duration_hours << 8) | duration_minutes
                await register_store.write_register(
                    int(ThermostatRegisterAddresses.HOLDTIME_HOUR_MIN),
                    hold_time_value,
                    refresh_values_after_writing=False
                )
                
                # Step 3: Update hold set temperature register
                # Temperature is scaled by factor of 10 (20°C = 200)
                temp_register_value = int(temperature * 10)
                await register_store.write_register(
                    int(ThermostatRegisterAddresses.HOLD_SET_TEMPERATURE),
                    temp_register_value,
                    refresh_values_after_writing=False
                )
                
                # Step 4: Change operation mode to Hold
                # "Hold" is at index 2 in PRESET_MODES
                await register_store.write_register(
                    int(ThermostatRegisterAddresses.CURRENT_OPERATION_MODE),
                    2,  # Hold mode
                    refresh_values_after_writing=True
                )
            except Exception as ex:
                _LOGGER.error(f"Error boosting thermostat: {ex}")
                raise

    async def boost_timer_output(call: ServiceCall) -> None:
        """Handle the service call to temporarily boost timer output."""
        _LOGGER.debug(f"[DEBUG] boost_timer_output service called with data: {call.data}")
        
        device_registry = dr.async_get(hass)
        device_ids = call.data.get("device")
        if isinstance(device_ids, str):
            device_ids = [device_ids]
        
        for device_id in device_ids:
            _LOGGER.debug(f"[DEBUG] Processing device_id: {device_id}")
            
            device_entry = device_registry.async_get(device_id)
            if not device_entry:
                raise ServiceValidationError(f"Device {device_id} not found")
                
            # Find the config entry for this device
            config_entry_id = next(iter(device_entry.config_entries))
            register_store = hass.data[DOMAIN].get(config_entry_id)
            
            if not register_store:
                raise ServiceValidationError(f"Device {device_id} is not a Heatmiser Edge device")
            
            if register_store.device_type != DEVICE_TYPE_TIMER:
                raise ServiceValidationError(f"Device {device_id} is not a timer")
            
            # Get service parameters
            state = call.data.get("state")
            duration_hours = call.data.get("duration_hours", 0)
            duration_minutes = call.data.get("duration_minutes", 0)
            frost_protection_override = call.data.get("frost_protection_override", False)
            
            # Check device is not in frost protection mode
            if not frost_protection_override:
                if register_store.registers[int(TimerRegisterAddresses.CURRENT_OPERATION_MODE_RD)] == int(PRESET_MODES.index("Frost protection")): # Frost protection mode 
                    raise ServiceValidationError(f"Device {device_id} is currently in frost protection mode. Boosting is not allowed in this mode unless 'frost_protection_override' is set to true.")
            
            # Validate parameters
            if not 0 <= duration_hours <= 99:
                raise ServiceValidationError("Duration hours must be between 0 and 99")
            if not 0 <= duration_minutes <= 59:
                raise ServiceValidationError("Duration minutes must be between 0 and 59")
            
            _LOGGER.info(f"Boosting timer {device_id} to {state} for {duration_hours}h{duration_minutes}m")
            
            try:
                # Step 1: Sync time to device
                await register_store.async_update_device_time()
                
                # Step 2: Update hold time register (HOLDTIME_HOUR_MIN)
                # High 8 bits = hours, low 8 bits = minutes
                hold_time_value = (duration_hours << 8) | duration_minutes
                await register_store.write_register(
                    int(TimerRegisterAddresses.HOLDTIME_HOUR_MIN),
                    hold_time_value,
                    refresh_values_after_writing=False
                )
                
                # Step 3: Update timer out force register with boolean state
                await register_store.write_register(
                    int(TimerRegisterAddresses.TIMER_OUT_FORCE),
                    1 if state else 0,
                    refresh_values_after_writing=False
                )
                
                # Step 4: Change operation mode to Hold
                # "Hold" is at index 2 in PRESET_MODES
                await register_store.write_register(
                    int(TimerRegisterAddresses.CURRENT_OPERATION_MODE),
                    2,  # Hold mode
                    refresh_values_after_writing=True
                )
            except Exception as ex:
                _LOGGER.error(f"Error boosting timer: {ex}")
                raise

    async def boost_heatmiser_generic(call: ServiceCall) -> None:
        """Handle the service call to boost a thermostat or timer device."""
        _LOGGER.debug(f"[DEBUG] boost_heatmiser_generic service called with data: {call.data}")

        device_registry = dr.async_get(hass)
        device_ids = call.data.get("device")
        if isinstance(device_ids, str):
            device_ids = [device_ids]

        for device_id in device_ids:
            _LOGGER.debug(f"[DEBUG] Processing device_id: {device_id}")

            device_entry = device_registry.async_get(device_id)
            if not device_entry:
                raise ServiceValidationError(f"Device {device_id} not found")

            # Find the config entry for this device
            config_entry_id = next(iter(device_entry.config_entries))
            register_store = hass.data[DOMAIN].get(config_entry_id)

            if not register_store:
                raise ServiceValidationError(f"Device {device_id} is not a Heatmiser Edge device")

            duration_hours = call.data.get("duration_hours", 0)
            duration_minutes = call.data.get("duration_minutes", 0)
            frost_protection_override = call.data.get("frost_protection_override", False)

            # Validate duration parameters
            if not 0 <= duration_hours <= 99:
                raise ServiceValidationError("Duration hours must be between 0 and 99")
            if not 0 <= duration_minutes <= 59:
                raise ServiceValidationError("Duration minutes must be between 0 and 59")

            if register_store.device_type == DEVICE_TYPE_THERMOSTAT:
                temperature = call.data.get("temperature", 24) # Default to 24 degC if not provided

                # Check device is not in frost protection mode
                if not frost_protection_override:
                    if register_store.registers[int(ThermostatRegisterAddresses.CURRENT_OPERATION_MODE_RD)] == int(PRESET_MODES.index("Frost protection")):
                        raise ServiceValidationError(
                            f"Device {device_id} is currently in frost protection mode. Boosting is not allowed in this mode unless 'frost_protection_override' is set to true."
                        )

                if not 5 <= temperature <= 35:
                    raise ServiceValidationError("Temperature must be between 5 and 35 degrees Celsius")

                _LOGGER.info(f"Boosting thermostat {device_id} to {temperature}°C for {duration_hours}h{duration_minutes}m")

                try:
                    await register_store.async_update_device_time()

                    hold_time_value = (duration_hours << 8) | duration_minutes
                    await register_store.write_register(
                        int(ThermostatRegisterAddresses.HOLDTIME_HOUR_MIN),
                        hold_time_value,
                        refresh_values_after_writing=False
                    )

                    temp_register_value = int(temperature * 10)
                    await register_store.write_register(
                        int(ThermostatRegisterAddresses.HOLD_SET_TEMPERATURE),
                        temp_register_value,
                        refresh_values_after_writing=False
                    )

                    await register_store.write_register(
                        int(ThermostatRegisterAddresses.CURRENT_OPERATION_MODE),
                        2,
                        refresh_values_after_writing=True
                    )
                except Exception as ex:
                    _LOGGER.error(f"Error boosting thermostat: {ex}")
                    raise
            elif register_store.device_type == DEVICE_TYPE_TIMER:
                # Temperature is ignored for timer devices; force output on
                if not frost_protection_override:
                    if register_store.registers[int(TimerRegisterAddresses.CURRENT_OPERATION_MODE_RD)] == int(PRESET_MODES.index("Frost protection")):
                        raise ServiceValidationError(
                            f"Device {device_id} is currently in frost protection mode. Boosting is not allowed in this mode unless 'frost_protection_override' is set to true."
                        )

                _LOGGER.info(f"Boosting timer {device_id} on for {duration_hours}h{duration_minutes}m")

                try:
                    await register_store.async_update_device_time()

                    hold_time_value = (duration_hours << 8) | duration_minutes
                    await register_store.write_register(
                        int(TimerRegisterAddresses.HOLDTIME_HOUR_MIN),
                        hold_time_value,
                        refresh_values_after_writing=False
                    )

                    await register_store.write_register(
                        int(TimerRegisterAddresses.TIMER_OUT_FORCE),
                        1,
                        refresh_values_after_writing=False
                    )

                    await register_store.write_register(
                        int(TimerRegisterAddresses.CURRENT_OPERATION_MODE),
                        2,
                        refresh_values_after_writing=True
                    )
                except Exception as ex:
                    _LOGGER.error(f"Error boosting timer: {ex}")
                    raise
            else:
                raise ServiceValidationError(f"Device {device_id} has an unknown device type")

    async def reset_heatmiser_schedule(call: ServiceCall) -> None:
        """Handle the service call to reset a device to schedule mode."""
        _LOGGER.debug(f"[DEBUG] reset_heatmiser_schedule service called with data: {call.data}")

        device_registry = dr.async_get(hass)
        device_ids = call.data.get("device")
        if isinstance(device_ids, str):
            device_ids = [device_ids]

        for device_id in device_ids:
            _LOGGER.debug(f"[DEBUG] Processing device_id: {device_id}")

            device_entry = device_registry.async_get(device_id)
            if not device_entry:
                raise ServiceValidationError(f"Device {device_id} not found")

            config_entry_id = next(iter(device_entry.config_entries))
            register_store = hass.data[DOMAIN].get(config_entry_id)

            if not register_store:
                raise ServiceValidationError(f"Device {device_id} is not a Heatmiser Edge device")

            frost_protection_override = call.data.get("frost_protection_override", False)

            if not frost_protection_override:
                if register_store.device_type == DEVICE_TYPE_THERMOSTAT:
                    current_mode = register_store.registers[int(ThermostatRegisterAddresses.CURRENT_OPERATION_MODE_RD)]
                elif register_store.device_type == DEVICE_TYPE_TIMER:
                    current_mode = register_store.registers[int(TimerRegisterAddresses.CURRENT_OPERATION_MODE_RD)]
                else:
                    raise ServiceValidationError(f"Device {device_id} has an unknown device type")

                if current_mode == int(PRESET_MODES.index("Frost protection")):
                    raise ServiceValidationError(
                        f"Device {device_id} is currently in frost protection mode. Resetting to schedule is not allowed in this mode unless 'frost_protection_override' is set to true."
                    )

            _LOGGER.info(f"Resetting device {device_id} to schedule mode")

            try:
                await register_store.write_register(
                    int(ThermostatRegisterAddresses.CURRENT_OPERATION_MODE),
                    value=int(PRESET_MODES.index("Schedule")),
                    refresh_values_after_writing=True
                )
            except Exception as ex:
                _LOGGER.error(f"Error resetting device to schedule: {ex}")
                raise

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

    hass.services.async_register(
        DOMAIN,
        "boost_thermostat_heating",
        boost_thermostat_heating
    )

    hass.services.async_register(
        DOMAIN,
        "boost_timer_output",
        boost_timer_output
    )

    hass.services.async_register(
        DOMAIN,
        "boost_heatmiser_generic",
        boost_heatmiser_generic
    )

    hass.services.async_register(
        DOMAIN,
        "reset_heatmiser_schedule",
        reset_heatmiser_schedule
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
    # Ask the shared `modbus` integration for a unit handle instead of opening our own socket
    unit = async_get_unit(
        hass,
        entry,
        ModbusTcpParams(host=entry.data["host"], port=entry.data["port"]),
        entry.data["modbus_id"],
    )
    register_store = heatmiser_edge_register_store(entry.data["host"], entry.data["modbus_id"], unit)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = register_store

    try:
        await register_store.async_update() # Make sure values are all up to date in the register store
    except ModbusError as ex:
        _LOGGER.error(f"Unable to connect to device at {entry.data['host']} with Modbus ID {entry.data['modbus_id']}. Please check the device is online and the configuration is correct. Exception details: {ex}")
        raise ConfigEntryNotReady(f"Unable to connect to device at {entry.data['host']} with Modbus ID {entry.data['modbus_id']}. Please check the device is online and the configuration is correct.") from ex
    except Exception as ex:
        _LOGGER.error(f"Unable to connect to device at {entry.data['host']} with Modbus ID {entry.data['modbus_id']}. Please check the device is online and the configuration is correct. Exception details: {ex}")
        raise ConfigEntryNotReady(f"Unable to connect to device at {entry.data['host']} with Modbus ID {entry.data['modbus_id']}. Please check the device is online and the configuration is correct.") from ex

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