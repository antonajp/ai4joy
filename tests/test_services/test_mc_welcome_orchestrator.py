"""
Unit Tests for MC Welcome Orchestrator Service - IQS-55 Implementation

Test Coverage:
- TC-MC-01: Initial welcome message generation
- TC-MC-02: Game selection flow
- TC-MC-03: Audience suggestion collection
- TC-MC-04: Rules explanation and scene start transition
- TC-MC-05: Session status transitions through MC welcome phases
- TC-MC-06: Error handling for MC agent failures
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from app.services.mc_welcome_orchestrator import MCWelcomeOrchestrator
from app.models.session import Session, SessionStatus


class TestMCWelcomeInitialWelcome:
    """TC-MC-01: Initial Welcome Message Generation"""

    @pytest.fixture
    def session_manager(self):
        """Mock session manager"""
        manager = Mock()
        manager.update_session_status = AsyncMock()
        manager.update_session_game = AsyncMock()
        manager.update_session_suggestion = AsyncMock()
        manager.complete_mc_welcome = AsyncMock()
        return manager

    @pytest.fixture
    def orchestrator(self, session_manager):
        """Create MCWelcomeOrchestrator instance"""
        return MCWelcomeOrchestrator(session_manager)

    @pytest.fixture
    def initialized_session(self):
        """Create initialized session for testing"""
        return Session(
            session_id="test-session-123",
            user_id="user-456",
            user_email="test@example.com",
            location="Mars Colony",
            status=SessionStatus.INITIALIZED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
            conversation_history=[],
            turn_count=0,
        )

    @pytest.mark.asyncio
    async def test_tc_mc_01a_initial_welcome_returns_mc_response(
        self, orchestrator, session_manager, initialized_session
    ):
        """
        TC-MC-01a: Initial Welcome Returns MC Response

        When session status is INITIALIZED, execute_welcome should return
        an MC response welcoming the user.
        """
        with patch.object(
            orchestrator, "_run_mc_agent", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = "Welcome to Improv Olympics! I'm your MC tonight!"

            with patch(
                "app.services.mc_welcome_orchestrator.get_all_games",
                new_callable=AsyncMock,
            ) as mock_games:
                mock_games.return_value = [
                    {"id": "freeze_tag", "name": "Freeze Tag", "difficulty": "beginner"}
                ]

                result = await orchestrator.execute_welcome(
                    session=initialized_session, user_input=None
                )

        assert "mc_response" in result
        assert "Welcome to Improv Olympics" in result["mc_response"]
        assert result["phase"] == "welcome"
        assert result["next_status"] == SessionStatus.MC_WELCOME.value

    @pytest.mark.asyncio
    async def test_tc_mc_01b_initial_welcome_includes_available_games(
        self, orchestrator, session_manager, initialized_session
    ):
        """
        TC-MC-01b: Initial Welcome Includes Available Games

        The response should include a list of available games for selection.
        """
        with patch.object(
            orchestrator, "_run_mc_agent", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = "Welcome! Let's pick a game!"

            with patch(
                "app.services.mc_welcome_orchestrator.get_all_games",
                new_callable=AsyncMock,
            ) as mock_games:
                mock_games.return_value = [
                    {
                        "id": "freeze_tag",
                        "name": "Freeze Tag",
                        "difficulty": "beginner",
                    },
                    {"id": "185", "name": "185", "difficulty": "intermediate"},
                ]

                result = await orchestrator.execute_welcome(
                    session=initialized_session, user_input=None
                )

        assert "available_games" in result
        assert len(result["available_games"]) == 2
        assert result["available_games"][0]["name"] == "Freeze Tag"

    @pytest.mark.asyncio
    async def test_tc_mc_01c_initial_welcome_updates_session_status(
        self, orchestrator, session_manager, initialized_session
    ):
        """
        TC-MC-01c: Initial Welcome Updates Session Status

        After initial welcome, session status should be updated to MC_WELCOME.
        """
        with patch.object(
            orchestrator, "_run_mc_agent", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = "Welcome!"

            with patch(
                "app.services.mc_welcome_orchestrator.get_all_games",
                new_callable=AsyncMock,
            ) as mock_games:
                mock_games.return_value = []

                await orchestrator.execute_welcome(
                    session=initialized_session, user_input=None
                )

        session_manager.update_session_status.assert_called_once_with(
            session_id="test-session-123", status=SessionStatus.MC_WELCOME
        )


class TestMCWelcomeGameSelection:
    """TC-MC-02: Game Selection Flow"""

    @pytest.fixture
    def session_manager(self):
        manager = Mock()
        manager.update_session_status = AsyncMock()
        manager.update_session_game = AsyncMock()
        manager.update_session_suggestion = AsyncMock()
        manager.complete_mc_welcome = AsyncMock()
        return manager

    @pytest.fixture
    def orchestrator(self, session_manager):
        return MCWelcomeOrchestrator(session_manager)

    @pytest.fixture
    def mc_welcome_session(self):
        return Session(
            session_id="test-session-123",
            user_id="user-456",
            user_email="test@example.com",
            location="Mars Colony",
            status=SessionStatus.MC_WELCOME,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
            conversation_history=[],
            turn_count=0,
        )

    @pytest.mark.asyncio
    async def test_tc_mc_02a_game_selection_with_user_mood(
        self, orchestrator, session_manager, mc_welcome_session
    ):
        """
        TC-MC-02a: Game Selection Based on User Mood

        When user describes their mood, MC should suggest appropriate game.
        """
        with patch.object(
            orchestrator, "_run_mc_agent", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = "You're feeling silly? Perfect! Let's play Freeze Tag - it's high energy and fun!"

            with patch(
                "app.services.mc_welcome_orchestrator.get_all_games",
                new_callable=AsyncMock,
            ) as mock_games:
                mock_games.return_value = [
                    {"id": "freeze_tag", "name": "Freeze Tag", "difficulty": "beginner"}
                ]

                result = await orchestrator.execute_welcome(
                    session=mc_welcome_session, user_input="I'm feeling silly tonight!"
                )

        assert "mc_response" in result
        assert "Freeze Tag" in result["mc_response"]
        assert result["phase"] == "game_selection"

    @pytest.mark.asyncio
    async def test_tc_mc_02b_game_selection_detects_game_from_response(
        self, orchestrator, session_manager, mc_welcome_session
    ):
        """
        TC-MC-02b: Game Selection Detects Game from MC Response

        Orchestrator should detect which game was suggested and store it.
        """
        with patch.object(
            orchestrator, "_run_mc_agent", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = "Let's play Freeze Tag tonight!"

            with patch(
                "app.services.mc_welcome_orchestrator.get_all_games",
                new_callable=AsyncMock,
            ) as mock_games:
                mock_games.return_value = [
                    {"id": "freeze_tag", "name": "Freeze Tag", "difficulty": "beginner"}
                ]

                result = await orchestrator.execute_welcome(
                    session=mc_welcome_session, user_input="Surprise me!"
                )

        assert result["selected_game"]["id"] == "freeze_tag"
        session_manager.update_session_game.assert_called_once_with(
            session_id="test-session-123",
            game_id="freeze_tag",
            game_name="Freeze Tag",
        )

    @pytest.mark.asyncio
    async def test_tc_mc_02c_game_selection_updates_status_to_game_select(
        self, orchestrator, session_manager, mc_welcome_session
    ):
        """
        TC-MC-02c: Game Selection Updates Status to GAME_SELECT

        After game suggestion, status should transition to GAME_SELECT.
        """
        with patch.object(
            orchestrator, "_run_mc_agent", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = "Let's play Freeze Tag!"

            with patch(
                "app.services.mc_welcome_orchestrator.get_all_games",
                new_callable=AsyncMock,
            ) as mock_games:
                mock_games.return_value = [
                    {"id": "freeze_tag", "name": "Freeze Tag", "difficulty": "beginner"}
                ]

                await orchestrator.execute_welcome(
                    session=mc_welcome_session, user_input="sounds good"
                )

        session_manager.update_session_status.assert_called_with(
            session_id="test-session-123", status=SessionStatus.GAME_SELECT
        )


class TestMCWelcomeAudienceSuggestion:
    """TC-MC-03: Audience Suggestion Collection"""

    @pytest.fixture
    def session_manager(self):
        manager = Mock()
        manager.update_session_status = AsyncMock()
        manager.update_session_game = AsyncMock()
        manager.update_session_suggestion = AsyncMock()
        manager.complete_mc_welcome = AsyncMock()
        return manager

    @pytest.fixture
    def orchestrator(self, session_manager):
        return MCWelcomeOrchestrator(session_manager)

    @pytest.fixture
    def game_select_session(self):
        return Session(
            session_id="test-session-123",
            user_id="user-456",
            user_email="test@example.com",
            location="Mars Colony",
            status=SessionStatus.GAME_SELECT,
            selected_game_id="freeze_tag",
            selected_game_name="Freeze Tag",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
            conversation_history=[],
            turn_count=0,
        )

    @pytest.mark.asyncio
    async def test_tc_mc_03a_suggestion_collection_with_valid_input(
        self, orchestrator, session_manager, game_select_session
    ):
        """
        TC-MC-03a: Suggestion Collection with Valid User Input

        When user provides suggestion, it should be saved and acknowledged.
        """
        with patch.object(
            orchestrator, "_run_mc_agent", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = "A coffee shop! I love it!"

            result = await orchestrator.execute_welcome(
                session=game_select_session, user_input="A coffee shop"
            )

        assert result["audience_suggestion"] == "A coffee shop"
        assert result["phase"] == "suggestion_received"
        session_manager.update_session_suggestion.assert_called_once_with(
            session_id="test-session-123", audience_suggestion="A coffee shop"
        )

    @pytest.mark.asyncio
    async def test_tc_mc_03b_suggestion_request_when_no_input(
        self, orchestrator, session_manager, game_select_session
    ):
        """
        TC-MC-03b: Prompt for Suggestion When None Provided

        If user doesn't provide suggestion, MC should ask again.
        """
        with patch.object(
            orchestrator, "_run_mc_agent", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = "Come on, give me a location! Don't be shy!"

            result = await orchestrator.execute_welcome(
                session=game_select_session, user_input=None
            )

        assert result["phase"] == "awaiting_suggestion"
        assert result["next_status"] == SessionStatus.GAME_SELECT.value
        session_manager.update_session_suggestion.assert_not_called()

    @pytest.mark.asyncio
    async def test_tc_mc_03c_suggestion_transitions_to_suggestion_phase(
        self, orchestrator, session_manager, game_select_session
    ):
        """
        TC-MC-03c: Suggestion Transitions Status to SUGGESTION_PHASE

        After collecting suggestion, status should update.
        """
        with patch.object(
            orchestrator, "_run_mc_agent", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = "A hospital, perfect!"

            await orchestrator.execute_welcome(
                session=game_select_session, user_input="A hospital"
            )

        session_manager.update_session_status.assert_called_with(
            session_id="test-session-123", status=SessionStatus.SUGGESTION_PHASE
        )


class TestMCWelcomeSceneStart:
    """TC-MC-04: Rules Explanation and Scene Start Transition"""

    @pytest.fixture
    def session_manager(self):
        manager = Mock()
        manager.update_session_status = AsyncMock()
        manager.update_session_game = AsyncMock()
        manager.update_session_suggestion = AsyncMock()
        manager.complete_mc_welcome = AsyncMock()
        return manager

    @pytest.fixture
    def orchestrator(self, session_manager):
        return MCWelcomeOrchestrator(session_manager)

    @pytest.fixture
    def suggestion_phase_session(self):
        return Session(
            session_id="test-session-123",
            user_id="user-456",
            user_email="test@example.com",
            location="Mars Colony",
            status=SessionStatus.SUGGESTION_PHASE,
            selected_game_id="freeze_tag",
            selected_game_name="Freeze Tag",
            audience_suggestion="A coffee shop",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
            conversation_history=[],
            turn_count=0,
        )

    @pytest.mark.asyncio
    async def test_tc_mc_04a_rules_and_start_completes_mc_welcome(
        self, orchestrator, session_manager, suggestion_phase_session
    ):
        """
        TC-MC-04a: Rules and Start Marks MC Welcome Complete

        Final MC phase should set mc_welcome_complete to True.
        """
        with patch.object(
            orchestrator, "_run_mc_agent", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = (
                "Remember - Yes, And! Meet your partner. Take it away!"
            )

            result = await orchestrator.execute_welcome(
                session=suggestion_phase_session, user_input=None
            )

        assert result["mc_welcome_complete"] is True
        assert result["phase"] == "scene_start"
        session_manager.complete_mc_welcome.assert_called_once_with(
            session_id="test-session-123"
        )

    @pytest.mark.asyncio
    async def test_tc_mc_04b_rules_and_start_includes_game_and_suggestion(
        self, orchestrator, session_manager, suggestion_phase_session
    ):
        """
        TC-MC-04b: Rules Response Includes Game and Suggestion

        The final MC response should reference the selected game and suggestion.
        """
        with patch.object(
            orchestrator, "_run_mc_agent", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = "Playing Freeze Tag at a coffee shop! Yes, And! Go!"

            result = await orchestrator.execute_welcome(
                session=suggestion_phase_session, user_input=None
            )

        assert result["game_name"] == "Freeze Tag"
        assert result["audience_suggestion"] == "A coffee shop"

    @pytest.mark.asyncio
    async def test_tc_mc_04c_rules_and_start_transitions_to_active(
        self, orchestrator, session_manager, suggestion_phase_session
    ):
        """
        TC-MC-04c: Rules and Start Transitions to ACTIVE Status

        After MC welcome completes, status should be ACTIVE for scene work.
        """
        with patch.object(
            orchestrator, "_run_mc_agent", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = "Let's go!"

            result = await orchestrator.execute_welcome(
                session=suggestion_phase_session, user_input=None
            )

        assert result["next_status"] == SessionStatus.ACTIVE.value


class TestMCWelcomeStatusTransitions:
    """TC-MC-05: Session Status Transitions Through MC Welcome Phases"""

    @pytest.fixture
    def session_manager(self):
        manager = Mock()
        manager.update_session_status = AsyncMock()
        manager.update_session_game = AsyncMock()
        manager.update_session_suggestion = AsyncMock()
        manager.complete_mc_welcome = AsyncMock()
        return manager

    @pytest.fixture
    def orchestrator(self, session_manager):
        return MCWelcomeOrchestrator(session_manager)

    @pytest.mark.asyncio
    async def test_tc_mc_05a_invalid_status_raises_error(
        self, orchestrator, session_manager
    ):
        """
        TC-MC-05a: Invalid Status Raises ValueError

        If session is in ACTIVE or CLOSED status, execute_welcome should raise.
        """
        active_session = Session(
            session_id="test-session-123",
            user_id="user-456",
            user_email="test@example.com",
            location="Mars",
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
            conversation_history=[],
            turn_count=0,
        )

        with pytest.raises(ValueError, match="Invalid status for MC welcome phase"):
            await orchestrator.execute_welcome(session=active_session, user_input=None)


class TestMCWelcomeErrorHandling:
    """TC-MC-06: Error Handling for MC Agent Failures"""

    @pytest.fixture
    def session_manager(self):
        manager = Mock()
        manager.update_session_status = AsyncMock()
        manager.update_session_game = AsyncMock()
        manager.update_session_suggestion = AsyncMock()
        manager.complete_mc_welcome = AsyncMock()
        return manager

    @pytest.fixture
    def orchestrator(self, session_manager):
        return MCWelcomeOrchestrator(session_manager)

    @pytest.fixture
    def initialized_session(self):
        return Session(
            session_id="test-session-123",
            user_id="user-456",
            user_email="test@example.com",
            location="Mars",
            status=SessionStatus.INITIALIZED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
            conversation_history=[],
            turn_count=0,
        )

    @pytest.mark.asyncio
    async def test_tc_mc_06a_mc_agent_timeout_propagates(
        self, orchestrator, session_manager, initialized_session
    ):
        """
        TC-MC-06a: MC Agent Timeout Propagates Error

        If MC agent times out, the error should propagate to caller.
        """
        import asyncio

        with patch.object(
            orchestrator, "_run_mc_agent", new_callable=AsyncMock
        ) as mock_run:
            mock_run.side_effect = asyncio.TimeoutError("Agent timed out")

            with patch(
                "app.services.mc_welcome_orchestrator.get_all_games",
                new_callable=AsyncMock,
            ) as mock_games:
                mock_games.return_value = []

                with pytest.raises(asyncio.TimeoutError):
                    await orchestrator.execute_welcome(
                        session=initialized_session, user_input=None
                    )
