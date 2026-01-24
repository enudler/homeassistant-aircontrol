"""AirControlBase API Client."""
import logging
import aiohttp
import async_timeout
from typing import Any, Dict, List, Optional
import time
import json

_LOGGER = logging.getLogger(__name__)
class AirControlBaseError(Exception):
    """Base exception for AirControlBase."""

class AirControlBaseAuthError(AirControlBaseError):
    """Exception for authentication errors."""

class AirControlBaseConnectionError(AirControlBaseError):
    """Exception for connection errors."""

class AirControlBaseAPI:
    """AirControlBase API Client."""

    def __init__(
        self,
        email: str,
        password: str,
        session: aiohttp.ClientSession,
        avoid_refresh_status_on_update_in_ms: int = 5000,
    ) -> None:
        """Initialize the API client."""
        self._email = email
        self._password = password
        self._session = session
        self._base_url = "https://www.aircontrolbase.com"
        self._user_id = None
        self._session_id = None
        self._last_update_time = 0
        self._avoid_refresh_status_on_update_in_ms = avoid_refresh_status_on_update_in_ms

    async def login(self) -> None:
        """Login to AirControlBase."""
        data = {
            "account": self._email,
            "password": self._password,
            "avoidRefreshStatusOnUpdateInMs": self._avoid_refresh_status_on_update_in_ms,
        }
        
        _LOGGER.debug("Attempting login to AirControlBase with email: %s", self._email)
        
        try:
            # Use form data (this is what works!)
            async with async_timeout.timeout(10):
                async with self._session.post(
                    f"{self._base_url}/web/user/login",
                    data=data,  # Use form data, not JSON
                ) as response:
                    _LOGGER.debug("Login response status: %s", response.status)
                    _LOGGER.debug("Login response headers: %s", dict(response.headers))
                    
                    if response.status in (401, 403):
                        raise AirControlBaseAuthError(f"HTTP error {response.status}")
                    if response.status != 200:
                        raise AirControlBaseConnectionError(f"HTTP error {response.status}")
                    
                    try:
                        result = await response.json()
                    except Exception as e:
                        text_result = await response.text()
                        _LOGGER.error("Failed to parse JSON response: %s. Raw response: %s", e, text_result)
                        raise Exception(f"Invalid response format: {e}")
                    
                    _LOGGER.debug("Login response: %s", result)
                    
                    # Check for success (code "200" for form data)
                    if (result.get("code") == "200" or 
                        result.get("code") == 200 or
                        result.get("msg") == "操作成功"):  # "Operation successful" in Chinese
                        
                        # Extract user ID from result
                        if "result" in result and "id" in result["result"]:
                            self._user_id = result["result"]["id"]
                        else:
                            _LOGGER.error("No user ID found in response: %s", result)
                            raise AirControlBaseAuthError("No user ID in response")
                        
                        # Extract session cookie
                        cookies = response.headers.getall('Set-Cookie', [])
                        if cookies:
                            self._session_id = '; '.join(cookies)
                        else:
                            _LOGGER.warning("No session cookies found")
                            self._session_id = ""
                        
                        _LOGGER.info("Successfully logged in to AirControlBase (User ID: %s)", self._user_id)
                    else:
                        error_msg = result.get('msg') or result.get('message') or f"Unknown error (code: {result.get('code')})"
                        _LOGGER.error("Login failed: %s", error_msg)
                        raise AirControlBaseAuthError(f"Login failed: {error_msg}")
                        
        except AirControlBaseAuthError:
            raise
        except Exception as e:
            _LOGGER.error("Login exception: %s", e)
            raise AirControlBaseConnectionError(f"Authentication failed: {e}")

    async def _request(self, endpoint: str, data: Dict[str, Any], retry: bool = True) -> Dict[str, Any]:
        """Centralized request method with automatic re-authentication."""
        if not self._user_id:
            await self.login()

        url = f"{self._base_url}{endpoint}"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        if self._session_id:
            headers["Cookie"] = self._session_id

        try:
            async with async_timeout.timeout(10):
                async with self._session.post(url, data=data, headers=headers) as response:
                    _LOGGER.debug("%s response status: %s", endpoint, response.status)

                    if response.status in (401, 403):
                        if retry:
                            _LOGGER.warning("Unauthorized (%s). Attempting re-authentication...", response.status)
                            self._user_id = None
                            self._session_id = None
                            await self.login()
                            return await self._request(endpoint, data, retry=False)
                        raise AirControlBaseAuthError(f"HTTP error {response.status}")

                    if response.status != 200:
                        raise AirControlBaseConnectionError(f"HTTP error {response.status}")

                    result = await response.json()
                    _LOGGER.debug("%s response: %s", endpoint, result)

                    # Check for "session expired" or "not logged in" messages/codes
                    # Some APIs return 200 but with an error code in the body
                    code = result.get("code")
                    if (code in ("401", 401, "403", 403) or 
                        result.get("msg") in ("token expired", "session expired", "请重新登录")): # "Please log in again"
                        if retry:
                            _LOGGER.warning("Session expired (code %s). Attempting re-authentication...", code)
                            self._user_id = None
                            self._session_id = None
                            await self.login()
                            return await self._request(endpoint, data, retry=False)
                        error_msg = result.get('msg') or "Session expired"
                        raise AirControlBaseAuthError(f"Authentication failed: {error_msg}")

                    if not (code in ("200", 200) or result.get("msg") == "操作成功"):
                        error_msg = result.get('msg') or result.get('message') or f"Unknown error (code: {code})"
                        raise AirControlBaseError(f"API error: {error_msg}")

                    return result
        except (AirControlBaseAuthError, AirControlBaseError):
            raise
        except Exception as e:
            _LOGGER.error("Request to %s failed: %s", endpoint, e)
            raise AirControlBaseConnectionError(f"Request failed: {e}")

    async def control_device(self, control: Dict[str, Any], operation: Dict[str, Any]) -> None:
        """Control a device."""
        self._last_update_time = int(time.time() * 1000)
        
        # Convert operation to JSON string for form encoding
        # The original code seemed to use 'operation' for both 'control' and 'operation' fields in form_data
        # but the filtered_control logic suggested it might want more. 
        # Keeping consistent with the working implementation I see in the file lines 114-117.
        form_data = {
            "userId": self._user_id if self._user_id else "", # _request will handle login if empty
            "control": json.dumps(operation),
            "operation": json.dumps(operation),
        }

        await self._request("/web/device/control", form_data)

    async def get_devices(self) -> List[Dict[str, Any]]:
        """Get all devices."""
        if (
            self._last_update_time > 0
            and int(time.time() * 1000) - self._last_update_time
            < self._avoid_refresh_status_on_update_in_ms
        ):
            return []

        data = {"userId": self._user_id if self._user_id else ""}
        
        result = await self._request("/web/userGroup/getDetails", data)
        
        all_devices = []
        if result.get("result", {}).get("areas"):
            for area in result["result"]["areas"]:
                all_devices.extend(area.get("data", []))
        _LOGGER.debug("Parsed devices: %s", all_devices)
        return all_devices

    async def getDetails(self) -> List[Dict[str, Any]]:
        """Fetch device details from the API."""
        data = {"userId": self._user_id if self._user_id else ""}
        
        result = await self._request("/web/userGroup/getDetails", data)

        all_devices = []
        if result.get("result", {}).get("areas"):
            for area in result["result"]["areas"]:
                all_devices.extend(area.get("data", []))
        _LOGGER.debug("Parsed devices: %s", all_devices)
        return all_devices

    async def test_connection(self) -> bool:
        """Test if the connection and authentication are working."""
        try:
            await self.login()
            # Try to get devices to fully test the connection
            devices = await self.get_devices()
            return True
        except Exception as e:
            _LOGGER.error("Connection test failed: %s", e)
            return False

    async def ensure_authenticated(self) -> None:
        """Ensure the API client is authenticated."""
        if not self._user_id or not self._session_id:
            _LOGGER.warning("Session expired or not authenticated. Re-authenticating...")
            await self.login()