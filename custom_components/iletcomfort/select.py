"""Select entities for the iLetComfort integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ILetComfortCoordinator
from .entity import build_device_info
from .model_profiles import ModelProfile, resolve_profile
from .semantic import (
    coerce_semantic_value,
    semantic_value,
)

MUTE_OPTIONS = ["Off", "Level 1", "Level 2"]
_MUTE_TO_API = {"Off": 0, "Level 1": 1, "Level 2": 2}
CURVE_TYPE_OPTIONS = [f"Standard {value}" for value in range(1, 9)] + ["Custom"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities."""
    coordinator: ILetComfortCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SelectEntity] = []
    if resolve_profile(coordinator.sn8) is ModelProfile.KJRH120L2:
        entities.append(ILetComfortKjrh120l2CurveTypeSelect(coordinator))
    else:
        entities.append(ILetComfortMuteSelect(coordinator))
    async_add_entities(entities)


class ILetComfortMuteSelect(CoordinatorEntity[ILetComfortCoordinator], SelectEntity):
    """Select entity for mute/silent mode."""

    _attr_has_entity_name = True
    _attr_name = "Silent Mode"
    _attr_icon = "mdi:volume-off"
    _attr_options = MUTE_OPTIONS

    def __init__(self, coordinator: ILetComfortCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.appliance_code}_mute"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def current_option(self) -> str:
        if self.coordinator.data is None:
            return "Off"
        sensors = self.coordinator.data.get("sensors")
        if sensors is None or sensors.ctrl_flag != 1:
            return "Off"
        # mute_level: 0=Level 1, 1=Level 2
        return "Level 2" if sensors.mute_level == 1 else "Level 1"

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_device(mute=_MUTE_TO_API[option])


class ILetComfortKjrh120l2CurveTypeSelect(
    CoordinatorEntity[ILetComfortCoordinator], SelectEntity
):
    """Zone-1 weather-curve type for KJRH-120L2."""

    _attr_has_entity_name = True
    _attr_name = "Zone-1 Weather Curve Type"
    _attr_icon = "mdi:chart-bell-curve-cumulative"
    _attr_options = CURVE_TYPE_OPTIONS

    def __init__(self, coordinator: ILetComfortCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.appliance_code}_zone1_curve_type"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def current_option(self) -> str | None:
        curve_type = coerce_semantic_value(
            semantic_value(self.coordinator.data, "zone1_curve_type", "2010")
        )
        if curve_type is None:
            status = (self.coordinator.data or {}).get("status")
            curve_type = status.kjrh120l2_curve_type if status else None
        if curve_type == 9:
            return "Custom"
        return f"Standard {curve_type}" if curve_type in range(1, 9) else None

    async def async_select_option(self, option: str) -> None:
        curve_type = 9 if option == "Custom" else int(option.rsplit(" ", 1)[1])
        await self.coordinator.async_set_device(curve_type=curve_type)


__all__ = ["ILetComfortKjrh120l2CurveTypeSelect", "ILetComfortMuteSelect"]
