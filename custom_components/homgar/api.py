"""API client for HomGar."""
from __future__ import annotations

import asyncio
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
        except HomgarApiException as err:
            _LOGGER.error("Failed to login to HomGar API: %s", err)
            raise

    def get_homes(self):
        """Get all homes."""
        return self._api.get_homes()

    def get_devices_for_hid(self, hid: str):
        """Get devices for a home ID."""
        return self._api.get_devices_for_hid(hid)

    def get_device_status(self, hub):
        """Get device status."""
        return self._api.get_device_status(hub)
