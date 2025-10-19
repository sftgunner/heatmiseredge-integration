"""Support selectable options for Heatmiser Edge via Modbus."""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from pymodbus.client import AsyncModbusTcpClient

from .const import *
from .heatmiser_edge import heatmiser_edge_register_store

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities from a config entry."""
    register_store = hass.data[DOMAIN][config_entry.entry_id]

    host = config_entry.data["host"]
    port = config_entry.data["port"]
    slave_id = config_entry.data["modbus_id"]
    name = config_entry.data["name"]

    select_entities: list[HeatmiserEdgeSelectableRegister] = []

    # Common/selectable registers for both device types
    common_registers: list[dict[str, Any]] = [
            {
                "name": "Device power",
                "register": int(RegisterAddresses[register_store.device_type].THERMOSTAT_ON_OFF_MODE),
                "lookup": ON_OFF_MODES,
            },
            {
                "name": "Schedule mode",
                "register": int(RegisterAddresses[register_store.device_type].SCHEDULE_MODE),
                "lookup": SCHEDULE_MODES,
            },
    ]

    # Device-specific selectable registers
    if register_store.device_type == DEVICE_TYPE_THERMOSTAT:
        device_registers = [            
            {
                "name": "Operation mode",
                "register": int(RegisterAddresses[register_store.device_type].CURRENT_OPERATION_MODE),
                "lookup": THERMOSTAT_OPERATION_MODES,
            }
        ]
    elif register_store.device_type == DEVICE_TYPE_TIMER:
        device_registers = [
            {
                "name": "Operation mode",
                "register": int(RegisterAddresses[register_store.device_type].CURRENT_OPERATION_MODE),
                "lookup": TIMER_OPERATION_MODES,
            }
        ]
    else:
        device_registers = []

    for rg in [*common_registers, *device_registers]:
        select_entities.append(
            HeatmiserEdgeSelectableRegister(
                host,
                port,
                slave_id,
                name,
                register_store,
                rg["register"],
                rg["name"],
                rg["lookup"],
            )
        )

    if select_entities:
        async_add_entities(select_entities)


class HeatmiserEdgeSelectableRegister(SelectEntity):
    """Representation of a selectable register for Heatmiser Edge."""

    def __init__(
        self,
        host: str,
        port: int,
        slave_id: int,
        name: str,
        register_store: heatmiser_edge_register_store,
        register_id: int,
        register_name: str,
        lookup: List[str],
    ) -> None:
        self._host = host
        self._port = port
        self._slave_id = slave_id
        self._register_id = register_id
        self._name = f"{name} {register_name}"
        self._device_name = name

        self.register_store = register_store
        
        self._id = f"{DOMAIN}{self._host}{self._slave_id}{self.register_store.device_type}"

        self._options = list(lookup)
        self._current_index: Optional[int] = None

        if port != 502:
            _LOGGER.error("Support not added for ports other than 502")

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._id)},
            name=self._device_name,
            sw_version="1.0.0",
            model="Edge",
            manufacturer="Heatmiser",
        )

    @property
    def entity_category(self):
        return EntityCategory.CONFIG

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return f"{self._id}_select_{self._register_id}"

    @property
    def options(self) -> list[str]:
        return self._options

    @property
    def current_option(self) -> Optional[str]:
        value = self.register_store.registers[self._register_id]
        if value is None:
            return None
        if 0 <= int(value) < len(self._options):
            return self._options[int(value)]
        return None

    async def async_select_option(self, option: str) -> None:
        if option not in self._options:
            raise ValueError(f"Invalid option {option}")
        index = self._options.index(option)

        client = AsyncModbusTcpClient(self._host)
        await client.connect()
        await client.write_register(self._register_id, value=int(index), device_id=self._slave_id)
        client.close()

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


