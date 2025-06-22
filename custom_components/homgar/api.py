"""API client for HomGar."""
from __future__ import annotations

import logging
from typing import Any

from homgarapi import HomgarApi, HomgarApiException

_LOGGER = logging.getLogger(__name__)


class HomgarApiClient:
    """HomGar API client wrapper."""

    def __init__(self, email: str, password: str, area_code: str = "31") -> None:
        """Initialize the API client."""
        self.email = email
        self.password = password
        self.area_code = area_code
        self._api = HomgarApi()

    def ensure_logged_in(self) -> None:
        """Ensure we're logged in to the API."""
        try:
            self._api.ensure_logged_in(self.email, self.password, self.area_code)
            _LOGGER.debug("Successfully logged in to HomGar API")
        except HomgarApiException as err:
            _LOGGER.error("Failed to login to HomGar API: %s", err)
            raise
        except Exception as err:
            _LOGGER.error("Unexpected error during HomGar API login: %s", err)
            raise HomgarApiException(f"Login failed: {err}") from err

    def get_homes(self):
        """Get all homes."""
        try:
            homes = self._api.get_homes()
            _LOGGER.debug("Retrieved %d homes from HomGar API", len(homes) if homes else 0)
            return homes
        except Exception as err:
            _LOGGER.error("Failed to get homes from HomGar API: %s", err)
            raise

    def get_devices_for_hid(self, hid: str):
        """Get devices for a home ID."""
        try:
            devices = self._api.get_devices_for_hid(hid)
            _LOGGER.debug("Retrieved %d devices for home %s", len(devices) if devices else 0, hid)
            return devices
        except Exception as err:
            _LOGGER.error("Failed to get devices for home %s: %s", hid, err)
            raise

    def get_device_status(self, hub):
        """Get device status."""
        try:
            status = self._api.get_device_status(hub)
            _LOGGER.debug("Retrieved status for device %s", getattr(hub, 'name', 'unknown'))
            return status
        except Exception as err:
            _LOGGER.error("Failed to get device status for %s: %s", getattr(hub, 'name', 'unknown'), err)
            raise
