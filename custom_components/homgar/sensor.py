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
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
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
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "battery": SensorEntityDescription(
        key="battery",
        name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
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
        device_sensors = []
        
        if isinstance(device, RainPointDisplayHub):
            device_sensors = _create_hub_sensors(coordinator, device)
        elif isinstance(device, RainPointSoilMoistureSensor):
            device_sensors = _create_soil_moisture_sensors(coordinator, device)
        elif isinstance(device, RainPointRainSensor):
            device_sensors = _create_rain_sensors(coordinator, device)
        elif isinstance(device, RainPointAirSensor):
            device_sensors = _create_air_sensors(coordinator, device)
        else:
            _LOGGER.debug("Unknown device type: %s for device %s", 
                         type(device).__name__, getattr(device, 'name', 'Unknown'))
            continue
            
        _LOGGER.debug("Creating %d sensors for device %s (%s)", 
                     len(device_sensors), getattr(device, 'name', 'Unknown'), 
                     type(device).__name__)
        entities.extend(device_sensors)

    async_add_entities(entities)


def _create_hub_sensors(coordinator, device):
    """Create sensors for display hub."""
    sensors = []
    
    # Temperature sensor
    if hasattr(device, 'temp_mk_current') and device.temp_mk_current is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["temperature"],
                lambda d: round((d.temp_mk_current * 1e-3 - 273.15), 1) if d.temp_mk_current else None,
            )
        )
    
    # Humidity sensor
    if hasattr(device, 'hum_current') and device.hum_current is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["humidity"],
                lambda d: d.hum_current,
            )
        )
    
    # Pressure sensor
    if hasattr(device, 'press_pa_current') and device.press_pa_current is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["pressure"],
                lambda d: d.press_pa_current,
            )
        )
    
    # WiFi RSSI sensor
    if hasattr(device, 'wifi_rssi') and device.wifi_rssi is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SensorEntityDescription(
                    key="wifi_rssi",
                    name="WiFi Signal Strength",
                    device_class=SensorDeviceClass.SIGNAL_STRENGTH,
                    state_class=SensorStateClass.MEASUREMENT,
                    native_unit_of_measurement="dBm",
                    entity_category=EntityCategory.DIAGNOSTIC,
                ),
                lambda d: d.wifi_rssi,
            )
        )
    
    # Battery sensor (if available)
    if hasattr(device, 'battery_level') and device.battery_level is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["battery"],
                lambda d: d.battery_level,
            )
        )
    
    return sensors


def _create_soil_moisture_sensors(coordinator, device):
    """Create sensors for soil moisture sensor."""
    sensors = []
    
    # Temperature sensor
    if hasattr(device, 'temp_mk_current') and device.temp_mk_current is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["temperature"],
                lambda d: round((d.temp_mk_current * 1e-3 - 273.15), 1) if d.temp_mk_current else None,
            )
        )
    
    # Soil moisture sensor
    if hasattr(device, 'moist_percent_current') and device.moist_percent_current is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["soil_moisture"],
                lambda d: d.moist_percent_current,
            )
        )
    
    # Light sensor
    if hasattr(device, 'light_lux_current') and device.light_lux_current is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["light"],
                lambda d: d.light_lux_current,
            )
        )
    
    # RF RSSI sensor
    if hasattr(device, 'rf_rssi') and device.rf_rssi is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SensorEntityDescription(
                    key="rf_rssi",
                    name="RF Signal Strength",
                    device_class=SensorDeviceClass.SIGNAL_STRENGTH,
                    state_class=SensorStateClass.MEASUREMENT,
                    native_unit_of_measurement="dBm",
                    entity_category=EntityCategory.DIAGNOSTIC,
                ),
                lambda d: d.rf_rssi,
            )
        )
    
    # Battery sensor (if available)
    if hasattr(device, 'battery_level') and device.battery_level is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["battery"],
                lambda d: d.battery_level,
            )
        )
    
    return sensors


def _create_rain_sensors(coordinator, device):
    """Create sensors for rain sensor."""
    sensors = []
    
    # Total rainfall sensor
    if hasattr(device, 'rainfall_mm_total') and device.rainfall_mm_total is not None:
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
    
    # Hourly rainfall sensor
    if hasattr(device, 'rainfall_mm_hour') and device.rainfall_mm_hour is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SensorEntityDescription(
                    key="rainfall_hourly",
                    name="Hourly Rainfall",
                    device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
                    state_class=SensorStateClass.MEASUREMENT,
                    native_unit_of_measurement="mm/h",
                ),
                lambda d: d.rainfall_mm_hour,
            )
        )
    
    # Daily rainfall sensor
    if hasattr(device, 'rainfall_mm_daily') and device.rainfall_mm_daily is not None:
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
    
    # RF RSSI sensor
    if hasattr(device, 'rf_rssi') and device.rf_rssi is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SensorEntityDescription(
                    key="rf_rssi",
                    name="RF Signal Strength",
                    device_class=SensorDeviceClass.SIGNAL_STRENGTH,
                    state_class=SensorStateClass.MEASUREMENT,
                    native_unit_of_measurement="dBm",
                    entity_category=EntityCategory.DIAGNOSTIC,
                ),
                lambda d: d.rf_rssi,
            )
        )
    
    # Battery sensor (if available)
    if hasattr(device, 'battery_level') and device.battery_level is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["battery"],
                lambda d: d.battery_level,
            )
        )
    
    return sensors


def _create_air_sensors(coordinator, device):
    """Create sensors for air sensor."""
    sensors = []
    
    # Temperature sensor
    if hasattr(device, 'temp_mk_current') and device.temp_mk_current is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["temperature"],
                lambda d: round((d.temp_mk_current * 1e-3 - 273.15), 1) if d.temp_mk_current else None,
            )
        )
    
    # Humidity sensor
    if hasattr(device, 'hum_current') and device.hum_current is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["humidity"],
                lambda d: d.hum_current,
            )
        )
    
    # RF RSSI sensor
    if hasattr(device, 'rf_rssi') and device.rf_rssi is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SensorEntityDescription(
                    key="rf_rssi",
                    name="RF Signal Strength",
                    device_class=SensorDeviceClass.SIGNAL_STRENGTH,
                    state_class=SensorStateClass.MEASUREMENT,
                    native_unit_of_measurement="dBm",
                    entity_category=EntityCategory.DIAGNOSTIC,
                ),
                lambda d: d.rf_rssi,
            )
        )
    
    # Battery sensor (if available)
    if hasattr(device, 'battery_level') and device.battery_level is not None:
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                SENSOR_DESCRIPTIONS["battery"],
                lambda d: d.battery_level,
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
        
        # Safely get device identifiers with fallbacks
        device_mid = getattr(device, 'mid', 'unknown')
        device_did = getattr(device, 'did', 'unknown')
        device_name = getattr(device, 'name', 'Unknown Device')
        
        self._attr_unique_id = f"{device_mid}_{device_did}_{description.key}"
        self._attr_name = f"{device_name} {description.name}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        device_mid = getattr(self._device, 'mid', 'unknown')
        device_did = getattr(self._device, 'did', 'unknown')
        device_name = getattr(self._device, 'name', 'Unknown Device')
        device_model = getattr(self._device, 'model', None)
        device_sw_version = getattr(self._device, 'sw_version', None)
        device_serial = getattr(self._device, 'serial_number', None)
        
        # For hub devices (main devices)
        if isinstance(self._device, RainPointDisplayHub):
            device_info = DeviceInfo(
                identifiers={(DOMAIN, str(device_mid))},
                name=device_name,
                manufacturer="RainPoint",
                model=device_model or "Display Hub",
            )
            
            if device_sw_version:
                device_info["sw_version"] = device_sw_version
            if device_serial:
                device_info["serial_number"] = device_serial
                
            return device_info
        # For sub-devices that connect through a hub
        else:
            device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{device_mid}_{device_did}")},
                name=device_name,
                manufacturer="RainPoint",
                model=device_model or "Sensor",
                via_device=(DOMAIN, str(device_mid)),
            )
            
            if device_sw_version:
                device_info["sw_version"] = device_sw_version
            if device_serial:
                device_info["serial_number"] = device_serial
                
            return device_info

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        device_mid = getattr(self._device, 'mid', None)
        device_did = getattr(self._device, 'did', None)
        
        if device_mid is None or device_did is None:
            _LOGGER.warning("Device missing mid or did: %s", self._attr_unique_id)
            return None
            
        for device in self.coordinator.data.get("devices", []):
            if (getattr(device, 'mid', None) == device_mid and 
                getattr(device, 'did', None) == device_did):
                try:
                    value = self._value_fn(device)
                    _LOGGER.debug("Got value %s for sensor %s", value, self._attr_unique_id)
                    return value
                except (AttributeError, TypeError, ValueError) as err:
                    _LOGGER.debug("Error getting value for %s: %s", self._attr_unique_id, err)
                    return None
        
        _LOGGER.debug("Device not found for sensor %s", self._attr_unique_id)
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Fixed: Remove the None check - sensor should be available if coordinator is working
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        attributes = {}
        
        # Add device online status if available
        if hasattr(self._device, 'online'):
            attributes["device_online"] = getattr(self._device, 'online', False)
            
        # Add last seen timestamp if available
        if hasattr(self._device, 'last_seen'):
            attributes["last_seen"] = getattr(self._device, 'last_seen', None)
            
        return attributes if attributes else None
