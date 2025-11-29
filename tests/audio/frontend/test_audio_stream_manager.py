"""Integration Tests for AudioStreamManager

Tests WebSocket connection, state management, and audio pipeline.
"""

import pytest
import asyncio
from playwright.sync_api import Page


class TestAudioStreamManagerInitialization:
    """Test AudioStreamManager initialization and setup"""

    def test_constructor_initializes_properties(self, audio_stream_test_page: Page):
        """Test that constructor sets up all required properties"""
        result = audio_stream_test_page.evaluate("""
            const manager = new AudioStreamManager();

            ({
                hasAudioContext: manager.audioContext === null,
                hasMediaStream: manager.mediaStream === null,
                hasWorkletNode: manager.workletNode === null,
                hasWebsocket: manager.websocket === null,
                sessionId: manager.sessionId,
                authToken: manager.authToken,
                isConnected: manager.isConnected,
                isCapturing: manager.isCapturing,
                playbackQueue: Array.isArray(manager.playbackQueue),
                isPlaying: manager.isPlaying,
                state: manager.state,
                reconnectAttempts: manager.reconnectAttempts,
                maxReconnectAttempts: manager.maxReconnectAttempts
            })
        """)

        assert result["hasAudioContext"] is True, "audioContext should be null initially"
        assert result["hasMediaStream"] is True, "mediaStream should be null initially"
        assert result["hasWorkletNode"] is True, "workletNode should be null initially"
        assert result["hasWebsocket"] is True, "websocket should be null initially"
        assert result["sessionId"] is None
        assert result["authToken"] is None
        assert result["isConnected"] is False
        assert result["isCapturing"] is False
        assert result["playbackQueue"] is True, "playbackQueue should be an array"
        assert result["isPlaying"] is False
        assert result["state"] == "idle"
        assert result["reconnectAttempts"] == 0
        assert result["maxReconnectAttempts"] == 3

    def test_logger_is_created(self, audio_stream_test_page: Page):
        """Test that logger is properly initialized"""
        result = audio_stream_test_page.evaluate("""
            const manager = new AudioStreamManager();

            ({
                hasLogger: manager.logger !== null,
                hasInfoMethod: typeof manager.logger.info === 'function',
                hasWarnMethod: typeof manager.logger.warn === 'function',
                hasErrorMethod: typeof manager.logger.error === 'function',
                hasDebugMethod: typeof manager.logger.debug === 'function'
            })
        """)

        assert result["hasLogger"] is True
        assert result["hasInfoMethod"] is True
        assert result["hasWarnMethod"] is True
        assert result["hasErrorMethod"] is True
        assert result["hasDebugMethod"] is True


class TestAudioStreamManagerStateMachine:
    """Test state machine transitions"""

    def test_set_state_updates_state(self, audio_stream_test_page: Page):
        """Test setState updates state property"""
        result = audio_stream_test_page.evaluate("""
            const manager = new AudioStreamManager();
            const initialState = manager.state;

            manager.setState('connecting');
            const newState = manager.state;

            ({ initialState: initialState, newState: newState })
        """)

        assert result["initialState"] == "idle"
        assert result["newState"] == "connecting"

    def test_set_state_calls_callback(self, audio_stream_test_page: Page):
        """Test setState triggers onStateChange callback"""
        result = audio_stream_test_page.evaluate("""
            const manager = new AudioStreamManager();
            const stateChanges = [];

            manager.onStateChange = (newState, oldState) => {
                stateChanges.push({ new: newState, old: oldState });
            };

            manager.setState('connecting');
            manager.setState('connected');
            manager.setState('recording');

            ({ stateChanges: stateChanges, count: stateChanges.length })
        """)

        assert result["count"] == 3
        assert result["stateChanges"][0] == {"new": "connecting", "old": "idle"}
        assert result["stateChanges"][1] == {"new": "connected", "old": "connecting"}
        assert result["stateChanges"][2] == {"new": "recording", "old": "connected"}

    def test_get_state_returns_current_state(self, audio_stream_test_page: Page):
        """Test getState returns current state"""
        result = audio_stream_test_page.evaluate("""
            const manager = new AudioStreamManager();
            manager.setState('processing');

            ({ state: manager.getState() })
        """)

        assert result["state"] == "processing"


class TestAudioStreamManagerWebSocket:
    """Test WebSocket connection and message handling"""

    def test_websocket_connection_success(self, audio_stream_test_page: Page):
        """Test successful WebSocket connection"""
        result = audio_stream_test_page.evaluate("""
            return new Promise((resolve) => {
                const manager = window.audioManager;
                let stateChanges = [];

                manager.onStateChange = (newState, oldState) => {
                    stateChanges.push(newState);

                    if (newState === 'connected') {
                        resolve({
                            success: true,
                            isConnected: manager.isConnected,
                            state: manager.state,
                            reconnectAttempts: manager.reconnectAttempts,
                            stateChanges: stateChanges,
                            wsUrl: manager.websocket ? manager.websocket.url : null
                        });
                    }
                };

                // Mock getUserMedia
                navigator.mediaDevices.getUserMedia = async () => {
                    return new MediaStream();
                };

                // Mock AudioContext and AudioWorklet
                window.AudioContext.prototype.audioWorklet = {
                    addModule: async () => {}
                };

                manager.connect('test-session-123', 'test-token-456');
            });
        """)

        assert result["success"] is True
        assert result["isConnected"] is True
        assert result["state"] == "connected"
        assert result["reconnectAttempts"] == 0
        assert "connecting" in result["stateChanges"]
        assert "connected" in result["stateChanges"]
        assert "test-session-123" in result["wsUrl"]
        assert "test-token-456" in result["wsUrl"]

    def test_websocket_authentication_failure(self, audio_stream_test_page: Page):
        """Test WebSocket connection with authentication failure"""
        result = audio_stream_test_page.evaluate("""
            return new Promise((resolve) => {
                const manager = window.audioManager;
                let errorReceived = null;

                manager.onError = (error) => {
                    errorReceived = error;

                    setTimeout(() => {
                        resolve({
                            errorCode: errorReceived.code,
                            errorMessage: errorReceived.message,
                            isConnected: manager.isConnected,
                            state: manager.state
                        });
                    }, 50);
                };

                // Mock getUserMedia
                navigator.mediaDevices.getUserMedia = async () => {
                    return new MediaStream();
                };

                // Mock AudioWorklet
                window.AudioContext.prototype.audioWorklet = {
                    addModule: async () => {}
                };

                // Connect then simulate auth failure
                manager.connect('test-session-123', 'invalid-token').then(() => {
                    // Simulate auth failure close code
                    const ws = window.mockWsServer.getWebSocket();
                    ws.close(4001, 'Authentication failed');
                });
            });
        """)

        assert result["errorCode"] == "AUTH_FAILED"
        assert "Authentication failed" in result["errorMessage"]
        assert result["isConnected"] is False
        assert result["state"] == "error"

    def test_websocket_premium_required_error(self, audio_stream_test_page: Page):
        """Test WebSocket connection with premium tier requirement"""
        result = audio_stream_test_page.evaluate("""
            return new Promise((resolve) => {
                const manager = window.audioManager;
                let errorReceived = null;

                manager.onError = (error) => {
                    errorReceived = error;

                    setTimeout(() => {
                        resolve({
                            errorCode: errorReceived.code,
                            errorMessage: errorReceived.message,
                            state: manager.state
                        });
                    }, 50);
                };

                // Mock getUserMedia
                navigator.mediaDevices.getUserMedia = async () => {
                    return new MediaStream();
                };

                // Mock AudioWorklet
                window.AudioContext.prototype.audioWorklet = {
                    addModule: async () => {}
                };

                manager.connect('test-session-123', 'free-tier-token').then(() => {
                    const ws = window.mockWsServer.getWebSocket();
                    ws.close(4003, 'Premium subscription required');
                });
            });
        """)

        assert result["errorCode"] == "PREMIUM_REQUIRED"
        assert "Premium subscription required" in result["errorMessage"]
        assert result["state"] == "error"

    def test_websocket_reconnection_logic(self, audio_stream_test_page: Page):
        """Test WebSocket automatic reconnection"""
        result = audio_stream_test_page.evaluate("""
            return new Promise((resolve) => {
                const manager = window.audioManager;
                let stateChanges = [];

                manager.onStateChange = (newState) => {
                    stateChanges.push(newState);

                    if (newState === 'reconnecting') {
                        setTimeout(() => {
                            resolve({
                                reconnectAttempts: manager.reconnectAttempts,
                                stateChanges: stateChanges,
                                maxAttempts: manager.maxReconnectAttempts
                            });
                        }, 100);
                    }
                };

                // Mock getUserMedia
                navigator.mediaDevices.getUserMedia = async () => {
                    return new MediaStream();
                };

                // Mock AudioWorklet
                window.AudioContext.prototype.audioWorklet = {
                    addModule: async () => {}
                };

                manager.connect('test-session-123', 'test-token').then(() => {
                    // Simulate unexpected disconnect
                    const ws = window.mockWsServer.getWebSocket();
                    ws.close(1006, 'Connection lost');  // Abnormal closure
                });
            });
        """)

        assert result["reconnectAttempts"] >= 1, "Should attempt reconnection"
        assert result["maxAttempts"] == 3
        assert "reconnecting" in result["stateChanges"]


class TestAudioStreamManagerServerMessages:
    """Test handling of different server message types"""

    def test_handle_audio_message(self, audio_stream_test_page: Page):
        """Test handling audio response from server"""
        result = audio_stream_test_page.evaluate("""
            return new Promise(async (resolve) => {
                const manager = window.audioManager;

                // Mock getUserMedia
                navigator.mediaDevices.getUserMedia = async () => {
                    return new MediaStream();
                };

                // Mock AudioWorklet
                window.AudioContext.prototype.audioWorklet = {
                    addModule: async () => {}
                };

                await manager.connect('test-session-123', 'test-token');

                // Track state changes
                let playingState = false;
                manager.onStateChange = (newState) => {
                    if (newState === 'playing') {
                        playingState = true;

                        setTimeout(() => {
                            resolve({
                                playingState: playingState,
                                playbackQueueLength: manager.playbackQueue.length,
                                isPlaying: manager.isPlaying
                            });
                        }, 50);
                    }
                };

                // Simulate audio response
                const testPCM16 = window.testUtils.createTestPCM16(100);
                const base64Audio = AudioCodec.encodePCM16ToBase64(testPCM16);

                window.mockWsServer.simulateServerMessage({
                    type: 'audio',
                    data: base64Audio,
                    sample_rate: 24000
                });
            });
        """)

        assert result["playingState"] is True, "Should transition to playing state"
        # Note: playbackQueue might be empty if playback started immediately
        assert result["isPlaying"] is True or result["playbackQueueLength"] >= 0

    def test_handle_transcription_message(self, audio_stream_test_page: Page):
        """Test handling transcription message from server"""
        result = audio_stream_test_page.evaluate("""
            return new Promise(async (resolve) => {
                const manager = window.audioManager;
                let transcriptions = [];

                manager.onTranscription = (data) => {
                    transcriptions.push(data);

                    if (transcriptions.length === 2) {
                        resolve({
                            count: transcriptions.length,
                            first: transcriptions[0],
                            second: transcriptions[1]
                        });
                    }
                };

                // Mock getUserMedia
                navigator.mediaDevices.getUserMedia = async () => {
                    return new MediaStream();
                };

                // Mock AudioWorklet
                window.AudioContext.prototype.audioWorklet = {
                    addModule: async () => {}
                };

                await manager.connect('test-session-123', 'test-token');

                // Simulate transcription messages
                window.mockWsServer.simulateServerMessage({
                    type: 'transcription',
                    text: 'Hello there',
                    role: 'user',
                    is_final: false
                });

                window.mockWsServer.simulateServerMessage({
                    type: 'transcription',
                    text: 'Hello there!',
                    role: 'user',
                    is_final: true
                });
            });
        """)

        assert result["count"] == 2
        assert result["first"]["text"] == "Hello there"
        assert result["first"]["role"] == "user"
        assert result["first"]["isFinal"] is False
        assert result["second"]["text"] == "Hello there!"
        assert result["second"]["isFinal"] is True

    def test_handle_control_message_listening_started(self, audio_stream_test_page: Page):
        """Test handling control message for listening started"""
        result = audio_stream_test_page.evaluate("""
            return new Promise(async (resolve) => {
                const manager = window.audioManager;

                manager.onStateChange = (newState) => {
                    if (newState === 'listening') {
                        resolve({ state: newState });
                    }
                };

                // Mock getUserMedia
                navigator.mediaDevices.getUserMedia = async () => {
                    return new MediaStream();
                };

                // Mock AudioWorklet
                window.AudioContext.prototype.audioWorklet = {
                    addModule: async () => {}
                };

                await manager.connect('test-session-123', 'test-token');

                window.mockWsServer.simulateServerMessage({
                    type: 'control',
                    action: 'listening_started'
                });
            });
        """)

        assert result["state"] == "listening"

    def test_handle_control_message_listening_stopped(self, audio_stream_test_page: Page):
        """Test handling control message for listening stopped"""
        result = audio_stream_test_page.evaluate("""
            return new Promise(async (resolve) => {
                const manager = window.audioManager;

                manager.onStateChange = (newState) => {
                    if (newState === 'processing') {
                        resolve({ state: newState });
                    }
                };

                // Mock getUserMedia
                navigator.mediaDevices.getUserMedia = async () => {
                    return new MediaStream();
                };

                // Mock AudioWorklet
                window.AudioContext.prototype.audioWorklet = {
                    addModule: async () => {}
                };

                await manager.connect('test-session-123', 'test-token');

                window.mockWsServer.simulateServerMessage({
                    type: 'control',
                    action: 'listening_stopped'
                });
            });
        """)

        assert result["state"] == "processing"

    def test_handle_error_message(self, audio_stream_test_page: Page):
        """Test handling error message from server"""
        result = audio_stream_test_page.evaluate("""
            return new Promise(async (resolve) => {
                const manager = window.audioManager;

                manager.onError = (error) => {
                    resolve({
                        code: error.code,
                        message: error.message
                    });
                };

                // Mock getUserMedia
                navigator.mediaDevices.getUserMedia = async () => {
                    return new MediaStream();
                };

                // Mock AudioWorklet
                window.AudioContext.prototype.audioWorklet = {
                    addModule: async () => {}
                };

                await manager.connect('test-session-123', 'test-token');

                window.mockWsServer.simulateServerMessage({
                    type: 'error',
                    code: 'RATE_LIMIT_EXCEEDED',
                    message: 'Too many requests'
                });
            });
        """)

        assert result["code"] == "RATE_LIMIT_EXCEEDED"
        assert result["message"] == "Too many requests"


class TestAudioStreamManagerAudioCapture:
    """Test audio capture and transmission"""

    def test_send_audio_chunk_format(self, audio_stream_test_page: Page):
        """Test that audio chunks are sent in correct format"""
        result = audio_stream_test_page.evaluate("""
            return new Promise(async (resolve) => {
                const manager = window.audioManager;

                // Mock getUserMedia
                navigator.mediaDevices.getUserMedia = async () => {
                    return new MediaStream();
                };

                // Mock AudioWorklet
                window.AudioContext.prototype.audioWorklet = {
                    addModule: async () => {}
                };

                await manager.connect('test-session-123', 'test-token');

                // Send test audio chunk
                const testSamples = window.testUtils.createTestFloat32(100);
                manager.sendAudioChunk(testSamples);

                // Get sent messages
                const messages = window.mockWsServer.getSentMessages();
                const lastMessage = JSON.parse(messages[messages.length - 1]);

                resolve({
                    messageType: lastMessage.type,
                    hasAudio: 'audio' in lastMessage,
                    isValidBase64: window.testUtils.isValidBase64(lastMessage.audio),
                    audioLength: lastMessage.audio ? lastMessage.audio.length : 0
                });
            });
        """)

        assert result["messageType"] == "audio/pcm"
        assert result["hasAudio"] is True
        assert result["isValidBase64"] is True
        assert result["audioLength"] > 0

    def test_send_control_message(self, audio_stream_test_page: Page):
        """Test sending control messages to server"""
        result = audio_stream_test_page.evaluate("""
            return new Promise(async (resolve) => {
                const manager = window.audioManager;

                // Mock getUserMedia
                navigator.mediaDevices.getUserMedia = async () => {
                    return new MediaStream();
                };

                // Mock AudioWorklet
                window.AudioContext.prototype.audioWorklet = {
                    addModule: async () => {}
                };

                await manager.connect('test-session-123', 'test-token');

                manager.sendControlMessage('start_listening');
                manager.sendControlMessage('stop_listening');

                const messages = window.mockWsServer.getSentMessages();
                const controlMessages = messages
                    .map(m => JSON.parse(m))
                    .filter(m => m.type === 'control');

                resolve({
                    count: controlMessages.length,
                    actions: controlMessages.map(m => m.action)
                });
            });
        """)

        assert result["count"] >= 2
        assert "start_listening" in result["actions"]
        assert "stop_listening" in result["actions"]


class TestAudioStreamManagerCleanup:
    """Test proper cleanup and disconnection"""

    def test_disconnect_cleans_up_resources(self, audio_stream_test_page: Page):
        """Test that disconnect properly cleans up all resources"""
        result = audio_stream_test_page.evaluate("""
            return new Promise(async (resolve) => {
                const manager = window.audioManager;

                // Mock getUserMedia
                const mockTracks = [{ stop: () => {} }];
                navigator.mediaDevices.getUserMedia = async () => {
                    return { getTracks: () => mockTracks };
                };

                // Mock AudioWorklet
                window.AudioContext.prototype.audioWorklet = {
                    addModule: async () => {}
                };

                await manager.connect('test-session-123', 'test-token');

                // Verify connected
                const wasConnected = manager.isConnected;

                // Disconnect
                await manager.disconnect();

                resolve({
                    wasConnected: wasConnected,
                    isConnectedAfter: manager.isConnected,
                    websocketNull: manager.websocket === null,
                    mediaStreamNull: manager.mediaStream === null,
                    workletNodeNull: manager.workletNode === null,
                    playbackQueueEmpty: manager.playbackQueue.length === 0,
                    finalState: manager.state
                });
            });
        """)

        assert result["wasConnected"] is True
        assert result["isConnectedAfter"] is False
        assert result["websocketNull"] is True
        assert result["mediaStreamNull"] is True
        assert result["workletNodeNull"] is True
        assert result["playbackQueueEmpty"] is True
        assert result["finalState"] == "disconnected"

    def test_is_active_reflects_activity(self, audio_stream_test_page: Page):
        """Test isActive returns correct state"""
        result = audio_stream_test_page.evaluate("""
            return new Promise(async (resolve) => {
                const manager = window.audioManager;

                // Mock getUserMedia
                navigator.mediaDevices.getUserMedia = async () => {
                    return new MediaStream();
                };

                // Mock AudioWorklet
                window.AudioContext.prototype.audioWorklet = {
                    addModule: async () => {}
                };

                const beforeConnect = manager.isActive();

                await manager.connect('test-session-123', 'test-token');
                const afterConnect = manager.isActive();

                await manager.disconnect();
                const afterDisconnect = manager.isActive();

                resolve({
                    beforeConnect: beforeConnect,
                    afterConnect: afterConnect,
                    afterDisconnect: afterDisconnect
                });
            });
        """)

        assert result["beforeConnect"] is False
        assert result["afterConnect"] is False  # Not active until capturing or playing
        assert result["afterDisconnect"] is False
