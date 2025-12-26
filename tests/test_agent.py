import pytest
import respx
from unittest.mock import AsyncMock, MagicMock
from httpx import Response

from src.agent import TravelAgent
from src.provider import LLMProvider
from src.state import SQLiteStateStore
from src.models import ConversationState


@pytest.fixture
def mock_store():
    store = MagicMock(spec=SQLiteStateStore)
    store.load = AsyncMock(return_value=ConversationState())
    store.save = AsyncMock()
    return store


@pytest.fixture
def mock_provider():
    provider = MagicMock(spec=LLMProvider)
    provider.chat = AsyncMock(return_value="Mocked response")
    provider.json_chat = AsyncMock(
        return_value={"intent": "chat", "tool_call": "none", "reasoning": "test"}
    )
    return provider


@pytest.mark.asyncio
async def test_agent_initialization(mock_provider, mock_store):
    agent = TravelAgent(mock_provider, mock_store)
    assert agent.provider == mock_provider
    assert agent.store == mock_store


@pytest.mark.asyncio
async def test_agent_run_turn_basic_chat(mock_provider, mock_store):
    agent = TravelAgent(mock_provider, mock_store)

    response = await agent.run_turn("session_1", "Hello")

    assert response == "Mocked response"
    mock_store.load.assert_called_once_with("session_1")
    mock_store.save.assert_called_once()
    mock_provider.json_chat.assert_called_once()
    mock_provider.chat.assert_called_once()


@pytest.mark.asyncio
async def test_agent_tool_execution(mock_provider, mock_store):
    agent = TravelAgent(mock_provider, mock_store)

    mock_provider.json_chat.return_value = {
        "intent": "plan_trip",
        "tool_call": "weather",
        "reasoning": "Need weather",
        "extracted_updates": {"trip_spec": {"destination": "London"}},
    }

    async with respx.mock(base_url="https://geocoding-api.open-meteo.com") as router:
        router.get("/v1/search").mock(
            return_value=Response(
                200,
                json={
                    "results": [{"latitude": 51.5, "longitude": -0.1, "name": "London"}]
                },
            )
        )

        async with respx.mock(base_url="https://api.open-meteo.com") as weather_router:
            weather_router.get("/v1/forecast").mock(
                return_value=Response(
                    200,
                    json={
                        "daily": {
                            "time": ["2023-01-01"],
                            "temperature_2m_max": [10],
                            "temperature_2m_min": [5],
                            "precipitation_sum": [0],
                            "weather_code": [1],
                        }
                    },
                )
            )

            await agent.run_turn("session_1", "What's the weather in London?")

            # Verify weather data was injected into response context
            call_args = mock_provider.chat.call_args[0][0]
            system_msg = call_args[0]["content"]
            assert "10°C" in system_msg
