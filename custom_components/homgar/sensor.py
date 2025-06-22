"""Sensor platform for HomGar integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfLength,
    LIGHT_LUX,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from homgarapi.devices import (
    RainPointDisplayHub,
    RainPointSoilMoistureSensor,
    RainPointRainSensor,
    RainPointAirSensor,
    RainPoint2ZoneTimer,
)

from . import HomgarDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS = {
    "temperature": SensorEntityDescription(
        key="temperature",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    "humidity": SensorEntityDescription(
        key="humidity",
        name="Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    "pressure": SensorEntityDescription(
        key="pressure",
        name="Pressure",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.PA,
    ),
    "soil_moisture": SensorEntityDescription(
        key="soil_moisture",
        name="Soil Moisture",
        device_class=SensorDeviceClass.MOISTURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    "light": SensorEntityDescription(
        key="light",
        name="Light",
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=LIGHT_LUX,
    ),
    "rainfall": SensorEntityDescription(
        key="rainfall",
        name="Rainfall",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
    ),
    "rssi": SensorEntityDescription(
        key="rssi",
        name="Signal Strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="dBm",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HomGar sensors from a config entry."""
    coordinator: HomgarDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []

    for device in coordinator.data.get("devices", []):
        if isinstance(device, RainPointDisplayHub):
            entities.extend(_create_hub_sensors(coordinator, device))
        elif isinstance(device, RainPointSoilMoistureSensor):
            entities.extend(_create_soil_moisture_sensors(coordinator, device))
        elif isinstance(device, RainPointRainSensor):
            entities.extend(_create_rain_sensors(coordinator, device))
        elif isinstance(device, RainPointAirSensor):
            entities.extend(_create_air_sensors(coordinator, device))

    async_add_entities(entities)


def _create_hub_sensors(coordinator, device):
    """Create sensors for display hub."""
    sensors = []
    
    if device.temp_mk_current is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["temperature"],
                lambda d: (d.temp_mk_current * 1e-3 - 273.15) if d.temp_mk_current else None,
            )
        )
    
    if device.hum_current is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["humidity"],
                lambda d: d.hum_current,
            )
        )
    
    if device.press_pa_current is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["pressure"],
                lambda d: d.press_pa_current,
            )
        )
    
    if device.wifi_rssi is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["rssi"],
                lambda d: d.wifi_rssi,
            )
        )
    
    return sensors


def _create_soil_moisture_sensors(coordinator, device):
    """Create sensors for soil moisture sensor."""
    sensors = []
    
    if device.temp_mk_current is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["temperature"],
                lambda d: (d.temp_mk_current * 1e-3 - 273.15) if d.temp_mk_current else None,
            )
        )
    
    if device.moist_percent_current is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["soil_moisture"],
                lambda d: d.moist_percent_current,
            )
        )
    
    if device.light_lux_current is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["light"],
                lambda d: d.light_lux_current,
            )
        )
    
    if device.rf_rssi is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["rssi"],
                lambda d: d.rf_rssi,
            )
        )
    
    return sensors


def _create_rain_sensors(coordinator, device):
    """Create sensors for rain sensor."""
    sensors = []
    
    if device.rainfall_mm_total is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SensorEntityDescription(
                    key="rainfall_total",
                    name="Total Rainfall",
                    device_class=SensorDeviceClass.PRECIPITATION,
                    state_class=SensorStateClass.TOTAL_INCREASING,
                    native_unit_of_measurement=UnitOfLength.MILLIMETERS,
                ),
                lambda d: d.rainfall_mm_total,
            )
        )
    
    if device.rainfall_mm_hour is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SensorEntityDescription(
                    key="rainfall_hourly",
                    name="Hourly Rainfall",
                    device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
                    state_class=SensorStateClass.MEASUREMENT,
                    native_unit_of_measurement="mm/h",  # Fixed: Use string instead of UnitOfVolumeFlowRate
                ),
                lambda d: d.rainfall_mm_hour,
            )
        )
    
    if device.rainfall_mm_daily is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SensorEntityDescription(
                    key="rainfall_daily",
                    name="Daily Rainfall",
                    device_class=SensorDeviceClass.PRECIPITATION,
                    state_class=SensorStateClass.MEASUREMENT,
                    native_unit_of_measurement=UnitOfLength.MILLIMETERS,
                ),
                lambda d: d.rainfall_mm_daily,
            )
        )
    
    if device.rf_rssi is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["rssi"],
                lambda d: d.rf_rssi,
            )
        )
    
    return sensors


def _create_air_sensors(coordinator, device):
    """Create sensors for air sensor."""
    sensors = []
    
    if device.temp_mk_current is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["temperature"],
                lambda d: (d.temp_mk_current * 1e-3 - 273.15) if d.temp_mk_current else None,
            )
        )
    
    if device.hum_current is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["humidity"],
                lambda d: d.hum_current,
            )
        )
    
    if device.rf_rssi is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["rssi"],
                lambda d: d.rf_rssi,
            )
        )
    
    return sensors


class HomgarSensor(CoordinatorEntity, SensorEntity):
    """HomGar sensor."""

    def __init__(
        self,
        coordinator: HomgarDataUpdateCoordinator,
        device: Any,
        description: SensorEntityDescription,
        value_fn: callable,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device = device
        self._value_fn = value_fn
        self._attr_unique_id = f"{device.mid}_{device.did}_{description.key}"
        self._attr_name = f"{device.name} {description.name}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        # For hub devices (main devices)
        if isinstance(self._device, RainPointDisplayHub):
            return DeviceInfo(
                identifiers={(DOMAIN, str(self._device.mid))},
                name=self._device.name,
                manufacturer="RainPoint",
                model=getattr(self._device, 'model', 'Display Hub'),
                sw_version=getattr(self._device, 'sw_version', None),
            )
        # For sub-devices that connect through a hub
        else:
            return DeviceInfo(
                identifiers={(DOMAIN, f"{self._device.mid}_{self._device.did}")},
                name=self._device.name,
                manufacturer="RainPoint",
                model=getattr(self._device, 'model', 'Sensor'),
                sw_version=getattr(self._device, 'sw_version', None),
                via_device=(DOMAIN, str(self._device.mid)),
            )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        for device in self.coordinator.data.get("devices", []):
            if device.mid == self._device.mid and device.did == self._device.did:
                try:
                    return self._value_fn(device)
                except (AttributeError, TypeError) as err:
                    _LOGGER.debug("Error getting value for %s: %s", self._attr_unique_id, err)
                    return None
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.native_value is not None
