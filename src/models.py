from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field

__all__ = ["UserProfile", "TripSpec", "ConversationState"]


class UserProfile(BaseModel):
    budget: Optional[Literal["low", "medium", "high"]] = Field(
        None, description="User's budget preference"
    )
    pace: Optional[Literal["relaxed", "moderate", "fast_paced"]] = Field(
        None, description="Preferred travel pace"
    )
    interests: List[str] = Field(
        default_factory=list,
        description="List of user interests (e.g., 'history', 'food')",
    )


class TripSpec(BaseModel):
    destination: Optional[str] = Field(
        None, description="Target destination city/country"
    )
    origin: Optional[str] = Field(None, description="Where the user is traveling from")
    start_date: Optional[str] = Field(
        None, description="ISO date or vague time (e.g., 'next week')"
    )
    end_date: Optional[str] = Field(None, description="ISO date or vague time")
    duration_days: Optional[int] = Field(
        None, description="Number of days for the trip"
    )
    travelers: Optional[str] = Field(
        None, description="Who is traveling (e.g., 'solo', 'couple', 'family')"
    )


class ConversationState(BaseModel):
    user_profile: UserProfile = Field(default_factory=UserProfile)
    trip_spec: TripSpec = Field(default_factory=TripSpec)
    # simple history storage, convenient for context window management
    history: List[Dict[str, str]] = Field(
        default_factory=list, description="Raw conversation history (OpenAI format)"
    )
