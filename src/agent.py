from typing import Dict, Any, Optional
import json
from .models import ConversationState, TripSpec, UserProfile
from .interfaces import ILLMProvider, StateStore
from .tools import Tools
from .logger import get_logger
from .prompts import ROUTER_SYSTEM_PROMPT, RESPONSE_SYSTEM_PROMPT
from .config import settings

__all__ = ["TravelAgent"]

logger = get_logger(__name__)


class TravelAgent:
    def __init__(self, provider: ILLMProvider, store: StateStore):
        self.provider = provider
        self.store = store

    async def run_turn(self, session_id: str, user_input: str) -> str:
        logger.info("run_turn_start", session_id=session_id)

        state = await self.store.load(session_id)
        state.history.append({"role": "user", "content": user_input})

        # Router step
        router_messages = [
            {
                "role": "system",
                "content": ROUTER_SYSTEM_PROMPT.format(
                    user_profile=state.user_profile.model_dump_json(),
                    trip_spec=state.trip_spec.model_dump_json(),
                ),
            },
            {"role": "user", "content": f"User's latest message: {user_input}"},
        ]

        router_schema = {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": ["plan_trip", "packing", "attractions", "chat"],
                },
                "extracted_updates": {
                    "type": "object",
                    "properties": {
                        "trip_spec": {"type": "object"},
                        "user_profile": {"type": "object"},
                    },
                },
                "tool_call": {"type": "string", "enum": ["weather", "none"]},
                "reasoning": {"type": "string"},
            },
            "required": ["intent", "tool_call", "reasoning"],
        }

        # Call LLM for decision
        decision = await self.provider.json_chat(router_messages, schema=router_schema)
        logger.info("router_decision", session_id=session_id, decision=decision)

        # Apply state updates
        updates = decision.get("extracted_updates", {})
        if updates:
            self._apply_updates(state, updates)

        # Tool execution
        tool_output = ""
        tool_call = decision.get("tool_call")
        dest = state.trip_spec.destination

        if tool_call == "weather":
            if dest:
                logger.info("executing_tool", tool="weather", destination=dest)
                geo = await Tools.get_lat_lon(dest)
                if geo:
                    tool_output = await Tools.get_weather(geo["lat"], geo["lon"])
                else:
                    tool_output = f"System: Could not find coordinates for {dest}. Cannot fetch weather."
                    logger.warning(
                        "tool_execution_failed", tool="weather", error="geocode_failed"
                    )
            else:
                tool_output = "System: Destination unknown, cannot fetch weather."
                logger.warning(
                    "tool_execution_skipped", tool="weather", reason="no_destination"
                )

        # Response generation
        response_messages = [
            {
                "role": "system",
                "content": RESPONSE_SYSTEM_PROMPT.format(
                    user_profile=state.user_profile.model_dump_json(),
                    trip_spec=state.trip_spec.model_dump_json(),
                    tool_output=tool_output,
                ),
            }
        ]
        # Append recent conversation history (configurable turns)
        response_messages.extend(state.history[-settings.CONTEXT_WINDOW_TURNS :])

        final_answer = await self.provider.chat(response_messages)

        # Strip quotes if model wrapped response in them
        if final_answer.startswith('"') and final_answer.endswith('"'):
            final_answer = final_answer[1:-1]

        state.history.append({"role": "assistant", "content": final_answer})
        await self.store.save(session_id, state)

        return final_answer

    def _apply_updates(self, state: ConversationState, updates: Dict[str, Any]):
        if "trip_spec" in updates and isinstance(updates["trip_spec"], dict):
            try:
                valid_updates = {
                    k: v
                    for k, v in updates["trip_spec"].items()
                    if v not in (None, [], "")
                }
                current_data = state.trip_spec.model_dump()
                current_data.update(valid_updates)
                state.trip_spec = TripSpec(**current_data)
            except Exception as e:
                logger.error("state_update_failed", target="trip_spec", error=str(e))

        if "user_profile" in updates and isinstance(updates["user_profile"], dict):
            try:
                valid_updates = {
                    k: v
                    for k, v in updates["user_profile"].items()
                    if v not in (None, [], "")
                }
                current_data = state.user_profile.model_dump()
                current_data.update(valid_updates)
                state.user_profile = UserProfile(**current_data)
            except Exception as e:
                logger.error("state_update_failed", target="user_profile", error=str(e))
