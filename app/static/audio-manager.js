class AudioStreamManager {
    constructor() {
        this.audioContext = null;
        this.playbackContext = null;
        this.mediaStream = null;
        this.workletNode = null;
        this.mediaStreamSource = null;
        this.websocket = null;
        this.sessionId = null;
        this.authToken = null;
        this.isConnected = false;
        this.isCapturing = false;
        this.playbackQueue = [];
        this.isPlaying = false;
        this.onTranscription = null;
        this.onStateChange = null;
        this.onError = null;
        this.onAudioLevel = null;
        this.onTurnComplete = null;
        this.state = 'idle';
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 3;
        this.reconnectTimeoutId = null;
        this.logger = this.createLogger();
    }

    createLogger() {
        const prefix = '[AudioStreamManager]';
        return {
            info: (...args) => console.log(prefix, ...args),
            warn: (...args) => console.warn(prefix, ...args),
            error: (...args) => console.error(prefix, ...args),
            debug: (...args) => console.debug(prefix, ...args)
        };
    }

    setState(newState) {
        const oldState = this.state;
        this.state = newState;
        this.logger.info(`State change: ${oldState} -> ${newState}`);
        if (this.onStateChange) {
            this.onStateChange(newState, oldState);
        }
    }

    async checkMicrophonePermission() {
        try {
            const result = await navigator.permissions.query({ name: 'microphone' });
            return result.state;
        } catch (e) {
            return 'prompt';
        }
    }

    async requestMicrophoneAccess() {
        this.setState('requesting_permission');
        try {
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: AudioCodec.INPUT_SAMPLE_RATE,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            this.logger.info('Microphone access granted');
            return true;
        } catch (error) {
            this.logger.error('Microphone access denied:', error);
            this.setState('error');
            if (this.onError) {
                this.onError({
                    code: 'MIC_PERMISSION_DENIED',
                    message: 'Microphone access was denied. Please allow microphone access to use voice mode.'
                });
            }
            return false;
        }
    }

    async initializeAudioContext() {
        if (this.audioContext) {
            return;
        }
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: AudioCodec.INPUT_SAMPLE_RATE
        });
        if (this.audioContext.state === 'suspended') {
            await this.audioContext.resume();
        }
        try {
            await this.audioContext.audioWorklet.addModule('/static/audio-worklet.js');
            this.logger.info('AudioWorklet loaded');
        } catch (error) {
            this.logger.error('Failed to load AudioWorklet:', error);
            throw error;
        }
    }

    async initializePlaybackContext(sampleRate) {
        if (this.playbackContext && this.playbackContext.sampleRate === sampleRate) {
            return this.playbackContext;
        }
        if (this.playbackContext) {
            await this.playbackContext.close();
        }
        this.playbackContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: sampleRate
        });
        return this.playbackContext;
    }

    async connect(sessionId, authToken, selectedGame = null) {
        this.sessionId = sessionId;
        this.authToken = authToken;
        this.selectedGame = selectedGame;
        this.setState('connecting');
        const hasPermission = await this.requestMicrophoneAccess();
        if (!hasPermission) {
            return false;
        }
        await this.initializeAudioContext();
        return this.connectWebSocket();
    }

    connectWebSocket() {
        return new Promise((resolve, reject) => {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const encodedToken = encodeURIComponent(this.authToken);
            let wsUrl = `${protocol}//${window.location.host}/ws/audio/${this.sessionId}?token=${encodedToken}`;

            // Include selected game info for the MC to know what scene to run
            if (this.selectedGame) {
                const encodedGame = encodeURIComponent(this.selectedGame.name || this.selectedGame);
                wsUrl += `&game=${encodedGame}`;
            }

            const safeUrl = wsUrl
                .replace(encodedToken, '[REDACTED]')
                .replace(/game=[^&]*/, 'game=[GAME]');
            this.logger.info('Connecting to WebSocket:', safeUrl);
            this.websocket = new WebSocket(wsUrl);
            this.websocket.onopen = () => {
                this.logger.info('WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.setState('connected');
                resolve(true);
            };
            this.websocket.onclose = (event) => {
                this.logger.info('WebSocket closed:', event.code, event.reason);
                this.isConnected = false;
                if (event.code === 4001) {
                    this.setState('error');
                    if (this.onError) {
                        this.onError({ code: 'AUTH_FAILED', message: 'Authentication failed' });
                    }
                } else if (event.code === 4003) {
                    this.setState('error');
                    if (this.onError) {
                        this.onError({ code: 'PREMIUM_REQUIRED', message: 'Premium subscription required for voice mode' });
                    }
                } else if (this.state !== 'disconnecting') {
                    this.handleDisconnect();
                }
            };
            this.websocket.onerror = (error) => {
                this.logger.error('WebSocket error:', error);
                reject(new Error('WebSocket connection failed'));
            };
            this.websocket.onmessage = (event) => {
                this.handleServerMessage(event);
            };
        });
    }

    handleDisconnect() {
        this.stopCapture();
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            this.setState('reconnecting');
            this.logger.info(`Reconnecting attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
            const backoffMs = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 10000);
            const jitter = Math.random() * 1000;
            this.reconnectTimeoutId = setTimeout(() => {
                this.connectWebSocket().catch(() => {
                    this.logger.error('Reconnection failed');
                });
            }, backoffMs + jitter);
        } else {
            this.setState('disconnected');
            if (this.onError) {
                this.onError({ code: 'CONNECTION_LOST', message: 'Connection to server lost' });
            }
        }
    }

    handleServerMessage(event) {
        try {
            const message = JSON.parse(event.data);
            if (!message || typeof message.type !== 'string') {
                this.logger.warn('Invalid message format received');
                return;
            }
            this.logger.debug('Received message:', message.type);
            switch (message.type) {
                case 'audio':
                    if (message.data && typeof message.data === 'string') {
                        this.handleAudioResponse(message);
                    } else {
                        this.logger.warn('Invalid audio message: missing data');
                    }
                    break;
                case 'transcription':
                    if (typeof message.text === 'string') {
                        this.handleTranscription(message);
                    } else {
                        this.logger.warn('Invalid transcription message: missing text');
                    }
                    break;
                case 'control':
                    if (typeof message.action === 'string') {
                        this.handleControlMessage(message);
                    } else {
                        this.logger.warn('Invalid control message: missing action');
                    }
                    break;
                case 'error':
                    this.handleErrorMessage(message);
                    break;
                case 'turn_complete':
                    this.handleTurnComplete(message);
                    break;
                default:
                    this.logger.warn('Unknown message type:', message.type);
            }
        } catch (error) {
            this.logger.error('Failed to parse server message:', error);
        }
    }

    handleAudioResponse(message) {
        const { data, sample_rate } = message;
        if (!data) return;
        const validSampleRate = sample_rate === 24000 ? sample_rate : AudioCodec.OUTPUT_SAMPLE_RATE;
        if (sample_rate && sample_rate !== 24000) {
            this.logger.warn(`Unexpected sample rate: ${sample_rate}, using ${validSampleRate}`);
        }
        try {
            const pcm16Bytes = AudioCodec.decodeBase64ToPCM16(data);
            const { samples } = AudioCodec.pcm16ToFloat32(pcm16Bytes, validSampleRate);
            this.queueAudioPlayback(samples, validSampleRate);
            this.setState('playing');
        } catch (error) {
            this.logger.error('Failed to decode audio response:', error);
        }
    }

    handleTranscription(message) {
        const { text, role, is_final } = message;
        this.logger.debug('Transcription:', { text, role, is_final });
        if (this.onTranscription) {
            this.onTranscription({ text, role, isFinal: is_final });
        }
    }

    handleControlMessage(message) {
        const { action } = message;
        this.logger.debug('Control message:', action);
        if (action === 'listening_started') {
            this.setState('listening');
        } else if (action === 'listening_stopped') {
            this.setState('processing');
        }
    }

    handleErrorMessage(message) {
        const { code, message: errorMsg } = message;
        this.logger.error('Server error:', code, errorMsg);
        if (this.onError) {
            this.onError({ code, message: errorMsg });
        }
    }

    handleTurnComplete(message) {
        const { turn_count } = message;
        this.logger.info('Turn complete:', turn_count);
        if (this.onTurnComplete) {
            this.onTurnComplete({ turnCount: turn_count });
        }
    }

    async startCapture() {
        if (!this.isConnected || !this.mediaStream) {
            this.logger.warn('Cannot start capture: not connected or no media stream');
            return false;
        }
        if (this.isCapturing) {
            return true;
        }
        this.setState('recording');
        this.isCapturing = true;
        this.mediaStreamSource = this.audioContext.createMediaStreamSource(this.mediaStream);
        this.workletNode = new AudioWorkletNode(this.audioContext, 'pcm-capture-processor');
        this.workletNode.port.onmessage = (event) => {
            if (event.data.type === 'audio') {
                this.sendAudioChunk(event.data.samples);
                if (this.onAudioLevel && event.data.level !== undefined) {
                    this.onAudioLevel(event.data.level);
                }
            }
        };
        this.workletNode.addEventListener('processorerror', (e) => {
            this.logger.error('AudioWorklet processor error:', e);
            this.setState('error');
            if (this.onError) {
                this.onError({
                    code: 'WORKLET_ERROR',
                    message: 'Audio processing failed. Please reconnect.'
                });
            }
        });
        this.mediaStreamSource.connect(this.workletNode);
        this.workletNode.port.postMessage({ type: 'start' });
        this.sendControlMessage('start_listening');
        this.logger.info('Audio capture started');
        return true;
    }

    stopCapture() {
        if (!this.isCapturing) {
            return;
        }
        this.isCapturing = false;
        if (this.workletNode) {
            this.workletNode.port.postMessage({ type: 'stop' });
            this.workletNode.disconnect();
            this.workletNode = null;
        }
        if (this.mediaStreamSource) {
            this.mediaStreamSource.disconnect();
            this.mediaStreamSource = null;
        }
        this.sendControlMessage('stop_listening');
        this.setState('processing');
        this.logger.info('Audio capture stopped');
    }

    sendAudioChunk(float32Samples) {
        if (!this.isConnected || !this.websocket) {
            return;
        }
        try {
            const pcm16Bytes = AudioCodec.float32ToPCM16(float32Samples);
            const base64Audio = AudioCodec.encodePCM16ToBase64(pcm16Bytes);
            this.websocket.send(JSON.stringify({
                type: 'audio/pcm',
                audio: base64Audio
            }));
        } catch (error) {
            this.logger.error('Failed to send audio chunk:', error);
        }
    }

    sendControlMessage(action) {
        if (!this.isConnected || !this.websocket) {
            return;
        }
        this.websocket.send(JSON.stringify({
            type: 'control',
            action: action
        }));
    }

    queueAudioPlayback(float32Samples, sampleRate) {
        this.playbackQueue.push({ samples: float32Samples, sampleRate });
        if (!this.isPlaying) {
            this.processPlaybackQueue();
        }
    }

    async processPlaybackQueue() {
        if (this.playbackQueue.length === 0) {
            this.isPlaying = false;
            if (this.state === 'playing') {
                this.setState('connected');
            }
            return;
        }
        this.isPlaying = true;
        const { samples, sampleRate } = this.playbackQueue.shift();
        try {
            const ctx = await this.initializePlaybackContext(sampleRate);
            const buffer = AudioCodec.createAudioBuffer(ctx, samples, sampleRate);
            const source = ctx.createBufferSource();
            source.buffer = buffer;
            source.connect(ctx.destination);
            source.onended = () => {
                this.processPlaybackQueue();
            };
            source.start();
        } catch (error) {
            this.logger.error('Failed to play audio:', error);
            this.processPlaybackQueue();
        }
    }

    async disconnect() {
        this.setState('disconnecting');
        if (this.reconnectTimeoutId) {
            clearTimeout(this.reconnectTimeoutId);
            this.reconnectTimeoutId = null;
        }
        this.stopCapture();
        if (this.websocket) {
            this.websocket.close(1000, 'User disconnected');
            this.websocket = null;
        }
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
        if (this.playbackContext) {
            await this.playbackContext.close();
            this.playbackContext = null;
        }
        this.isConnected = false;
        this.playbackQueue = [];
        this.setState('disconnected');
        this.logger.info('Disconnected');
    }

    getState() {
        return this.state;
    }

    isActive() {
        return this.isConnected && (this.isCapturing || this.isPlaying);
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = AudioStreamManager;
}
