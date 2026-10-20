"""Tests for Home Assistant entity translation support."""

from __future__ import annotations

import json
from pathlib import Path

from homeassistant.const import UnitOfPower
from homeassistant.components.sensor import SensorDeviceClass

from custom_components.iletcomfort.sensor import SENSOR_DESCRIPTIONS


INTEGRATION_PATH = Path(__file__).resolve().parent.parent / "custom_components" / "iletcomfort"


def _missing_translation_paths(source, translated, path=()):
    missing = []
    for key, value in source.items():
        current_path = (*path, key)
        if key not in translated:
            missing.append(current_path)
        elif isinstance(value, dict):
            missing.extend(
                _missing_translation_paths(value, translated[key], current_path)
            )
    return missing


def test_polish_translation_covers_every_english_translation_key():
    source = json.loads(
        (INTEGRATION_PATH / "strings.json").read_text(encoding="utf-8")
    )
    polish = json.loads(
        (INTEGRATION_PATH / "translations" / "pl.json").read_text(
            encoding="utf-8"
        )
    )

    assert _missing_translation_paths(source, polish) == []


def test_sensor_translation_keys_exist_in_english_and_polish():
    source = json.loads(
        (INTEGRATION_PATH / "strings.json").read_text(encoding="utf-8")
    )["entity"]["sensor"]
    polish = json.loads(
        (INTEGRATION_PATH / "translations" / "pl.json").read_text(
            encoding="utf-8"
        )
    )["entity"]["sensor"]

    for description in SENSOR_DESCRIPTIONS:
        assert description.translation_key in source
        assert description.translation_key in polish


def test_instant_power_is_reported_as_kilowatts():
    description = next(
        item for item in SENSOR_DESCRIPTIONS if item.key == "instant_power"
    )

    assert description.native_unit_of_measurement == UnitOfPower.KILO_WATT
    assert description.device_class is SensorDeviceClass.POWER
