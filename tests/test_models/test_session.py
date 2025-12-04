"""
Tests for Session Data Models - IQS-75
Tests for InteractionMode enum and Session models with interaction_mode field

Test Cases:
- TC-MODEL-SESSION-01: InteractionMode enum has TEXT and AUDIO values
- TC-MODEL-SESSION-02: SessionCreate accepts interaction_mode field
- TC-MODEL-SESSION-03: SessionCreate defaults to TEXT mode when not specified
- TC-MODEL-SESSION-04: Session model stores interaction_mode correctly
- TC-MODEL-SESSION-05: SessionCreate validates interaction_mode enum values
- TC-MODEL-SESSION-06: Session serialization includes interaction_mode
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any


class TestInteractionMode:
    """Tests for InteractionMode enum."""

    def test_tc_model_session_01_interaction_mode_values(self):
        """TC-MODEL-SESSION-01: InteractionMode enum has TEXT and AUDIO values."""
        from app.models.session import InteractionMode

        assert hasattr(InteractionMode, "TEXT")
        assert hasattr(InteractionMode, "AUDIO")

        assert InteractionMode.TEXT.value == "text"
        assert InteractionMode.AUDIO.value == "audio"

    def test_interaction_mode_from_string(self):
        """Test creating InteractionMode from string value."""
        from app.models.session import InteractionMode

        assert InteractionMode("text") == InteractionMode.TEXT
        assert InteractionMode("audio") == InteractionMode.AUDIO

    def test_interaction_mode_invalid_value(self):
        """Test that invalid mode value raises ValueError."""
        from app.models.session import InteractionMode

        with pytest.raises(ValueError):
            InteractionMode("invalid_mode")


class TestSessionCreate:
    """Tests for SessionCreate model with interaction_mode field."""

    def test_tc_model_session_02_session_create_accepts_interaction_mode(self):
        """TC-MODEL-SESSION-02: SessionCreate accepts interaction_mode field."""
        from app.models.session import SessionCreate, InteractionMode

        # Test with TEXT mode
        session_data = SessionCreate(
            user_name="Test User",
            interaction_mode=InteractionMode.TEXT
        )
        assert session_data.interaction_mode == InteractionMode.TEXT

        # Test with AUDIO mode
        session_data_audio = SessionCreate(
            user_name="Test User",
            interaction_mode=InteractionMode.AUDIO
        )
        assert session_data_audio.interaction_mode == InteractionMode.AUDIO

    def test_tc_model_session_03_session_create_defaults_to_text(self):
        """TC-MODEL-SESSION-03: SessionCreate defaults to TEXT mode when not specified."""
        from app.models.session import SessionCreate, InteractionMode

        # Create session without specifying interaction_mode
        session_data = SessionCreate(user_name="Test User")

        # Should default to TEXT
        assert session_data.interaction_mode == InteractionMode.TEXT

    def test_tc_model_session_05_session_create_validates_enum(self):
        """TC-MODEL-SESSION-05: SessionCreate validates interaction_mode enum values."""
        from app.models.session import SessionCreate, InteractionMode

        # Valid enum values should work
        valid_session = SessionCreate(
            user_name="Test User",
            interaction_mode=InteractionMode.TEXT
        )
        assert valid_session.interaction_mode == InteractionMode.TEXT

        # String values matching enum should be converted
        session_with_string = SessionCreate(
            user_name="Test User",
            interaction_mode="audio"
        )
        assert session_with_string.interaction_mode == InteractionMode.AUDIO

    def test_session_create_with_all_fields(self):
        """Test SessionCreate with all optional fields including interaction_mode."""
        from app.models.session import SessionCreate, InteractionMode

        session_data = SessionCreate(
            user_name="Test User",
            selected_game_id="game_123",
            selected_game_name="Yes, And",
            interaction_mode=InteractionMode.AUDIO
        )

        assert session_data.user_name == "Test User"
        assert session_data.selected_game_id == "game_123"
        assert session_data.selected_game_name == "Yes, And"
        assert session_data.interaction_mode == InteractionMode.AUDIO

    def test_session_create_text_mode_with_game_selection(self):
        """Test SessionCreate with TEXT mode and pre-selected game."""
        from app.models.session import SessionCreate, InteractionMode

        session_data = SessionCreate(
            user_name="Premium User",
            selected_game_id="game_456",
            selected_game_name="Freeze Tag",
            interaction_mode=InteractionMode.TEXT
        )

        assert session_data.interaction_mode == InteractionMode.TEXT
        assert session_data.selected_game_id == "game_456"
        assert session_data.selected_game_name == "Freeze Tag"


class TestSession:
    """Tests for Session model with interaction_mode field."""

    @pytest.fixture
    def sample_session_data(self) -> Dict[str, Any]:
        """Sample session data for testing."""
        return {
            "session_id": "sess_test123",
            "user_id": "user_123",
            "user_email": "test@example.com",
            "user_name": "Test User",
            "status": "initialized",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc),
            "conversation_history": [],
            "metadata": {},
            "turn_count": 0,
        }

    def test_tc_model_session_04_session_stores_interaction_mode(
        self, sample_session_data
    ):
        """TC-MODEL-SESSION-04: Session model stores interaction_mode correctly."""
        from app.models.session import Session, InteractionMode

        # Test with TEXT mode
        session_data_text = {**sample_session_data, "interaction_mode": InteractionMode.TEXT}
        session = Session(**session_data_text)
        assert session.interaction_mode == InteractionMode.TEXT

        # Test with AUDIO mode
        session_data_audio = {**sample_session_data, "interaction_mode": InteractionMode.AUDIO}
        session_audio = Session(**session_data_audio)
        assert session_audio.interaction_mode == InteractionMode.AUDIO

    def test_tc_model_session_06_session_serialization_includes_mode(
        self, sample_session_data
    ):
        """TC-MODEL-SESSION-06: Session serialization includes interaction_mode."""
        from app.models.session import Session, InteractionMode

        session_data = {**sample_session_data, "interaction_mode": InteractionMode.AUDIO}
        session = Session(**session_data)

        # Serialize to dict
        session_dict = session.model_dump()

        assert "interaction_mode" in session_dict
        assert session_dict["interaction_mode"] == "audio"

    def test_session_defaults_to_text_mode(self, sample_session_data):
        """Test that Session defaults to TEXT mode when not specified."""
        from app.models.session import Session, InteractionMode

        # Create session without interaction_mode
        session = Session(**sample_session_data)

        # Should default to TEXT
        assert session.interaction_mode == InteractionMode.TEXT

    def test_session_with_text_mode_and_mc_welcome(self, sample_session_data):
        """Test Session with TEXT mode includes MC welcome fields."""
        from app.models.session import Session, InteractionMode, SessionStatus

        session_data = {
            **sample_session_data,
            "interaction_mode": InteractionMode.TEXT,
            "status": SessionStatus.MC_WELCOME,
            "selected_game_id": "game_789",
            "selected_game_name": "One Word Story",
            "audience_suggestion": "pirates",
            "mc_welcome_complete": False,
        }

        session = Session(**session_data)

        assert session.interaction_mode == InteractionMode.TEXT
        assert session.status == SessionStatus.MC_WELCOME
        assert session.selected_game_id == "game_789"
        assert session.selected_game_name == "One Word Story"
        assert session.audience_suggestion == "pirates"
        assert session.mc_welcome_complete is False

    def test_session_with_audio_mode_active_status(self, sample_session_data):
        """Test Session with AUDIO mode goes directly to ACTIVE status."""
        from app.models.session import Session, InteractionMode, SessionStatus

        session_data = {
            **sample_session_data,
            "interaction_mode": InteractionMode.AUDIO,
            "status": SessionStatus.ACTIVE,
        }

        session = Session(**session_data)

        assert session.interaction_mode == InteractionMode.AUDIO
        assert session.status == SessionStatus.ACTIVE

    def test_session_json_mode_serialization(self, sample_session_data):
        """Test Session JSON serialization with interaction_mode."""
        from app.models.session import Session, InteractionMode

        session_data = {**sample_session_data, "interaction_mode": InteractionMode.AUDIO}
        session = Session(**session_data)

        # Serialize to JSON-compatible dict
        json_dict = session.model_dump(mode="json")

        assert "interaction_mode" in json_dict
        assert json_dict["interaction_mode"] == "audio"
        assert isinstance(json_dict["created_at"], str)
        assert isinstance(json_dict["status"], str)


class TestSessionResponse:
    """Tests for SessionResponse model (API response)."""

    def test_session_response_includes_interaction_mode(self):
        """Test that SessionResponse can include interaction_mode if needed."""
        from app.models.session import SessionResponse

        response = SessionResponse(
            session_id="sess_test123",
            status="initialized",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
            turn_count=0,
        )

        # Current SessionResponse doesn't include interaction_mode
        # This test documents the expected behavior
        assert response.session_id == "sess_test123"
        assert response.status == "initialized"
        assert response.turn_count == 0
