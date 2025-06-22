"""API client for HomGar."""
from __future__ import annotations

import logging
import random
import time
from typing import Any

from homgarapi import HomgarApi, HomgarApiException

_LOGGER = logging.getLogger(__name__)

# Constants
LOGIN_RETRY_TIMEOUT = 300  # 5 minutes
MAX_LOGIN_RETRIES = 3
MIN_BACKOFF_DELAY = 1
MAX_BACKOFF_DELAY = 60
REQUEST_TIMEOUT = 30


class HomgarApiClient:
    """HomGar API client wrapper."""

    def __init__(self, email: str, password: str, area_code: str = "31", timeout: int = REQUEST_TIMEOUT) -> None:
        """Initialize the API client."""
        self.email = email
        self.password = password
        self.area_code = area_code
        self._api = HomgarApi()
        self._last_login_time = 0
        self._login_retry_count = 0
        self._max_retries = MAX_LOGIN_RETRIES
        self._timeout = timeout

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter."""
        base_delay = min(MAX_BACKOFF_DELAY, (2 ** attempt))
        jitter = random.uniform(0.1, 0.5)
        return max(MIN_BACKOFF_DELAY, base_delay * jitter)

    def _is_authentication_error(self, error_str: str) -> bool:
        """Check if error indicates authentication failure."""
        auth_indicators = ['401', '403', 'unauthorized', 'forbidden', 'invalid credentials']
        return any(indicator in error_str for indicator in auth_indicators)

    def _is_connection_error(self, error_str: str) -> bool:
        """Check if error indicates connection issues."""
        connection_indicators = ['timeout', 'connection', 'network', 'unreachable']
        return any(indicator in error_str for indicator in connection_indicators)

    def ensure_logged_in(self) -> None:
        """Ensure we're logged in to the API with retry logic."""
        current_time = time.time()
        
        # If we've failed too many times recently, wait before retrying
        if self._login_retry_count >= self._max_retries:
            if current_time - self._last_login_time < LOGIN_RETRY_TIMEOUT:
                backoff_delay = self._calculate_backoff_delay(self._login_retry_count)
                raise HomgarApiException(
                    f"Too many login failures, please wait {backoff_delay:.1f} seconds before retrying"
                )
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
            
            error_str = str(err).lower()
            if self._is_authentication_error(error_str):
                _LOGGER.error("Authentication failed for HomGar API - check credentials: %s", err)
                raise HomgarApiException("Invalid credentials") from err
            elif self._is_connection_error(error_str):
                _LOGGER.error("Connection timeout to HomGar API: %s", err)
                raise HomgarApiException("Connection timeout") from err
            else:
                _LOGGER.error("Failed to login to HomGar API (attempt %d/%d): %s", 
                             self._login_retry_count, self._max_retries, err)
                raise
                
        except Exception as err:
            self._login_retry_count += 1
            self._last_login_time = current_time
            _LOGGER.error("Unexpected error during HomGar API login: %s", err)
            raise HomgarApiException(f"Login failed: {err}") from err

    def get_homes(self) -> list[Any]:
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

    def get_devices_for_hid(self, hid: str) -> list[Any]:
        """Get devices for a home ID with error handling."""
        if not hid or not isinstance(hid, str):
            _LOGGER.warning("Invalid HID provided to get_devices_for_hid: %s", hid)
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

    def get_device_status(self, hub: Any) -> Any:
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
            self._last_login_time = 0
            _LOGGER.info("Reset HomGar API connection")
        except Exception as err:
            _LOGGER.error("Failed to reset HomGar API connection: %s", err)

    async def async_health_check(self) -> bool:
        """Check if the API connection is healthy."""
        try:
            # This would need to be implemented with proper async context
            self.get_homes()
            return True
        except Exception:
            return False

    @property
    def retry_count(self) -> int:
        """Get current retry count for diagnostics."""
        return self._login_retry_count

    @property
    def last_login_time(self) -> float:
        """Get last login time for diagnostics."""
        return self._last_login_time
