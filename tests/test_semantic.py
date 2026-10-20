"""Tests for KJRH-120L2 semantic telemetry and duplicate filtering."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.iletcomfort.binary_sensor import BINARY_SENSOR_DESCRIPTIONS
from custom_components.iletcomfort.semantic import (
    compressor_frequency,
    compressor_running,
    iter_semantic_fields,
)


@pytest.mark.parametrize(
    ("frequency", "expected_running"),
    [("0", False), ("46", True), ("invalid", None)],
)
def test_compressor_state_uses_semantic_frequency(frequency, expected_running):
    data = {
        "status": SimpleNamespace(comp_frq=None, comp_running=None),
        "semantic": {"20b0": {"compRunFreq": frequency}},
    }

    assert compressor_frequency(data) == (
        None if frequency == "invalid" else int(frequency)
    )
    assert compressor_running(data) is expected_running


def test_compressor_state_remains_unknown_without_a_valid_frequency():
    data = {
        "status": SimpleNamespace(comp_frq=None, comp_running=None),
        "semantic": {"20b0": {"compRunFreq": "odu"}},
    }

    assert compressor_frequency(data) is None
    assert compressor_running(data) is None


def test_compressor_binary_sensor_uses_the_frequency_fallback():
    description = next(
        item
        for item in BINARY_SENSOR_DESCRIPTIONS
        if item.key == "compressor_running"
    )
    data = {
        "status": SimpleNamespace(comp_frq=None, comp_running=None),
        "semantic": {"20b0": {"compRunFreq": "0"}},
    }

    assert description.is_on_fn(data) is False


def test_semantic_iterator_omits_values_with_curated_entities():
    fields = set(
        iter_semantic_fields(
            {
                "semantic": {
                    "2010": {
                        "run_mode_set": "heat",
                        "zone1_temp_set": "24",
                    },
                    "20b0": {
                        "compRunFreq": "0",
                        "totalRenewPower0": "350",
                        "tempT4": "11",
                        "roomRelHum": "50",
                    },
                    "2f11": {
                        "SysHeatCapacity": "12500",
                        "SysHeatDayCapacity": "12",
                        "SysHeatRenewPower": "9800",
                        "SysCoolCapacity": "500",
                    },
                    "2f12": {
                        "SysTotalHPCapacity": "22000",
                        "SysTotalRenewPower": "350",
                        "SysTotalPowerConsum": "12000",
                        "SysDhwYearCapacity": "361",
                    },
                },
            }
        )
    )

    assert ("2010", "run_mode_set") not in fields
    assert ("20b0", "compRunFreq") not in fields
    assert ("20b0", "totalRenewPower0") not in fields
    assert ("20b0", "tempT4") not in fields
    assert ("2f11", "SysHeatCapacity") not in fields
    assert ("2f11", "SysHeatDayCapacity") not in fields
    assert ("2f12", "SysTotalRenewPower") not in fields
    assert ("2f12", "SysTotalHPCapacity") not in fields
    assert ("2f12", "SysTotalPowerConsum") not in fields
    assert ("2f12", "SysDhwYearCapacity") not in fields
    assert ("2010", "zone1_temp_set") in fields
    assert ("20b0", "roomRelHum") in fields
    assert ("2f11", "SysHeatRenewPower") not in fields
    assert ("2f11", "SysCoolCapacity") in fields
