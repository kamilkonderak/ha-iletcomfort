"""Tests for KJRH-120L2 direct curve controls and semantic details."""

from unittest.mock import AsyncMock, MagicMock

from custom_components.iletcomfort.api import ITSSensors, ITSStatus
from custom_components.iletcomfort.model_profiles import KJRH120L2_SN8
from custom_components.iletcomfort.select import ILetComfortKjrh120l2CurveTypeSelect
from custom_components.iletcomfort.sensor import ILetComfortCurveDetailsSensor
from custom_components.iletcomfort.switch import (
    ILetComfortBoostSwitch,
    ILetComfortKjrh120l2TbhSwitch,
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
                "zone1_curve_state": "on",
                "zone1_curve_type": "2",
                "zone1_temp_type": "water_temperature_type",
                "eco_on_state": "off",
                "run_mode_set": "heat",
                "t4": "11",
            },
            "2070": {
                "eco_timer_state": "off",
                "eco_timer_starthour": "6",
                "eco_timer_startmin": "0",
                "eco_timer_endhour": "13",
                "eco_timer_endmin": "0",
            },
            "2080": {
                "t1SetH1": "35",
                "t1SetH2": "28",
                "t4H1": "-5",
                "t4H2": "7",
                "t1SetC1": "10",
                "t1SetC2": "16",
                "t4C1": "35",
                "t4C2": "25",
            },
            "2050": {
                "silence_function_state": "on",
                "silence_function_level": "level_2",
            },
        },
    }
    coordinator.async_set_device = AsyncMock()
    return coordinator


async def test_fast_dhw_switch_uses_captured_boost_write():
    coordinator = _coordinator()
    coordinator.data["status"].kjrh120l2_fast_dhw_enabled = True
    entity = ILetComfortBoostSwitch(coordinator)

    assert entity.is_on is True
    await entity.async_turn_off()

    coordinator.async_set_device.assert_awaited_once_with(boost=False)


async def test_tbh_switch_uses_captured_tank_heater_write():
    coordinator = _coordinator()
    coordinator.data["status"].kjrh120l2_tbh_enabled = False
    entity = ILetComfortKjrh120l2TbhSwitch(coordinator)

    assert entity.is_on is False
    await entity.async_turn_on()

    coordinator.async_set_device.assert_awaited_once_with(tank_heater=True)


async def test_curve_preset_select_uses_named_standard_options():
    entity = ILetComfortKjrh120l2CurveTypeSelect(_coordinator())

    assert entity.current_option == "Standard 2"
    await entity.async_select_option("Custom")

    entity.coordinator.async_set_device.assert_awaited_once_with(curve_type=9)


def test_curve_details_exposes_family_preset_and_custom_points():
    entity = ILetComfortCurveDetailsSensor(_coordinator())

    assert entity.native_value == "Standard"
    assert entity.extra_state_attributes == {
        "enabled": True,
        "preset": 2,
        "temperature_control": "water_temperature_type",
        "manual_temperature_available": False,
        "active_mode": "heat",
        "outdoor_temperature": 11,
        "custom_heating_curve": [
            {"outdoor": -5, "water": 35},
            {"outdoor": 7, "water": 28},
        ],
        "custom_cooling_curve": [
            {"outdoor": 35, "water": 10},
            {"outdoor": 25, "water": 16},
        ],
        "eco_timer_enabled": False,
        "eco_timer_start": "06:00",
        "eco_timer_end": "13:00",
    }


def test_custom_curve_details_estimates_active_target():
    coordinator = _coordinator()
    coordinator.data["semantic"]["2010"]["zone1_curve_type"] = "9"
    entity = ILetComfortCurveDetailsSensor(coordinator)

    assert entity.native_value == "Custom"
    assert entity.extra_state_attributes["estimated_water_target"] == 28
