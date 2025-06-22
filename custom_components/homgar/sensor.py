"""Sensor platform for HomGar integration."""
from __future__ import annotations

import logging
from typing import Any, Callable

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

# Constants
TEMPERATURE_CONVERSION_FACTOR = 1e-3
KELVIN_TO_CELSIUS_OFFSET = 273.15

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


def kelvin_millikelvin_to_celsius(temp_mk: float | None) -> float | None:
    """Convert temperature from millikelvin to Celsius."""
    if temp_mk is None:
        return None
    return round((temp_mk * TEMPERATURE_CONVERSION_FACTOR - KELVIN_TO_CELSIUS_OFFSET), 1)


def create_rf_rssi_description() -> SensorEntityDescription:
    """Create RF RSSI sensor description."""
    return SensorEntityDescription(
        key="rf_rssi",
        name="RF Signal Strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="dBm",
        entity_category=EntityCategory.DIAGNOSTIC,
    )


def create_wifi_rssi_description() -> SensorEntityDescription:
    """Create WiFi RSSI sensor description."""
    return SensorEntityDescription(
        key="wifi_rssi",
        name="WiFi Signal Strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="dBm",
        entity_category=EntityCategory.DIAGNOSTIC,
    )


def create_sensor_if_exists(
    sensors: list[HomgarSensor],
    coordinator: HomgarDataUpdateCoordinator,
    device: Any,
    attr_name: str,
    description: SensorEntityDescription,
    value_fn: Callable[[Any], Any] | None = None,
) -> None:
    """Helper to create sensor if attribute exists on device."""
    if hasattr(device, attr_name) and getattr(device, attr_name) is not None:
        final_value_fn = value_fn or (lambda d, attr=attr_name: getattr(d, attr))
        sensors.append(
            HomgarSensor(
                coordinator,
                device,
                description,
                final_value_fn,
            )
        )


def add_common_sensors(
    sensors: list[HomgarSensor],
    coordinator: HomgarDataUpdateCoordinator,
    device: Any,
) -> None:
    """Add common sensors that appear on multiple device types."""
    
    # Temperature sensor (common pattern)
    create_sensor_if_exists(
        sensors, coordinator, device, 'temp_mk_current',
        SENSOR_DESCRIPTIONS["temperature"],
        lambda d: kelvin_millikelvin_to_celsius(d.temp_mk_current)
    )
    
    # Humidity sensor (common pattern)
    create_sensor_if_exists(
        sensors, coordinator, device, 'hum_current',
        SENSOR_DESCRIPTIONS["humidity"]
    )
    
    # RF RSSI sensor (common pattern)
    create_sensor_if_exists(
        sensors, coordinator, device, 'rf_rssi',
        create_rf_rssi_description()
    )
    
    # Battery sensor (common pattern)
    create_sensor_if_exists(
        sensors, coordinator, device, 'battery_level',
        SENSOR_DESCRIPTIONS["battery"]
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HomGar sensors from a config entry."""
    coordinator: HomgarDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[HomgarSensor] = []

    for device in coordinator.data.get("devices", []):
        device_sensors: list[HomgarSensor] = []
        
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


def _create_hub_sensors(coordinator: HomgarDataUpdateCoordinator, device: Any) -> list[HomgarSensor]:
    """Create sensors for display hub."""
    sensors: list[HomgarSensor] = []
    
    # Add common sensors
    add_common_sensors(sensors, coordinator, device)
    
    # Hub-specific sensors
    create_sensor_if_exists(
        sensors, coordinator, device, 'press_pa_current',
        SENSOR_DESCRIPTIONS["pressure"]
    )
    
    create_sensor_if_exists(
        sensors, coordinator, device, 'wifi_rssi',
        create_wifi_rssi_description()
    )
    
    return sensors


def _create_soil_moisture_sensors(coordinator: HomgarDataUpdateCoordinator, device: Any) -> list[HomgarSensor]:
    """Create sensors for soil moisture sensor."""
    sensors: list[HomgarSensor] = []
    
    # Add common sensors
    add_common_sensors(sensors, coordinator, device)
    
    # Soil moisture specific sensors
    create_sensor_if_exists(
        sensors, coordinator, device, 'moist_percent_current',
        SENSOR_DESCRIPTIONS["soil_moisture"]
    )
    
    create_sensor_if_exists(
        sensors, coordinator, device, 'light_lux_current',
        SENSOR_DESCRIPTIONS["light"]
    )
    
    return sensors


def _create_rain_sensors(coordinator: HomgarDataUpdateCoordinator, device: Any) -> list[HomgarSensor]:
    """Create sensors for rain sensor."""
    sensors: list[HomgarSensor] = []
    
    # Add common sensors (only RF RSSI and battery for rain sensors)
    create_sensor_if_exists(
        sensors, coordinator, device, 'rf_rssi',
        create_rf_rssi_description()
    )
    
    create_sensor_if_exists(
        sensors, coordinator, device, 'battery_level',
        SENSOR_DESCRIPTIONS["battery"]
    )
    
    # Rain specific sensors
    create_sensor_if_exists(
        sensors, coordinator, device, 'rainfall_mm_total',
        SensorEntityDescription(
            key="rainfall_total",
            name="Total Rainfall",
            device_class=SensorDeviceClass.PRECIPITATION,
            state_class=SensorStateClass.TOTAL_INCREASING,
            native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        )
    )
    
    create_sensor_if_exists(
        sensors, coordinator, device, 'rainfall_mm_hour',
        SensorEntityDescription(
            key="rainfall_hourly",
            name="Hourly Rainfall",
            device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="mm/h",
        )
    )
    
    create_sensor_if_exists(
        sensors, coordinator, device, 'rainfall_mm_daily',
        SensorEntityDescription(
            key="rainfall_daily",
            name="Daily Rainfall",
            device_class=SensorDeviceClass.PRECIPITATION,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        )
    )
    
    return sensors


def _create_air_sensors(coordinator: HomgarDataUpdateCoordinator, device: Any) -> list[HomgarSensor]:
    """Create sensors for air sensor."""
    sensors: list[HomgarSensor] = []
    
    # Add common sensors
    add_common_sensors(sensors, coordinator, device)
    
    return sensors


class HomgarSensor(CoordinatorEntity, SensorEntity):
    """HomGar sensor."""

    def __init__(
        self,
        coordinator: HomgarDataUpdateCoordinator,
        device: Any,
        description: SensorEntityDescription,
        value_fn: Callable[[Any], Any],
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
        # For sub-devices that connect through a hub
        else:
            device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{device_mid}_{device_did}")},
                name=device_name,
                manufacturer="RainPoint",
                model=device_model or "Sensor",
                via_device=(DOMAIN, str(device_mid)),
            )
        
        # Add optional fields if available
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
        if not self.coordinator.last_update_success:
            return False
        
        # Check if device is online if that information is available
        if hasattr(self._device, 'online'):
            return getattr(self._device, 'online', True)
        
        # Check if we have a valid value
        return self.native_value is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        attributes: dict[str, Any] = {}
        
        # Add device online status if available
        if hasattr(self._device, 'online'):
            attributes["device_online"] = getattr(self._device, 'online', False)
            
        # Add last seen timestamp if available
        if hasattr(self._device, 'last_seen'):
            last_seen = getattr(self._device, 'last_seen', None)
            if last_seen:
                attributes["last_seen"] = last_seen
        
        # Add signal quality indicators
        if hasattr(self._device, 'rf_rssi'):
            rf_rssi = getattr(self._device, 'rf_rssi', None)
            if rf_rssi is not None:
                attributes["rf_signal_quality"] = "Excellent" if rf_rssi > -50 else "Good" if rf_rssi > -70 else "Fair" if rf_rssi > -85 else "Poor"
        
        if hasattr(self._device, 'wifi_rssi'):
            wifi_rssi = getattr(self._device, 'wifi_rssi', None)
            if wifi_rssi is not None:
                attributes["wifi_signal_quality"] = "Excellent" if wifi_rssi > -50 else "Good" if wifi_rssi > -70 else "Fair" if wifi_rssi > -85 else "Poor"
                
        return attributes if attributes else None
