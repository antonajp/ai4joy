"""
Integration tests for turn-taking coordination.
Tests natural conversation flow and turn transitions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio


@pytest.mark.asyncio
async def test_mc_to_partner_transition():
    """MC to Partner turn transition should work smoothly."""
    from app.audio.orchestrator import AudioOrchestrator

    orchestrator = AudioOrchestrator()

    # MC speaks first
    assert orchestrator.get_current_agent_type() == "mc"
    await orchestrator.process_user_input("Hello MC", session_id="test-session")

    # Trigger partner turn
    orchestrator.switch_to_partner()

    # Partner speaks
    assert orchestrator.get_current_agent_type() == "partner"
    await orchestrator.process_user_input("Hello Partner", session_id="test-session")


@pytest.mark.asyncio
async def test_partner_to_mc_transition():
    """Partner to MC turn transition should work if needed."""
    from app.audio.orchestrator import AudioOrchestrator

    orchestrator = AudioOrchestrator()

    # Switch to partner
    orchestrator.switch_to_partner()
    await orchestrator.process_user_input("Partner speaking", session_id="test-session")

    # Switch back to MC
    orchestrator.switch_to_mc()

    assert orchestrator.get_current_agent_type() == "mc"
    await orchestrator.process_user_input("MC speaking again", session_id="test-session")


@pytest.mark.asyncio
async def test_concurrent_user_agent_speech_prevented():
    """User and agent should not speak simultaneously."""
    from app.audio.orchestrator import AudioOrchestrator

    orchestrator = AudioOrchestrator()

    # Mock agent response that takes time
    async def slow_response(input_text):
        await asyncio.sleep(0.1)
        return "Agent response"

    with patch.object(orchestrator.mc_agent, "run", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = slow_response

        # Start agent response
        task1 = asyncio.create_task(
            orchestrator.process_user_input("First input", session_id="test-session")
        )

        # Try to interrupt with user input
        await asyncio.sleep(0.01)  # Small delay
        task2 = asyncio.create_task(
            orchestrator.process_user_input("Interrupt!", session_id="test-session")
        )

        # Both should complete, but one should wait for the other
        await task1
        await task2

        # Should have called agent twice (not overlapping)
        assert mock_run.call_count == 2


@pytest.mark.asyncio
async def test_turn_taking_accuracy():
    """Correct agent should respond in turn sequence."""
    from app.audio.orchestrator import AudioOrchestrator

    orchestrator = AudioOrchestrator()

    turn_sequence = []

    # Track which agent responds
    async def track_mc_response(input_text):
        turn_sequence.append("mc")
        return "MC response"

    async def track_partner_response(input_text):
        turn_sequence.append("partner")
        return "Partner response"

    with patch.object(orchestrator.mc_agent, "run", new_callable=AsyncMock) as mock_mc:
        with patch.object(orchestrator.partner_agent, "run", new_callable=AsyncMock) as mock_partner:
            mock_mc.side_effect = track_mc_response
            mock_partner.side_effect = track_partner_response

            # MC, Partner, MC sequence
            await orchestrator.process_user_input("Turn 1", session_id="test-session")
            orchestrator.switch_to_partner()
            await orchestrator.process_user_input("Turn 2", session_id="test-session")
            orchestrator.switch_to_mc()
            await orchestrator.process_user_input("Turn 3", session_id="test-session")

            # Verify correct sequence
            assert turn_sequence == ["mc", "partner", "mc"]


@pytest.mark.asyncio
async def test_natural_turn_timing():
    """Turn transitions should feel natural without awkward pauses."""
    from app.audio.orchestrator import AudioOrchestrator
    import time

    orchestrator = AudioOrchestrator()

    with patch.object(orchestrator.mc_agent, "run", new_callable=AsyncMock) as mock_mc:
        with patch.object(orchestrator.partner_agent, "run", new_callable=AsyncMock) as mock_partner:
            mock_mc.return_value = "MC says hello"
            mock_partner.return_value = "Partner responds"

            # Measure transition time
            await orchestrator.process_user_input("Hello", session_id="test-session")

            start = time.time()
            orchestrator.switch_to_partner()
            await orchestrator.process_user_input("Response", session_id="test-session")
            transition_time = time.time() - start

            # Transition should be quick (< 500ms for test)
            assert transition_time < 0.5


@pytest.mark.asyncio
async def test_turn_end_detection():
    """System should detect when agent finishes speaking."""
    from app.audio.orchestrator import AudioOrchestrator

    orchestrator = AudioOrchestrator()

    with patch.object(orchestrator.mc_agent, "run", new_callable=AsyncMock) as mock_mc:
        mock_mc.return_value = "Complete response."

        await orchestrator.process_user_input("Test", session_id="test-session")

        # Turn should be marked complete
        assert hasattr(orchestrator, "is_turn_complete")
        assert orchestrator.is_turn_complete() == True


@pytest.mark.asyncio
async def test_interrupt_handling():
    """System should handle user interruptions gracefully."""
    from app.audio.orchestrator import AudioOrchestrator

    orchestrator = AudioOrchestrator()

    # Start agent response
    async def long_response(input_text):
        await asyncio.sleep(1.0)
        return "Long response that gets interrupted"

    with patch.object(orchestrator.mc_agent, "run", new_callable=AsyncMock) as mock_mc:
        mock_mc.side_effect = long_response

        # Start response
        task = asyncio.create_task(
            orchestrator.process_user_input("Start", session_id="test-session")
        )

        # Interrupt after short delay
        await asyncio.sleep(0.1)
        orchestrator.interrupt_current_turn()

        # Should handle gracefully
        try:
            await asyncio.wait_for(task, timeout=2.0)
        except asyncio.TimeoutError:
            pytest.fail("Interrupt handling timed out")


@pytest.mark.asyncio
async def test_turn_history_persistence():
    """Turn history should be persisted to session state."""
    from app.audio.orchestrator import AudioOrchestrator

    with patch("app.audio.orchestrator.firestore_client") as mock_firestore:
        orchestrator = AudioOrchestrator()

        # Multiple turns
        await orchestrator.process_user_input("Turn 1", session_id="test-session")
        orchestrator.on_turn_complete()

        orchestrator.switch_to_partner()
        await orchestrator.process_user_input("Turn 2", session_id="test-session")
        orchestrator.on_turn_complete()

        # Firestore should have been updated with turn history
        assert mock_firestore.update_session.called
        update_calls = mock_firestore.update_session.call_args_list
        assert len(update_calls) >= 2


@pytest.mark.asyncio
async def test_simultaneous_turn_requests():
    """System should serialize simultaneous turn requests."""
    from app.audio.orchestrator import AudioOrchestrator

    orchestrator = AudioOrchestrator()

    with patch.object(orchestrator.mc_agent, "run", new_callable=AsyncMock) as mock_mc:
        mock_mc.return_value = "Response"

        # Fire multiple requests simultaneously
        tasks = [
            asyncio.create_task(orchestrator.process_user_input(f"Input {i}", session_id="test-session"))
            for i in range(5)
        ]

        # All should complete without errors
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # No exceptions
        for result in results:
            assert not isinstance(result, Exception)


@pytest.mark.asyncio
async def test_turn_taking_with_phase_transition():
    """Turn-taking should continue smoothly through phase transitions."""
    from app.audio.orchestrator import AudioOrchestrator

    orchestrator = AudioOrchestrator()

    with patch.object(orchestrator.mc_agent, "run", new_callable=AsyncMock) as mock_mc:
        with patch.object(orchestrator.partner_agent, "run", new_callable=AsyncMock) as mock_partner:
            mock_mc.return_value = "MC response"
            mock_partner.return_value = "Partner response"

            # Turns leading up to phase transition
            for i in range(6):
                if i % 2 == 0:
                    await orchestrator.process_user_input(f"MC turn {i}", session_id="test-session")
                    orchestrator.on_turn_complete()
                else:
                    orchestrator.switch_to_partner()
                    await orchestrator.process_user_input(f"Partner turn {i}", session_id="test-session")
                    orchestrator.on_turn_complete()
                    orchestrator.switch_to_mc()

            # Should have transitioned to phase 2
            assert orchestrator.get_current_phase() == 2

            # Turn-taking still works
            await orchestrator.process_user_input("Post-transition", session_id="test-session")
            assert mock_mc.called or mock_partner.called


@pytest.mark.asyncio
async def test_voice_continuity_across_turns():
    """Voice configuration should remain consistent within agent turns."""
    from app.audio.orchestrator import AudioOrchestrator

    orchestrator = AudioOrchestrator()

    # MC voice at start
    voice1 = orchestrator.get_current_voice_config()
    await orchestrator.process_user_input("Test 1", session_id="test-session")
    voice2 = orchestrator.get_current_voice_config()

    # Should be same voice (Aoede for MC)
    assert voice1.voice == voice2.voice
    assert voice1.voice == "aoede"

    # Switch to partner
    orchestrator.switch_to_partner()
    voice3 = orchestrator.get_current_voice_config()
    await orchestrator.process_user_input("Test 2", session_id="test-session")
    voice4 = orchestrator.get_current_voice_config()

    # Partner voice consistent (Puck)
    assert voice3.voice == voice4.voice
    assert voice3.voice == "puck"
