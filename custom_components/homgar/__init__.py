"""HomGar integration for Home Assistant."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .api import HomgarApiClient
from homgarapi import HomgarApiException

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]
SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HomGar from a config entry."""
    coordinator = HomgarDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class HomgarDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the HomGar API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.api = HomgarApiClient(
            email=entry.data["email"],
            password=entry.data["password"],
            area_code=entry.data.get("area_code", "31"),
        )
        self.homes = []
        self.devices = []

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            await self.hass.async_add_executor_job(self._update_data)
            return {"homes": self.homes, "devices": self.devices}
        except HomgarApiException as exception:
            _LOGGER.error("Error communicating with HomGar API: %s", exception)
            raise UpdateFailed(f"Error communicating with API: {exception}") from exception
        except Exception as exception:
            _LOGGER.error("Unexpected error updating HomGar data: %s", exception)
            raise UpdateFailed(f"Unexpected error: {exception}") from exception

    def _update_data(self):
        """Fetch data from API endpoint."""
        self.api.ensure_logged_in()
        self.homes = self.api.get_homes()
        self.devices = []
        
        for home in self.homes:
            hubs = self.api.get_devices_for_hid(home.hid)
            for hub in hubs:
                self.api.get_device_status(hub)
                self.devices.append(hub)
                self.devices.extend(hub.subdevices)

async def _async_update_data(self):
    """Update data via library."""
    try:
        await self.hass.async_add_executor_job(self._update_data)
        
        # Validate data structure
        if not isinstance(self.homes, list):
            self.homes = []
        if not isinstance(self.devices, list):
            self.devices = []
            
        return {"homes": self.homes, "devices": self.devices}
    except Exception as exception:
        # ... existing error handling

def _update_data(self):
    """Fetch data from API endpoint."""
    self.api.ensure_logged_in()
    self.homes = self.api.get_homes()
    self.devices = []
    
    _LOGGER.debug("Found %d homes", len(self.homes))
    
    for home in self.homes:
        hubs = self.api.get_devices_for_hid(home.hid)
        for hub in hubs:
            self.api.get_device_status(hub)
            self.devices.append(hub)
            self.devices.extend(hub.subdevices)
            
    _LOGGER.debug("Total devices discovered: %d", len(self.devices))
