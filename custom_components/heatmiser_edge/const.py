from enum import IntEnum

DOMAIN = "heatmiser_edge"

# Register addresses courtesy of EDGE-RS485-MODBUS-Communication-protocol-V1.8

# NB Register addresses are offset by 1 from the documentation (i.e. doc 1 = digital 0)

class RegisterAddresses(IntEnum):
    CODE_VERSION_NUMBER_RD = 0
    ROOM_TEMPERATURE_RD = 2
    CURRENT_SETTING_TEMPERATURE_RD = 6
    THERMOSTAT_ON_OFF_MODE_RD = 7       # Read only
    CURRENT_OPERATION_MODE_RD = 8
    TEMP_FORMAT = 20
    THERMOSTAT_ON_OFF_MODE = 31
    CURRENT_OPERATION_MODE = 32
    HOLD_SET_TEMPERATURE = 33
    ADVANCED_SET_TEMPERATURE = 34
    FROST_SET_TEMPERATURE = 36

SINGLE_REGISTER = 1

PRESET_MODES = ["Override","Schedule","Hold","Advance","Away","Frost protection"] #Override aka change over in docs