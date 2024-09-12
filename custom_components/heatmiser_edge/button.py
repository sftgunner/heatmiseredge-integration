"""Support for the Heatmiser Edge themostats using the Modbus protocol."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from .const import *
from .heatmiser_edge import *

from homeassistant.components.button import (
    ButtonEntity,
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

    # register_id = int(RegisterAddresses.THERMOSTAT_ON_OFF_MODE)

    ScheduleTempRegisters = []

    register_map = {
        "1Mon": 74,
        "2Tue": 98,
        "3Wed": 122,
        "4Thu": 146,
        "5Fri": 170,
        "6Sat": 194,
        "7Sun": 50
    }

    for dayname, startingregister in register_map.items():
        for i in range(0,4):
            ScheduleTempRegisters.append(HeatmiserEdgeClearTimePeriodButton(host, port, slave_id, name, register_store, startingregister+(i*4), f"{dayname} Period{i+1} Temp delete"))
    



    # WritableRegister = HeatmiserEdgeWritableRegisterTemp(host, port, slave_id, name, register_id, register_name)

    # Add all entities to HA
    async_add_entities(ScheduleTempRegisters)




class HeatmiserEdgeClearTimePeriodButton(ButtonEntity):
    """Representation of a Heatmiser Edge thermostat."""

    def __init__(self, host, port, slave_id, name, register_store: heatmiser_edge_register_store, register_id, register_name):
        """Initialize the register write."""
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._register_id = register_id
        self._name = f"{register_name}"
        self._device_name = name
        self._id = f"{DOMAIN}{self._host}{self._slave_id}"

        self.register_store = register_store


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
        return f"{self._id}_clearregister{self._register_id}"


    async def async_press(self) -> None:
        """Update the current value."""
        _LOGGER.warning("Attempting to clear time period")
        client = AsyncModbusTcpClient(self._host)
        await client.connect()
        await client.write_register(self._register_id, int(24) , self._slave_id)
        client.close()

        self.register_store.registers[self._register_id] = int(24)