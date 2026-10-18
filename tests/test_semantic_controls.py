"""Tests for KJRH-120L2 semantic user controls."""

from unittest.mock import AsyncMock, MagicMock

from custom_components.iletcomfort.api import ITSSensors, ITSStatus
from custom_components.iletcomfort.model_profiles import KJRH120L2_SN8
from custom_components.iletcomfort.number import ILetComfortKjrh120l2RoomSetpoint
from custom_components.iletcomfort.select import (
    ILetComfortKjrh120l2HolidayModeSelect,
    ILetComfortMuteSelect,
)
from custom_components.iletcomfort.switch import (
    ILetComfortBoostSwitch,
    ILetComfortSemanticSwitch,
)


def _coordinator() -> MagicMock:
    coordinator = MagicMock()
    coordinator.appliance_code = "APPL1"
    coordinator.sn8 = KJRH120L2_SN8
    coordinator.appliance_meta = {"sn8": KJRH120L2_SN8}
    coordinator.entry.title = "Heat Pump"
    coordinator.data = {
        "status": ITSStatus(mode=1),
        "sensors": ITSSensors(),
        "semantic": {
            "2010": {
                "fastdhw_state": "off",
                "dhw_power_state": "on",
                "room_temp_set": "24",
                "room_min_set_temp": "17",
                "room_max_set_temp": "30",
                "holiday_on_state": "off",
                "holiday_on_type": "0",
            },
            "2050": {
                "silence_function_state": "on",
                "silence_function_level": "level_2",
            },
        },
    }
    coordinator.async_set_device = AsyncMock()
    coordinator.async_set_semantic_control = AsyncMock()
    return coordinator


async def test_kjrh120l2_boost_uses_fast_dhw_semantic_control():
    entity = ILetComfortBoostSwitch(_coordinator())

    assert entity.is_on is False
    await entity.async_turn_on()

    entity.coordinator.async_set_semantic_control.assert_awaited_once_with(
        "base", {"fastdhw_state": "on"}
    )


async def test_semantic_switch_reads_and_writes_on_off_field():
    entity = ILetComfortSemanticSwitch(
        _coordinator(),
        key="dhw_power",
        name="DHW Power",
        control_type="base",
        field="dhw_power_state",
        group="2010",
    )

    assert entity.is_on is True
    await entity.async_turn_off()

    entity.coordinator.async_set_semantic_control.assert_awaited_once_with(
        "base", {"dhw_power_state": "off"}
    )


async def test_kjrh120l2_silent_select_uses_semantic_level():
    entity = ILetComfortMuteSelect(_coordinator())

    assert entity.current_option == "Level 2"
    await entity.async_select_option("Level 1")

    entity.coordinator.async_set_semantic_control.assert_awaited_once_with(
        "silence",
        {
            "silence_function_state": "on",
            "silence_function_level": "level_1",
        },
    )


async def test_room_setpoint_uses_device_reported_bounds():
    entity = ILetComfortKjrh120l2RoomSetpoint(_coordinator())

    assert entity.native_value == 24
    assert entity.native_min_value == 17
    assert entity.native_max_value == 30
    await entity.async_set_native_value(28)

    entity.coordinator.async_set_semantic_control.assert_awaited_once_with(
        "base", {"room_temp_set": "28"}
    )


async def test_holiday_mode_select_sets_away_mode():
    entity = ILetComfortKjrh120l2HolidayModeSelect(_coordinator())

    assert entity.current_option == "Off"
    await entity.async_select_option("Away")

    entity.coordinator.async_set_semantic_control.assert_awaited_once_with(
        "base", {"holiday_on_state": "on", "holiday_on_type": "1"}
    )
