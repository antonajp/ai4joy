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
    lastMessageId: null,
    mcWelcomeComplete: false,
    mcPhase: null,
    availableGames: [],
    selectedGame: null,
    audienceSuggestion: null,
    audioManager: null,
    audioUI: null,
    isVoiceMode: false
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
 * Show modal with proper focus management
 */
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        // Store the element that triggered the modal for focus restoration
        modal.dataset.previousFocus = document.activeElement?.id || '';

        modal.style.display = 'flex';

        // For game selection modal, focus first game card after content loads
        // Otherwise focus first focusable element
        if (modalId === 'setup-modal') {
            // Focus will be set after games load in displayGameSelectionGrid
        } else {
            const firstFocusable = modal.querySelector('button, input, textarea, select');
            if (firstFocusable) {
                setTimeout(() => firstFocusable.focus(), 100);
            }
        }

        // Set up focus trap
        setupFocusTrap(modal);
    }
}

/**
 * Hide modal and restore focus to triggering element
 */
function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        const previousFocusId = modal.dataset.previousFocus;
        modal.style.display = 'none';

        // Return focus to triggering element
        if (previousFocusId) {
            const previousElement = document.getElementById(previousFocusId);
            if (previousElement) {
                setTimeout(() => previousElement.focus(), 100);
            }
        }

        // Remove focus trap
        removeFocusTrap(modal);
    }
}

/**
 * Set up focus trap within modal for accessibility
 */
function setupFocusTrap(modal) {
    const handleKeydown = (e) => {
        if (e.key !== 'Tab') return;

        const focusableElements = modal.querySelectorAll(
            'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])'
        );

        if (focusableElements.length === 0) return;

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey && document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
        } else if (!e.shiftKey && document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
        }
    };

    // Handle Escape key to close modal
    const handleEscape = (e) => {
        if (e.key === 'Escape') {
            hideModal(modal.id);
        }
    };

    modal.addEventListener('keydown', handleKeydown);
    modal.addEventListener('keydown', handleEscape);
    modal._focusTrapHandlers = { handleKeydown, handleEscape };
}

/**
 * Remove focus trap from modal
 */
function removeFocusTrap(modal) {
    if (modal._focusTrapHandlers) {
        modal.removeEventListener('keydown', modal._focusTrapHandlers.handleKeydown);
        modal.removeEventListener('keydown', modal._focusTrapHandlers.handleEscape);
        delete modal._focusTrapHandlers;
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
 * Fetch available games from the API
 */
async function fetchAvailableGames() {
    const response = await fetch(`${API_BASE}/games`, {
        credentials: 'include'
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to fetch games');
    }

    const data = await response.json();
    return data.games;
}

/**
 * Create a new session with optional pre-selected game
 */
async function createSession(selectedGame = null) {
    const body = {};
    if (selectedGame) {
        body.selected_game_id = selectedGame.id;
        body.selected_game_name = selectedGame.name;
    }

    const response = await fetch(`${API_BASE}/session/start`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(body)
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

/**
 * Execute MC welcome phase interaction
 */
async function executeMCWelcome(sessionId, userInput = null) {
    const body = userInput ? { user_input: userInput } : {};

    const response = await fetch(`${API_BASE}/session/${sessionId}/welcome`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(body)
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to execute MC welcome phase');
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
 * Handle start session button click - fetch games and show selection
 */
async function handleStartSession() {
    if (!AppState.isAuthenticated) {
        showToast('Please sign in to start a session', 'error');
        return;
    }

    showModal('setup-modal');

    // Show loading state with spinner
    const grid = document.getElementById('game-selection-grid');
    if (grid) {
        grid.innerHTML = `
            <div class="games-loading">
                <div class="spinner" aria-label="Loading games"></div>
                <p>Loading available games...</p>
            </div>
        `;
    }

    // Fetch and display available games
    try {
        const games = await fetchAvailableGames();
        AppState.availableGames = games;
        displayGameSelectionGrid(games);
    } catch (error) {
        console.error('Failed to fetch games:', error);
        // Show error state in the grid itself with retry button
        if (grid) {
            grid.innerHTML = `
                <div class="games-error">
                    <p>Failed to load games. Please try again.</p>
                    <button class="btn btn-secondary btn-small" onclick="retryLoadGames()">
                        Retry
                    </button>
                </div>
            `;
        }
        showToast('Failed to load games. Please try again.', 'error');
    }
}

/**
 * Retry loading games after an error
 */
async function retryLoadGames() {
    const grid = document.getElementById('game-selection-grid');
    if (grid) {
        grid.innerHTML = `
            <div class="games-loading">
                <div class="spinner" aria-label="Loading games"></div>
                <p>Retrying...</p>
            </div>
        `;
    }

    try {
        const games = await fetchAvailableGames();
        AppState.availableGames = games;
        displayGameSelectionGrid(games);
    } catch (error) {
        console.error('Failed to fetch games on retry:', error);
        if (grid) {
            grid.innerHTML = `
                <div class="games-error">
                    <p>Still unable to load games. Please check your connection.</p>
                    <button class="btn btn-secondary btn-small" onclick="retryLoadGames()">
                        Try Again
                    </button>
                </div>
            `;
        }
    }
}

/**
 * Display game selection grid in modal
 */
function displayGameSelectionGrid(games) {
    const grid = document.getElementById('game-selection-grid');
    if (!grid) return;

    if (!games || games.length === 0) {
        grid.innerHTML = '<p class="no-games">No games available</p>';
        return;
    }

    const gameCards = games.map((game, index) => {
        const difficultyClass = `difficulty-${game.difficulty || 'beginner'}`;
        const fullDescription = game.description || '';
        const truncatedDesc = fullDescription.length > 80 ? fullDescription.substring(0, 80) + '...' : fullDescription;

        return `
            <button class="game-card ${difficultyClass}"
                    onclick="handleGameSelection('${escapeHtml(game.id)}', '${escapeHtml(game.name)}', '${escapeHtml(game.difficulty || 'beginner')}')"
                    onkeydown="handleGameCardKeyboard(event, '${escapeHtml(game.id)}', '${escapeHtml(game.name)}', '${escapeHtml(game.difficulty || 'beginner')}')"
                    role="option"
                    aria-selected="false"
                    data-game-id="${escapeHtml(game.id)}"
                    data-game-index="${index}"
                    data-full-description="${escapeHtml(fullDescription)}">
                <span class="game-card-name">${escapeHtml(game.name)}</span>
                <span class="game-card-difficulty">${escapeHtml(game.difficulty || 'Beginner')}</span>
                ${truncatedDesc ? `<span class="game-card-description">${escapeHtml(truncatedDesc)}</span>` : ''}
            </button>
        `;
    }).join('');

    grid.innerHTML = gameCards;

    // Focus the first game card for accessibility
    setTimeout(() => {
        const firstCard = grid.querySelector('.game-card');
        if (firstCard) {
            firstCard.focus();
        }
    }, 100);
}

/**
 * Handle keyboard navigation for game cards
 */
function handleGameCardKeyboard(event, gameId, gameName, difficulty) {
    const cards = Array.from(document.querySelectorAll('.game-card'));
    const currentCard = event.target.closest('.game-card');
    const currentIndex = cards.indexOf(currentCard);

    switch (event.key) {
        case 'Enter':
        case ' ':
            event.preventDefault();
            handleGameSelection(gameId, gameName, difficulty);
            break;
        case 'ArrowDown':
        case 'ArrowRight':
            event.preventDefault();
            const nextIndex = (currentIndex + 1) % cards.length;
            cards[nextIndex].focus();
            break;
        case 'ArrowUp':
        case 'ArrowLeft':
            event.preventDefault();
            const prevIndex = (currentIndex - 1 + cards.length) % cards.length;
            cards[prevIndex].focus();
            break;
        case 'Home':
            event.preventDefault();
            cards[0].focus();
            break;
        case 'End':
            event.preventDefault();
            cards[cards.length - 1].focus();
            break;
    }
}

/**
 * Handle game selection from the grid
 */
function handleGameSelection(gameId, gameName, difficulty) {
    // Update selected state in UI
    const cards = document.querySelectorAll('.game-card');
    cards.forEach(card => {
        card.classList.remove('game-card-selected');
        card.setAttribute('aria-selected', 'false');
    });

    const selectedCard = document.querySelector(`[data-game-id="${gameId}"]`);
    let fullDescription = '';
    if (selectedCard) {
        selectedCard.classList.add('game-card-selected');
        selectedCard.setAttribute('aria-selected', 'true');
        fullDescription = selectedCard.dataset.fullDescription || '';
    }

    // Store selection in AppState
    AppState.selectedGame = { id: gameId, name: gameName, difficulty, description: fullDescription };

    // Update selected game info display with full description
    const infoEl = document.getElementById('selected-game-info');
    const nameEl = document.getElementById('selected-game-name');
    const descEl = document.getElementById('selected-game-description');
    if (infoEl && nameEl) {
        nameEl.textContent = gameName;
        if (descEl && fullDescription) {
            descEl.textContent = fullDescription;
        }
        infoEl.style.display = 'block';
    }

    // Enable the start button
    const startBtn = document.getElementById('create-session-btn');
    if (startBtn) {
        startBtn.disabled = false;
    }

    // Update instruction for screen readers (live region)
    const instruction = document.getElementById('game-selection-instruction');
    if (instruction) {
        instruction.textContent = `${gameName} selected. Click Start Scene to continue.`;
    }

    // Hide the button hint if present
    const hint = document.getElementById('button-hint');
    if (hint) {
        hint.classList.add('hidden');
    }
}

/**
 * Handle session creation with pre-selected game
 */
async function handleCreateSession() {
    if (!AppState.selectedGame) {
        showToast('Please select a game first', 'error');
        return;
    }

    try {
        showLoading('Creating your session...');
        hideModal('setup-modal');

        // Create session with pre-selected game
        const session = await createSession(AppState.selectedGame);
        AppState.currentSession = session;
        AppState.currentTurn = 0;

        storeSessionId(session.session_id);

        // Store selected game in sessionStorage for chat page
        sessionStorage.setItem('improv_selected_game', JSON.stringify(AppState.selectedGame));

        // Redirect to chat interface
        window.location.href = `/static/chat.html?session=${session.session_id}`;
    } catch (error) {
        hideLoading();
        showModal('setup-modal');
        showToast(error.message, 'error');
    }
}

/**
 * Handle session form submission (start new session) - legacy support
 */
async function handleSessionFormSubmit(event) {
    event.preventDefault();
    await handleCreateSession();
}

/**
 * Handle cancel session button
 */
function handleCancelSession() {
    hideModal('setup-modal');
}

// ============================================
// Chat Interface Functions
// ============================================

async function initializeAudioFeatures() {
    if (typeof AudioStreamManager === 'undefined' || typeof AudioUIController === 'undefined') {
        console.warn('[App] Audio modules not loaded');
        return;
    }
    const isPremium = AppState.currentUser?.tier === 'premium';
    AppState.audioManager = new AudioStreamManager();
    AppState.audioUI = new AudioUIController(AppState.audioManager);
    await AppState.audioUI.initialize(isPremium);
    console.log('[App] Audio features initialized', { isPremium });
}

async function initializeChatInterface() {
    await initializeAuth();
    if (!AppState.isAuthenticated) {
        window.location.href = '/';
        return;
    }
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session') || getStoredSessionId();
    if (!sessionId) {
        showToast('No active session found', 'error');
        setTimeout(() => window.location.href = '/', 2000);
        return;
    }

    // Check if we have a pre-selected game from the landing page
    const storedGame = sessionStorage.getItem('improv_selected_game');
    if (storedGame) {
        try {
            AppState.selectedGame = JSON.parse(storedGame);
            console.log('[App] Loaded pre-selected game:', AppState.selectedGame);
        } catch (e) {
            console.warn('[App] Failed to parse stored game:', e);
        }
    }

    try {
        showLoading('Loading your scene...');
        const session = await getSessionInfo(sessionId);
        AppState.currentSession = session;
        AppState.currentTurn = session.turn_count;

        // If session has a game but AppState doesn't, sync from session
        if (session.selected_game_name && !AppState.selectedGame) {
            AppState.selectedGame = {
                id: session.selected_game_id,
                name: session.selected_game_name
            };
        }

        updateSessionInfo(session);
        enableChatInput();
        await initializeAudioFeatures();

        // If game is pre-selected, enable voice mode button immediately for premium users
        if (AppState.selectedGame && AppState.audioUI) {
            AppState.audioUI.enableVoiceModeButton(AppState.selectedGame);
            updateGameDisplay(AppState.selectedGame.name);
        }

        hideLoading();
        const mcWelcomeStatuses = ['initialized', 'mc_welcome', 'game_select', 'suggestion_phase'];
        if (mcWelcomeStatuses.includes(session.status)) {
            AppState.mcWelcomeComplete = false;
            await startMCWelcomePhase(sessionId);
        } else {
            AppState.mcWelcomeComplete = true;
            if (session.turn_count === 0) {
                displaySystemMessage('Scene work is ready to begin! Enter your first line to start the improv scene, or enable Voice Mode for real-time audio.');
            }
        }
    } catch (error) {
        hideLoading();
        showErrorModal(error.message, () => {
            window.location.href = '/';
        });
    }
}

/**
 * Start MC Welcome Phase
 */
async function startMCWelcomePhase(sessionId) {
    try {
        showTypingIndicator();

        // Execute initial MC welcome call (no user input needed for first call)
        const response = await executeMCWelcome(sessionId, null);

        hideTypingIndicator();

        // Display MC message
        displayMCMessage(response.mc_response, response.timestamp);

        // Update state based on response
        AppState.mcPhase = response.phase;
        AppState.mcWelcomeComplete = response.mc_welcome_complete || false;

        if (response.available_games) {
            AppState.availableGames = response.available_games;
            displayGameOptions(response.available_games);
        }

        if (response.selected_game) {
            AppState.selectedGame = response.selected_game;
            updateGameDisplay(response.selected_game.name);

            // Enable voice mode button as soon as game is selected (for premium users)
            // User can switch to voice mode without completing full MC welcome phase
            if (AppState.audioUI) {
                AppState.audioUI.enableVoiceModeButton(response.selected_game);
            }
        }

        if (response.audience_suggestion) {
            AppState.audienceSuggestion = response.audience_suggestion;
        }

        // Update session status display
        updateMCPhaseDisplay(response.phase);

        // If MC welcome is complete, transition to scene work
        if (response.mc_welcome_complete) {
            AppState.mcWelcomeComplete = true;
            displaySystemMessage('MC welcome complete! The scene is about to begin. Enter your first line when ready, or enable Voice Mode.');

            // Enable voice mode button now that game is selected
            if (AppState.audioUI && AppState.selectedGame) {
                AppState.audioUI.enableVoiceModeButton(AppState.selectedGame);
            }
        }

    } catch (error) {
        hideTypingIndicator();
        showToast(`MC welcome failed: ${error.message}`, 'error');
    }
}

/**
 * Handle MC welcome phase user input
 */
async function handleMCWelcomeInput(userInput) {
    if (AppState.isProcessing) return;

    AppState.isProcessing = true;
    disableChatInput();

    try {
        // Display user message
        displayUserMessage(userInput, new Date().toISOString());

        // Show typing indicator
        showTypingIndicator();

        // Execute MC welcome with user input
        const response = await executeMCWelcome(
            AppState.currentSession.session_id,
            userInput
        );

        hideTypingIndicator();

        // Display MC response
        displayMCMessage(response.mc_response, response.timestamp);

        // Update state
        AppState.mcPhase = response.phase;

        if (response.available_games) {
            AppState.availableGames = response.available_games;
            displayGameOptions(response.available_games);
        }

        if (response.selected_game) {
            AppState.selectedGame = response.selected_game;
            updateGameDisplay(response.selected_game.name);
            displaySystemMessage(`Game selected: ${response.selected_game.name}`);

            // Enable voice mode button as soon as game is selected (for premium users)
            // User can switch to voice mode without completing full MC welcome phase
            if (AppState.audioUI) {
                AppState.audioUI.enableVoiceModeButton(response.selected_game);
            }
        }

        if (response.audience_suggestion) {
            AppState.audienceSuggestion = response.audience_suggestion;
        }

        // Update phase display
        updateMCPhaseDisplay(response.phase);

        // Check if MC welcome is complete
        if (response.mc_welcome_complete) {
            AppState.mcWelcomeComplete = true;
            displaySystemMessage('🎭 The stage is set! Enter your first line to begin the scene, or enable Voice Mode for a real-time audio experience.');

            // Enable voice mode button now that game is selected
            if (AppState.audioUI && AppState.selectedGame) {
                AppState.audioUI.enableVoiceModeButton(AppState.selectedGame);
            }
        }

    } catch (error) {
        hideTypingIndicator();
        showToast(`MC response failed: ${error.message}`, 'error');
    } finally {
        AppState.isProcessing = false;
        enableChatInput();
    }
}

/**
 * Display MC message (distinct styling from partner/coach)
 */
function displayMCMessage(text, timestamp) {
    const container = document.getElementById('messages-container');
    if (!container) return;

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-mc';

    messageDiv.innerHTML = `
        <div class="message-header">
            <span class="message-role">🎤 MC</span>
            <span class="message-time">${formatTime(timestamp)}</span>
        </div>
        <div class="message-bubble message-bubble-mc">
            <p class="message-text">${escapeHtml(text)}</p>
        </div>
    `;

    container.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * Display system message (for transitions and instructions)
 */
function displaySystemMessage(text) {
    const container = document.getElementById('messages-container');
    if (!container) return;

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-system';

    messageDiv.innerHTML = `
        <div class="message-bubble message-bubble-system">
            <p class="message-text">${escapeHtml(text)}</p>
        </div>
    `;

    container.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * Display game options for selection
 */
function displayGameOptions(games) {
    const container = document.getElementById('messages-container');
    if (!container || !games || games.length === 0) return;

    const optionsDiv = document.createElement('div');
    optionsDiv.className = 'game-options';
    optionsDiv.setAttribute('role', 'group');
    optionsDiv.setAttribute('aria-label', 'Available improv games');

    let optionsHtml = '<div class="game-options-header">Available Games:</div>';
    optionsHtml += '<div class="game-options-list">';

    games.forEach(game => {
        const difficultyClass = `difficulty-${game.difficulty || 'beginner'}`;
        optionsHtml += `
            <button class="game-option-btn ${difficultyClass}"
                    onclick="selectGame('${escapeHtml(game.id)}', '${escapeHtml(game.name)}')"
                    aria-label="Select ${escapeHtml(game.name)} - ${game.difficulty || 'beginner'} difficulty">
                <span class="game-name">${escapeHtml(game.name)}</span>
                <span class="game-difficulty">${game.difficulty || 'Beginner'}</span>
            </button>
        `;
    });

    optionsHtml += '</div>';
    optionsDiv.innerHTML = optionsHtml;

    container.appendChild(optionsDiv);
    scrollToBottom();
}

/**
 * Handle game selection button click
 */
function selectGame(gameId, gameName) {
    // Remove game options from UI
    const gameOptions = document.querySelectorAll('.game-options');
    gameOptions.forEach(el => el.remove());

    // Send game selection as user input
    handleMCWelcomeInput(`I'd like to play ${gameName}`);
}

/**
 * Update MC phase display
 */
function updateMCPhaseDisplay(phase) {
    const phaseEl = document.getElementById('current-phase');
    if (!phaseEl) return;

    const phaseLabels = {
        'welcome': 'MC Welcome',
        'game_selection': 'Game Selection',
        'awaiting_suggestion': 'Awaiting Suggestion',
        'suggestion_received': 'Setting the Scene',
        'scene_start': 'Scene Starting'
    };

    phaseEl.textContent = phaseLabels[phase] || phase || 'MC Welcome';
}

/**
 * Execute first turn to get MC introduction (legacy - kept for compatibility)
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
    const statusEl = document.getElementById('session-status');
    const turnEl = document.getElementById('turn-counter');

    if (statusEl) statusEl.textContent = session.status;
    if (turnEl) turnEl.textContent = session.turn_count;
}

/**
 * Update game display in sidebar
 */
function updateGameDisplay(gameName) {
    const gameEl = document.getElementById('session-game');
    if (gameEl) gameEl.textContent = gameName || 'Not selected';
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

    // Clear input early
    input.value = '';
    updateCharacterCount();

    // Route to MC welcome or scene turn based on state
    if (!AppState.mcWelcomeComplete) {
        // Still in MC welcome phase
        await handleMCWelcomeInput(userInput);
        return;
    }

    // Scene work - execute turn
    AppState.isProcessing = true;
    disableChatInput();

    try {
        // Display user message
        displayUserMessage(userInput, new Date().toISOString());

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
 * Display room vibe message and update mood visualization
 */
function displayRoomMessage(roomVibe, timestamp) {
    const container = document.getElementById('messages-container');
    if (!container) return;

    // Extract vibe text from room_vibe object
    const vibeText = typeof roomVibe === 'string'
        ? roomVibe
        : roomVibe.analysis || roomVibe.vibe || JSON.stringify(roomVibe);

    // Update mood visualization if mood_metrics are present
    if (roomVibe && roomVibe.mood_metrics && typeof moodVisualizer !== 'undefined') {
        moodVisualizer.update(roomVibe.mood_metrics);
    }

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

    // Create session button (in game selection modal)
    const createSessionBtn = document.getElementById('create-session-btn');
    if (createSessionBtn) {
        createSessionBtn.addEventListener('click', handleCreateSession);
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
