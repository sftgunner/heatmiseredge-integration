from enum import IntEnum

DOMAIN = "heatmiser_edge"

# Register addresses courtesy of EDGE-RS485-MODBUS-Communication-protocol-V1.8

# NB Register addresses are offset by 1 from the documentation (i.e. doc 1 = digital 0)

# Also NB all registers suffixed _RD are read-only

class ThermostatRegisterAddresses(IntEnum):
    CODE_VERSION_NUMBER_RD = 0
    RELAY_STATUS_RD = 1
    ROOM_TEMPERATURE_RD = 2
    CURRENT_SETTING_TEMPERATURE_RD = 6
    THERMOSTAT_ON_OFF_MODE_RD = 7
    CURRENT_OPERATION_MODE_RD = 8
    CURRENT_SCHEDULE_RD = 9
    NEXT_SCHEDULE_RD = 10
    DAYLIGHT_SAVING_STATUS_RD = 11
    TEMP_FORMAT_RD = 20
    SWITCHING_DIFFERENTIAL_RD = 21
    OUTPUT_DELAY_RD = 22
    PREHEAT_LIMIT_RD = 26
    SCHEDULE_MODE = 28
    DAYLIGHT_SAVING_STATUS = 29
    THERMOSTAT_ON_OFF_MODE = 31
    CURRENT_OPERATION_MODE = 32
    HOLD_SET_TEMPERATURE = 33
    ADVANCED_SET_TEMPERATURE = 34
    FROST_SET_TEMPERATURE = 36
    KEYLOCK_PASSWORD = 41
    SYNCHRONOUS_RTC_YEAR = 46
    SYNCHRONOUS_RTC_MONTH_DAY = 47
    SYNCHRONOUS_RTC_HOUR_MINUTE = 48
    SYNCHRONOUS_RTC_SECOND = 49
    MONDAY_PERIOD_1_START_HOUR = 74
    TUESDAY_PERIOD_1_START_HOUR = 98
    WEDNESDAY_PERIOD_1_START_HOUR = 122
    THURSDAY_PERIOD_1_START_HOUR = 146
    FRIDAY_PERIOD_1_START_HOUR = 170
    SATURDAY_PERIOD_1_START_HOUR = 194
    SUNDAY_PERIOD_1_START_HOUR = 50
    
class TimerRegisterAddresses(IntEnum):
    CODE_VERSION_NUMBER_RD = 0
    RELAY_STATUS_RD = 1
    THERMOSTAT_ON_OFF_MODE_RD = 2
    CURRENT_SCHEDULE_RD = 3
    NEXT_SCHEDULE_RD = 4
    DAYLIGHT_SAVING_STATUS_RD = 5
    CURRENT_OPERATION_MODE_RD = 8     # ========= Writeable registers below this point =========
    SCHEDULE_MODE = 28
    DAYLIGHT_SAVING_STATUS = 29
    THERMOSTAT_ON_OFF_MODE = 31 # This is physically turning the whole unit on or off
    CURRENT_OPERATION_MODE = 32
    TIMER_OUT_FORCE = 33
    SYNCHRONOUS_RTC_YEAR = 46
    SYNCHRONOUS_RTC_MONTH_DAY = 47
    SYNCHRONOUS_RTC_HOUR_MINUTE = 48
    SYNCHRONOUS_RTC_SECOND = 49
    MONDAY_PERIOD_1_START_HOUR = 66
    TUESDAY_PERIOD_1_START_HOUR = 82
    WEDNESDAY_PERIOD_1_START_HOUR = 98
    THURSDAY_PERIOD_1_START_HOUR = 114
    FRIDAY_PERIOD_1_START_HOUR = 130
    SATURDAY_PERIOD_1_START_HOUR = 146
    SUNDAY_PERIOD_1_START_HOUR = 50
    
RegisterAddresses = [ThermostatRegisterAddresses, TimerRegisterAddresses]

SINGLE_REGISTER = 1

HOUR_TO_SETTEMP_REGISTER_OFFSET = 2  # Offset from start of period time register to the corresponding temperature register

PRESET_MODES = ["Override","Schedule","Hold","Advance","Away","Frost protection"] # Override is known as "change over" in docs

DEVICE_TYPE_THERMOSTAT = 0
DEVICE_TYPE_TIMER = 1

# ===== Select/Option lookups =====
# These lists map integer register values to human-friendly strings
# Index position corresponds to the integer value written/read from the device

# Simple on/off mapping used for power and daylight saving flags
ON_OFF_MODES = ["Off", "On"]

SCHEDULE_MODES = [
    "Weekday/Weekend",   # 0
    "7 day",             # 1
    "24 hour",           # 2
    "No schedule"        # 3
]

# Thermostat temporary operation modes (index values must match device protocol)
THERMOSTAT_OPERATION_MODES = [
    "Override",          # 0
    "Schedule",          # 1
    "Hold",              # 2
    "Advance",           # 3
    "Away",              # 4
    "Frost protection"   # 5
]

# Timer operation modes (index values must match device protocol). Kept simple.
TIMER_OPERATION_MODES = [
    "Override",          # 0 (Doesn't seem to work on timer)
    "Schedule",          # 1
    "Hold",              # 2 (I think has to have hold time set to work)
    "Advance",           # 3
    "Away",              # 4 (I think has to have return time set to work)
    "Standby"            # 5
]

# Temperature format (if ever used)
TEMP_FORMATS = ["Celsius", "Fahrenheit"]
