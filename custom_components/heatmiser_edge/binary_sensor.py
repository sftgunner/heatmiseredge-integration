"""Support for the Heatmiser Edge themostats using the Modbus protocol."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from .const import *
from .heatmiser_edge import *

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
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

    register_lookup = [
        {"name": "Relay status", "register": RegisterAddresses[register_store.device_type].RELAY_STATUS_RD},
        {"name": "Daylight saving status", "register": RegisterAddresses[register_store.device_type].DAYLIGHT_SAVING_STATUS_RD},
    ]

    for rg in register_lookup:
        ReadableRegisters.append(HeatmiserEdgeReadableRegisterBinary(host, port, slave_id, name, register_store, rg["register"], rg["name"]))

    # Add all entities to HA
    async_add_entities(ReadableRegisters)




class HeatmiserEdgeReadableRegisterBinary(BinarySensorEntity):
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

        self._is_on = None


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
    def is_on(self):
        """Return the current value."""
        if self.register_store.registers[self._register_id] != None:
            self._is_on = bool(self.register_store.registers[self._register_id])
        else:
            self._is_on = None
        return self._is_on

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