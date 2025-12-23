"""Support for the Heatmiser Edge themostats using the Modbus protocol."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from .const import *
from .heatmiser_edge import *

from homeassistant.components.number import (
    NumberEntity,
    NumberDeviceClass,
    NumberMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_HOST,
    CONF_ID,
    CONF_NAME,
    CONF_PORT,
    UnitOfTemperature,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from pymodbus.client import AsyncModbusTcpClient

_LOGGER = logging.getLogger(__name__)

# This function is called as part of the __init__.async_setup_entry (via the
# hass.config_entries.async_forward_entry_setup call)
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add cover for passed config_entry in HA."""
    register_store = hass.data[DOMAIN][config_entry.entry_id]

    host = config_entry.data["host"]
    port = config_entry.data["port"]
    slave_id = config_entry.data["modbus_id"]
    name = config_entry.data["name"]

    GenericWritableRegisters = []
    
    # Set up writeable registers that applies for both thermostat and timer

    register_lookup = []
    
    # Add device specific writable registers
    if register_store.device_type == DEVICE_TYPE_THERMOSTAT:
        register_lookup.append({
            "name": "Switching differential", 
            "register": RegisterAddresses[register_store.device_type].SWITCHING_DIFFERENTIAL_RD, 
            "gain": 10, 
            "offset": 0, 
            "units": UnitOfTemperature.CELSIUS
            })
        register_lookup.append({
            "name": "Output delay", 
            "register": RegisterAddresses[register_store.device_type].OUTPUT_DELAY_RD, 
            "gain": 1, 
            "offset": 0, 
            "units": "minutes"
            })
        register_lookup.append({
            "name": "Pre-heat limit (optimum start)", 
            "register": RegisterAddresses[register_store.device_type].PREHEAT_LIMIT_RD, 
            "gain": 1, 
            "offset": 0, 
            "units": "hours"
            })
        register_lookup.append({
            "name": "Keylock Password (0 to clear)", 
            "register": RegisterAddresses[register_store.device_type].KEYLOCK_PASSWORD, 
            "gain": 1, 
            "offset": 0, 
            "units": ""
            })
    elif register_store.device_type == DEVICE_TYPE_TIMER:
        # No device specific writable registers for the timer
        pass
    
    for rg in register_lookup:
        GenericWritableRegisters.append(HeatmiserEdgeWritableRegisterGeneric(host, port, slave_id, name, register_store, rg["register"], rg["name"], rg["gain"], rg["offset"], rg["units"]))
    # Add all entities to HA
    async_add_entities(GenericWritableRegisters)

    ScheduleTempRegisters = []
    schedule_register_map = {
        "1Mon": RegisterAddresses[register_store.device_type].MONDAY_PERIOD_1_START_HOUR,
        "2Tue": RegisterAddresses[register_store.device_type].TUESDAY_PERIOD_1_START_HOUR,
        "3Wed": RegisterAddresses[register_store.device_type].WEDNESDAY_PERIOD_1_START_HOUR,
        "4Thu": RegisterAddresses[register_store.device_type].THURSDAY_PERIOD_1_START_HOUR,
        "5Fri": RegisterAddresses[register_store.device_type].FRIDAY_PERIOD_1_START_HOUR,
        "6Sat": RegisterAddresses[register_store.device_type].SATURDAY_PERIOD_1_START_HOUR,
        "7Sun": RegisterAddresses[register_store.device_type].SUNDAY_PERIOD_1_START_HOUR
    }
    if register_store.device_type == DEVICE_TYPE_THERMOSTAT:
        for dayname, startingregister in schedule_register_map.items():
            for timeperiod in range(0,4):
                temperature_register = startingregister + (timeperiod*4) + HOUR_TO_SETTEMP_REGISTER_OFFSET
                ScheduleTempRegisters.append(HeatmiserEdgeWritableRegisterTemp(host, port, slave_id, name, register_store, temperature_register, f"{dayname} Period{timeperiod+1} Temp"))
    elif register_store.device_type == DEVICE_TYPE_TIMER:
        # No number entities for the timer
        pass

    # Add all entities to HA
    async_add_entities(ScheduleTempRegisters)



class HeatmiserEdgeWritableRegisterGeneric(NumberEntity):
    """Representation of a Heatmiser Edge thermostat."""

    def __init__(self, host, port, slave_id, name, register_store: heatmiser_edge_register_store, register_id, register_name, gain, offset, units):
        """Initialize the register write."""
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._register_id = register_id
        self._name = f"{name} {register_name}"
        self._device_name = name
        self._id = f"{DOMAIN}{self._host}{self._slave_id}"
        self._gain = gain
        self._offset = offset

        self.register_store = register_store

        self._native_value = None

        self._attr_native_unit_of_measurement = units
        self._attr_mode = NumberMode.BOX
        # self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._attr_native_step = 1


        if port != 502:
            _LOGGER.error("Support not added for ports other than 502")


    async def async_added_to_hass(self) -> None:
        """Register for updates from the register store when entity is added."""
        self._remove_listener = self.register_store.add_update_listener(
            lambda: self.async_schedule_update_ha_state(True)
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unregister update listener when entity is removed."""
        remove = getattr(self, "_remove_listener", None)
        if remove is not None:
            remove()
            self._remove_listener = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info"""
        return DeviceInfo(
            identifiers={(DOMAIN,self._id)},
                name=self._device_name,
                sw_version="1.0.0",
                model="Edge",
                manufacturer="Heatmiser",
                )
    
    @property
    def entity_category(self):
        return EntityCategory.CONFIG

    @property
    def name(self):
        """Return the name of the thermostat, if any."""
        return self._name

    @property
    def unique_id(self):
        return f"{self._id}_writableregister{self._register_id}"

    @property
    def native_value(self):
        """Return the current temperature."""
        if self.register_store.registers[self._register_id] != None:
            if (self._gain == 1) and (self._offset == 0):
                self._native_value = int(self.register_store.registers[self._register_id])
            else:
                self._native_value = (self.register_store.registers[self._register_id] / self._gain) - self._offset
        else:
            self._native_value = None
        return self._native_value


    async def async_set_native_value(self,value: float) -> None:
        """Update the current value."""
        _LOGGER.warning("Attempting to set native value")
        client = AsyncModbusTcpClient(self._host)
        await client.connect()
        await client.write_register(self._register_id, value=int(value)*self._gain , device_id=self._slave_id)
        client.close()

        self._native_value = int(value)
        
        await self.register_store.async_update()  # Force an update to ensure HA shows the correct value


class HeatmiserEdgeWritableRegisterTemp(NumberEntity):
    """Representation of a Heatmiser Edge thermostat."""

    def __init__(self, host, port, slave_id, name, register_store: heatmiser_edge_register_store, register_id, register_name):
        """Initialize the register write."""
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._register_id = register_id
        self._name = f"{name} {register_name}"
        self._device_name = name
        self._id = f"{DOMAIN}{self._host}{self._slave_id}"

        self.register_store = register_store

        self._native_value = None

        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_mode = NumberMode.BOX
        self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._attr_native_step = 0.5


        if port != 502:
            _LOGGER.error("Support not added for ports other than 502")


    async def async_added_to_hass(self) -> None:
        """Register for updates from the register store when entity is added."""
        self._remove_listener = self.register_store.add_update_listener(
            lambda: self.async_schedule_update_ha_state(True)
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unregister update listener when entity is removed."""
        remove = getattr(self, "_remove_listener", None)
        if remove is not None:
            remove()
            self._remove_listener = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info"""
        return DeviceInfo(
            identifiers={(DOMAIN,self._id)},
                name=self._device_name,
                sw_version="1.0.0",
                model="Edge",
                manufacturer="Heatmiser",
                )
    
    @property
    def entity_category(self):
        return EntityCategory.CONFIG

    @property
    def name(self):
        """Return the name of the thermostat, if any."""
        return self._name

    @property
    def unique_id(self):
        return f"{self._id}_writableregister{self._register_id}"

    @property
    def native_value(self):
        """Return the current temperature."""
        if self.register_store.registers[self._register_id] != None:
            self._native_value = self.register_store.registers[self._register_id]/10
        else:
            self._native_value = None
        return self._native_value


    async def async_set_native_value(self,value: float) -> None:
        """Update the current value."""
        _LOGGER.warning("Attempting to set native value")
        client = AsyncModbusTcpClient(self._host)
        await client.connect()
        await client.write_register(self._register_id, value=int(value)*10 , device_id=self._slave_id)
        client.close()

        self._native_value = int(value)
        
        await self.register_store.async_update()  # Force an update to ensure HA shows the correct value