"""Sensor entities for the iLetComfort integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ILetComfortCoordinator
from .entity import build_device_info
from .error_codes import ERROR_CODES
from .semantic import (
    SEMANTIC_DIAGNOSTIC_GROUPS,
    coerce_semantic_value,
    iter_semantic_fields,
    semantic_field_name,
    semantic_value,
    zone1_curve_details,
    zone1_curve_profile,
)
from .model_profiles import ModelProfile, resolve_profile


@dataclass(frozen=True, kw_only=True)
class ILetComfortSensorDescription(SensorEntityDescription):
    """Describe an iLetComfort sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    attributes_fn: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None


def _s(attr: str) -> Callable[[dict[str, Any]], Any]:
    """Helper: get attribute from sensors data."""
    def _get(data: dict[str, Any]) -> Any:
        sensors = data.get("sensors")
        return getattr(sensors, attr, None) if sensors else None
    return _get


def _st(attr: str) -> Callable[[dict[str, Any]], Any]:
    """Helper: get attribute from status data."""
    def _get(data: dict[str, Any]) -> Any:
        status = data.get("status")
        return getattr(status, attr, None) if status else None
    return _get


def _e(attr: str) -> Callable[[dict[str, Any]], Any]:
    """Helper: get attribute from model-specific energy telemetry."""
    def _get(data: dict[str, Any]) -> Any:
        energy = data.get("energy")
        return getattr(energy, attr, None) if energy else None
    return _get


def _controller_state(group: str) -> Callable[[dict[str, Any]], Any]:
    """Return a controller group's on/off state when it has been refreshed."""
    def _get(data: dict[str, Any]) -> Any:
        value = (data.get("controller") or {}).get(group)
        if value is None:
            return None
        return "on" if value["state"] else "off"
    return _get


def _controller_attributes(group: str) -> Callable[[dict[str, Any]], dict[str, Any] | None]:
    """Return the remaining decoded fields for a controller settings group."""
    def _get(data: dict[str, Any]) -> dict[str, Any] | None:
        value = (data.get("controller") or {}).get(group)
        if value is None:
            return None
        return {key: item for key, item in value.items() if key != "state"}
    return _get


def _extended(group: str) -> Callable[[dict[str, Any]], Any]:
    """Return a cached extended response as hex, when available."""
    def _get(data: dict[str, Any]) -> Any:
        frames = data.get("extended") or {}
        body = frames.get(group)
        return body.hex() if body else None
    return _get


def _extended_state(group: str) -> Callable[[dict[str, Any]], Any]:
    """Return the payload when it fits in a state, otherwise availability."""
    def _get(data: dict[str, Any]) -> Any:
        payload = _extended(group)(data)
        if payload is None:
            return None
        return payload if len(payload) <= 255 else "available"
    return _get


def _extended_attributes(group: str) -> Callable[[dict[str, Any]], dict[str, Any] | None]:
    """Return the complete extended response as state attributes."""
    def _get(data: dict[str, Any]) -> dict[str, Any] | None:
        payload = _extended(group)(data)
        if payload is None:
            return None
        return {
            "raw_payload": payload,
            "payload_length": len(payload) // 2,
        }
    return _get


SENSOR_DESCRIPTIONS: tuple[ILetComfortSensorDescription, ...] = (
    ILetComfortSensorDescription(
        key="water_inlet",
        name="Water Inlet Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s("twin_temp"),
    ),
    ILetComfortSensorDescription(
        key="water_outlet",
        name="Water Outlet Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s("twout_temp"),
    ),
    ILetComfortSensorDescription(
        key="dhw_tank",
        name="DHW Tank Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s("th_temp"),
    ),
    ILetComfortSensorDescription(
        key="outdoor_ambient",
        name="Outdoor Ambient Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s("t4_temp"),
    ),
    ILetComfortSensorDescription(
        key="condenser",
        name="Condenser Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s("t3_temp"),
    ),
    ILetComfortSensorDescription(
        key="evaporator",
        name="Evaporator Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s("t2_temp"),
    ),
    ILetComfortSensorDescription(
        key="t2b_temperature",
        name="T2b Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s("t2b_temp"),
    ),
    ILetComfortSensorDescription(
        key="t1_temperature",
        name="T1 Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s("t1_temp"),
    ),
    ILetComfortSensorDescription(
        key="refrigerant",
        name="Refrigerant Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s("tf_temp"),
    ),
    ILetComfortSensorDescription(
        key="plate_hx",
        name="Plate Heat Exchanger Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s("tp_temp"),
    ),
    ILetComfortSensorDescription(
        key="compressor_freq",
        name="Compressor Frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_st("comp_frq"),
    ),
    ILetComfortSensorDescription(
        key="total_energy",
        name="Total Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_st("total_kwh"),
    ),
    ILetComfortSensorDescription(
        key="comp_run_hours",
        name="Compressor Run Hours",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_st("comp_total_run_hours"),
    ),
    ILetComfortSensorDescription(
        key="pressure_high",
        name="High Pressure",
        icon="mdi:gauge-full",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_st("pressure_h"),
    ),
    ILetComfortSensorDescription(
        key="pressure_low",
        name="Low Pressure",
        icon="mdi:gauge-low",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_st("pressure_l"),
    ),
    ILetComfortSensorDescription(
        key="error_code",
        name="Error Code",
        icon="mdi:alert-circle-outline",
        value_fn=_st("error_code"),
    ),
    ILetComfortSensorDescription(
        key="operating_mode",
        name="Operating Mode",
        icon="mdi:heat-pump-outline",
        value_fn=_st("mode_name"),
    ),
    ILetComfortSensorDescription(
        key="compressor_running",
        name="Compressor Running",
        icon="mdi:engine-outline",
        value_fn=_st("comp_running"),
    ),
    ILetComfortSensorDescription(
        key="fan_run_hours",
        name="Fan Run Hours",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_st("fan_total_run_hours"),
    ),
    ILetComfortSensorDescription(
        key="zone1_dhw_setpoint",
        name="DHW Setpoint",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_st("kjrh120l_dhw_setpoint"),
    ),
    ILetComfortSensorDescription(
        key="weather_curve_enabled",
        name="Weather Curve Enabled",
        icon="mdi:chart-bell-curve-cumulative",
        value_fn=_st("kjrh120l2_curve_enabled"),
    ),
    ILetComfortSensorDescription(
        key="weather_curve_type",
        name="Weather Curve Type",
        icon="mdi:chart-bell-curve",
        value_fn=_st("kjrh120l2_curve_type"),
    ),
    ILetComfortSensorDescription(
        key="odu_voltage",
        name="ODU Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s("odu_voltage"),
    ),
    # odu_current is decoded as fixed-point Amperes (raw 16-bit value / 256).
    # The ÷256 scale was confirmed against the official app for the MSC-70D2N8-A
    # (issue #11): raw 1024 -> 4.0 A. See decode_its_sensors() in api.py.
    ILetComfortSensorDescription(
        key="odu_current",
        name="ODU Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_s("odu_current"),
    ),
    ILetComfortSensorDescription(
        key="water_flow",
        name="Water Flow",
        native_unit_of_measurement="L/min",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s("water_flow"),
    ),
    ILetComfortSensorDescription(
        key="current_unit_capacity",
        name="Current Unit Capacity",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s("current_unit_capacity"),
    ),
    ILetComfortSensorDescription(
        key="pwm_pump_output",
        name="Pump Output",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s("pwm_pump_output"),
    ),
    ILetComfortSensorDescription(
        key="heat_total_capacity",
        name="Total Heat Capacity",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s("heat_total_capacity"),
    ),
    ILetComfortSensorDescription(
        key="instant_power",
        name="Instant Power",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s("instant_power"),
    ),
    ILetComfortSensorDescription(
        key="instant_renewable_power",
        name="Instant Renewable Power",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s("instant_renewable_power"),
    ),
    ILetComfortSensorDescription(
        key="total_renewable_power",
        name="Total Renewable Power",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s("total_renewable_power"),
    ),
    ILetComfortSensorDescription(
        key="heating_capacity",
        name="Heating Capacity",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_e("heat_capacity"),
    ),
    ILetComfortSensorDescription(
        key="heating_renewable_energy",
        name="Heating Renewable Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_e("heat_renewable_energy"),
    ),
    ILetComfortSensorDescription(
        key="heating_electric_consumption",
        name="Heating Electricity Consumption",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_e("heat_electric_consumption"),
    ),
    ILetComfortSensorDescription(
        key="heating_cop",
        name="Heating COP",
        icon="mdi:chart-line",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_e("heat_cop"),
    ),
    ILetComfortSensorDescription(
        key="heating_day_capacity",
        name="Heating Day Capacity",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_e("heat_day_capacity"),
    ),
    ILetComfortSensorDescription(
        key="heating_week_capacity",
        name="Heating Week Capacity",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_e("heat_week_capacity"),
    ),
    ILetComfortSensorDescription(
        key="heating_month_capacity",
        name="Heating Month Capacity",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_e("heat_month_capacity"),
    ),
    ILetComfortSensorDescription(
        key="heating_year_capacity",
        name="Heating Year Capacity",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_e("heat_year_capacity"),
    ),
    ILetComfortSensorDescription(
        key="total_electric_consumption",
        name="Total Electricity Consumption",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_e("total_electric_consumption"),
    ),
    ILetComfortSensorDescription(
        key="total_heat_pump_capacity",
        name="Total Heat Pump Capacity",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_e("total_heat_pump_capacity"),
    ),
    ILetComfortSensorDescription(
        key="total_renewable_energy",
        name="Total Renewable Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_e("total_renewable_energy"),
    ),
    ILetComfortSensorDescription(
        key="dhw_year_capacity",
        name="DHW Year Capacity",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_e("dhw_year_capacity"),
    ),
    ILetComfortSensorDescription(
        key="dhw_year_renewable_energy",
        name="DHW Year Renewable Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_e("dhw_year_renewable_energy"),
    ),
    ILetComfortSensorDescription(
        key="dhw_year_electric_consumption",
        name="DHW Year Electricity Consumption",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_e("dhw_year_electric_consumption"),
    ),
    ILetComfortSensorDescription(
        key="dhw_year_cop",
        name="DHW Year COP",
        icon="mdi:chart-line",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_e("dhw_year_cop"),
    ),
    ILetComfortSensorDescription(
        key="holiday_away_settings",
        name="Holiday Away Settings",
        icon="mdi:home-export-outline",
        value_fn=_controller_state("holiday_away"),
        attributes_fn=_controller_attributes("holiday_away"),
    ),
    ILetComfortSensorDescription(
        key="silent_settings",
        name="Silent Settings",
        icon="mdi:volume-off",
        value_fn=_controller_state("silent"),
        attributes_fn=_controller_attributes("silent"),
    ),
    ILetComfortSensorDescription(
        key="eco_settings",
        name="Eco Settings",
        icon="mdi:leaf",
        value_fn=_controller_state("eco"),
        attributes_fn=_controller_attributes("eco"),
    ),
    ILetComfortSensorDescription(
        key="disinfection_settings",
        name="Disinfection Settings",
        icon="mdi:water-boiler-alert",
        value_fn=_controller_state("disinfection"),
        attributes_fn=_controller_attributes("disinfection"),
    ),
    # The vendor exposes these groups, but their internal fields are not
    # documented or present in a recoverable capture. Keep the validated raw
    # responses visible without assigning unverified units or offsets.
    ILetComfortSensorDescription(
        key="extended_2f10_raw",
        name="Extended 2F10 Raw Payload",
        icon="mdi:code-braces",
        value_fn=_extended_state("2f10"),
        attributes_fn=_extended_attributes("2f10"),
    ),
    ILetComfortSensorDescription(
        key="extended_2f11_raw",
        name="Extended 2F11 Raw Payload",
        icon="mdi:code-braces",
        value_fn=_extended_state("2f11"),
        attributes_fn=_extended_attributes("2f11"),
    ),
    ILetComfortSensorDescription(
        key="extended_2f12_raw",
        name="Extended 2F12 Raw Payload",
        icon="mdi:code-braces",
        value_fn=_extended_state("2f12"),
        attributes_fn=_extended_attributes("2f12"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator: ILetComfortCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        ILetComfortSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    ]
    entities.extend(
        ILetComfortSemanticSensor(coordinator, group, field)
        for group, field in iter_semantic_fields(coordinator.data)
    )
    if resolve_profile(coordinator.sn8) is ModelProfile.KJRH120L2:
        entities.append(ILetComfortCurveDetailsSensor(coordinator))
    async_add_entities(entities)


class ILetComfortSensor(CoordinatorEntity[ILetComfortCoordinator], SensorEntity):
    """Sensor entity for iLetComfort heat pump."""

    _attr_has_entity_name = True
    entity_description: ILetComfortSensorDescription

    def __init__(
        self,
        coordinator: ILetComfortCoordinator,
        description: ILetComfortSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.appliance_code}_{description.key}"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(  # pyright: ignore[reportIncompatibleVariableOverride]
        self,
    ) -> dict[str, Any] | None:
        """Expose panel fault details without changing the numeric sensor state."""
        if self.entity_description.attributes_fn is not None:
            if self.coordinator.data is None:
                return None
            return self.entity_description.attributes_fn(self.coordinator.data)
        if self.entity_description.key != "error_code":
            return None
        error_code = self.native_value
        return ERROR_CODES.get(error_code, {}).copy()


class ILetComfortSemanticSensor(
    CoordinatorEntity[ILetComfortCoordinator], SensorEntity,
):
    """Expose one model-aware field returned by the vendor semantic decoder."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ILetComfortCoordinator,
        group: str,
        field: str,
    ) -> None:
        super().__init__(coordinator)
        self._group = group.lower()
        self._field = field
        self._attr_name = semantic_field_name(field)
        self._attr_unique_id = (
            f"{coordinator.appliance_code}_semantic_{self._group}_{field}"
        )
        self._attr_device_info = build_device_info(coordinator)
        if self._group in SEMANTIC_DIAGNOSTIC_GROUPS:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Any:
        return coerce_semantic_value(
            semantic_value(self.coordinator.data, self._field, self._group)
        )

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return {"command_group": self._group}


class ILetComfortCurveDetailsSensor(
    CoordinatorEntity[ILetComfortCoordinator], SensorEntity,
):
    """Summarize Zone-1 curve family, preset, points, and ECO timing."""

    _attr_has_entity_name = True
    _attr_name = "Zone-1 Weather Curve Details"
    _attr_icon = "mdi:chart-bell-curve-cumulative"

    def __init__(self, coordinator: ILetComfortCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.appliance_code}_zone1_curve_details"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def native_value(self) -> str:
        return zone1_curve_profile(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return zone1_curve_details(self.coordinator.data)
