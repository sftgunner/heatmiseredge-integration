"""Support for the Heatmiser Edge themostats using the Modbus protocol."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from .const import *
from .heatmiser_edge import *

from homeassistant.components.climate import (
    PLATFORM_SCHEMA as CLIMATE_PLATFORM_SCHEMA,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_HOST,
    CONF_ID,
    CONF_NAME,
    CONF_PORT,
    UnitOfTemperature,
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
    # The hub is loaded from the associated hass.data entry that was created in the
    # __init__.async_setup_entry function
    register_store = hass.data[DOMAIN][config_entry.entry_id]

    host = config_entry.data["host"]
    port = config_entry.data["port"]
    slave_id = config_entry.data["modbus_id"]
    name = config_entry.data["name"]

    thermostat = HeatmiserEdgeThermostat(host, port, slave_id, name, register_store)

    # Add all entities to HA
    async_add_entities([thermostat])




class HeatmiserEdgeThermostat(ClimateEntity):
    """Representation of a Heatmiser Edge thermostat."""

    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_preset_modes = PRESET_MODES
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )

    def __init__(self, host, port, slave_id, name, register_store: heatmiser_edge_register_store):
        """Initialize the thermostat."""
        self.temperature_unit = UnitOfTemperature.CELSIUS
        self._current_temperature = None
        self._target_temperature = None
        self._hvac_mode = HVACMode.HEAT
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._name = f"{name} thermostat"
        self._preset_mode = "SCHEDULE"
        self._id = f"{DOMAIN}{self._host}{self._slave_id}"
        self.register_store = register_store

        if port != 502:
            _LOGGER.error("Support not added for ports other than 502")


    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info"""
        return DeviceInfo(
            identifiers={(DOMAIN,self._id)},
                name=self._name,
                sw_version="1.0.0",
                model="Edge",
                manufacturer="Heatmiser",
                )

    @property
    def name(self):
        """Return the name of the thermostat, if any."""
        return self._name

    @property
    def unique_id(self):
        return f"{self._id}_climate"

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def preset_mode(self):
        """The current active preset"""
        return self._preset_mode

    @property
    def hvac_mode(self):
        """The current mode (heat/off)"""
        return self._hvac_mode

    async def async_turn_on(self):
        """Turn the entity on."""
        self._attr_hvac_mode = HVACMode.HEAT


    async def async_turn_off(self):
        """Turn the entity off."""
        self._attr_hvac_mode = HVACMode.Off

    async def async_set_hvac_mode(self,hvac_mode):
        # Do nothing
        match hvac_mode:
            case HVACMode.OFF:
                OnOffValue = 0
            case _:
                OnOffValue = 1
                
        client = AsyncModbusTcpClient(self._host)
        await client.connect()
        await client.write_register(int(RegisterAddresses.THERMOSTAT_ON_OFF_MODE), OnOffValue , self._slave_id)
        client.close()

        self._hvac_mode = hvac_mode

    async def async_set_preset_mode(self, preset_mode):
        """Set new target preset mode."""
        client = AsyncModbusTcpClient(self._host)
        await client.connect()
        await client.write_register(int(RegisterAddresses.CURRENT_OPERATION_MODE), int(PRESET_MODES.index(preset_mode)), self._slave_id)
        client.close()

        self._preset_mode = preset_mode

        await self.async_update() # Force an update


    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return

        # When setting temperature, we need to enter preset mode Override
        # This changes the temp until the next scheduled period (same as on device)

        client = AsyncModbusTcpClient(self._host)
        await client.connect()
        await client.write_register(int(RegisterAddresses.CURRENT_OPERATION_MODE), int(PRESET_MODES.index("Override")) , self._slave_id)
        await client.write_register(int(RegisterAddresses.HOLD_SET_TEMPERATURE), int(temperature)*10, self._slave_id)
        await client.write_register(int(RegisterAddresses.ADVANCED_SET_TEMPERATURE), int(temperature)*10, self._slave_id)
        client.close()

        self._target_temperature = int(temperature)

        await self.async_update() # Force an update

    async def async_update(self) -> None:
        await self.register_store.async_update()
        # client = AsyncModbusTcpClient(self._host)
        # await client.connect()

        # register_updated_values = [None] * 218

        # # Seems like the most amount of registers we can update at a time is 10
        # for i in range (0,200,10):
        #     result = await client.read_holding_registers(i, 10, self._slave_id)     # get information from device
        #     register_updated_values[i:i+10] = result.registers

        # result = await client.read_holding_registers(210, 8, self._slave_id)     # Do last 8 seperately
        # register_updated_values[210:218] = result.registers
        # self.register_store.registers = register_updated_values

        # current_temperature_result = await client.read_holding_registers(int(RegisterAddresses.ROOM_TEMPERATURE_RD), SINGLE_REGISTER, self._slave_id)
        self._current_temperature = self.register_store.registers[int(RegisterAddresses.ROOM_TEMPERATURE_RD)] / 10

        # target_temperature_result = await client.read_holding_registers(int(RegisterAddresses.CURRENT_SETTING_TEMPERATURE_RD), SINGLE_REGISTER, self._slave_id)
        self._target_temperature = self.register_store.registers[int(RegisterAddresses.CURRENT_SETTING_TEMPERATURE_RD)] / 10

        # cur_preset_mode = await client.read_holding_registers(int(RegisterAddresses.CURRENT_OPERATION_MODE_RD), SINGLE_REGISTER, self._slave_id)
        self._preset_mode = PRESET_MODES[self.register_store.registers[int(RegisterAddresses.CURRENT_OPERATION_MODE_RD)]]

        # onoff_state = await client.read_holding_registers(int(RegisterAddresses.THERMOSTAT_ON_OFF_MODE), SINGLE_REGISTER , self._slave_id)
        onoff_state = self.register_store.registers[int(RegisterAddresses.THERMOSTAT_ON_OFF_MODE)]
        match onoff_state:
            case 1:
                self._hvac_mode = HVACMode.HEAT
            case 0:
                self._hvac_mode = HVACMode.OFF

        # client.close()                                   # Disconnect device