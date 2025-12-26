from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from .models import ConversationState


class StateStore(ABC):
    @abstractmethod
    async def load(self, session_id: str) -> ConversationState:
        """Loads state for a session. Returns empty state if new."""
        pass

    @abstractmethod
    async def save(self, session_id: str, state: ConversationState):
        """Saves session state."""
        pass


class ILLMProvider(ABC):
    @abstractmethod
    async def chat(
        self, messages: List[Dict[str, str]], temperature: float = 0.7
    ) -> str:
        pass

    @abstractmethod
    async def json_chat(
        self, messages: List[Dict[str, str]], schema: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        pass
