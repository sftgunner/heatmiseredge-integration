"""Support for the Heatmiser Edge themostats using the Modbus protocol."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

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
    TEMP_CELSIUS,
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
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, therm, device, modbushub, host, port):
        """Initialize the thermostat."""
        # self.therm = therm(device[CONF_ID], "prt", uh1)
        # self.uh1 = uh1
        self.temperature_unit = TEMP_CELSIUS
        self._slave_id = device[CONF_ID]
        self._name = device[CONF_NAME]
        self._current_temperature = None
        self._target_temperature = None
        self._id = device
        self._attr_hvac_mode = HVACMode.HEAT
        self._host = host
        self._port = port

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

    def set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        self._target_temperature = int(temperature)
        self.therm.set_target_temp(self._target_temperature)

    async def async_update(self) -> None:
        client = AsyncModbusTcpClient(self._host)    # Create client object
        await client.connect()                           # connect to device, reconnect automatically
        # await client.write_coil(1, True, slave=1)        # set information in device
        result = await client.read_holding_registers(3-1, 1, self._slave_id) # Offset is 1
        # _LOGGER.warning(result)
        self._current_temperature = result.registers[0]/10
        client.close()                                   # Disconnect device