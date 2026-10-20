"""Helpers for vendor semantic state and controls."""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

SEMANTIC_METADATA_FIELDS = {"cmd_type", "msg_up_type", "query_type", "version"}
SEMANTIC_FIELDS_WITH_NATIVE_ENTITIES = {
    "2010": {
        "error_code",
        "dhw_temp_set",
        "fastdhw_state",
        "forcetbh_state",
        "run_mode_set",
        "tank_actual_temp",
        "zone1_curve_state",
        "zone1_curve_type",
        "zone1_power_state",
    },
    "20b0": {
        "compRunFreq",
        "currentUnitCapacity",
        "heatTotCapacity0",
        "instantPower0",
        "instantRenewPower0",
        "oduCompCurrent",
        "oduVoltage",
        "pwmPumpOut",
        "tempT1",
        "tempT2",
        "tempT2b",
        "tempT3",
        "tempT4",
        "tempTf",
        "tempTh",
        "tempTp",
        "tempTwin",
        "tempTwout",
        "totalRenewPower0",
        "waterFlow",
    },
    "2f11": {
        "SysHeatCapacity",
        "SysHeatCOPEER",
        "SysHeatDayCapacity",
        "SysHeatElecConsum",
        "SysHeatMonthCapacity",
        "SysHeatRenewPower",
        "SysHeatWeekCapacity",
        "SysHeatYearCapacity",
    },
    "2f12": {
        "SysDhwYearCOPEER",
        "SysDhwYearCapacity",
        "SysDhwYearElecConsum",
        "SysDhwYearRenewPower",
        "SysTotalHPCapacity",
        "SysTotalPowerConsum",
        "SysTotalRenewPower",
    },
}


def semantic_value(
    data: dict[str, Any] | None,
    field: str,
    group: str | None = None,
) -> Any:
    """Return one semantic field, optionally constrained to a command group."""
    semantic = (data or {}).get("semantic") or {}
    if group is not None:
        values = semantic.get(group.lower()) or semantic.get(group.upper()) or {}
        return values.get(field)
    for values in semantic.values():
        if isinstance(values, dict) and field in values:
            return values[field]
    return None


def coerce_semantic_value(value: Any) -> Any:
    """Convert vendor string values into stable Home Assistant state values."""
    if value is None or value == "invalid":
        return None
    if not isinstance(value, str):
        return value
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value


def compressor_frequency(data: dict[str, Any] | None) -> int | float | None:
    """Return the decoded compressor frequency, including KJRH-120L2 telemetry."""
    status = (data or {}).get("status")
    frequency = getattr(status, "comp_frq", None)
    if isinstance(frequency, (int, float)) and not isinstance(frequency, bool):
        return frequency

    frequency = coerce_semantic_value(
        semantic_value(data, "compRunFreq", "20b0")
    )
    if isinstance(frequency, (int, float)) and not isinstance(frequency, bool):
        return frequency
    return None


def compressor_running(data: dict[str, Any] | None) -> bool | None:
    """Infer compressor activity only from an actual frequency reading."""
    status = (data or {}).get("status")
    running = getattr(status, "comp_running", None)
    if isinstance(running, bool):
        return running
    frequency = compressor_frequency(data)
    return frequency > 0 if frequency is not None else None


def _number(value: Any) -> int | float | None:
    value = coerce_semantic_value(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return None


def _status_or_semantic(
    data: dict[str, Any] | None,
    attr: str,
    field: str,
    group: str,
    *,
    source: str = "status",
) -> int | float | None:
    """Prefer a decoded frame value, else the vendor semantic reading."""
    decoded = getattr((data or {}).get(source), attr, None)
    if isinstance(decoded, (int, float)) and not isinstance(decoded, bool):
        return decoded
    return _number(semantic_value(data, field, group))


def error_code(data: dict[str, Any] | None) -> int | None:
    """Return the fault code, falling back to the KJRH-120L2 semantic fields."""
    code = _status_or_semantic(data, "error_code", "error_code", "2010")
    if code is None:
        code = _number(semantic_value(data, "error_new_code", "2010"))
    return int(code) if code is not None else None


def error_active(data: dict[str, Any] | None) -> bool | None:
    """Report a fault from any known code; ``error_code_str`` "/" is no fault."""
    codes = [
        _status_or_semantic(data, "error_code", "error_code", "2010"),
        _number(semantic_value(data, "error_new_code", "2010")),
    ]
    known = [code for code in codes if code is not None]
    if known:
        return any(known)
    label = semantic_value(data, "error_code_str", "2010")
    if isinstance(label, str) and label.strip() and label != "invalid":
        return label.strip() != "/"
    return None


def ibh_running(data: dict[str, Any] | None) -> bool | None:
    """Return backup-heater output from status or the 20B0 IBH output flags."""
    running = getattr((data or {}).get("status"), "ibh_running", None)
    if isinstance(running, bool):
        return running
    outputs = [
        semantic_value(data, field, "20b0")
        for field in ("fgIBH1Output", "fgIBH2Output")
    ]
    if "on" in outputs:
        return True
    return False if "off" in outputs else None


def odu_voltage(data: dict[str, Any] | None) -> int | float | None:
    """Return ODU supply voltage, including KJRH-120L2 semantic telemetry."""
    return _status_or_semantic(
        data, "odu_voltage", "oduVoltage", "20b0", source="sensors",
    )


def odu_current(data: dict[str, Any] | None) -> int | float | None:
    """Return ODU compressor current, including KJRH-120L2 semantic telemetry."""
    return _status_or_semantic(
        data, "odu_current", "oduCompCurrent", "20b0", source="sensors",
    )


def iter_semantic_fields(
    data: dict[str, Any] | None,
) -> Iterator[tuple[str, str]]:
    """Yield every non-metadata semantic field in deterministic order."""
    semantic = (data or {}).get("semantic") or {}
    for group in sorted(semantic):
        values = semantic[group]
        if not isinstance(values, dict):
            continue
        for field in sorted(values):
            if (
                field not in SEMANTIC_METADATA_FIELDS
                and field not in SEMANTIC_FIELDS_WITH_NATIVE_ENTITIES.get(
                    str(group).lower(), set()
                )
            ):
                yield str(group).lower(), str(field)


def semantic_field_name(field: str) -> str:
    """Turn vendor snake/camel case identifiers into readable entity names."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", field.replace("_", " "))
    return " ".join(word.upper() if word in {"dhw", "hmi", "cop", "idu", "odu"} else word.capitalize() for word in spaced.split())


def zone1_curve_enabled(data: dict[str, Any] | None) -> bool:
    """Return whether the curve for the current Zone-1 operating mode is on."""
    mode = semantic_value(data, "run_mode_set", "2010")
    field = (
        "zone1_cool_curve_state"
        if mode == "cool"
        else "zone1_heat_curve_state"
    )
    state = semantic_value(data, field, "2010")
    if state not in {"on", "off"}:
        state = semantic_value(data, "zone1_curve_state", "2010")
    if state in {"on", "off"}:
        return state == "on"
    status = (data or {}).get("status")
    return bool(status and status.kjrh120l2_curve_enabled)


def zone1_manual_temperature_available(data: dict[str, Any] | None) -> bool:
    """Apply the controller manual's curve/manual-temperature interlock."""
    if not zone1_curve_enabled(data):
        return True
    return (
        semantic_value(data, "zone1_temp_type", "2010")
        == "room_temperature_type"
    )


def zone1_curve_profile(data: dict[str, Any] | None) -> str:
    """Return the app-facing Standard, ECO, or Custom curve family."""
    if semantic_value(data, "eco_on_state", "2010") == "on":
        return "ECO"
    curve_type = coerce_semantic_value(
        semantic_value(data, "zone1_curve_type", "2010")
    )
    if curve_type is None:
        status = (data or {}).get("status")
        curve_type = getattr(status, "kjrh120l2_curve_type", None)
    return "Custom" if curve_type == 9 else "Standard"


def _semantic_time(data: dict[str, Any] | None, prefix: str) -> str | None:
    hour = coerce_semantic_value(semantic_value(data, f"{prefix}hour", "2070"))
    minute = coerce_semantic_value(semantic_value(data, f"{prefix}min", "2070"))
    if hour is None or minute is None:
        return None
    return f"{int(hour):02d}:{int(minute):02d}"


def _curve_point(
    data: dict[str, Any] | None,
    outdoor_field: str,
    water_field: str,
) -> dict[str, float | int] | None:
    outdoor = coerce_semantic_value(semantic_value(data, outdoor_field, "2080"))
    water = coerce_semantic_value(semantic_value(data, water_field, "2080"))
    if outdoor is None or water is None:
        return None
    return {"outdoor": outdoor, "water": water}


def zone1_curve_details(data: dict[str, Any] | None) -> dict[str, Any]:
    """Build an app-like summary of the active Zone-1 weather curve."""
    curve_type = coerce_semantic_value(
        semantic_value(data, "zone1_curve_type", "2010")
    )
    details: dict[str, Any] = {
        "enabled": zone1_curve_enabled(data),
    }
    if isinstance(curve_type, int) and 1 <= curve_type <= 8:
        details["preset"] = curve_type
    details["temperature_control"] = semantic_value(
        data, "zone1_temp_type", "2010"
    )
    details["manual_temperature_available"] = (
        zone1_manual_temperature_available(data)
    )
    active_mode = semantic_value(data, "run_mode_set", "2010")
    if active_mode is not None:
        details["active_mode"] = active_mode

    outdoor = coerce_semantic_value(semantic_value(data, "t4", "2010"))
    if outdoor is None:
        outdoor = coerce_semantic_value(semantic_value(data, "tempT4", "20b0"))
    if outdoor is not None:
        details["outdoor_temperature"] = outdoor

    heating_points = [
        _curve_point(data, "t4H1", "t1SetH1"),
        _curve_point(data, "t4H2", "t1SetH2"),
    ]
    heating_curve = [point for point in heating_points if point is not None]
    if len(heating_curve) == 2:
        details["custom_heating_curve"] = heating_curve

    cooling_points = [
        _curve_point(data, "t4C1", "t1SetC1"),
        _curve_point(data, "t4C2", "t1SetC2"),
    ]
    cooling_curve = [point for point in cooling_points if point is not None]
    if len(cooling_curve) == 2:
        details["custom_cooling_curve"] = cooling_curve

    if zone1_curve_profile(data) == "Custom" and outdoor is not None:
        active_curve = cooling_curve if active_mode == "cool" else heating_curve
        if len(active_curve) == 2:
            first, second = active_curve
            x1, y1 = float(first["outdoor"]), float(first["water"])
            x2, y2 = float(second["outdoor"]), float(second["water"])
            bounded = max(min(float(outdoor), max(x1, x2)), min(x1, x2))
            target = y1 if x1 == x2 else y1 + (bounded - x1) * (y2 - y1) / (x2 - x1)
            details["estimated_water_target"] = round(target, 1)

    timer = semantic_value(data, "eco_timer_state", "2070")
    if timer in {"on", "off"}:
        details["eco_timer_enabled"] = timer == "on"
    start = _semantic_time(data, "eco_timer_start")
    end = _semantic_time(data, "eco_timer_end")
    if start is not None:
        details["eco_timer_start"] = start
    if end is not None:
        details["eco_timer_end"] = end
    return details


# ---------------------------------------------------------------------------
# KJRH-120L2 DHW schedule (read-only)
# ---------------------------------------------------------------------------
#
# The controller has two DHW programs (user manual 5.1): a daily timer of up
# to six commands repeated every day (group 2020, ``dhwdaytimer_*``) and a
# weekly plan of up to four schedules, each with weekdays and four commands
# (group 20D0, ``dhw_weeklytimer_*``). A command is a start time, a mode and
# a target temperature. Weekday masks use bit 0 = Monday, matching the
# disinfection weekday (16 = Friday, the vendor default); 127 = every day.

DHW_DAILY_TIMERS = 6
DHW_WEEKLY_SCHEDULES = 4
DHW_WEEKLY_TIMERS = 4

# Installer group 2080 fields relevant to DHW, keyed by attribute name. Units
# and meanings follow the installation manual's parameter table.
DHW_INSTALLER_FIELDS = {
    "restart_hysteresis": "dT5On",
    "tbh_off_hysteresis": "dT5STBHoff",
    "heat_pump_outdoor_max": "t4Dhwmax",
    "heat_pump_outdoor_min": "t4Dhwmin",
    "heat_pump_max_run_minutes": "tDHWHPmax",
    "heating_restrict_minutes": "tDHWHPrestrict",
    "dhw_priority": "fgdhwPriorEn",
    "tbh_delay_minutes": "tTBHdelay",
    "tbh_outdoor_on": "t4TBHon",
    "tbh_power_kw": "powerTbh",
    "disinfection_temperature": "t5sDI",
    "disinfection_max_minutes": "tDImax",
    "disinfection_hold_minutes": "tDIhightemp",
    "holiday_temperature": "t5SHolDhw",
}


def _weekday_numbers(mask: Any) -> list[int] | None:
    """Return ISO weekdays (1 = Monday) set in a controller weekday mask."""
    value = coerce_semantic_value(mask)
    if not isinstance(value, int):
        return None
    return [day + 1 for day in range(7) if value & (1 << day)]


def _dhw_command(
    data: dict[str, Any] | None,
    group: str,
    prefix: str,
    enabled_field: str,
    hour_field: str,
    minute_field: str,
) -> dict[str, Any] | None:
    """Return one enabled schedule command, or None when off or incomplete."""
    if semantic_value(data, enabled_field, group) != "on":
        return None
    hour = coerce_semantic_value(semantic_value(data, hour_field, group))
    minute = coerce_semantic_value(semantic_value(data, minute_field, group))
    if not isinstance(hour, int) or not isinstance(minute, int):
        return None
    return {
        "start": f"{hour:02d}:{minute:02d}",
        "mode": semantic_value(data, f"{prefix}mode", group),
        "temperature": coerce_semantic_value(
            semantic_value(data, f"{prefix}temp", group)
        ),
    }


def dhw_daily_commands(data: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Return the enabled DHW daily-timer commands sorted by start time."""
    commands = []
    for timer in range(1, DHW_DAILY_TIMERS + 1):
        base = f"dhwdaytimer_timer{timer}"
        command = _dhw_command(
            data, "2020", f"{base}_", f"{base}en",
            f"{base}_openhour", f"{base}_openmin",
        )
        if command is not None:
            commands.append(command)
    return sorted(commands, key=lambda item: item["start"])


def dhw_weekly_schedules(data: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Return every reported DHW weekly schedule with its enabled commands."""
    schedules = []
    for number in range(1, DHW_WEEKLY_SCHEDULES + 1):
        base = f"dhw_weeklytimer_schedule_{number}"
        status = semantic_value(data, f"{base}_status", "20d0")
        if status is None:
            continue
        commands = []
        for timer in range(1, DHW_WEEKLY_TIMERS + 1):
            prefix = f"{base}_timer_{timer}_"
            command = _dhw_command(
                data, "20d0", prefix, f"{prefix}en",
                f"{prefix}starthour", f"{prefix}startmin",
            )
            if command is not None:
                commands.append(command)
        schedules.append({
            "number": number,
            "enabled": status == "on",
            "weekdays": _weekday_numbers(
                semantic_value(data, f"{base}_weekday", "20d0")
            ),
            "commands": sorted(commands, key=lambda item: item["start"]),
        })
    return schedules


def dhw_schedule_mode(data: dict[str, Any] | None) -> str | None:
    """Return which DHW program is active: weekly, daily, off, or unknown."""
    weekly = semantic_value(data, "dhw_weeklytimer_status", "20d0")
    daily_known = semantic_value(data, "dhwdaytimer_timer1en", "2020") is not None
    if weekly is None and not daily_known:
        return None
    if weekly == "on":
        return "weekly"
    if dhw_daily_commands(data):
        return "daily"
    return "off"


def dhw_schedule_details(data: dict[str, Any] | None) -> dict[str, Any]:
    """Build the DHW schedule and installer settings for one sensor."""
    details: dict[str, Any] = {
        "weekly_enabled": semantic_value(data, "dhw_weeklytimer_status", "20d0") == "on",
        "weekly_schedules": dhw_weekly_schedules(data),
        "daily_commands": dhw_daily_commands(data),
    }
    settings = {}
    for name, field in DHW_INSTALLER_FIELDS.items():
        value = coerce_semantic_value(semantic_value(data, field, "2080"))
        if value in ("on", "off"):
            value = value == "on"
        if value is not None:
            settings[name] = value
    if settings:
        details["installer_settings"] = settings
    return details
