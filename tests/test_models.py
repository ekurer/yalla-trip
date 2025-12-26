import pytest
from src.models import TripSpec, UserProfile, ConversationState


class TestModels:

    def test_trip_spec_defaults(self):
        spec = TripSpec()
        assert spec.destination is None
        assert spec.origin is None

    def test_trip_spec_with_values(self):
        spec = TripSpec(destination="Paris", travelers="couple")
        assert spec.destination == "Paris"
        assert spec.travelers == "couple"

    def test_user_profile_defaults(self):
        profile = UserProfile()
        assert profile.budget is None
        assert profile.interests == []

    def test_conversation_state_initialization(self):
        state = ConversationState()
        assert state.user_profile is not None
        assert state.trip_spec is not None
        assert state.history == []
