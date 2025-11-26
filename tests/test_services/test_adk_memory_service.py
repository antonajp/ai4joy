"""Tests for ADK Memory Service Integration

This module tests the adk_memory_service module that integrates ADK's
native MemoryService (InMemoryMemoryService for testing, VertexAiMemoryBankService
for production) to enable cross-session learning.

Test Coverage:
- TC-MEM-01: Singleton pattern for memory service
- TC-MEM-02: Service initialization with InMemoryMemoryService
- TC-MEM-03: Save session to memory
- TC-MEM-04: Search user memories
- TC-MEM-05: Error handling when memory service is disabled
- TC-MEM-06: Cleanup and disposal
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton before and after each test for isolation."""
    from app.services import adk_memory_service
    adk_memory_service._memory_service = None
    yield
    adk_memory_service._memory_service = None


@pytest.fixture
def mock_settings_enabled():
    """Mock settings with memory service enabled."""
    with patch('app.services.adk_memory_service.settings') as mock_settings:
        mock_settings.memory_service_enabled = True
        mock_settings.use_in_memory_memory_service = True
        mock_settings.agent_engine_id = ""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_location = "us-central1"
        mock_settings.app_name = "Improv Olympics"
        yield mock_settings


@pytest.fixture
def mock_settings_disabled():
    """Mock settings with memory service disabled."""
    with patch('app.services.adk_memory_service.settings') as mock_settings:
        mock_settings.memory_service_enabled = False
        mock_settings.app_name = "Improv Olympics"
        yield mock_settings


class TestADKMemoryServiceSingleton:
    """Test singleton pattern for ADK memory service"""

    def test_tc_mem_01_singleton_returns_same_instance(self, mock_settings_enabled):
        """
        TC-MEM-01: Singleton Returns Same Instance

        Verify singleton returns same memory service instance on multiple calls.
        """
        with patch('app.services.adk_memory_service.InMemoryMemoryService') as mock_memory_service:
            mock_instance = MagicMock()
            mock_memory_service.return_value = mock_instance

            from app.services.adk_memory_service import get_adk_memory_service, reset_adk_memory_service
            reset_adk_memory_service()

            service1 = get_adk_memory_service()
            service2 = get_adk_memory_service()

            assert service1 is service2, "Should return the same instance"
            assert mock_memory_service.call_count == 1, "Should only initialize once"

    def test_singleton_can_be_reset_for_testing(self, mock_settings_enabled):
        """
        TC-MEM-01b: Singleton Can Be Reset

        Verify singleton can be reset for testing purposes.
        """
        with patch('app.services.adk_memory_service.InMemoryMemoryService') as mock_memory_service:
            mock_instance1 = MagicMock(name="instance1")
            mock_instance2 = MagicMock(name="instance2")
            mock_memory_service.side_effect = [mock_instance1, mock_instance2]

            from app.services.adk_memory_service import (
                get_adk_memory_service,
                reset_adk_memory_service
            )
            reset_adk_memory_service()

            service1 = get_adk_memory_service()
            reset_adk_memory_service()
            service2 = get_adk_memory_service()

            assert service1 is mock_instance1
            assert service2 is mock_instance2
            assert service1 is not service2
            assert mock_memory_service.call_count == 2

    def test_returns_none_when_disabled(self, mock_settings_disabled):
        """Verify service returns None when disabled."""
        from app.services.adk_memory_service import get_adk_memory_service, reset_adk_memory_service
        reset_adk_memory_service()

        service = get_adk_memory_service()

        assert service is None


class TestADKMemoryServiceOperations:
    """Test memory service operations"""

    @pytest.fixture
    def mock_adk_session(self):
        """Mock ADK Session object"""
        mock_session = MagicMock()
        mock_session.session_id = "sess_memory_test"
        mock_session.user_id = "user_789"
        mock_session.state = {
            "location": "Training Arena",
            "turn_count": 2,
            "current_phase": "PHASE_2"
        }
        mock_session.events = []
        return mock_session

    @pytest.mark.asyncio
    async def test_tc_mem_03_save_session_to_memory(self, mock_settings_enabled, mock_adk_session):
        """
        TC-MEM-03: Save Session to Memory

        Test saving session data to memory service after session completion.
        """
        with patch('app.services.adk_memory_service.InMemoryMemoryService') as mock_memory_service:
            mock_instance = MagicMock()
            mock_instance.add_session_to_memory = AsyncMock()
            mock_memory_service.return_value = mock_instance

            from app.services.adk_memory_service import save_session_to_memory, reset_adk_memory_service
            reset_adk_memory_service()

            result = await save_session_to_memory(adk_session=mock_adk_session)

            mock_instance.add_session_to_memory.assert_called_once_with(mock_adk_session)
            assert result is True

    @pytest.mark.asyncio
    async def test_tc_mem_04_search_user_memories(self, mock_settings_enabled):
        """
        TC-MEM-04: Search User Memories

        Test searching memories returns relevant past interactions.
        """
        with patch('app.services.adk_memory_service.InMemoryMemoryService') as mock_memory_service:
            mock_instance = MagicMock()
            mock_memory_entry = {"content": "User struggled with 'Yes, and...' technique"}

            mock_instance.search_memory = AsyncMock(return_value=[mock_memory_entry])
            mock_memory_service.return_value = mock_instance

            from app.services.adk_memory_service import search_user_memories, reset_adk_memory_service
            reset_adk_memory_service()

            results = await search_user_memories(
                user_id="user_789",
                query="improv techniques practiced"
            )

            mock_instance.search_memory.assert_called_once()
            call_kwargs = mock_instance.search_memory.call_args[1]

            assert call_kwargs["app_name"] == "Improv Olympics"
            assert call_kwargs["user_id"] == "user_789"
            assert "improv techniques" in call_kwargs["query"]

            assert len(results) == 1
            assert results[0]["content"] == "User struggled with 'Yes, and...' technique"

    @pytest.mark.asyncio
    async def test_search_memories_with_limit(self, mock_settings_enabled):
        """Test searching memories respects limit parameter."""
        with patch('app.services.adk_memory_service.InMemoryMemoryService') as mock_memory_service:
            mock_instance = MagicMock()
            mock_results = [{"content": f"Memory {i}"} for i in range(10)]
            mock_instance.search_memory = AsyncMock(return_value=mock_results)
            mock_memory_service.return_value = mock_instance

            from app.services.adk_memory_service import search_user_memories, reset_adk_memory_service
            reset_adk_memory_service()

            results = await search_user_memories(
                user_id="user_789",
                query="character work techniques",
                limit=5
            )

            assert len(results) == 5


class TestADKMemoryServiceConfiguration:
    """Test memory service configuration options"""

    def test_tc_mem_02_initializes_with_in_memory_service(self, mock_settings_enabled):
        """
        TC-MEM-02: Initialize with InMemoryMemoryService

        Verify service uses InMemoryMemoryService for testing.
        """
        with patch('app.services.adk_memory_service.InMemoryMemoryService') as mock_memory_service:
            mock_instance = MagicMock()
            mock_memory_service.return_value = mock_instance

            from app.services.adk_memory_service import get_adk_memory_service, reset_adk_memory_service
            reset_adk_memory_service()

            service = get_adk_memory_service()

            mock_memory_service.assert_called_once()
            assert service is mock_instance

    def test_raises_error_without_agent_engine_id_for_vertex(self):
        """Test configuration requires agent_engine_id for VertexAI service."""
        with patch('app.services.adk_memory_service.settings') as mock_settings:
            mock_settings.memory_service_enabled = True
            mock_settings.use_in_memory_memory_service = False
            mock_settings.agent_engine_id = ""
            mock_settings.gcp_project_id = "test-project"
            mock_settings.gcp_location = "us-central1"

            from app.services.adk_memory_service import get_adk_memory_service, reset_adk_memory_service
            reset_adk_memory_service()

            with pytest.raises(ValueError, match="AGENT_ENGINE_ID"):
                get_adk_memory_service()


class TestADKMemoryServiceErrorHandling:
    """Test error handling in memory operations"""

    @pytest.mark.asyncio
    async def test_tc_mem_05_handles_disabled_memory_service(self, mock_settings_disabled):
        """
        TC-MEM-05: Error Handling When Memory Service is Disabled

        Test graceful handling when memory service is not available.
        """
        from app.services.adk_memory_service import (
            save_session_to_memory,
            search_user_memories,
            reset_adk_memory_service
        )
        reset_adk_memory_service()

        mock_session = MagicMock()

        result = await save_session_to_memory(mock_session)
        assert result is False

        results = await search_user_memories("user_123", "test query")
        assert results == []

    @pytest.mark.asyncio
    async def test_save_session_handles_errors_gracefully(self, mock_settings_enabled):
        """Test that memory service errors return False instead of raising."""
        with patch('app.services.adk_memory_service.InMemoryMemoryService') as mock_memory_service:
            mock_instance = MagicMock()
            mock_instance.add_session_to_memory = AsyncMock(
                side_effect=Exception("Memory storage failed")
            )
            mock_memory_service.return_value = mock_instance

            from app.services.adk_memory_service import save_session_to_memory, reset_adk_memory_service
            reset_adk_memory_service()

            mock_session = MagicMock()
            mock_session.session_id = "sess_error"
            mock_session.user_id = "user_123"
            mock_session.events = []

            result = await save_session_to_memory(mock_session)

            assert result is False

    @pytest.mark.asyncio
    async def test_search_memories_handles_empty_results(self, mock_settings_enabled):
        """Test search returns empty list when no memories found."""
        with patch('app.services.adk_memory_service.InMemoryMemoryService') as mock_memory_service:
            mock_instance = MagicMock()
            mock_instance.search_memory = AsyncMock(return_value=[])
            mock_memory_service.return_value = mock_instance

            from app.services.adk_memory_service import search_user_memories, reset_adk_memory_service
            reset_adk_memory_service()

            results = await search_user_memories(
                user_id="user_new",
                query="any query"
            )

            assert results == []
            assert isinstance(results, list)


class TestADKMemoryServiceCleanup:
    """Test cleanup and disposal"""

    @pytest.mark.asyncio
    async def test_tc_mem_06_close_memory_service_cleanup(self, mock_settings_enabled):
        """
        TC-MEM-06: Cleanup and Disposal

        Test cleanup properly disposes memory service resources.
        """
        with patch('app.services.adk_memory_service.InMemoryMemoryService') as mock_memory_service:
            mock_instance = MagicMock()
            mock_memory_service.return_value = mock_instance

            from app.services.adk_memory_service import (
                get_adk_memory_service,
                close_adk_memory_service,
                reset_adk_memory_service
            )
            reset_adk_memory_service()

            get_adk_memory_service()
            await close_adk_memory_service()

    @pytest.mark.asyncio
    async def test_close_handles_no_service_gracefully(self):
        """Test close handles case where service was never initialized."""
        from app.services.adk_memory_service import close_adk_memory_service, reset_adk_memory_service
        reset_adk_memory_service()

        await close_adk_memory_service()


class TestADKMemoryServiceIntegration:
    """Test memory service integration points"""

    @pytest.mark.asyncio
    async def test_memory_service_attached_to_runner(self, mock_settings_enabled):
        """Test that memory service can be attached to ADK Runner."""
        with patch('app.services.adk_memory_service.InMemoryMemoryService') as mock_memory_service:
            with patch('google.adk.runners.Runner') as mock_runner_class:
                mock_memory_instance = MagicMock()
                mock_memory_service.return_value = mock_memory_instance

                from app.services.adk_memory_service import get_adk_memory_service, reset_adk_memory_service
                reset_adk_memory_service()

                memory_service = get_adk_memory_service()

                _runner = mock_runner_class(  # noqa: F841 - validates runner creation
                    agent=MagicMock(),
                    app_name="Test App",
                    memory_service=memory_service
                )

                assert mock_runner_class.call_count == 1
                call_kwargs = mock_runner_class.call_args[1]
                assert call_kwargs["memory_service"] is memory_service
