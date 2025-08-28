import logging
from typing import Callable, List
from pymodbus.client import AsyncModbusTcpClient
from .const import *
import time

_LOGGER = logging.getLogger(__name__)

class heatmiser_edge_register_store:
    def __init__(self, host, port, modbus_id) -> None:
        _LOGGER.warning("Initialising Register store")
        self.registers = [None] * 218
        self.device_type = None
        self.time_of_last_update = None
        self._slave_id = modbus_id # TO CHANGE
        self._host = host
        self._port = port
        self._update_listeners: List[Callable[[], None]] = []

    async def async_update(self) -> None:
        _LOGGER.warning("Updating register store for device %s at %s", self._slave_id, self._host)
        client = AsyncModbusTcpClient(self._host)
        await client.connect()

        register_updated_values = [None] * 218
        
        MAX_REGISTER_UPDATE_COUNT = 10

        # Seems like the most amount of registers we can update at a time is 10
        for i in range(0,210,MAX_REGISTER_UPDATE_COUNT):
            result = await client.read_holding_registers(i, count=MAX_REGISTER_UPDATE_COUNT, slave=self._slave_id)     # get information from device
            register_updated_values[i:i+MAX_REGISTER_UPDATE_COUNT] = result.registers

        result = await client.read_holding_registers(210, count=8, slave=self._slave_id)     # Do last 8 seperately
        register_updated_values[210:218] = result.registers
        client.close()
        self.registers = register_updated_values
        
        # Check to see whether the device is a thermostat or a timer
        # Technically this should never change, but check just in case
        if self.registers[int(ThermostatRegisterAddresses.ROOM_TEMPERATURE_RD)] > 1:
            self.device_type = DEVICE_TYPE_THERMOSTAT
        else:
            self.device_type = DEVICE_TYPE_TIMER
        
        await self.async_update_device_time()  # Ensure the device time is correct
        # NB This shouldn't be checked this often as it involves writing to the device
        # Ideally only once a day should be enough
        
        # Notify listeners (HA entities) that new data is available
        self._notify_update_listeners()
            
    async def async_update_device_time(self) -> None:
        
        # Update daylight saving status first
        current_time = time.localtime()
        
        if (self.time_of_last_update is not None):
            if (current_time > (self.time_of_last_update + 86400)):
                # Last update was more than a day ago, so update the time
                
                # Update the time on the device to match the time on the HA server
                _LOGGER.warning("Updating time on device to match HA server time")
                
                is_dst = current_time.tm_isdst

                year = current_time.tm_year
                month_day = (current_time.tm_mon << 8) + current_time.tm_mday
                hour_minute = (current_time.tm_hour << 8) + current_time.tm_min
                second = current_time.tm_sec
                _LOGGER.warning("Updating time on device to %d-%02d-%02d %02d:%02d:%02d", year, current_time.tm_mon, current_time.tm_mday, current_time.tm_hour, current_time.tm_min, current_time.tm_sec)
                client = AsyncModbusTcpClient(self._host)
                await client.connect()
                if int(is_dst) != int(self.registers[int(RegisterAddresses[self.device_type].DAYLIGHT_SAVING_STATUS_RD)]):
                    _LOGGER.warning("Updating daylight saving status on device to %d", is_dst)
                    await client.write_register(int(RegisterAddresses[self.device_type].DAYLIGHT_SAVING_STATUS), value=int(is_dst), slave=self._slave_id)
                await client.write_register(int(RegisterAddresses[self.device_type].SYNCHRONOUS_RTC_YEAR), value=year, slave=self._slave_id)
                await client.write_register(int(RegisterAddresses[self.device_type].SYNCHRONOUS_RTC_MONTH_DAY), value=month_day, slave=self._slave_id)
                await client.write_register(int(RegisterAddresses[self.device_type].SYNCHRONOUS_RTC_HOUR_MINUTE), value=hour_minute, slave=self._slave_id)
                await client.write_register(int(RegisterAddresses[self.device_type].SYNCHRONOUS_RTC_SECOND), value=second, slave=self._slave_id)
                client.close()
                self.time_of_last_update = current_time
        
    def add_update_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a listener that will be called after each successful update.
        Returns a function that, when called, removes the listener.
        """
        self._update_listeners.append(listener)
        def _remove() -> None:
            try:
                self._update_listeners.remove(listener)
            except ValueError:
                pass
        return _remove

    def _notify_update_listeners(self) -> None:
        """Notify all registered listeners that an update occurred."""
        for listener in list(self._update_listeners):
            try:
                listener()
            except Exception as exc:  # pragma: no cover
                _LOGGER.debug("Update listener raised: %s", exc)