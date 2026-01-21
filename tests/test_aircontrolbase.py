import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
import aiohttp
from custom_components.aircontrolbase.api import AirControlBaseAPI

@pytest.mark.asyncio
async def test_login_success(api_client):
    """Test successful login."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "code": "200",
        "result": {"id": "user123"},
        "msg": "操作成功"
    })
    mock_response.headers = MagicMock()
    mock_response.headers.getall.return_value = ["session_id=xyz"]
    
    # Mock the context manager
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_response
    
    with patch.object(api_client._session, 'post', return_value=mock_cm):
        await api_client.login()
        assert api_client._user_id == "user123"
        assert "session_id=xyz" in api_client._session_id

@pytest.mark.asyncio
async def test_login_failure(api_client):
    """Test failed login."""
    mock_response = MagicMock()
    mock_response.status = 401
    mock_response.json = AsyncMock(return_value={"code": "401", "msg": "Unauthorized"})
    
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_response
    
    with patch.object(api_client._session, 'post', return_value=mock_cm):
        with pytest.raises(Exception, match="Authentication failed: HTTP error 401"):
            await api_client.login()

@pytest.mark.asyncio
async def test_get_devices_success(api_client):
    """Test successful device listing."""
    api_client._user_id = "user123"
    api_client._session_id = "session_id=xyz"
    
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "code": "200",
        "result": {
            "areas": [
                {
                    "data": [
                        {"id": "device1", "name": "Living Room AC"},
                        {"id": "device2", "name": "Bedroom AC"}
                    ]
                }
            ]
        }
    })
    
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_response
    
    with patch.object(api_client._session, 'post', return_value=mock_cm):
        devices = await api_client.get_devices()
        assert len(devices) == 2
        assert devices[0]["id"] == "device1"
        assert devices[1]["name"] == "Bedroom AC"

@pytest.mark.asyncio
async def test_control_device_success(api_client):
    """Test successful device control."""
    api_client._user_id = "user123"
    api_client._session_id = "session_id=xyz"
    
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"code": "200", "msg": "操作成功"})
    
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_response
    
    with patch.object(api_client._session, 'post', return_value=mock_cm):
        control = {"power": "y", "mode": "cool"}
        operation = {"power": "y", "mode": "cool"}
        await api_client.control_device(control, operation)

@pytest.mark.asyncio
async def test_request_retry_on_expired_session(api_client):
    """Test that a request retries after session expiration."""
    api_client._user_id = "expired_user"
    api_client._session_id = "expired_session"

    # First response: Session expired (code 401 in body)
    mock_response_expired = MagicMock()
    mock_response_expired.status = 200
    mock_response_expired.json = AsyncMock(return_value={"code": "401", "msg": "session expired"})
    
    # Second response (after re-login): Success
    mock_response_success = MagicMock()
    mock_response_success.status = 200
    mock_response_success.json = AsyncMock(return_value={
        "code": "200", 
        "result": {"areas": [{"data": [{"id": "1"}]}]},
        "msg": "操作成功"
    })

    # Mock login success
    mock_response_login = MagicMock()
    mock_response_login.status = 200
    mock_response_login.json = AsyncMock(return_value={
        "code": "200",
        "result": {"id": "new_user"},
        "msg": "操作成功"
    })
    mock_response_login.headers = MagicMock()
    mock_response_login.headers.getall.return_value = ["new_session"]

    # Set up the mock to return different side effects for each call
    mock_cm_expired = AsyncMock()
    mock_cm_expired.__aenter__.return_value = mock_response_expired
    
    mock_cm_login = AsyncMock()
    mock_cm_login.__aenter__.return_value = mock_response_login
    
    mock_cm_success = AsyncMock()
    mock_cm_success.__aenter__.return_value = mock_response_success

    with patch.object(api_client._session, 'post', side_effect=[mock_cm_expired, mock_cm_login, mock_cm_success]):
        devices = await api_client.get_devices()
        
        assert len(devices) == 1
        assert api_client._user_id == "new_user"
        assert api_client._session_id == "new_session"

@pytest.mark.asyncio
async def test_test_connection_success(api_client):
    """Test connection success."""
    with patch.object(api_client, 'login', new_callable=AsyncMock) as mock_login, \
         patch.object(api_client, 'get_devices', new_callable=AsyncMock) as mock_get_devices:
        
        mock_get_devices.return_value = [{"id": "1"}]
        result = await api_client.test_connection()
        assert result is True
        mock_login.assert_called_once()
        mock_get_devices.assert_called_once()
