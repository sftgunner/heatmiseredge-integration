"""Support for the Heatmiser Edge themostats using the Modbus protocol."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from .const import *

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
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from pymodbus.client import AsyncModbusTcpClient

_LOGGER = logging.getLogger(__name__)

CONF_THERMOSTATS = "tstats"

TSTATS_SCHEMA = vol.Schema(
    vol.All(
        cv.ensure_list,
        [{vol.Required(CONF_ID): cv.positive_int, vol.Required(CONF_NAME): cv.string}],
    )
)

PLATFORM_SCHEMA = CLIMATE_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT): cv.string,
        vol.Optional(CONF_THERMOSTATS, default=[]): TSTATS_SCHEMA,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the heatmiser thermostat."""

    # heatmiser_v3_thermostat = heatmiser.HeatmiserThermostat
    heatmiser_v3_thermostat = None

    host = config[CONF_HOST]
    port = config[CONF_PORT]

    thermostats = config[CONF_THERMOSTATS]

    # modbus_hub = connection.HeatmiserUH1(host, port)
    modbus_hub = None

    add_entities(
        [
            HeatmiserEdgeThermostat(heatmiser_v3_thermostat, thermostat, modbus_hub, host, port)
            for thermostat in thermostats
        ],
        True,
    )


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

    def __init__(self, therm, device, modbushub, host, port):
        """Initialize the thermostat."""
        # self.therm = therm(device[CONF_ID], "prt", uh1)
        # self.uh1 = uh1
        self.temperature_unit = UnitOfTemperature.CELSIUS
        self._slave_id = device[CONF_ID]
        self._name = device[CONF_NAME]
        self._current_temperature = None
        self._target_temperature = None
        self._id = device
        self._hvac_mode = HVACMode.HEAT
        self._host = host
        self._port = port
        self._preset_mode = "SCHEDULE"

    @property
    def name(self):
        """Return the name of the thermostat, if any."""
        return self._name

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
        """The current active preset"""
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
                
        client = AsyncModbusTcpClient(self._host)    # Create client object
        await client.connect()                           # connect to device, reconnect automatically
        await client.write_register(int(RegisterAddresses.THERMOSTAT_ON_OFF_MODE), OnOffValue , self._slave_id)
        client.close()

        self._hvac_mode = hvac_mode

    async def async_set_preset_mode(self, preset_mode):
        """Set new target preset mode."""
        client = AsyncModbusTcpClient(self._host)    # Create client object
        await client.connect()                           # connect to device, reconnect automatically
        await client.write_register(int(RegisterAddresses.CURRENT_OPERATION_MODE), int(PRESET_MODES.index(preset_mode)), self._slave_id)
        client.close()

        self._preset_mode = preset_mode

        self.async_update() # Force an update


    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return

        # When setting temperature, we need to enter preset mode Override
        # This changes the temp until the next scheduled period (same as on device)

        client = AsyncModbusTcpClient(self._host)    # Create client object
        await client.connect()                           # connect to device, reconnect automatically
        await client.write_register(int(RegisterAddresses.CURRENT_OPERATION_MODE), int(PRESET_MODES.index("Override")) , self._slave_id)
        await client.write_register(int(RegisterAddresses.HOLD_SET_TEMPERATURE), int(temperature)*10, self._slave_id)
        await client.write_register(int(RegisterAddresses.ADVANCED_SET_TEMPERATURE), int(temperature)*10, self._slave_id)
        client.close()

        self._target_temperature = int(temperature)

        self.async_update() # Force an update

    async def async_update(self) -> None:
        client = AsyncModbusTcpClient(self._host)    # Create client object
        await client.connect()                           # connect to device, reconnect automatically

        current_temperature_result = await client.read_holding_registers(int(RegisterAddresses.ROOM_TEMPERATURE_RD), SINGLE_REGISTER, self._slave_id)
        self._current_temperature = current_temperature_result.registers[0] / 10

        target_temperature_result = await client.read_holding_registers(int(RegisterAddresses.CURRENT_SETTING_TEMPERATURE_RD), SINGLE_REGISTER, self._slave_id)
        self._target_temperature = target_temperature_result.registers[0] / 10

        cur_preset_mode = await client.read_holding_registers(int(RegisterAddresses.CURRENT_OPERATION_MODE_RD), SINGLE_REGISTER, self._slave_id)
        self._preset_mode = PRESET_MODES[cur_preset_mode.registers[0]]

        onoff_state = await client.read_holding_registers(int(RegisterAddresses.THERMOSTAT_ON_OFF_MODE), SINGLE_REGISTER , self._slave_id)
        match onoff_state:
            case 1:
                self._hvac_mode = HVACMode.HEAT
            case 0:
                self._hvac_mode = HVACMode.OFF

        client.close()                                   # Disconnect device