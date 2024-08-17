"""Support for the Heatmiser Edge themostats using the Modbus protocol."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from .const import *
from .heatmiser_edge import *

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
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

    ReadableRegisters = []

    # register_map = {
    #     "Code version number": 0,
    #     "Relay status": 1, # Should be a binary_sensor
    #     "Time period (current)": 9,
    #     "Time period (next scheduled)": 10,
    #     "Daylight saving status": 11, # Should be a binary_sensor
    #     "Rate of Change": 12, # Add specific units
    #     "Board sensor temp (raw)": 14, # Add scaling and units
    #     "Board sensor temp (calib)": 15, # Add scaling and units
    #     "Switching differential": 21, # Add scaling and units, should be editable
    #     "Output delay": 22, # Add units, should be editable
    #     "Pre-heat limit (optimum start)": 26 # Add units hrs, should be editable
    # }

    register_lookup = [
        {"name": "Code version number", "register": 0, "gain": 1, "offset": 0, "units": ""},
        {"name": "Time period (current)", "register": 9, "gain": 1, "offset": 0, "units": ""},
        {"name": "Time period (next scheduled)", "register": 10, "gain": 1, "offset": 0, "units": ""},
        {"name": "Rate of Change", "register": 12, "gain": 1, "offset": 0, "units": "mins per degC"},
        {"name": "Board sensor temp (raw)", "register": 14, "gain": 10, "offset": 0, "units": UnitOfTemperature.CELSIUS},
        {"name": "Board sensor temp (calib)", "register": 15, "gain": 10, "offset": 0, "units": UnitOfTemperature.CELSIUS},
    ]

    for rg in register_lookup:
        ReadableRegisters.append(HeatmiserEdgeReadableRegisterGeneric(host, port, slave_id, name, register_store, rg["register"], rg["name"], rg["gain"], rg["offset"], rg["units"]))

    # for registername, register_num in register_map.items():
    #     ReadableRegisters.append(HeatmiserEdgeReadableRegisterGeneric(host, port, slave_id, name, register_store, register_num, registername))

    # Add all entities to HA
    async_add_entities(ReadableRegisters)




class HeatmiserEdgeReadableRegisterGeneric(SensorEntity):
    """Representation of a Heatmiser Edge thermostat."""

    def __init__(self, host, port, slave_id, name, register_store: heatmiser_edge_register_store, register_id, register_name, gain, offset, units):
        """Initialize the register write."""
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._register_id = register_id
        self._name = f"{register_name}"
        self._device_name = name
        self._id = f"{DOMAIN}{self._host}{self._slave_id}"

        self.register_store = register_store

        self._native_value = None

        self._gain = gain
        self._offset = offset

        self._attr_native_unit_of_measurement = units


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
        return EntityCategory.DIAGNOSTIC

    @property
    def name(self):
        """Return the name of the thermostat, if any."""
        return self._name

    @property
    def unique_id(self):
        return f"{self._id}_readableregister{self._register_id}"

    @property
    def native_value(self):
        """Return the current value."""
        if self.register_store.registers[self._register_id] != None:
            if (self._gain == 1) and (self._offset == 0):
                self._native_value = int(self.register_store.registers[self._register_id])
            else:
                self._native_value = (self.register_store.registers[self._register_id] / self._gain) + self._offset
        else:
            self._native_value = None
        return self._native_value


    # async def async_set_native_value(self,value: float) -> None:
    #     """Update the current value."""
    #     _LOGGER.warning("Attempting to set native value")
    #     client = AsyncModbusTcpClient(self._host)
    #     await client.connect()
    #     await client.write_register(self._register_id, int(value)*10 , self._slave_id)
    #     client.close()

    #     self._native_value = int(value)