"""Number entities for the iLetComfort integration."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ILetComfortCoordinator
from .entity import build_device_info
from .model_profiles import (
    KJRH120L2_DHW_TEMP_MAX,
    KJRH120L2_DHW_TEMP_MIN,
    KJRH120L_DHW_TEMP_MAX,
    KJRH120L_DHW_TEMP_MIN,
    ModelProfile,
    kjrh120l_has_zone1,
    resolve_profile,
)
from .semantic import coerce_semantic_value, semantic_value


def _is_kjrh120l_dual(coordinator: ILetComfortCoordinator) -> bool:
    if resolve_profile(coordinator.sn8) is not ModelProfile.KJRH120L:
        return False
    status = (coordinator.data or {}).get("status")
    return bool(status and kjrh120l_has_zone1(status.raw_body))


def _is_kjrh120l2(coordinator: ILetComfortCoordinator) -> bool:
    return resolve_profile(coordinator.sn8) is ModelProfile.KJRH120L2


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create a DHW control only for the validated dual KJRH-120L variant."""
    coordinator: ILetComfortCoordinator = hass.data[DOMAIN][entry.entry_id]
    if _is_kjrh120l2(coordinator):
        async_add_entities([
            ILetComfortKjrh120l2DhwSetpoint(coordinator),
            ILetComfortKjrh120l2RoomSetpoint(coordinator),
        ])
    elif _is_kjrh120l_dual(coordinator):
        async_add_entities([ILetComfortKjrh120lDhwSetpoint(coordinator)])


class ILetComfortKjrh120l2DhwSetpoint(
    CoordinatorEntity[ILetComfortCoordinator], NumberEntity
):
    """DHW target using the captured KJRH-120L2 framed write."""

    _attr_has_entity_name = True
    _attr_name = "DHW Setpoint"
    _attr_icon = "mdi:water-thermometer"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = float(KJRH120L2_DHW_TEMP_MIN)
    _attr_native_max_value = float(KJRH120L2_DHW_TEMP_MAX)
    _attr_native_step = 1.0
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: ILetComfortCoordinator) -> None:
        super().__init__(coordinator)
        minimum = coerce_semantic_value(
            semantic_value(coordinator.data, "dhw_min_set_temp", "2010")
        )
        maximum = coerce_semantic_value(
            semantic_value(coordinator.data, "dhw_max_set_temp", "2010")
        )
        if minimum is not None:
            self._attr_native_min_value = float(minimum)
        if maximum is not None:
            self._attr_native_max_value = float(maximum)
        self._attr_unique_id = f"{coordinator.appliance_code}_kjrh120l2_dhw_setpoint"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def native_value(self) -> float | None:
        status = (self.coordinator.data or {}).get("status")
        return status.kjrh120l_dhw_setpoint if status else None

    async def async_set_native_value(self, value: float) -> None:
        clamped = max(
            self._attr_native_min_value,
            min(float(value), self._attr_native_max_value),
        )
        await self.coordinator.async_set_device(temperature=int(clamped))


class ILetComfortKjrh120l2RoomSetpoint(
    CoordinatorEntity[ILetComfortCoordinator], NumberEntity,
):
    """Room target exposed by the KJRH-120L2 base semantic group."""

    _attr_has_entity_name = True
    _attr_name = "Room Setpoint"
    _attr_icon = "mdi:home-thermometer"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_step = 1.0
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: ILetComfortCoordinator) -> None:
        super().__init__(coordinator)
        minimum = coerce_semantic_value(
            semantic_value(coordinator.data, "room_min_set_temp", "2010")
        )
        maximum = coerce_semantic_value(
            semantic_value(coordinator.data, "room_max_set_temp", "2010")
        )
        self._attr_native_min_value = float(minimum if minimum is not None else 17)
        self._attr_native_max_value = float(maximum if maximum is not None else 30)
        self._attr_unique_id = f"{coordinator.appliance_code}_room_setpoint"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def native_value(self) -> float | None:
        value = coerce_semantic_value(
            semantic_value(
                self.coordinator.data, "room_temp_set", "2010"
            )
        )
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        clamped = max(
            self._attr_native_min_value,
            min(float(value), self._attr_native_max_value),
        )
        await self.coordinator.async_set_semantic_control(
            "base", {"room_temp_set": f"{clamped:g}"}
        )


class ILetComfortKjrh120lDhwSetpoint(
    CoordinatorEntity[ILetComfortCoordinator], NumberEntity
):
    """DHW target using the hardware-confirmed KJRH-120L field 0x07 write."""

    _attr_has_entity_name = True
    _attr_name = "DHW Setpoint"
    _attr_icon = "mdi:water-thermometer"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = float(KJRH120L_DHW_TEMP_MIN)
    _attr_native_max_value = float(KJRH120L_DHW_TEMP_MAX)
    _attr_native_step = 1.0
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: ILetComfortCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.appliance_code}_kjrh120l_dhw_setpoint"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def native_value(self) -> float | None:
        status = (self.coordinator.data or {}).get("status")
        return status.kjrh120l_dhw_setpoint if status else None

    async def async_set_native_value(self, value: float) -> None:
        clamped = max(
            self._attr_native_min_value,
            min(float(value), self._attr_native_max_value),
        )
        await self.coordinator.async_set_device(temperature=int(clamped))
