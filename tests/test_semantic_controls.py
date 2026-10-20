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


# --- DHW schedule ------------------------------------------------------------

from custom_components.iletcomfort.sensor import ILetComfortDhwScheduleSensor  # noqa: E402


def _dhw_semantic(weekly_status: str = "off") -> dict[str, dict[str, str]]:
    """Semantic 2020/20D0/2080 groups as captured from the official app."""
    daily = {}
    for timer in range(1, 7):
        daily.update({
            f"dhwdaytimer_timer{timer}en": "off",
            f"dhwdaytimer_timer{timer}_mode": "off",
            f"dhwdaytimer_timer{timer}_openhour": "0",
            f"dhwdaytimer_timer{timer}_openmin": "0",
            f"dhwdaytimer_timer{timer}_temp": "0",
        })
    weekly = {
        "dhw_weeklytimer_status": weekly_status,
        "dhw_weeklytimer_schedule_num": "4",
    }
    for schedule in range(1, 5):
        base = f"dhw_weeklytimer_schedule_{schedule}"
        weekly[f"{base}_status"] = "off"
        weekly[f"{base}_weekday"] = "127"
        for timer in range(1, 5):
            prefix = f"{base}_timer_{timer}_"
            weekly.update({
                f"{prefix}en": "off",
                f"{prefix}mode": "off",
                f"{prefix}starthour": "0",
                f"{prefix}startmin": "0",
                f"{prefix}temp": "0",
            })
    installer = {
        "dT5On": "5", "dT5STBHoff": "5", "t4Dhwmax": "43", "t4Dhwmin": "-10",
        "tDHWHPmax": "90", "tDHWHPrestrict": "30", "fgdhwPriorEn": "on",
        "tTBHdelay": "30", "t4TBHon": "5", "powerTbh": "2", "t5sDI": "65",
        "tDImax": "210", "tDIhightemp": "15", "t5SHolDhw": "25",
    }
    return {"2020": daily, "20d0": weekly, "2080": installer}


def _dhw_entity(semantic: dict[str, dict[str, str]]) -> ILetComfortDhwScheduleSensor:
    coordinator = _coordinator()
    coordinator.data["semantic"].update(semantic)
    return ILetComfortDhwScheduleSensor(coordinator)


def test_dhw_schedule_reports_captured_all_off_program():
    entity = _dhw_entity(_dhw_semantic())

    assert entity.native_value == "off"
    attrs = entity.extra_state_attributes
    assert attrs["weekly_enabled"] is False
    assert attrs["daily_commands"] == []
    assert [s["number"] for s in attrs["weekly_schedules"]] == [1, 2, 3, 4]
    assert attrs["weekly_schedules"][0] == {
        "number": 1,
        "enabled": False,
        "weekdays": [1, 2, 3, 4, 5, 6, 7],
        "commands": [],
    }
    assert attrs["installer_settings"] == {
        "restart_hysteresis": 5,
        "tbh_off_hysteresis": 5,
        "heat_pump_outdoor_max": 43,
        "heat_pump_outdoor_min": -10,
        "heat_pump_max_run_minutes": 90,
        "heating_restrict_minutes": 30,
        "dhw_priority": True,
        "tbh_delay_minutes": 30,
        "tbh_outdoor_on": 5,
        "tbh_power_kw": 2,
        "disinfection_temperature": 65,
        "disinfection_max_minutes": 210,
        "disinfection_hold_minutes": 15,
        "holiday_temperature": 25,
    }


def test_dhw_schedule_lists_enabled_weekly_commands_in_time_order():
    semantic = _dhw_semantic(weekly_status="on")
    weekly = semantic["20d0"]
    base = "dhw_weeklytimer_schedule_2"
    weekly[f"{base}_status"] = "on"
    weekly[f"{base}_weekday"] = "31"  # Monday-Friday
    weekly.update({
        f"{base}_timer_1_en": "on", f"{base}_timer_1_mode": "on",
        f"{base}_timer_1_starthour": "13", f"{base}_timer_1_startmin": "30",
        f"{base}_timer_1_temp": "50",
        f"{base}_timer_2_en": "on", f"{base}_timer_2_mode": "on",
        f"{base}_timer_2_starthour": "4", f"{base}_timer_2_startmin": "0",
        f"{base}_timer_2_temp": "48",
    })
    entity = _dhw_entity(semantic)

    assert entity.native_value == "weekly"
    schedule = entity.extra_state_attributes["weekly_schedules"][1]
    assert schedule["enabled"] is True
    assert schedule["weekdays"] == [1, 2, 3, 4, 5]
    assert schedule["commands"] == [
        {"start": "04:00", "mode": "on", "temperature": 48},
        {"start": "13:30", "mode": "on", "temperature": 50},
    ]


def test_dhw_schedule_reports_daily_program_when_weekly_is_off():
    semantic = _dhw_semantic()
    semantic["2020"].update({
        "dhwdaytimer_timer3en": "on",
        "dhwdaytimer_timer3_mode": "on",
        "dhwdaytimer_timer3_openhour": "22",
        "dhwdaytimer_timer3_openmin": "15",
        "dhwdaytimer_timer3_temp": "55",
    })
    entity = _dhw_entity(semantic)

    assert entity.native_value == "daily"
    assert entity.extra_state_attributes["daily_commands"] == [
        {"start": "22:15", "mode": "on", "temperature": 55},
    ]


def test_dhw_schedule_is_unknown_without_schedule_groups():
    entity = _dhw_entity({})

    assert entity.native_value is None
    assert entity.extra_state_attributes["weekly_schedules"] == []
