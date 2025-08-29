"""Support for the Heatmiser Edge themostats using the Modbus protocol."""

from __future__ import annotations

import logging
from typing import Any
from datetime import time as datetime_time

import voluptuous as vol

from .const import *
from .heatmiser_edge import *

from homeassistant.components.time import (
    TimeEntity,
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
    
    # Add device specific writable registers
    
    ScheduleTempRegisters = []
    # Days have to have the number first so they sort correctly in HA
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
                time_register = startingregister + (timeperiod*4)
                ScheduleTempRegisters.append(HeatmiserEdgeWritableRegisterTime(host, port, slave_id, name, register_store, time_register, f"{dayname} Period{timeperiod+1} StartTime"))
    elif register_store.device_type == DEVICE_TYPE_TIMER:
        for dayname, startingregister in schedule_register_map.items():
            for timeperiod in range(0,4):
                time_register = startingregister + (timeperiod*4)
                ScheduleTempRegisters.append(HeatmiserEdgeWritableRegisterTime(host, port, slave_id, name, register_store, time_register, f"{dayname} Period{timeperiod+1} 1ON")) # Have to have 1ON to ensure that ON shows before OFF in HA
                ScheduleTempRegisters.append(HeatmiserEdgeWritableRegisterTime(host, port, slave_id, name, register_store, time_register + 2, f"{dayname} Period{timeperiod+1} 2OFF")) # Have to have 2OFF to ensure that ON shows before OFF in HA
            

    # Add all entities to HA
    async_add_entities(ScheduleTempRegisters)




class HeatmiserEdgeWritableRegisterTime(TimeEntity):
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

        if port != 502:
            _LOGGER.error("Support not added for ports other than 502")


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
        """Return the current time."""
        if self.register_store.registers[self._register_id] in (None, 24):
            self._native_value = None
        else:
            self._native_value = datetime_time(self.register_store.registers[self._register_id],self.register_store.registers[self._register_id+1],0)

        return self._native_value

    # @property
    # def mode(self):
    #     return "box"

    async def async_set_value(self,value: time) -> None:
        """Update the current value."""
        _LOGGER.warning(f"Attempting to set time to {int(value.hour)}:{int(value.minute)}")
        client = AsyncModbusTcpClient(self._host)
        await client.connect()
        await client.write_register(self._register_id, value=int(value.hour) , slave=self._slave_id)
        await client.write_register(self._register_id+1, value=int(value.minute) , slave=self._slave_id)
        client.close()

        self._native_value = value

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

    # async def async_update(self) -> None:
    #     _LOGGER.warning("Attempting to update time (skipping)")
    #     # client = AsyncModbusTcpClient(self._host)
    #     # await client.connect()
    #     # value_result = await client.read_holding_registers(self._register_id, SINGLE_REGISTER, self._slave_id)
    #     # self._current_temperature = value_result.registers[0]/10

    #     # client.close()

