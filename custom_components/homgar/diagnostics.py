"""Diagnostics support for HomGar."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import HomgarDataUpdateCoordinator
from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: HomgarDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Get device info without sensitive data
    devices_info = []
    for device in coordinator.data.get("devices", []):
        device_info = {
            "name": getattr(device, "name", "Unknown"),
            "model": getattr(device, "model", "Unknown"),
            "mid": getattr(device, "mid", "Unknown"),
            "did": getattr(device, "did", "Unknown"),
            "type": type(device).__name__,
            "online": getattr(device, "online", False),
        }
        
        # Add sensor values (non-sensitive)
        if hasattr(device, "temp_mk_current") and device.temp_mk_current is not None:
            device_info["temperature"] = round((device.temp_mk_current * 1e-3 - 273.15), 2)
        if hasattr(device, "hum_current") and device.hum_current is not None:
            device_info["humidity"] = device.hum_current
        if hasattr(device, "moist_percent_current") and device.moist_percent_current is not None:
            device_info["soil_moisture"] = device.moist_percent_current
        if hasattr(device, "rainfall_mm_total") and device.rainfall_mm_total is not None:
            device_info["rainfall_total"] = device.rainfall_mm_total
        if hasattr(device, "rf_rssi") and device.rf_rssi is not None:
            device_info["rf_rssi"] = device.rf_rssi
        if hasattr(device, "wifi_rssi") and device.wifi_rssi is not None:
            device_info["wifi_rssi"] = device.wifi_rssi
            
        devices_info.append(device_info)
    
    return {
        "entry": {
            "title": entry.title,
            "version": entry.version,
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval": coordinator.update_interval.total_seconds(),
            "homes_count": len(coordinator.data.get("homes", [])),
            "devices_count": len(coordinator.data.get("devices", [])),
        },
        "devices": devices_info,
    }
