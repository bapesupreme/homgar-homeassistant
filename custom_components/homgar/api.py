"""API client for HomGar."""
from __future__ import annotations

import logging
import time
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
        self._last_login_time = 0
        self._login_retry_count = 0
        self._max_retries = 3

    def ensure_logged_in(self) -> None:
        """Ensure we're logged in to the API with retry logic."""
        current_time = time.time()
        
        # If we've failed too many times recently, wait before retrying
        if self._login_retry_count >= self._max_retries:
            if current_time - self._last_login_time < 300:  # 5 minutes
                raise HomgarApiException("Too many login failures, please wait before retrying")
            else:
                # Reset retry count after waiting period
                self._login_retry_count = 0

        try:
            self._api.ensure_logged_in(self.email, self.password, self.area_code)
            self._last_login_time = current_time
            self._login_retry_count = 0  # Reset on successful login
            _LOGGER.debug("Successfully logged in to HomGar API")
            
        except HomgarApiException as err:
            self._login_retry_count += 1
            self._last_login_time = current_time
            
            # Check for specific error types
            error_str = str(err).lower()
            if any(code in error_str for code in ['401', '403', 'unauthorized', 'forbidden']):
                _LOGGER.error("Authentication failed for HomGar API - check credentials: %s", err)
                raise HomgarApiException("Invalid credentials") from err
            elif 'timeout' in error_str or 'connection' in error_str:
                _LOGGER.error("Connection timeout to HomGar API: %s", err)
                raise HomgarApiException("Connection timeout") from err
            else:
                _LOGGER.error("Failed to login to HomGar API: %s", err)
                raise
                
        except Exception as err:
            self._login_retry_count += 1
            self._last_login_time = current_time
            _LOGGER.error("Unexpected error during HomGar API login: %s", err)
            raise HomgarApiException(f"Login failed: {err}") from err

    def get_homes(self):
        """Get all homes with error handling."""
        try:
            homes = self._api.get_homes()
            home_count = len(homes) if homes else 0
            _LOGGER.debug("Retrieved %d homes from HomGar API", home_count)
            
            if homes:
                for home in homes:
                    _LOGGER.debug("Home: %s (HID: %s)", 
                                 getattr(home, 'name', 'Unknown'), 
                                 getattr(home, 'hid', 'Unknown'))
            
            return homes or []
            
        except HomgarApiException:
            # Re-raise HomGar specific exceptions
            raise
        except Exception as err:
            _LOGGER.error("Failed to get homes from HomGar API: %s", err)
            raise HomgarApiException(f"Failed to retrieve homes: {err}") from err

    def get_devices_for_hid(self, hid: str):
        """Get devices for a home ID with error handling."""
        if not hid:
            _LOGGER.warning("Empty HID provided to get_devices_for_hid")
            return []
            
        try:
            devices = self._api.get_devices_for_hid(hid)
            device_count = len(devices) if devices else 0
            _LOGGER.debug("Retrieved %d devices for home %s from HomGar API", device_count, hid)
            
            if devices:
                for device in devices:
                    _LOGGER.debug("Device: %s (MID: %s, DID: %s, Type: %s)", 
                                 getattr(device, 'name', 'Unknown'),
                                 getattr(device, 'mid', 'Unknown'),
                                 getattr(device, 'did', 'Unknown'),
                                 type(device).__name__)
            
            return devices or []
            
        except HomgarApiException:
            # Re-raise HomGar specific exceptions
            raise
        except Exception as err:
            _LOGGER.error("Failed to get devices for home %s from HomGar API: %s", hid, err)
            raise HomgarApiException(f"Failed to retrieve devices for home {hid}: {err}") from err

    def get_device_status(self, hub):
        """Get device status with error handling."""
        if not hub:
            _LOGGER.warning("No hub provided to get_device_status")
            return None
            
        device_name = getattr(hub, 'name', 'Unknown')
        device_mid = getattr(hub, 'mid', 'Unknown')
        
        try:
            status = self._api.get_device_status(hub)
            _LOGGER.debug("Retrieved status for device %s (MID: %s)", device_name, device_mid)
            
            # Log some status details if available
            if hasattr(hub, 'online'):
                _LOGGER.debug("Device %s online status: %s", device_name, hub.online)
            if hasattr(hub, 'subdevices') and hub.subdevices:
                _LOGGER.debug("Device %s has %d subdevices", device_name, len(hub.subdevices))
                
            return status
            
        except HomgarApiException:
            # Re-raise HomGar specific exceptions
            raise
        except Exception as err:
            _LOGGER.error("Failed to get device status for %s (MID: %s): %s", 
                         device_name, device_mid, err)
            raise HomgarApiException(f"Failed to get status for device {device_name}: {err}") from err

    def is_authenticated(self) -> bool:
        """Check if we're currently authenticated."""
        try:
            # This is a simple check - you might need to implement this in the homgarapi library
            return hasattr(self._api, '_session') and self._api._session is not None
        except Exception:
            return False

    def reset_connection(self) -> None:
        """Reset the API connection (useful for error recovery)."""
        try:
            self._api = HomgarApi()
            self._login_retry_count = 0
            _LOGGER.info("Reset HomGar API connection")
        except Exception as err:
            _LOGGER.error("Failed to reset HomGar API connection: %s", err)
