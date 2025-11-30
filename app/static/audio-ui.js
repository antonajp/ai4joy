class AudioUIController {
    constructor(audioManager) {
        this.audioManager = audioManager;
        this.isPremium = false;
        this.isVoiceMode = false;
        this.isPushToTalkActive = false;
        this.isPttTransitioning = false;
        this.elements = {};
        this.logger = this.createLogger();
        this.boundKeyDownHandler = this.handleKeyDown.bind(this);
        this.boundKeyUpHandler = this.handleKeyUp.bind(this);
        this.setupCallbacks();
    }

    createLogger() {
        const prefix = '[AudioUI]';
        return {
            info: (...args) => console.log(prefix, ...args),
            warn: (...args) => console.warn(prefix, ...args),
            error: (...args) => console.error(prefix, ...args),
            debug: (...args) => console.debug(prefix, ...args)
        };
    }

    setupCallbacks() {
        this.audioManager.onStateChange = (newState, oldState) => {
            this.handleStateChange(newState, oldState);
        };
        this.audioManager.onTranscription = (data) => {
            this.handleTranscription(data);
        };
        this.audioManager.onError = (error) => {
            this.handleError(error);
        };
        this.audioManager.onAudioLevel = (level) => {
            this.handleAudioLevel(level);
        };
        this.audioManager.onTurnComplete = (data) => {
            this.handleTurnComplete(data);
        };
    }

    handleTurnComplete(data) {
        const { turnCount } = data;
        this.logger.info('Turn complete:', turnCount);
        // Update the turn counter in the UI
        if (typeof updateTurnCounter === 'function') {
            updateTurnCounter(turnCount);
        }
        // Also update AppState if available
        if (typeof AppState !== 'undefined') {
            AppState.currentTurn = turnCount;
        }
    }

    async initialize(isPremium) {
        this.isPremium = isPremium;
        this.isGameSelected = false;  // Voice mode disabled until game is selected
        this.selectedGame = null;
        this.createModeSelector();
        this.createPushToTalkButton();
        this.createMicrophoneModal();
        this.setupKeyboardShortcuts();
        this.logger.info('AudioUI initialized', { isPremium, voiceEnabled: false });
    }

    /**
     * Enable voice mode after game selection is complete.
     * Called by app.js when MC welcome phase completes.
     */
    enableVoiceModeButton(selectedGame) {
        this.isGameSelected = true;
        this.selectedGame = selectedGame;

        if (this.elements.voiceModeBtn && this.isPremium) {
            this.elements.voiceModeBtn.disabled = false;
            this.elements.voiceModeBtn.classList.remove('mode-btn-disabled');
            this.elements.voiceModeBtn.setAttribute('aria-label', 'Voice mode - Ready to start scene');
            this.logger.info('Voice mode button enabled', { game: selectedGame?.name });
        }
    }

    /**
     * Get the selected game for the audio session.
     */
    getSelectedGame() {
        return this.selectedGame;
    }

    createModeSelector() {
        const navActions = document.querySelector('.nav-actions');
        if (!navActions) {
            this.logger.warn('nav-actions not found');
            return;
        }
        const container = document.createElement('div');
        container.className = 'mode-selector-container';
        // Voice mode starts disabled - enabled after game selection
        // Premium users see "Select game first", non-premium see "PRO" badge
        const voiceDisabledReason = this.isPremium ? 'Select a game first' : 'Premium required';
        const voiceBadge = this.isPremium
            ? '<span class="setup-badge" title="Complete setup first">Setup</span>'
            : '<span class="premium-badge" title="Upgrade to Premium">PRO</span>';

        container.innerHTML = `
            <div class="mode-selector" role="group" aria-label="Communication mode">
                <button id="text-mode-btn" class="mode-btn mode-btn-active" aria-pressed="true" aria-label="Text mode (active)">
                    <span class="mode-icon">💬</span>
                    <span class="mode-label">Text</span>
                </button>
                <button id="voice-mode-btn" class="mode-btn mode-btn-disabled"
                        aria-pressed="false"
                        aria-label="Voice mode (${voiceDisabledReason})"
                        disabled>
                    <span class="mode-icon">🎤</span>
                    <span class="mode-label">Voice</span>
                    ${voiceBadge}
                </button>
            </div>
        `;
        navActions.insertBefore(container, navActions.firstChild);
        this.elements.modeSelector = container;
        this.elements.textModeBtn = document.getElementById('text-mode-btn');
        this.elements.voiceModeBtn = document.getElementById('voice-mode-btn');
        this.elements.textModeBtn.addEventListener('click', () => this.setTextMode());
        this.elements.voiceModeBtn.addEventListener('click', () => this.enableVoiceMode());
    }

    createPushToTalkButton() {
        const chatSection = document.querySelector('.chat-section');
        if (!chatSection) {
            this.logger.warn('chat-section not found');
            return;
        }
        const pttContainer = document.createElement('div');
        pttContainer.id = 'ptt-container';
        pttContainer.className = 'ptt-container';
        pttContainer.style.display = 'none';
        pttContainer.innerHTML = `
            <button id="ptt-button" class="ptt-button" aria-label="Push to talk (hold Space or click)">
                <span class="ptt-icon" aria-hidden="true">🎤</span>
                <span class="ptt-status">Hold to speak</span>
            </button>
            <div class="audio-indicator" aria-hidden="true">
                <div class="audio-level-bar"></div>
            </div>
            <div id="voice-status" class="voice-status" role="status" aria-live="polite"></div>
        `;
        const chatForm = chatSection.querySelector('.chat-input-form');
        if (chatForm) {
            chatSection.insertBefore(pttContainer, chatForm);
        } else {
            chatSection.appendChild(pttContainer);
        }
        this.elements.pttContainer = pttContainer;
        this.elements.pttButton = document.getElementById('ptt-button');
        this.elements.pttStatus = this.elements.pttButton.querySelector('.ptt-status');
        this.elements.audioLevelBar = pttContainer.querySelector('.audio-level-bar');
        this.elements.voiceStatus = document.getElementById('voice-status');
        this.elements.pttButton.addEventListener('mousedown', () => this.startPushToTalk());
        this.elements.pttButton.addEventListener('mouseup', () => this.stopPushToTalk());
        this.elements.pttButton.addEventListener('mouseleave', () => {
            if (this.isPushToTalkActive) this.stopPushToTalk();
        });
        this.elements.pttButton.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.startPushToTalk();
        });
        this.elements.pttButton.addEventListener('touchend', (e) => {
            e.preventDefault();
            this.stopPushToTalk();
        });
    }

    createMicrophoneModal() {
        const modal = document.createElement('div');
        modal.id = 'mic-permission-modal';
        modal.className = 'modal';
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-modal', 'true');
        modal.setAttribute('aria-labelledby', 'mic-modal-title');
        modal.style.display = 'none';
        modal.innerHTML = `
            <div class="modal-overlay"></div>
            <div class="modal-content">
                <h2 id="mic-modal-title" class="modal-title">🎤 Enable Voice Mode</h2>
                <p class="modal-text">
                    Voice mode lets you speak with the MC agent in real-time. Your voice is processed
                    securely and not stored after your session ends.
                </p>
                <div class="privacy-notice">
                    <span class="privacy-icon" aria-hidden="true">🔒</span>
                    <span>Audio is streamed securely and deleted after processing</span>
                </div>
                <div class="modal-actions">
                    <button id="mic-cancel-btn" class="btn btn-secondary">Cancel</button>
                    <button id="mic-allow-btn" class="btn btn-primary">Allow Microphone</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        this.elements.micModal = modal;
        this.elements.micModalContent = modal.querySelector('.modal-content');
        this.elements.micCancelBtn = document.getElementById('mic-cancel-btn');
        this.elements.micAllowBtn = document.getElementById('mic-allow-btn');
        this.elements.micCancelBtn.addEventListener('click', () => this.hideMicrophoneModal());
        this.elements.micAllowBtn.addEventListener('click', () => this.requestMicrophoneAndConnect());
        modal.querySelector('.modal-overlay').addEventListener('click', () => this.hideMicrophoneModal());
        this.elements.micModalContent.addEventListener('keydown', (e) => this.handleModalKeydown(e));
    }

    handleModalKeydown(e) {
        if (e.key !== 'Tab') return;
        const focusableElements = this.elements.micModalContent.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusableElements.length === 0) {
            this.logger.warn('No focusable elements in modal');
            return;
        }
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];
        if (e.shiftKey && document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
        } else if (!e.shiftKey && document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
        }
    }

    handleKeyDown(e) {
        if (e.code === 'Space' && this.isVoiceMode && !this.isPushToTalkActive) {
            const activeEl = document.activeElement;
            const isTyping = activeEl.tagName === 'INPUT' ||
                            activeEl.tagName === 'TEXTAREA' ||
                            activeEl.isContentEditable;
            if (!isTyping) {
                e.preventDefault();
                this.startPushToTalk();
            }
        }
        if (e.key === 'Escape' &&
            this.elements.micModal &&
            this.elements.micModal.parentNode &&
            this.elements.micModal.style.display !== 'none') {
            this.hideMicrophoneModal();
        }
    }

    handleKeyUp(e) {
        if (e.code === 'Space' && this.isPushToTalkActive) {
            e.preventDefault();
            this.stopPushToTalk();
        }
    }

    setupKeyboardShortcuts() {
        document.removeEventListener('keydown', this.boundKeyDownHandler);
        document.removeEventListener('keyup', this.boundKeyUpHandler);
        document.addEventListener('keydown', this.boundKeyDownHandler);
        document.addEventListener('keyup', this.boundKeyUpHandler);
    }

    async enableVoiceMode() {
        if (!this.isPremium) {
            this.showUpgradePrompt();
            return;
        }
        if (!this.isGameSelected) {
            this.showGameSelectionPrompt();
            return;
        }
        const permissionState = await this.audioManager.checkMicrophonePermission();
        if (permissionState === 'granted') {
            await this.connectVoiceMode();
        } else if (permissionState === 'denied') {
            this.handleError({
                code: 'MIC_PERMISSION_DENIED',
                message: 'Microphone access was previously denied. Please enable it in your browser settings.'
            });
        } else {
            this.showMicrophoneModal();
        }
    }

    showMicrophoneModal() {
        this.previousActiveElement = document.activeElement;
        this.elements.micModal.style.display = 'flex';
        this.elements.micAllowBtn.focus();
    }

    hideMicrophoneModal() {
        this.elements.micModal.style.display = 'none';
        if (this.previousActiveElement && this.previousActiveElement.focus) {
            this.previousActiveElement.focus();
        }
    }

    async requestMicrophoneAndConnect() {
        this.hideMicrophoneModal();
        this.setVoiceStatus('Requesting microphone access...');
        await this.connectVoiceMode();
    }

    async connectVoiceMode() {
        const sessionId = AppState.currentSession?.session_id;
        if (!sessionId) {
            this.logger.error('No session ID available');
            return;
        }
        const authToken = await this.getAuthToken();
        if (!authToken) {
            this.handleError({
                code: 'AUTH_MISSING',
                message: 'Authentication token not found. Please refresh the page.'
            });
            return;
        }
        this.setVoiceStatus('Connecting...');
        try {
            // Pass selected game to audio manager for context-aware greeting
            const connected = await this.audioManager.connect(sessionId, authToken, this.selectedGame);
            if (connected) {
                this.isVoiceMode = true;
                this.updateModeButtons();
                this.showVoiceModeUI();
                this.setVoiceStatus('Connected - Hold Space or button to speak');
            }
        } catch (error) {
            this.logger.error('Failed to connect voice mode:', error);
            this.handleError({
                code: 'CONNECTION_FAILED',
                message: 'Failed to connect to voice service. Please try again.'
            });
        }
    }

    async getAuthToken() {
        // Fetch a WebSocket auth token from the backend
        // The session cookie is httponly, so we need a dedicated endpoint
        try {
            const response = await fetch('/auth/ws-token', {
                credentials: 'include'
            });
            if (response.ok) {
                const data = await response.json();
                return data.token;
            }
            this.logger.warn('Failed to get WS token:', response.status);
            return null;
        } catch (error) {
            this.logger.error('Error fetching WS token:', error);
            return null;
        }
    }

    setTextMode() {
        if (!this.isVoiceMode) return;
        this.audioManager.disconnect();
        this.isVoiceMode = false;
        this.updateModeButtons();
        this.hideVoiceModeUI();
        this.setVoiceStatus('');
    }

    updateModeButtons() {
        if (this.isVoiceMode) {
            this.elements.textModeBtn.classList.remove('mode-btn-active');
            this.elements.textModeBtn.setAttribute('aria-pressed', 'false');
            this.elements.voiceModeBtn.classList.add('mode-btn-active');
            this.elements.voiceModeBtn.setAttribute('aria-pressed', 'true');
        } else {
            this.elements.textModeBtn.classList.add('mode-btn-active');
            this.elements.textModeBtn.setAttribute('aria-pressed', 'true');
            this.elements.voiceModeBtn.classList.remove('mode-btn-active');
            this.elements.voiceModeBtn.setAttribute('aria-pressed', 'false');
        }
    }

    showVoiceModeUI() {
        if (this.elements.pttContainer) {
            this.elements.pttContainer.style.display = 'flex';
        }
        const chatForm = document.getElementById('chat-form');
        if (chatForm) {
            chatForm.style.display = 'none';
        }
    }

    hideVoiceModeUI() {
        if (this.elements.pttContainer) {
            this.elements.pttContainer.style.display = 'none';
        }
        const chatForm = document.getElementById('chat-form');
        if (chatForm) {
            chatForm.style.display = 'flex';
        }
    }

    async startPushToTalk() {
        const managerState = this.audioManager.getState();
        if (!this.isVoiceMode || this.isPushToTalkActive || this.isPttTransitioning) return;
        if (managerState === 'reconnecting' || managerState === 'connecting') {
            this.logger.warn('Cannot start PTT during', managerState);
            return;
        }
        this.isPttTransitioning = true;
        this.isPushToTalkActive = true;
        this.elements.pttButton.classList.add('ptt-active');
        this.elements.pttStatus.textContent = 'Listening...';
        try {
            const started = await this.audioManager.startCapture();
            if (started) {
                this.announceToScreenReader('Recording started');
            } else {
                this.isPushToTalkActive = false;
                this.elements.pttButton.classList.remove('ptt-active');
                this.elements.pttStatus.textContent = 'Hold to speak';
            }
        } catch (error) {
            this.logger.error('Failed to start capture:', error);
            this.isPushToTalkActive = false;
            this.elements.pttButton.classList.remove('ptt-active');
        } finally {
            this.isPttTransitioning = false;
        }
    }

    stopPushToTalk() {
        if (!this.isPushToTalkActive || this.isPttTransitioning) return;
        const managerState = this.audioManager.getState();
        if (managerState !== 'recording' && managerState !== 'connected' && managerState !== 'listening') {
            this.logger.warn('Stopping PTT during unexpected state:', managerState);
            this.isPushToTalkActive = false;
            this.elements.pttButton.classList.remove('ptt-active');
            this.elements.pttStatus.textContent = 'Hold to speak';
            return;
        }
        this.isPushToTalkActive = false;
        this.elements.pttButton.classList.remove('ptt-active');
        this.elements.pttStatus.textContent = 'Processing...';
        this.audioManager.stopCapture();
        this.announceToScreenReader('Recording stopped, processing');
    }

    handleStateChange(newState, oldState) {
        this.logger.debug('State change:', oldState, '->', newState);
        this.elements.pttButton?.classList.remove('ptt-recording', 'ptt-processing', 'ptt-playing');
        switch (newState) {
            case 'recording':
                this.elements.pttButton?.classList.add('ptt-recording');
                this.setVoiceStatus('Listening...');
                break;
            case 'processing':
                this.elements.pttButton?.classList.add('ptt-processing');
                this.elements.pttStatus.textContent = 'Processing...';
                this.setVoiceStatus('Processing...');
                break;
            case 'playing':
                this.elements.pttButton?.classList.add('ptt-playing');
                this.elements.pttStatus.textContent = 'MC speaking...';
                this.setVoiceStatus('MC is responding...');
                break;
            case 'connected':
                this.elements.pttStatus.textContent = 'Hold to speak';
                this.setVoiceStatus('Ready - Hold Space or button to speak');
                break;
            case 'reconnecting':
                this.setVoiceStatus('Reconnecting...');
                break;
            case 'disconnected':
                if (this.isVoiceMode) {
                    this.setTextMode();
                }
                break;
            case 'error':
                this.elements.pttStatus.textContent = 'Error';
                break;
        }
    }

    handleTranscription(data) {
        const { text, role, isFinal } = data;
        if (!text) return;
        const validRoles = ['user', 'mc', 'assistant'];
        const safeRole = validRoles.includes(role) ? role : 'mc';
        if (isFinal) {
            this.displayTranscriptionMessage(text, safeRole);
        } else {
            this.updateLiveTranscription(text, safeRole);
        }
    }

    displayTranscriptionMessage(text, role) {
        const container = document.getElementById('messages-container');
        if (!container) return;
        const messageDiv = document.createElement('div');
        const isUser = role === 'user';
        messageDiv.className = `message ${isUser ? 'message-user' : 'message-mc'} message-transcribed`;
        const roleLabel = isUser ? 'You (voice)' : '🎤 MC';
        messageDiv.innerHTML = `
            <div class="message-header">
                <span class="message-role">${this.escapeHtml(roleLabel)}</span>
                <span class="message-time">${this.escapeHtml(this.formatTime(new Date()))}</span>
                <span class="transcription-badge" title="Transcribed from audio" aria-label="Voice transcription">🎙️</span>
            </div>
            <div class="message-bubble ${isUser ? '' : 'message-bubble-mc'}">
                <p class="message-text">${this.escapeHtml(text)}</p>
            </div>
        `;
        container.appendChild(messageDiv);
        container.scrollTop = container.scrollHeight;
    }

    updateLiveTranscription(text, role) {
        let liveEl = document.getElementById('live-transcription');
        if (!liveEl) {
            const container = document.getElementById('messages-container');
            if (!container) return;
            liveEl = document.createElement('div');
            liveEl.id = 'live-transcription';
            liveEl.className = 'live-transcription';
            liveEl.setAttribute('aria-live', 'polite');
            container.appendChild(liveEl);
        }
        liveEl.textContent = text;
        liveEl.style.display = text ? 'block' : 'none';
        const container = document.getElementById('messages-container');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }

    handleAudioLevel(level) {
        if (!this.elements.audioLevelBar) return;
        const normalizedLevel = Math.max(0, Math.min(1, level));
        const percentage = Math.min(normalizedLevel * 300, 100);
        this.elements.audioLevelBar.style.width = `${percentage}%`;
    }

    handleError(error) {
        this.logger.error('Audio error:', error);
        let userMessage = error.message;
        switch (error.code) {
            case 'MIC_PERMISSION_DENIED':
                userMessage = 'Microphone access denied. Please allow microphone access in your browser settings.';
                break;
            case 'PREMIUM_REQUIRED':
                this.showUpgradePrompt();
                return;
            case 'AUTH_FAILED':
                userMessage = 'Session expired. Please refresh the page and try again.';
                break;
            case 'CONNECTION_LOST':
                userMessage = 'Connection lost. Please check your internet connection.';
                break;
        }
        if (typeof showToast === 'function') {
            showToast(userMessage, 'error');
        } else {
            alert(userMessage);
        }
    }

    showUpgradePrompt() {
        if (typeof showToast === 'function') {
            showToast('Voice mode is a Premium feature. Upgrade to access real-time audio conversations!', 'info');
        }
    }

    showGameSelectionPrompt() {
        if (typeof showToast === 'function') {
            showToast('Please select a game first before enabling voice mode.', 'info');
        }
    }

    setVoiceStatus(text) {
        if (this.elements.voiceStatus) {
            this.elements.voiceStatus.textContent = text;
        }
    }

    announceToScreenReader(message) {
        const announcement = document.createElement('div');
        announcement.setAttribute('role', 'status');
        announcement.setAttribute('aria-live', 'assertive');
        announcement.className = 'sr-only';
        announcement.textContent = message;
        document.body.appendChild(announcement);
        setTimeout(() => announcement.remove(), 1000);
    }

    formatTime(date) {
        return date.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit'
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    destroy() {
        document.removeEventListener('keydown', this.boundKeyDownHandler);
        document.removeEventListener('keyup', this.boundKeyUpHandler);
        this.audioManager.disconnect();
        if (this.elements.modeSelector) {
            this.elements.modeSelector.remove();
        }
        if (this.elements.pttContainer) {
            this.elements.pttContainer.remove();
        }
        if (this.elements.micModal) {
            this.elements.micModal.remove();
        }
        this.elements = {};
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = AudioUIController;
}
