"""Support for the Heatmiser Edge timers using the Modbus protocol."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from .const import *
from .heatmiser_edge import *

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchDeviceClass,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_ID,
    CONF_NAME,
    CONF_PORT,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from pymodbus.client import AsyncModbusTcpClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add switch for passed config_entry in HA."""
    register_store = hass.data[DOMAIN][config_entry.entry_id]

    host = config_entry.data["host"]
    port = config_entry.data["port"]
    slave_id = config_entry.data["modbus_id"]
    name = config_entry.data["name"]

    timer = HeatmiserEdgeTimer(host, port, slave_id, name, register_store)

    async_add_entities([timer])


class HeatmiserEdgeTimer(SwitchEntity):
    """Representation of a Heatmiser Edge timer switch."""

    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, host, port, slave_id, name, register_store: heatmiser_edge_register_store):
        """Initialize the timer switch."""
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._name = f"{name} timer"
        self._device_name = name
        self._id = f"{DOMAIN}{self._host}{self._slave_id}"
        self._is_on = False
        self.register_store = register_store

        if port != 502:
            _LOGGER.error("Support not added for ports other than 502")

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._id)},
            name=self._device_name,
            sw_version="1.0.0",
            model="Edge (In timer mode)",
            manufacturer="Heatmiser",
        )

    @property
    def name(self):
        """Return the name of the timer switch."""
        return self._name

    @property
    def unique_id(self):
        """Return unique ID for the entity."""
        return f"{self._id}_switch"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        self._is_on = self.register_store.registers[int(ThermostatRegisterAddresses.RELAY_STATUS_RD)]
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self._is_on = True
        # Add your Modbus write logic here to turn on the timer
        client = AsyncModbusTcpClient(self._host)
        await client.connect()
        await client.write_register(int(TimerRegisterAddresses.CURRENT_OPERATION_MODE), value=int(PRESET_MODES.index("Advance")) , device_id=self._slave_id) # Override also known as "change over" in docs
        await client.write_register(int(TimerRegisterAddresses.TIMER_OUT_FORCE), value=1, device_id=self._slave_id)
        client.close()

        await self.async_update() # Force an update

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self._is_on = False
        # Add your Modbus write logic here to turn off the timer
        client = AsyncModbusTcpClient(self._host)
        await client.connect()
        await client.write_register(int(TimerRegisterAddresses.CURRENT_OPERATION_MODE), value=int(PRESET_MODES.index("Advance")) , device_id=self._slave_id) # Override also known as "change over" in docs
        await client.write_register(int(TimerRegisterAddresses.TIMER_OUT_FORCE), value=0, device_id=self._slave_id)
        client.close()
        
        await self.async_update() # Force an update

    async def async_update(self) -> None:
        """Update the switch state."""
        await self.register_store.async_update()

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