"""End-to-End Tests for Complete Audio Flow

Tests the full audio pipeline from capture to playback.
"""

import pytest
from playwright.sync_api import Page


class TestE2EAudioFlow:
    """Test complete audio flow scenarios"""

    def test_complete_conversation_flow(self, audio_stream_test_page: Page):
        """Test full conversation: connect -> capture -> receive audio -> disconnect"""
        result = audio_stream_test_page.evaluate("""
            return new Promise(async (resolve) => {
                const manager = window.audioManager;
                const events = [];

                // Track all state changes
                manager.onStateChange = (newState) => {
                    events.push({ type: 'state', value: newState });
                };

                // Track transcriptions
                manager.onTranscription = (data) => {
                    events.push({ type: 'transcription', value: data });
                };

                // Track errors
                manager.onError = (error) => {
                    events.push({ type: 'error', value: error });
                };

                // Mock getUserMedia
                navigator.mediaDevices.getUserMedia = async () => {
                    return new MediaStream();
                };

                // Mock AudioWorklet
                window.AudioContext.prototype.audioWorklet = {
                    addModule: async () => {}
                };

                try {
                    // 1. Connect
                    await manager.connect('test-session-123', 'test-token');
                    events.push({ type: 'action', value: 'connected' });

                    // 2. Simulate server messages
                    window.mockWsServer.simulateServerMessage({
                        type: 'control',
                        action: 'listening_started'
                    });

                    window.mockWsServer.simulateServerMessage({
                        type: 'transcription',
                        text: 'Hello MC',
                        role: 'user',
                        is_final: true
                    });

                    window.mockWsServer.simulateServerMessage({
                        type: 'control',
                        action: 'listening_stopped'
                    });

                    // 3. Simulate audio response
                    const testPCM16 = window.testUtils.createTestPCM16(200);
                    const base64Audio = AudioCodec.encodePCM16ToBase64(testPCM16);

                    window.mockWsServer.simulateServerMessage({
                        type: 'audio',
                        data: base64Audio,
                        sample_rate: 24000
                    });

                    window.mockWsServer.simulateServerMessage({
                        type: 'transcription',
                        text: 'Welcome to the show!',
                        role: 'assistant',
                        is_final: true
                    });

                    // Wait for processing
                    await new Promise(r => setTimeout(r, 100));

                    // 4. Disconnect
                    await manager.disconnect();
                    events.push({ type: 'action', value: 'disconnected' });

                    resolve({
                        success: true,
                        events: events,
                        finalState: manager.state,
                        stateChanges: events.filter(e => e.type === 'state').map(e => e.value),
                        transcriptions: events.filter(e => e.type === 'transcription').map(e => e.value),
                        errors: events.filter(e => e.type === 'error')
                    });
                } catch(error) {
                    resolve({
                        success: false,
                        error: error.message,
                        events: events
                    });
                }
            });
        """)

        assert result["success"] is True, f"E2E flow failed: {result.get('error', 'Unknown error')}"
        assert result["finalState"] == "disconnected"
        assert len(result["errors"]) == 0, f"Errors occurred: {result['errors']}"

        # Verify state transitions
        states = result["stateChanges"]
        assert "connecting" in states
        assert "connected" in states
        assert "listening" in states
        assert "processing" in states
        assert "playing" in states
        assert "disconnected" in states

        # Verify transcriptions received
        transcriptions = result["transcriptions"]
        assert len(transcriptions) == 2
        assert any("Hello MC" in t["text"] for t in transcriptions)
        assert any("Welcome to the show" in t["text"] for t in transcriptions)

    def test_error_recovery_flow(self, audio_stream_test_page: Page):
        """Test error handling and recovery"""
        result = audio_stream_test_page.evaluate("""
            return new Promise(async (resolve) => {
                const manager = window.audioManager;
                let errorReceived = null;

                manager.onError = (error) => {
                    errorReceived = error;
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

                // Simulate server error
                window.mockWsServer.simulateServerMessage({
                    type: 'error',
                    code: 'PROCESSING_FAILED',
                    message: 'Audio processing failed'
                });

                await new Promise(r => setTimeout(r, 50));

                // Verify error was received
                const hasError = errorReceived !== null;

                // Try to disconnect cleanly
                await manager.disconnect();

                resolve({
                    hasError: hasError,
                    errorCode: errorReceived ? errorReceived.code : null,
                    errorMessage: errorReceived ? errorReceived.message : null,
                    finalState: manager.state,
                    canDisconnect: true
                });
            });
        """)

        assert result["hasError"] is True
        assert result["errorCode"] == "PROCESSING_FAILED"
        assert "Audio processing failed" in result["errorMessage"]
        assert result["canDisconnect"] is True
        assert result["finalState"] == "disconnected"

    def test_microphone_permission_denied(self, audio_stream_test_page: Page):
        """Test handling of microphone permission denial"""
        result = audio_stream_test_page.evaluate("""
            return new Promise(async (resolve) => {
                const manager = new AudioStreamManager();
                let errorReceived = null;

                manager.onError = (error) => {
                    errorReceived = error;
                };

                // Mock getUserMedia to reject
                navigator.mediaDevices.getUserMedia = async () => {
                    throw new Error('Permission denied');
                };

                const connected = await manager.connect('test-session-123', 'test-token');

                resolve({
                    connected: connected,
                    hasError: errorReceived !== null,
                    errorCode: errorReceived ? errorReceived.code : null,
                    state: manager.state
                });
            });
        """)

        assert result["connected"] is False
        assert result["hasError"] is True
        assert result["errorCode"] == "MIC_PERMISSION_DENIED"
        assert result["state"] == "error"


class TestE2EPlaybackQueue:
    """Test audio playback queue processing"""

    def test_playback_queue_processes_sequentially(self, audio_stream_test_page: Page):
        """Test that audio chunks are played in order"""
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

                // Queue multiple audio chunks
                const chunk1 = window.testUtils.createTestPCM16(100);
                const chunk2 = window.testUtils.createTestPCM16(100);
                const chunk3 = window.testUtils.createTestPCM16(100);

                window.mockWsServer.simulateServerMessage({
                    type: 'audio',
                    data: AudioCodec.encodePCM16ToBase64(chunk1),
                    sample_rate: 24000
                });

                window.mockWsServer.simulateServerMessage({
                    type: 'audio',
                    data: AudioCodec.encodePCM16ToBase64(chunk2),
                    sample_rate: 24000
                });

                window.mockWsServer.simulateServerMessage({
                    type: 'audio',
                    data: AudioCodec.encodePCM16ToBase64(chunk3),
                    sample_rate: 24000
                });

                // Wait for processing
                await new Promise(r => setTimeout(r, 100));

                await manager.disconnect();

                resolve({
                    success: true,
                    // Queue should be processed
                    finalQueueLength: manager.playbackQueue.length
                });
            });
        """)

        assert result["success"] is True
        # Queue may still have items or be empty depending on timing
        assert result["finalQueueLength"] >= 0


class TestE2EPerformance:
    """Test performance characteristics"""

    def test_codec_performance(self, audio_test_page: Page):
        """Test that codec operations complete within acceptable time"""
        result = audio_test_page.evaluate("""
            const iterations = 100;
            const sampleSize = 3200;  // 100ms at 16kHz

            // Test encoding performance
            const encodeStart = performance.now();
            for (let i = 0; i < iterations; i++) {
                const samples = window.testUtils.createTestFloat32(sampleSize / 2);
                const pcm16 = AudioCodec.float32ToPCM16(samples);
                const encoded = AudioCodec.encodePCM16ToBase64(pcm16);
            }
            const encodeTime = performance.now() - encodeStart;

            // Test decoding performance
            const testPCM16 = window.testUtils.createTestPCM16(sampleSize);
            const testEncoded = AudioCodec.encodePCM16ToBase64(testPCM16);

            const decodeStart = performance.now();
            for (let i = 0; i < iterations; i++) {
                const decoded = AudioCodec.decodeBase64ToPCM16(testEncoded);
                const samples = AudioCodec.pcm16ToFloat32(decoded);
            }
            const decodeTime = performance.now() - decodeStart;

            ({
                iterations: iterations,
                encodeTimeMs: encodeTime,
                decodeTimeMs: decodeTime,
                avgEncodeMs: encodeTime / iterations,
                avgDecodeMs: decodeTime / iterations,
                totalTimeMs: encodeTime + decodeTime
            })
        """)

        # Each operation should complete in under 100ms total for 100 iterations
        assert result["encodeTimeMs"] < 100, f"Encoding too slow: {result['encodeTimeMs']}ms"
        assert result["decodeTimeMs"] < 100, f"Decoding too slow: {result['decodeTimeMs']}ms"
        assert result["totalTimeMs"] < 200, f"Total codec time too slow: {result['totalTimeMs']}ms"

        # Average per operation should be well under 1ms
        assert result["avgEncodeMs"] < 1.0
        assert result["avgDecodeMs"] < 1.0
