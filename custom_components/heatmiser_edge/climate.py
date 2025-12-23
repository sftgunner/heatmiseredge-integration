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
        self._device_name = name
        self._preset_mode = "SCHEDULE"
        
        self.register_store = register_store
        
        self._id = f"{DOMAIN}{self._host}{self._slave_id}{self.register_store.device_type}"

        if port != 502:
            _LOGGER.error("Support not added for ports other than 502")


    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info"""
        return DeviceInfo(
            identifiers={(DOMAIN,self._id)},
                name=self._device_name,
                sw_version="1.0.0",
                model="Edge", # Ought to match this using the code version number
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
        self._current_temperature = self.register_store.registers[int(ThermostatRegisterAddresses.ROOM_TEMPERATURE_RD)] / 10
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        self._target_temperature = self.register_store.registers[int(ThermostatRegisterAddresses.CURRENT_SETTING_TEMPERATURE_RD)] / 10
        return self._target_temperature

    @property
    def preset_mode(self):
        """The current active preset"""
        self._preset_mode = PRESET_MODES[self.register_store.registers[int(ThermostatRegisterAddresses.CURRENT_OPERATION_MODE_RD)]]
        return self._preset_mode

    @property
    def hvac_mode(self):
        """The current mode (heat/off)"""
        onoff_state = self.register_store.registers[int(ThermostatRegisterAddresses.THERMOSTAT_ON_OFF_MODE)]
        match onoff_state:
            case 1:
                self._hvac_mode = HVACMode.HEAT
            case 0:
                self._hvac_mode = HVACMode.OFF
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
        await client.write_register(int(ThermostatRegisterAddresses.THERMOSTAT_ON_OFF_MODE), value=OnOffValue , device_id=self._slave_id)
        client.close()

        self._hvac_mode = hvac_mode

    async def async_set_preset_mode(self, preset_mode):
        """Set new target preset mode."""
        client = AsyncModbusTcpClient(self._host)
        await client.connect()
        await client.write_register(int(ThermostatRegisterAddresses.CURRENT_OPERATION_MODE), value=int(PRESET_MODES.index(preset_mode)), device_id=self._slave_id)
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
        await client.write_register(int(ThermostatRegisterAddresses.CURRENT_OPERATION_MODE), value=int(PRESET_MODES.index("Override")) , device_id=self._slave_id)
        await client.write_register(int(ThermostatRegisterAddresses.HOLD_SET_TEMPERATURE), value=int(temperature)*10, device_id=self._slave_id)
        await client.write_register(int(ThermostatRegisterAddresses.ADVANCED_SET_TEMPERATURE), value=int(temperature)*10, device_id=self._slave_id)
        client.close()

        self._target_temperature = int(temperature)

        await self.async_update() # Force an update

    async def async_update(self) -> None:
        await self.register_store.async_update()