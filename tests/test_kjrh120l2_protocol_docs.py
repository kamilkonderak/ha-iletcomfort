"""Keep the KJRH-120L2 protocol reference aligned with captured vectors."""

from pathlib import Path

from custom_components.iletcomfort.api import build_c3_query_group
from custom_components.iletcomfort.model_profiles import (
    build_kjrh120l2_curve_state,
    build_kjrh120l2_curve_type,
    build_kjrh120l2_fast_dhw,
    build_kjrh120l2_set_temperature,
    build_kjrh120l2_tbh,
    build_kjrh120l2_zone1_power,
)

DOC_PATH = Path(__file__).resolve().parent.parent / "docs" / "KJRH120L2_PROTOCOL.md"


def test_protocol_reference_contains_every_runtime_query_vector() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")

    for group in (
        0x2010,
        0x2020,
        0x2040,
        0x2050,
        0x2060,
        0x2070,
        0x2080,
        0x2090,
        0x20B0,
        0x20D0,
        0x20E0,
        0x20F0,
        0x2100,
        0x2F10,
        0x2F11,
        0x2F12,
    ):
        assert f"`0x{group:04X}`" in text
        assert build_c3_query_group(group) in text


def test_protocol_reference_contains_every_captured_write_vector() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")

    vectors = (
        build_kjrh120l2_zone1_power(False),
        build_kjrh120l2_zone1_power(True),
        build_kjrh120l2_set_temperature(50),
        build_kjrh120l2_tbh(False),
        build_kjrh120l2_tbh(True),
        build_kjrh120l2_fast_dhw(False),
        build_kjrh120l2_fast_dhw(True),
        build_kjrh120l2_curve_state(False),
        build_kjrh120l2_curve_state(True),
        build_kjrh120l2_curve_type(1),
        build_kjrh120l2_curve_type(2),
    )
    for vector in vectors:
        assert vector in text


def test_protocol_reference_contains_no_capture_credentials_or_device_id() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")

    for forbidden in (
        "accessToken",
        "authorization: Bearer",
        "Cookie:",
        "153931629812319",
        "0000C352017100007492941000193nv3",
    ):
        assert forbidden not in text


def test_protocol_reference_covers_reverse_engineered_semantic_registry() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")

    assert build_c3_query_group(0x20B1) in text

    groups = {
        "2010": 67,
        "2020": 90,
        "2040": 12,
        "2050": 12,
        "2060": 97,
        "2070": 7,
        "2080": 135,
        "2090": 7,
        "20B0": 109,
        "20B1": 100,
        "20D0": 90,
        "20E0": 90,
        "20F0": 90,
        "2100": 15,
        "2F11": 52,
        "2F12": 36,
    }
    for group, count in groups.items():
        assert f"`0x{group}` ({count} fields)" in text

    for field in (
        "zone1_temp_set",
        "holidayaway_state",
        "silence_function_level",
        "holidayhome_state",
        "eco_timer_state",
        "t1SetH1",
        "disinfect_setweekday",
        "fgDefrost",
        "oduVersionNum",
        "dhw_weeklytimer_schedule_{s}_timer_{t}_temp",
        "zone1_weeklytimer_schedule_{s}_timer_{t}_temp",
        "zone2_weeklytimer_schedule_{s}_timer_{t}_temp",
        "energyMeterExist",
        "SysCoolYearCOPEER",
        "SysDhwMonthCOPEER",
    ):
        assert f"`{field}`" in text
