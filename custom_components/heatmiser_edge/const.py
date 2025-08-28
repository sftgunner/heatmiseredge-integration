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
    SCHEDULE_MODE_RD = 28
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
    MONDAY_PERIOD_1_START_HOUR = 76
    TUESDAY_PERIOD_1_START_HOUR = 100
    WEDNESDAY_PERIOD_1_START_HOUR = 124
    THURSDAY_PERIOD_1_START_HOUR = 148
    FRIDAY_PERIOD_1_START_HOUR = 172
    SATURDAY_PERIOD_1_START_HOUR = 196
    SUNDAY_PERIOD_1_START_HOUR = 52
    
class TimerRegisterAddresses(IntEnum):
    CODE_VERSION_NUMBER_RD = 0
    RELAY_STATUS_RD = 1
    THERMOSTAT_ON_OFF_MODE_RD = 2
    CURRENT_SCHEDULE_RD = 3
    NEXT_SCHEDULE_RD = 4
    DAYLIGHT_SAVING_STATUS_RD = 5
    CURRENT_OPERATION_MODE_RD = 8     # ========= Writeable registers below this point =========
    DAYLIGHT_SAVING_STATUS = 29
    THERMOSTAT_ON_OFF_MODE = 31 # This is physically turning the whole unit on or off
    CURRENT_OPERATION_MODE = 32
    TIMER_OUT_FORCE = 33
    SYNCHRONOUS_RTC_YEAR = 46
    SYNCHRONOUS_RTC_MONTH_DAY = 47
    SYNCHRONOUS_RTC_HOUR_MINUTE = 48
    SYNCHRONOUS_RTC_SECOND = 49
    
RegisterAddresses = [ThermostatRegisterAddresses, TimerRegisterAddresses]

SINGLE_REGISTER = 1

PRESET_MODES = ["Override","Schedule","Hold","Advance","Away","Frost protection"] # Override is known as "change over" in docs

DEVICE_TYPE_THERMOSTAT = 0
DEVICE_TYPE_TIMER = 1