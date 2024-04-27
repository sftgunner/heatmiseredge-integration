import logging
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import SUPPORT_TARGET_TEMPERATURE, HVAC_MODE_HEAT
from homeassistant.const import TEMP_CELSIUS

_LOGGER = logging.getLogger(__name__)

class HeatmiserEdgeThermostat(ClimateEntity):
    def __init__(self):
        # Initialize your thermostat
        self._temperature = 21.0  # Example temperature

    @property
    def name(self):
        return "Heatmiser Edge Thermostat"

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        return self._temperature

    @property
    def hvac_mode(self):
        return HVAC_MODE_HEAT

    @property
    def hvac_modes(self):
        return [HVAC_MODE_HEAT]

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE

    # Implement other necessary methods like set_temperature, update, etc.
