"""Switch entities for the iLetComfort integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ILetComfortCoordinator
from .entity import build_device_info
from .model_profiles import ModelProfile, resolve_profile
from .semantic import semantic_value, zone1_curve_enabled

KJRH120L2_SEMANTIC_SWITCHES = (
    {
        "key": "dhw_power",
        "name": "DHW Power",
        "control_type": "base",
        "field": "dhw_power_state",
        "group": "2010",
        "icon": "mdi:water-boiler",
    },
    {
        "key": "forced_tank_heater",
        "name": "Forced Tank Heater",
        "control_type": "base",
        "field": "forcetbh_state",
        "group": "2010",
        "icon": "mdi:heating-coil",
    },
    {
        "key": "eco",
        "name": "ECO",
        "control_type": "base",
        "field": "eco_on_state",
        "group": "2010",
        "icon": "mdi:leaf",
    },
    {
        "key": "disinfection",
        "name": "Disinfection",
        "control_type": "disinfect",
        "field": "disinfect_function_state",
        "group": "2090",
        "icon": "mdi:water-boiler-alert",
    },
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities."""
    coordinator: ILetComfortCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = [ILetComfortBoostSwitch(coordinator)]
    if resolve_profile(coordinator.sn8) is ModelProfile.KJRH120L2:
        entities.append(ILetComfortKjrh120l2CurveSwitch(coordinator))
        entities.extend(
            ILetComfortSemanticSwitch(coordinator, **description)
            for description in KJRH120L2_SEMANTIC_SWITCHES
        )
    async_add_entities(entities)


class ILetComfortBoostSwitch(CoordinatorEntity[ILetComfortCoordinator], SwitchEntity):
    """Switch entity for boost mode."""

    _attr_has_entity_name = True
    _attr_name = "Boost"
    _attr_icon = "mdi:rocket-launch"

    def __init__(self, coordinator: ILetComfortCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.appliance_code}_boost"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def is_on(self) -> bool:
        if resolve_profile(self.coordinator.sn8) is ModelProfile.KJRH120L2:
            return (
                semantic_value(
                    self.coordinator.data, "fastdhw_state", "2010"
                )
                == "on"
            )
        if self.coordinator.data is None:
            return False
        sensors = self.coordinator.data.get("sensors")
        if sensors is None:
            return False
        return sensors.ctrl_flag == 2

    async def async_turn_on(self, **kwargs: Any) -> None:
        if resolve_profile(self.coordinator.sn8) is ModelProfile.KJRH120L2:
            await self.coordinator.async_set_semantic_control(
                "base", {"fastdhw_state": "on"}
            )
            return
        await self.coordinator.async_set_device(boost=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        if resolve_profile(self.coordinator.sn8) is ModelProfile.KJRH120L2:
            await self.coordinator.async_set_semantic_control(
                "base", {"fastdhw_state": "off"}
            )
            return
        await self.coordinator.async_set_device(boost=False)


class ILetComfortSemanticSwitch(
    CoordinatorEntity[ILetComfortCoordinator], SwitchEntity,
):
    """Switch an on/off field through the vendor semantic control API."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ILetComfortCoordinator,
        *,
        key: str,
        name: str,
        control_type: str,
        field: str,
        group: str,
        icon: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._control_type = control_type
        self._field = field
        self._group = group
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{coordinator.appliance_code}_{key}"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def is_on(self) -> bool | None:
        value = semantic_value(
            self.coordinator.data, self._field, self._group
        )
        if value == "invalid" or value is None:
            return None
        return value == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_semantic_control(
            self._control_type, {self._field: "on"}
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_semantic_control(
            self._control_type, {self._field: "off"}
        )


class ILetComfortKjrh120l2CurveSwitch(
    CoordinatorEntity[ILetComfortCoordinator], SwitchEntity
):
    """Zone-1 weather-curve enable switch for KJRH-120L2."""

    _attr_has_entity_name = True
    _attr_name = "Zone-1 Weather Curve"
    _attr_icon = "mdi:chart-bell-curve-cumulative"

    def __init__(self, coordinator: ILetComfortCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.appliance_code}_zone1_curve"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def is_on(self) -> bool:
        return zone1_curve_enabled(self.coordinator.data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_device(curve_enabled=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_device(curve_enabled=False)
