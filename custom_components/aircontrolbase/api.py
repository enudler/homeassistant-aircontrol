"""AirControlBase API Client."""
import logging
import aiohttp
import async_timeout
from typing import Any, Dict, List, Optional
import time
import json

_LOGGER = logging.getLogger(__name__)

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
                    
                    if response.status != 200:
                        raise Exception(f"HTTP error {response.status}")
                    
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
                            raise Exception("No user ID in response")
                        
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
                        raise Exception(f"Login failed: {error_msg}")
                        
        except Exception as e:
            _LOGGER.error("Login exception: %s", e)
            raise Exception(f"Authentication failed: {e}")

    async def control_device(self, control: Dict[str, Any], operation: Dict[str, Any]) -> None:
        """Control a device."""
        if not self._user_id:
            raise Exception("Not authenticated - please login first")

        self._last_update_time = int(time.time() * 1000)
        data = {
            "userId": self._user_id,
            "control": control,
            "operation": operation,
        }

        # Filter the control data to include only the required fields
        allowed_fields = [
            "power", "mode", "setTemp", "wind", "swing", "lock", "factTemp",
            "modeLockValue", "coolLockValue", "heatLockValue", "windLockValue", "unlock", "id"
        ]
        filtered_control = {key: control[key] for key in allowed_fields if key in control}

        # Convert control and operation to JSON strings for form encoding
        form_data = {
            "userId": self._user_id,
            "control": json.dumps(operation),
            "operation": json.dumps(operation),
        }

        _LOGGER.debug("Sending control request with filtered data: %s", form_data)

        try:
            async with async_timeout.timeout(10):
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                }
                if self._session_id:
                    headers["Cookie"] = self._session_id

                async with self._session.post(
                    f"{self._base_url}/web/device/control",
                    data=form_data,  # Use form-encoded data
                    headers=headers,
                ) as response:
                    _LOGGER.debug("Control device response status: %s", response.status)

                    if response.status != 200:
                        raise Exception(f"HTTP error {response.status}")

                    result = await response.json()
                    _LOGGER.debug("Control device response: %s", result)

                    # Generate a cURL command for debugging
                    curl_command = (
                        f"curl --location '{self._base_url}/web/device/control' \\"
                        f"\n--header 'Content-Type: application/x-www-form-urlencoded' \\"
                        f"\n--header 'Cookie: {headers.get('Cookie', '')}' \\"
                        f"\n--data-urlencode 'userId={self._user_id}' \\"
                        f"\n--data-urlencode 'control={json.dumps(operation)}' \\"
                        f"\n--data-urlencode 'operation={json.dumps(operation)}'"
                    )
                    _LOGGER.debug("Generated cURL command: %s", curl_command)

                    # Check for success
                    if not (result.get("code") == "200" or result.get("code") == 200 or 
                            result.get("msg") == "操作成功"):
                        error_msg = result.get('msg') or result.get('message') or "Unknown error"
                        raise Exception(f"Control failed: {error_msg}")

        except Exception as e:
            _LOGGER.error("Control device failed: %s", e)
            raise Exception(f"Device control failed: {e}")

    async def get_devices(self) -> List[Dict[str, Any]]:
        """Get all devices."""
        if (
            self._last_update_time > 0
            and int(time.time() * 1000) - self._last_update_time
            < self._avoid_refresh_status_on_update_in_ms
        ):
            return []

        if not self._user_id:
            raise Exception("Not authenticated - please login first")

        data = {"userId": self._user_id}
        
        try:
            async with async_timeout.timeout(10):
                headers = {}
                if self._session_id:
                    headers["Cookie"] = self._session_id
                
                # Use form data consistently
                async with self._session.post(
                    f"{self._base_url}/web/userGroup/getDetails",
                    data=data,  # Use form data
                    headers=headers,
                ) as response:
                    _LOGGER.debug("Get devices response status: %s", response.status)
                    
                    if response.status != 200:
                        raise Exception(f"HTTP error {response.status}")
                    
                    result = await response.json()
                    _LOGGER.debug("Get devices response: %s", result)
                    
                    # Check for success (code "200" for this API)
                    if (result.get("code") == "200" or result.get("code") == 200 or
                        result.get("msg") == "操作成功"):  # "Operation successful"
                        all_devices = []
                        if result.get("result", {}).get("areas"):
                            for area in result["result"]["areas"]:
                                all_devices.extend(area.get("data", []))
                        _LOGGER.debug("Parsed devices: %s", all_devices)
                        return all_devices
                    else:
                        error_msg = result.get('msg') or result.get('message') or "Unknown error"
                        _LOGGER.error("Failed to get devices: %s", error_msg)
                        raise Exception(f"Failed to get devices: {error_msg}")
                        
        except Exception as e:
            _LOGGER.error("Get devices failed: %s", e)
            raise Exception(f"Failed to get devices: {e}")

    async def getDetails(self) -> List[Dict[str, Any]]:
        """Fetch device details from the API."""
        if not self._user_id:
            raise Exception("Not authenticated - please login first")

        data = {"userId": self._user_id}

        try:
            async with async_timeout.timeout(10):
                headers = {}
                if self._session_id:
                    headers["Cookie"] = self._session_id

                async with self._session.post(
                    f"{self._base_url}/web/userGroup/getDetails",
                    data=data,
                    headers=headers,
                ) as response:
                    _LOGGER.debug("GetDetails response status: %s", response.status)

                    if response.status != 200:
                        raise Exception(f"HTTP error {response.status}")

                    result = await response.json()
                    _LOGGER.debug("GetDetails response: %s", result)

                    if result.get("code") in ("200", 200) or result.get("msg") == "操作成功":
                        all_devices = []
                        if result.get("result", {}).get("areas"):
                            for area in result["result"]["areas"]:
                                all_devices.extend(area.get("data", []))
                        _LOGGER.debug("Parsed devices: %s", all_devices)
                        return all_devices
                    else:
                        error_msg = result.get('msg') or result.get('message') or "Unknown error"
                        raise Exception(f"API error: {error_msg}")
        except Exception as err:
            _LOGGER.error("Error in getDetails: %s", err)
            raise

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