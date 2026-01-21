import sys
from unittest.mock import MagicMock

# Mock Home Assistant modules before importing anything that depends on them
mock_hass = MagicMock()
sys.modules["homeassistant"] = mock_hass
sys.modules["homeassistant.config_entries"] = mock_hass
sys.modules["homeassistant.const"] = mock_hass
sys.modules["homeassistant.core"] = mock_hass
sys.modules["homeassistant.helpers"] = mock_hass
sys.modules["homeassistant.helpers.aiohttp_client"] = mock_hass
sys.modules["homeassistant.helpers.update_coordinator"] = mock_hass

import pytest_asyncio
import pytest
import aiohttp
from custom_components.aircontrolbase.api import AirControlBaseAPI

@pytest_asyncio.fixture
async def session():
    """Create an aiohttp session for testing."""
    async with aiohttp.ClientSession() as session:
        yield session

@pytest.fixture
def api_client(session):
    """Create a mock AirControlBaseAPI client."""
    return AirControlBaseAPI(
        email="test@example.com",
        password="password123",
        session=session,
    )
