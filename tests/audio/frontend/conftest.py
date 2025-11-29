"""Pytest configuration for Frontend Audio Tests

Provides Playwright fixtures and test utilities for browser-based audio testing.
"""

import pytest
import asyncio
from pathlib import Path
from playwright.sync_api import Browser, BrowserContext, Page, Playwright


@pytest.fixture(scope="session")
def static_files_dir():
    """Return path to static files directory"""
    return Path(__file__).parent.parent.parent.parent / "app" / "static"


@pytest.fixture(scope="session")
def browser_type_launch_args():
    """Launch arguments for all browser types"""
    return {
        "headless": True,
        "slow_mo": 0,
        "args": [
            "--use-fake-ui-for-media-stream",  # Auto-grant microphone permission
            "--use-fake-device-for-media-stream",  # Use fake audio device
            "--disable-web-security",  # Allow local file access
        ]
    }


@pytest.fixture(scope="session")
def browser_context_args():
    """Browser context arguments with audio permissions"""
    return {
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
        "java_script_enabled": True,
        "permissions": ["microphone"],  # Grant microphone access
    }


@pytest.fixture(scope="session")
def playwright_instance():
    """Create Playwright instance for session"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright_instance: Playwright, browser_type_launch_args):
    """Launch browser with audio testing capabilities"""
    browser = playwright_instance.chromium.launch(**browser_type_launch_args)
    yield browser
    browser.close()


@pytest.fixture
def context(browser: Browser, browser_context_args):
    """Create new browser context with audio permissions"""
    context = browser.new_context(**browser_context_args)
    yield context
    context.close()


@pytest.fixture
def page(context: BrowserContext):
    """Create new page for each test"""
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture
def audio_test_page(page: Page, static_files_dir):
    """
    Create page with audio testing utilities injected.

    Loads AudioCodec and provides testing helpers.
    """
    # Navigate to a blank page
    page.goto("about:blank")

    # Inject AudioCodec module
    audio_codec_js = (static_files_dir / "audio-codec.js").read_text()
    page.evaluate(audio_codec_js)

    # Inject test utilities
    page.evaluate("""
        window.testUtils = {
            createTestPCM16: function(length) {
                const buffer = new ArrayBuffer(length);
                const view = new Int16Array(buffer);
                for (let i = 0; i < view.length; i++) {
                    view[i] = (i % 32768) - 16384;  // Sawtooth wave
                }
                return new Uint8Array(buffer);
            },

            createTestFloat32: function(length) {
                const samples = new Float32Array(length);
                for (let i = 0; i < length; i++) {
                    samples[i] = Math.sin(2 * Math.PI * 440 * i / 16000);  // 440Hz sine
                }
                return samples;
            },

            isValidBase64: function(str) {
                try {
                    return btoa(atob(str)) === str;
                } catch(e) {
                    return false;
                }
            },

            compareFloat32Arrays: function(arr1, arr2, tolerance = 0.001) {
                if (arr1.length !== arr2.length) return false;
                for (let i = 0; i < arr1.length; i++) {
                    if (Math.abs(arr1[i] - arr2[i]) > tolerance) return false;
                }
                return true;
            }
        };
    """)

    yield page


@pytest.fixture
def mock_websocket_server(page: Page):
    """
    Create mock WebSocket server in browser context.

    Simulates server responses for testing AudioStreamManager.
    """
    page.evaluate("""
        class MockWebSocketServer {
            constructor() {
                this.messages = [];
                this.originalWebSocket = window.WebSocket;
                this.mockWebSocket = null;

                // Replace global WebSocket
                const self = this;
                window.WebSocket = function(url, protocols) {
                    self.mockWebSocket = {
                        url: url,
                        readyState: WebSocket.CONNECTING,
                        onopen: null,
                        onclose: null,
                        onerror: null,
                        onmessage: null,
                        sentMessages: [],

                        send: function(data) {
                            this.sentMessages.push(data);
                            self.messages.push({ type: 'sent', data: data });
                        },

                        close: function(code, reason) {
                            this.readyState = WebSocket.CLOSED;
                            if (this.onclose) {
                                this.onclose({ code: code || 1000, reason: reason || '' });
                            }
                        },

                        // Simulate receiving message
                        simulateMessage: function(message) {
                            if (this.onmessage) {
                                this.onmessage({ data: JSON.stringify(message) });
                            }
                        },

                        // Simulate connection
                        simulateOpen: function() {
                            this.readyState = WebSocket.OPEN;
                            if (this.onopen) {
                                this.onopen({});
                            }
                        },

                        // Simulate error
                        simulateError: function(error) {
                            if (this.onerror) {
                                this.onerror(error);
                            }
                        }
                    };

                    // Auto-connect after short delay
                    setTimeout(() => {
                        if (self.mockWebSocket) {
                            self.mockWebSocket.simulateOpen();
                        }
                    }, 10);

                    return self.mockWebSocket;
                };

                window.WebSocket.CONNECTING = 0;
                window.WebSocket.OPEN = 1;
                window.WebSocket.CLOSING = 2;
                window.WebSocket.CLOSED = 3;
            }

            getWebSocket() {
                return this.mockWebSocket;
            }

            getSentMessages() {
                return this.mockWebSocket ? this.mockWebSocket.sentMessages : [];
            }

            simulateServerMessage(message) {
                if (this.mockWebSocket) {
                    this.mockWebSocket.simulateMessage(message);
                }
            }

            restore() {
                window.WebSocket = this.originalWebSocket;
            }
        }

        window.mockWsServer = new MockWebSocketServer();
    """)

    yield page

    # Restore original WebSocket
    page.evaluate("window.mockWsServer.restore()")


@pytest.fixture
def audio_stream_test_page(page: Page, static_files_dir, mock_websocket_server):
    """
    Create page with AudioStreamManager and mocked WebSocket.

    Ready for integration testing.
    """
    # Load dependencies
    audio_codec_js = (static_files_dir / "audio-codec.js").read_text()
    audio_manager_js = (static_files_dir / "audio-manager.js").read_text()

    page.evaluate(audio_codec_js)
    page.evaluate(audio_manager_js)

    # Create test instance
    page.evaluate("""
        window.audioManager = new AudioStreamManager();
        window.audioManager.sessionId = 'test-session-123';
        window.audioManager.authToken = 'test-token-456';
    """)

    yield page
