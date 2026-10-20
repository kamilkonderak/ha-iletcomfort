"""KJRH-120L2 entities report vendor-parser data or unknown, never defaults.

The 0x2010/0x20B0 frames below come from a real iOS-app capture. Fields
without a capture-backed byte offset (fault code, IBH output, ODU electrical
values) are taken from the authenticated semantic parser's JSON for the same
capture; when that parser is unavailable they are unknown instead of 0/off.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.iletcomfort import binary_sensor, sensor
from custom_components.iletcomfort.binary_sensor import (
    BINARY_SENSOR_DESCRIPTIONS,
    ILetComfortBinarySensor,
)
from custom_components.iletcomfort.const import (
    CONF_APPLIANCE_CODE,
    CONF_REGION,
    DOMAIN,
    REGION_US,
)
from custom_components.iletcomfort.coordinator import ILetComfortCoordinator
from custom_components.iletcomfort.model_profiles import (
    KJRH120L2_SN8,
    decode_kjrh120l2_sensors,
    decode_kjrh120l2_status,
)
from custom_components.iletcomfort.sensor import (
    SENSOR_DESCRIPTIONS,
    ILetComfortSensor,
)

from .test_model_profiles import (
    KJRH120L2_CAPTURED_20B0,
    KJRH120L2_CAPTURED_2010,
)

# Vendor parser JSON for the captured frames (no fault, compressor stopped).
CAPTURED_SEMANTIC: dict[str, dict[str, str]] = {
    "2010": {
        "error_code": "0",
        "error_new_code": "0",
        "error_code_str": "/",
    },
    "20b0": {
        "oduVoltage": "229",
        "oduCompCurrent": "0",
        "fgIBH1Output": "off",
        "fgIBH2Output": "off",
    },
}


def _coordinator(
    hass: HomeAssistant,
    semantic: dict[str, dict[str, str]] | None = None,
) -> ILetComfortCoordinator:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Heat Pump",
        unique_id="user@example.com:APPL1",
        data={
            CONF_EMAIL: "user@example.com",
            CONF_PASSWORD: "secret",
            CONF_APPLIANCE_CODE: "APPL1",
            CONF_REGION: REGION_US,
        },
        version=2,
    )
    entry.add_to_hass(hass)
    with patch("custom_components.iletcomfort.coordinator.ILetComfortClient"):
        coord = ILetComfortCoordinator(hass, entry)
    coord.appliance_meta = {"sn8": KJRH120L2_SN8}
    coord.data = {
        "status": decode_kjrh120l2_status(KJRH120L2_CAPTURED_2010[10:-1]),
        "sensors": decode_kjrh120l2_sensors(KJRH120L2_CAPTURED_20B0[10:-1]),
    }
    if semantic is not None:
        coord.data["semantic"] = semantic
    return coord


def _sensor(coord: ILetComfortCoordinator, key: str) -> ILetComfortSensor:
    return ILetComfortSensor(
        coord, next(d for d in SENSOR_DESCRIPTIONS if d.key == key),
    )


def _binary(coord: ILetComfortCoordinator, key: str) -> ILetComfortBinarySensor:
    return ILetComfortBinarySensor(
        coord, next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == key),
    )


def _with(**groups: dict[str, str]) -> dict[str, dict[str, str]]:
    semantic = {group: dict(values) for group, values in CAPTURED_SEMANTIC.items()}
    for group, values in groups.items():
        semantic[group].update(values)
    return semantic


def test_fault_entities_read_captured_semantic_no_fault(hass: HomeAssistant):
    coord = _coordinator(hass, CAPTURED_SEMANTIC)

    assert _sensor(coord, "error_code").native_value == 0
    assert _binary(coord, "error").is_on is False


def test_fault_entities_are_unknown_without_semantic_data(hass: HomeAssistant):
    coord = _coordinator(hass)

    assert _sensor(coord, "error_code").native_value is None
    assert _binary(coord, "error").is_on is None


def test_semantic_fault_code_raises_problem_and_maps_panel_code(
    hass: HomeAssistant,
):
    coord = _coordinator(hass, _with(**{"2010": {"error_code": "61"}}))

    error_code = _sensor(coord, "error_code")
    assert error_code.native_value == 61
    assert error_code.extra_state_attributes["panel"] == "E0"
    assert _binary(coord, "error").is_on is True


def test_semantic_new_fault_code_alone_raises_problem(hass: HomeAssistant):
    coord = _coordinator(hass, _with(**{"2010": {"error_new_code": "5"}}))

    assert _binary(coord, "error").is_on is True


def test_fault_string_is_used_when_numeric_codes_are_missing(
    hass: HomeAssistant,
):
    no_fault = _coordinator(hass, {"2010": {"error_code_str": "/"}})
    assert _binary(no_fault, "error").is_on is False
    assert _sensor(no_fault, "error_code").native_value is None

    fault = _coordinator(hass, {"2010": {"error_code_str": "E0"}})
    assert _binary(fault, "error").is_on is True


def test_odu_electrical_sensors_fall_back_to_semantic_values(
    hass: HomeAssistant,
):
    coord = _coordinator(hass, CAPTURED_SEMANTIC)

    assert _sensor(coord, "odu_voltage").native_value == 229
    assert _sensor(coord, "odu_current").native_value == 0


def test_odu_electrical_sensors_are_unknown_without_semantic_data(
    hass: HomeAssistant,
):
    coord = _coordinator(hass)

    assert _sensor(coord, "odu_voltage").native_value is None
    assert _sensor(coord, "odu_current").native_value is None


def test_ibh_running_reads_semantic_outputs(hass: HomeAssistant):
    assert _binary(_coordinator(hass, CAPTURED_SEMANTIC), "ibh_running").is_on is False

    running = _coordinator(hass, _with(**{"20b0": {"fgIBH2Output": "on"}}))
    assert _binary(running, "ibh_running").is_on is True

    assert _binary(_coordinator(hass), "ibh_running").is_on is None


UNSUPPORTED_SENSOR_KEYS = {
    "pressure_high",
    "pressure_low",
    "total_energy",
    "comp_run_hours",
    "fan_run_hours",
}


async def _setup_keys(hass: HomeAssistant, platform: Any, coord) -> set[str]:
    added: list[Any] = []
    hass.data.setdefault(DOMAIN, {})[coord.entry.entry_id] = coord
    await platform.async_setup_entry(hass, coord.entry, added.extend)
    return {
        entity.entity_description.key
        for entity in added
        if hasattr(entity, "entity_description")
    }


async def test_kjrh120l2_skips_sensors_without_a_data_source(
    hass: HomeAssistant,
):
    coord = _coordinator(hass, CAPTURED_SEMANTIC)

    keys = await _setup_keys(hass, sensor, coord)

    assert not keys & UNSUPPORTED_SENSOR_KEYS
    assert {"error_code", "odu_voltage", "odu_current"} <= keys
    assert {"error", "ibh_running"} <= await _setup_keys(
        hass, binary_sensor, coord,
    )


async def test_standard_profile_keeps_status_counter_sensors(
    hass: HomeAssistant,
):
    coord = _coordinator(hass)
    coord.appliance_meta = {}

    assert UNSUPPORTED_SENSOR_KEYS <= await _setup_keys(hass, sensor, coord)
