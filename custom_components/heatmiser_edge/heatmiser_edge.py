import logging
from pymodbus.client import AsyncModbusTcpClient

_LOGGER = logging.getLogger(__name__)

class heatmiser_edge_register_store:
    def __init__(self, host, port, modbus_id) -> None:
        _LOGGER.warning("Initialising Register store")
        self.registers = [None] * 218
        self._slave_id = modbus_id # TO CHANGE
        self._host = host
        self._port = port

    async def async_update(self) -> None:
        _LOGGER.warning("Updating register store")
        client = AsyncModbusTcpClient(self._host)
        await client.connect()

        register_updated_values = [None] * 218

        # Seems like the most amount of registers we can update at a time is 10
        for i in range(0,210,10):
            result = await client.read_holding_registers(i, 10, self._slave_id)     # get information from device
            register_updated_values[i:i+10] = result.registers

        result = await client.read_holding_registers(210, 8, self._slave_id)     # Do last 8 seperately
        register_updated_values[210:218] = result.registers
        client.close()
        self.registers = register_updated_values