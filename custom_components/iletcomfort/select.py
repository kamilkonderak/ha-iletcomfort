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
    zone1_curve_profile,
)

MUTE_OPTIONS = ["Off", "Level 1", "Level 2"]
_MUTE_TO_API = {"Off": 0, "Level 1": 1, "Level 2": 2}
CURVE_TYPE_OPTIONS = [f"Standard {value}" for value in range(1, 9)] + ["Custom"]
CURVE_PROFILE_OPTIONS = ["Standard", "ECO", "Custom"]
HOLIDAY_MODE_OPTIONS = ["Off", "Away", "Home"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities."""
    coordinator: ILetComfortCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SelectEntity] = [ILetComfortMuteSelect(coordinator)]
    if resolve_profile(coordinator.sn8) is ModelProfile.KJRH120L2:
        entities.append(ILetComfortKjrh120l2CurveTypeSelect(coordinator))
        entities.append(ILetComfortKjrh120l2CurveProfileSelect(coordinator))
        entities.append(ILetComfortKjrh120l2HolidayModeSelect(coordinator))
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
        if resolve_profile(self.coordinator.sn8) is ModelProfile.KJRH120L2:
            if (
                semantic_value(
                    self.coordinator.data, "silence_function_state", "2050"
                )
                != "on"
            ):
                return "Off"
            level = semantic_value(
                self.coordinator.data, "silence_function_level", "2050"
            )
            return "Level 2" if level == "level_2" else "Level 1"
        if self.coordinator.data is None:
            return "Off"
        sensors = self.coordinator.data.get("sensors")
        if sensors is None or sensors.ctrl_flag != 1:
            return "Off"
        # mute_level: 0=Level 1, 1=Level 2
        return "Level 2" if sensors.mute_level == 1 else "Level 1"

    async def async_select_option(self, option: str) -> None:
        if resolve_profile(self.coordinator.sn8) is ModelProfile.KJRH120L2:
            fields = {"silence_function_state": "off"}
            if option != "Off":
                fields = {
                    "silence_function_state": "on",
                    "silence_function_level": (
                        "level_2" if option == "Level 2" else "level_1"
                    ),
                }
            await self.coordinator.async_set_semantic_control("silence", fields)
            return
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
            semantic_value(
                self.coordinator.data, "zone1_curve_type", "2010"
            )
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


class ILetComfortKjrh120l2CurveProfileSelect(
    CoordinatorEntity[ILetComfortCoordinator], SelectEntity,
):
    """Select the controller's Standard, ECO, or Custom curve family."""

    _attr_has_entity_name = True
    _attr_name = "Zone-1 Weather Curve Profile"
    _attr_icon = "mdi:chart-bell-curve"
    _attr_options = CURVE_PROFILE_OPTIONS

    def __init__(self, coordinator: ILetComfortCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.appliance_code}_zone1_curve_profile"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def current_option(self) -> str:
        return zone1_curve_profile(self.coordinator.data)

    async def async_select_option(self, option: str) -> None:
        if option == "Custom":
            await self.coordinator.async_set_device(curve_type=9)
            fields = {"eco_on_state": "off", "zone1_curve_state": "on"}
        elif option == "ECO":
            fields = {"eco_on_state": "on", "zone1_curve_state": "on"}
        else:
            current = coerce_semantic_value(
                semantic_value(
                    self.coordinator.data, "zone1_curve_type", "2010"
                )
            )
            if current == 9:
                await self.coordinator.async_set_device(curve_type=1)
            fields = {"eco_on_state": "off", "zone1_curve_state": "on"}
        await self.coordinator.async_set_semantic_control("base", fields)


class ILetComfortKjrh120l2HolidayModeSelect(
    CoordinatorEntity[ILetComfortCoordinator], SelectEntity,
):
    """Select the controller's documented holiday mode."""

    _attr_has_entity_name = True
    _attr_name = "Holiday Mode"
    _attr_icon = "mdi:home-clock-outline"
    _attr_options = HOLIDAY_MODE_OPTIONS

    def __init__(self, coordinator: ILetComfortCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.appliance_code}_holiday_mode"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def current_option(self) -> str:
        state = semantic_value(
            self.coordinator.data, "holiday_on_state", "2010"
        )
        if state != "on":
            return "Off"
        holiday_type = semantic_value(
            self.coordinator.data, "holiday_on_type", "2010"
        )
        return "Home" if str(holiday_type) == "2" else "Away"

    async def async_select_option(self, option: str) -> None:
        if option == "Off":
            fields = {"holiday_on_state": "off", "holiday_on_type": "0"}
        else:
            fields = {
                "holiday_on_state": "on",
                "holiday_on_type": "2" if option == "Home" else "1",
            }
        await self.coordinator.async_set_semantic_control("base", fields)
