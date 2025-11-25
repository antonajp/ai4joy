/**
 * Improv Olympics - Frontend Application
 *
 * This JavaScript file handles:
 * - OAuth authentication flow
 * - Session creation and management
 * - Real-time message updates
 * - Error handling and retry logic
 * - Accessibility features
 */

// ============================================
// Constants and Configuration
// ============================================

const API_BASE = '/api/v1';
const AUTH_BASE = '/auth';
const POLLING_INTERVAL = 2000; // 2 seconds
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000;

// ============================================
// State Management
// ============================================

const AppState = {
    isAuthenticated: false,
    currentUser: null,
    currentSession: null,
    currentTurn: 0,
    pollingInterval: null,
    isProcessing: false,
    lastMessageId: null
};

// ============================================
// Utility Functions
// ============================================

/**
 * Show loading overlay with custom message
 */
function showLoading(message = 'Loading...') {
    const overlay = document.getElementById('loading-overlay');
    const messageEl = document.getElementById('loading-message');
    if (overlay && messageEl) {
        messageEl.textContent = message;
        overlay.style.display = 'flex';
    }
}

/**
 * Hide loading overlay
 */
function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');

    const messageEl = document.createElement('div');
    messageEl.className = 'toast-message';
    messageEl.textContent = message;

    toast.appendChild(messageEl);
    container.appendChild(toast);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

/**
 * Show modal
 */
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        // Set focus to first focusable element in modal
        const firstFocusable = modal.querySelector('button, input, textarea, select');
        if (firstFocusable) {
            setTimeout(() => firstFocusable.focus(), 100);
        }
    }
}

/**
 * Hide modal
 */
function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Format timestamp for display
 */
function formatTime(date) {
    return new Date(date).toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit'
    });
}

/**
 * Store session ID in sessionStorage
 */
function storeSessionId(sessionId) {
    sessionStorage.setItem('improv_session_id', sessionId);
}

/**
 * Get session ID from sessionStorage
 */
function getStoredSessionId() {
    return sessionStorage.getItem('improv_session_id');
}

/**
 * Clear stored session ID
 */
function clearStoredSessionId() {
    sessionStorage.removeItem('improv_session_id');
}

// ============================================
// API Functions
// ============================================

/**
 * Check authentication status
 */
async function checkAuthStatus() {
    try {
        const response = await fetch(`${AUTH_BASE}/user`, {
            credentials: 'include'
        });

        if (response.ok) {
            const data = await response.json();
            return data;
        }
        return { authenticated: false, user: null };
    } catch (error) {
        console.error('Auth check failed:', error);
        return { authenticated: false, user: null };
    }
}

/**
 * Create a new session
 */
async function createSession(location) {
    const response = await fetch(`${API_BASE}/session/start`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({ location })
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create session');
    }

    return await response.json();
}

/**
 * Get session information
 */
async function getSessionInfo(sessionId) {
    const response = await fetch(`${API_BASE}/session/${sessionId}`, {
        credentials: 'include'
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to get session');
    }

    return await response.json();
}

/**
 * Execute a turn
 */
async function executeTurn(sessionId, userInput, turnNumber) {
    const response = await fetch(`${API_BASE}/session/${sessionId}/turn`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
            user_input: userInput,
            turn_number: turnNumber
        })
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to execute turn');
    }

    return await response.json();
}

/**
 * Close a session
 */
async function closeSession(sessionId) {
    const response = await fetch(`${API_BASE}/session/${sessionId}/close`, {
        method: 'POST',
        credentials: 'include'
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to close session');
    }

    return await response.json();
}

/**
 * Get user rate limits
 */
async function getUserLimits() {
    const response = await fetch(`${API_BASE}/user/limits`, {
        credentials: 'include'
    });

    if (!response.ok) {
        return null;
    }

    return await response.json();
}

// ============================================
// Authentication Functions
// ============================================

/**
 * Initialize authentication state
 */
async function initializeAuth() {
    const authData = await checkAuthStatus();
    AppState.isAuthenticated = authData.authenticated;
    AppState.currentUser = authData.user;

    updateAuthUI();
}

/**
 * Update UI based on authentication state
 */
function updateAuthUI() {
    const loginBtn = document.getElementById('login-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const startSessionBtn = document.getElementById('start-session-btn');
    const authNotice = document.getElementById('auth-notice');

    if (AppState.isAuthenticated) {
        if (loginBtn) loginBtn.style.display = 'none';
        if (logoutBtn) logoutBtn.style.display = 'inline-flex';
        if (startSessionBtn) startSessionBtn.disabled = false;
        if (authNotice) authNotice.textContent = 'Ready to start your improv journey';
    } else {
        if (loginBtn) loginBtn.style.display = 'inline-flex';
        if (logoutBtn) logoutBtn.style.display = 'none';
        if (startSessionBtn) startSessionBtn.disabled = true;
        if (authNotice) authNotice.textContent = 'Sign in to start your improv session';
    }
}

/**
 * Handle login button click
 */
function handleLogin() {
    // Redirect to OAuth login endpoint
    window.location.href = `${AUTH_BASE}/login?next=${encodeURIComponent(window.location.pathname)}`;
}

/**
 * Handle logout button click
 */
function handleLogout() {
    // Redirect to logout endpoint
    window.location.href = `${AUTH_BASE}/logout`;
}

// ============================================
// Session Management Functions
// ============================================

/**
 * Handle start session button click
 */
function handleStartSession() {
    if (!AppState.isAuthenticated) {
        showToast('Please sign in to start a session', 'error');
        return;
    }
    showModal('setup-modal');
}

/**
 * Handle session form submission
 */
async function handleSessionFormSubmit(event) {
    event.preventDefault();

    const locationInput = document.getElementById('location-input');
    const location = locationInput.value.trim();

    if (!location) {
        showToast('Please enter a location', 'error');
        return;
    }

    try {
        showLoading('Creating your scene...');
        hideModal('setup-modal');

        const session = await createSession(location);
        AppState.currentSession = session;
        AppState.currentTurn = 0;

        storeSessionId(session.session_id);

        // Redirect to chat interface
        window.location.href = `/static/chat.html?session=${session.session_id}`;
    } catch (error) {
        hideLoading();
        showModal('setup-modal');
        showToast(error.message, 'error');
    }
}

/**
 * Handle cancel session button
 */
function handleCancelSession() {
    hideModal('setup-modal');
    const locationInput = document.getElementById('location-input');
    if (locationInput) locationInput.value = '';
}

// ============================================
// Chat Interface Functions
// ============================================

/**
 * Initialize chat interface
 */
async function initializeChatInterface() {
    // Check authentication first
    await initializeAuth();

    if (!AppState.isAuthenticated) {
        window.location.href = '/';
        return;
    }

    // Get session ID from URL or storage
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session') || getStoredSessionId();

    if (!sessionId) {
        showToast('No active session found', 'error');
        setTimeout(() => window.location.href = '/', 2000);
        return;
    }

    try {
        showLoading('Loading your scene...');

        // Load session info
        const session = await getSessionInfo(sessionId);
        AppState.currentSession = session;
        AppState.currentTurn = session.turn_count;

        // Update UI
        updateSessionInfo(session);

        // Enable input
        enableChatInput();

        hideLoading();

        // If this is the first turn, execute it to get MC introduction
        if (session.turn_count === 0) {
            await executeFirstTurn(sessionId);
        }

    } catch (error) {
        hideLoading();
        showErrorModal(error.message, () => {
            window.location.href = '/';
        });
    }
}

/**
 * Execute first turn to get MC introduction
 */
async function executeFirstTurn(sessionId) {
    try {
        showTypingIndicator();

        const response = await executeTurn(sessionId, "Hello", 1);

        hideTypingIndicator();

        // Display messages
        displayPartnerMessage(response.partner_response, response.timestamp);
        displayRoomMessage(response.room_vibe, response.timestamp);

        AppState.currentTurn = response.turn_number;
        updateTurnCounter(response.turn_number);
        updatePhaseDisplay(response.current_phase);

    } catch (error) {
        hideTypingIndicator();
        showToast(`Failed to start scene: ${error.message}`, 'error');
    }
}

/**
 * Update session info panel
 */
function updateSessionInfo(session) {
    const locationEl = document.getElementById('session-location');
    const statusEl = document.getElementById('session-status');
    const turnEl = document.getElementById('turn-counter');

    if (locationEl) locationEl.textContent = session.location;
    if (statusEl) statusEl.textContent = session.status;
    if (turnEl) turnEl.textContent = session.turn_count;
}

/**
 * Update turn counter
 */
function updateTurnCounter(turn) {
    const turnEl = document.getElementById('turn-counter');
    if (turnEl) turnEl.textContent = turn;
}

/**
 * Update phase display
 */
function updatePhaseDisplay(phase) {
    const phaseEl = document.getElementById('current-phase');
    if (phaseEl) phaseEl.textContent = phase;
}

/**
 * Enable chat input
 */
function enableChatInput() {
    const input = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');

    if (input) {
        input.disabled = false;
        input.focus();
    }
    if (sendBtn) sendBtn.disabled = false;
}

/**
 * Disable chat input
 */
function disableChatInput() {
    const input = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');

    if (input) input.disabled = true;
    if (sendBtn) sendBtn.disabled = true;
}

/**
 * Handle chat form submission
 */
async function handleChatFormSubmit(event) {
    event.preventDefault();

    if (AppState.isProcessing) return;

    const input = document.getElementById('user-input');
    const userInput = input.value.trim();

    if (!userInput) {
        showToast('Please enter a response', 'error');
        return;
    }

    AppState.isProcessing = true;
    disableChatInput();

    try {
        // Display user message
        displayUserMessage(userInput, new Date().toISOString());

        // Clear input
        input.value = '';
        updateCharacterCount();

        // Show typing indicator
        showTypingIndicator();

        // Execute turn
        const nextTurn = AppState.currentTurn + 1;
        const response = await executeTurn(
            AppState.currentSession.session_id,
            userInput,
            nextTurn
        );

        // Hide typing indicator
        hideTypingIndicator();

        // Display responses
        displayPartnerMessage(response.partner_response, response.timestamp);
        displayRoomMessage(response.room_vibe, response.timestamp);

        if (response.coach_feedback) {
            displayCoachMessage(response.coach_feedback, response.timestamp);
        }

        // Update state
        AppState.currentTurn = response.turn_number;
        updateTurnCounter(response.turn_number);
        updatePhaseDisplay(response.current_phase);

    } catch (error) {
        hideTypingIndicator();
        showErrorModal(error.message, () => {
            // Retry option
            handleChatFormSubmit(event);
        });
    } finally {
        AppState.isProcessing = false;
        enableChatInput();
    }
}

/**
 * Display user message
 */
function displayUserMessage(text, timestamp) {
    const container = document.getElementById('messages-container');
    if (!container) return;

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-user';

    messageDiv.innerHTML = `
        <div class="message-header">
            <span class="message-role">You</span>
            <span class="message-time">${formatTime(timestamp)}</span>
        </div>
        <div class="message-bubble">
            <p class="message-text">${escapeHtml(text)}</p>
        </div>
    `;

    container.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * Display partner message
 */
function displayPartnerMessage(text, timestamp) {
    const container = document.getElementById('messages-container');
    if (!container) return;

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-partner';

    messageDiv.innerHTML = `
        <div class="message-header">
            <span class="message-role">Scene Partner</span>
            <span class="message-time">${formatTime(timestamp)}</span>
        </div>
        <div class="message-bubble">
            <p class="message-text">${escapeHtml(text)}</p>
        </div>
    `;

    container.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * Display room vibe message
 */
function displayRoomMessage(roomVibe, timestamp) {
    const container = document.getElementById('messages-container');
    if (!container) return;

    // Extract vibe text from room_vibe object
    const vibeText = typeof roomVibe === 'string'
        ? roomVibe
        : roomVibe.vibe || JSON.stringify(roomVibe);

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-room';

    messageDiv.innerHTML = `
        <div class="message-header">
            <span class="message-role">Audience Vibe</span>
            <span class="message-time">${formatTime(timestamp)}</span>
        </div>
        <div class="message-bubble">
            <p class="message-text">${escapeHtml(vibeText)}</p>
        </div>
    `;

    container.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * Display coach feedback message
 */
function displayCoachMessage(text, timestamp) {
    const container = document.getElementById('messages-container');
    if (!container) return;

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-coach';

    messageDiv.innerHTML = `
        <div class="message-header">
            <span class="message-role">Coach</span>
            <span class="message-time">${formatTime(timestamp)}</span>
        </div>
        <div class="message-bubble">
            <p class="message-text">${escapeHtml(text)}</p>
        </div>
    `;

    container.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * Show typing indicator
 */
function showTypingIndicator() {
    const indicator = document.getElementById('partner-typing');
    if (indicator) indicator.style.display = 'flex';
}

/**
 * Hide typing indicator
 */
function hideTypingIndicator() {
    const indicator = document.getElementById('partner-typing');
    if (indicator) indicator.style.display = 'none';
}

/**
 * Scroll messages to bottom
 */
function scrollToBottom() {
    const container = document.getElementById('messages-container');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

/**
 * Update character count
 */
function updateCharacterCount() {
    const input = document.getElementById('user-input');
    const counter = document.getElementById('char-count');

    if (input && counter) {
        const count = input.value.length;
        counter.textContent = `${count} / 1000`;

        if (count > 900) {
            counter.style.color = 'var(--danger)';
        } else {
            counter.style.color = 'var(--text-light)';
        }
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// Error Handling
// ============================================

/**
 * Show error modal with retry option
 */
function showErrorModal(message, onRetry = null) {
    const modal = document.getElementById('error-modal');
    const messageEl = document.getElementById('error-message');
    const retryBtn = document.getElementById('retry-btn');
    const exitBtn = document.getElementById('exit-scene-btn');

    if (messageEl) messageEl.textContent = message;

    if (retryBtn) {
        retryBtn.onclick = () => {
            hideModal('error-modal');
            if (onRetry) onRetry();
        };
    }

    if (exitBtn) {
        exitBtn.onclick = handleExitScene;
    }

    showModal('error-modal');
}

/**
 * Handle exit scene
 */
function handleExitScene() {
    hideModal('error-modal');
    window.location.href = '/';
}

// ============================================
// Session End Handling
// ============================================

/**
 * Handle end session button click
 */
function handleEndSessionClick() {
    showModal('end-modal');
}

/**
 * Handle confirm end session
 */
async function handleConfirmEndSession() {
    try {
        showLoading('Ending scene...');

        if (AppState.currentSession) {
            await closeSession(AppState.currentSession.session_id);
        }

        clearStoredSessionId();
        hideLoading();

        showToast('Scene ended successfully', 'success');
        setTimeout(() => window.location.href = '/', 1000);

    } catch (error) {
        hideLoading();
        showToast('Failed to end scene properly', 'error');
        // Still redirect even if close fails
        setTimeout(() => window.location.href = '/', 1000);
    }
}

/**
 * Handle cancel end session
 */
function handleCancelEndSession() {
    hideModal('end-modal');
}

// ============================================
// Event Listeners Setup
// ============================================

/**
 * Setup event listeners for landing page
 */
function setupLandingPageListeners() {
    // Auth buttons
    const loginBtn = document.getElementById('login-btn');
    const logoutBtn = document.getElementById('logout-btn');

    if (loginBtn) loginBtn.addEventListener('click', handleLogin);
    if (logoutBtn) logoutBtn.addEventListener('click', handleLogout);

    // Start session
    const startSessionBtn = document.getElementById('start-session-btn');
    if (startSessionBtn) {
        startSessionBtn.addEventListener('click', handleStartSession);
    }

    // Session form
    const sessionForm = document.getElementById('session-form');
    if (sessionForm) {
        sessionForm.addEventListener('submit', handleSessionFormSubmit);
    }

    // Modal controls
    const closeModalBtn = document.getElementById('close-modal');
    const cancelSessionBtn = document.getElementById('cancel-session');

    if (closeModalBtn) closeModalBtn.addEventListener('click', handleCancelSession);
    if (cancelSessionBtn) cancelSessionBtn.addEventListener('click', handleCancelSession);

    // Close modal on overlay click
    const setupModal = document.getElementById('setup-modal');
    if (setupModal) {
        setupModal.addEventListener('click', (e) => {
            if (e.target === setupModal) {
                handleCancelSession();
            }
        });
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Escape key closes modals
        if (e.key === 'Escape') {
            hideModal('setup-modal');
        }
    });
}

/**
 * Setup event listeners for chat page
 */
function setupChatPageListeners() {
    // Chat form
    const chatForm = document.getElementById('chat-form');
    if (chatForm) {
        chatForm.addEventListener('submit', handleChatFormSubmit);
    }

    // Character count
    const userInput = document.getElementById('user-input');
    if (userInput) {
        userInput.addEventListener('input', updateCharacterCount);

        // Handle Enter key (submit) vs Shift+Enter (new line)
        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
    }

    // End session
    const endSessionBtn = document.getElementById('end-session-btn');
    if (endSessionBtn) {
        endSessionBtn.addEventListener('click', handleEndSessionClick);
    }

    const confirmEndBtn = document.getElementById('confirm-end-btn');
    const cancelEndBtn = document.getElementById('cancel-end-btn');

    if (confirmEndBtn) confirmEndBtn.addEventListener('click', handleConfirmEndSession);
    if (cancelEndBtn) cancelEndBtn.addEventListener('click', handleCancelEndSession);

    // Close modal on overlay click
    const endModal = document.getElementById('end-modal');
    if (endModal) {
        endModal.addEventListener('click', (e) => {
            if (e.target === endModal) {
                handleCancelEndSession();
            }
        });
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            hideModal('end-modal');
            hideModal('error-modal');
        }
    });

    // Warn on page unload if session is active
    window.addEventListener('beforeunload', (e) => {
        if (AppState.currentSession && AppState.currentTurn > 0) {
            e.preventDefault();
            e.returnValue = 'You have an active scene. Are you sure you want to leave?';
        }
    });
}

// ============================================
// Initialization
// ============================================

/**
 * Initialize application
 */
async function initializeApp() {
    // Determine which page we're on
    const isChat = window.location.pathname.includes('chat.html');

    if (isChat) {
        setupChatPageListeners();
        // Chat interface initialization happens separately
    } else {
        setupLandingPageListeners();
        await initializeAuth();
    }
}

// Run initialization when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}
