/**
 * Improv Olympics - Frontend Application
 *
 * This JavaScript file handles:
 * - Firebase Authentication integration (IQS-65)
 * - OAuth authentication flow (legacy)
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

// Firebase Auth Module (imported as ES6 module in HTML)
let firebaseAuth = null;

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
 * Utility functions for safe sessionStorage operations (IQS-66 Issue #2)
 * Handles exceptions in private browsing, disabled cookies, and quota exceeded scenarios
 */
function safeStorageGet(key, defaultValue = null) {
    try {
        return sessionStorage.getItem(key);
    } catch (error) {
        console.warn(`[Storage] Failed to read ${key}:`, error);
        return defaultValue;
    }
}

function safeStorageSet(key, value) {
    try {
        sessionStorage.setItem(key, value);
        return true;
    } catch (error) {
        console.error(`[Storage] Failed to write ${key}:`, error);
        showToast('Unable to save session preferences. Private browsing mode?', 'warning');
        return false;
    }
}

function safeStorageRemove(key) {
    try {
        sessionStorage.removeItem(key);
        return true;
    } catch (error) {
        console.warn(`[Storage] Failed to remove ${key}:`, error);
        return false;
    }
}

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
    safeStorageSet('improv_session_id', sessionId);
}

/**
 * Get session ID from sessionStorage
 */
function getStoredSessionId() {
    return safeStorageGet('improv_session_id');
}

/**
 * Clear stored session ID
 */
function clearStoredSessionId() {
    safeStorageRemove('improv_session_id');
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
 * Initialize authentication state with Firebase
 */
async function initializeAuth() {
    // Initialize Firebase Auth if available
    if (window.FIREBASE_CONFIG && typeof firebase !== 'undefined') {
        try {
            // Wait for firebase-auth.js module to load
            await waitForFirebaseAuthModule();

            // Initialize Firebase Auth with config and WAIT for initial auth state
            // This ensures onAuthStateChanged has fired and verified any existing session
            const firebaseAuthResult = await firebaseAuth.initializeFirebaseAuth(window.FIREBASE_CONFIG);

            console.log('[App] Firebase Auth initialized successfully', firebaseAuthResult);

            // If Firebase says user is authenticated, wait a moment for cookie to be set
            if (firebaseAuthResult && firebaseAuthResult.authenticated) {
                console.log('[App] Firebase user authenticated, waiting for session cookie...');
                // Small delay to ensure cookie is set before checking backend
                await new Promise(resolve => setTimeout(resolve, 100));
            }
        } catch (error) {
            console.error('[App] Firebase Auth initialization failed:', error);
            // Fall back to checking backend auth status
        }
    }

    // Check backend authentication status (session cookie)
    const authData = await checkAuthStatus();
    AppState.isAuthenticated = authData.authenticated;
    AppState.currentUser = authData.user;

    console.log('[App] Auth status from backend:', authData);

    updateAuthUI();
}

/**
 * Wait for Firebase Auth module to load (ES6 module loaded asynchronously)
 */
async function waitForFirebaseAuthModule(timeout = 5000) {
    const startTime = Date.now();

    while (!window.firebaseAuthModule) {
        if (Date.now() - startTime > timeout) {
            throw new Error('Firebase Auth module load timeout');
        }
        await new Promise(resolve => setTimeout(resolve, 100));
    }

    firebaseAuth = window.firebaseAuthModule;
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
 * Handle login button click - show Firebase auth modal
 */
function handleLogin() {
    showModal('auth-modal');
}

/**
 * Handle logout button click - use Firebase signOut
 */
async function handleLogout() {
    try {
        showLoading('Signing out...');
        // Sign out from Firebase
        if (window.firebaseAuthModule) {
            await window.firebaseAuthModule.signOut();
        }
        // Clear backend session
        await fetch(`${AUTH_BASE}/logout`, { credentials: 'include' });
        hideLoading();
        showToast('Signed out successfully', 'success');
        // Reload to update UI
        setTimeout(() => window.location.reload(), 500);
    } catch (error) {
        hideLoading();
        console.error('Logout error:', error);
        window.location.href = `${AUTH_BASE}/logout`;
    }
}

/**
 * Handle Firebase email sign-in form submission
 */
async function handleEmailSignIn(event) {
    event.preventDefault();

    const emailInput = document.getElementById('signin-email');
    const passwordInput = document.getElementById('signin-password');
    const emailErrorDiv = document.getElementById('signin-email-error');
    const passwordErrorDiv = document.getElementById('signin-password-error');

    // Clear previous errors
    if (emailErrorDiv) emailErrorDiv.textContent = '';
    if (passwordErrorDiv) passwordErrorDiv.textContent = '';

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    // Basic validation
    if (!email) {
        if (emailErrorDiv) emailErrorDiv.textContent = 'Email is required';
        return;
    }
    if (!password) {
        if (passwordErrorDiv) passwordErrorDiv.textContent = 'Password is required';
        return;
    }

    try {
        showLoading('Signing in...');

        if (!firebaseAuth) {
            throw new Error('Firebase Auth not initialized');
        }

        const user = await firebaseAuth.signInWithEmail(email, password);

        // Check email verification (AC-AUTH-03)
        if (!user.emailVerified) {
            hideLoading();
            // Show verification notice
            const verificationNotice = document.getElementById('email-verification-notice');
            const verificationEmailDisplay = document.getElementById('verification-email-display');
            if (verificationNotice && verificationEmailDisplay) {
                verificationEmailDisplay.textContent = email;
                document.getElementById('panel-signin').hidden = true;
                verificationNotice.hidden = false;
            } else {
                if (passwordErrorDiv) passwordErrorDiv.textContent = 'Please verify your email address before signing in.';
            }
            await firebaseAuth.signOut();
            return;
        }

        // Verify token with backend and create session (wait for this!)
        showLoading('Verifying session...');
        const idToken = await user.getIdToken();
        const response = await fetch(`${AUTH_BASE}/firebase/token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ id_token: idToken }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Session verification failed');
        }

        hideLoading();
        hideModal('auth-modal');
        showToast('Signed in successfully!', 'success');

        // Reload to update UI (session cookie is now set)
        setTimeout(() => window.location.reload(), 300);

    } catch (error) {
        hideLoading();
        console.error('[App] Email sign-in failed:', error);
        if (passwordErrorDiv) passwordErrorDiv.textContent = error.message;
    }
}

/**
 * Handle Firebase email sign-up form submission
 */
async function handleEmailSignUp(event) {
    event.preventDefault();

    const emailInput = document.getElementById('signup-email');
    const passwordInput = document.getElementById('signup-password');
    const confirmInput = document.getElementById('signup-password-confirm');
    const emailErrorDiv = document.getElementById('signup-email-error');
    const passwordErrorDiv = document.getElementById('signup-password-error');
    const confirmErrorDiv = document.getElementById('signup-confirm-error');

    // Clear previous errors
    if (emailErrorDiv) emailErrorDiv.textContent = '';
    if (passwordErrorDiv) passwordErrorDiv.textContent = '';
    if (confirmErrorDiv) confirmErrorDiv.textContent = '';

    const email = emailInput.value.trim();
    const password = passwordInput.value;
    const confirmPassword = confirmInput ? confirmInput.value : password;

    // Basic validation
    if (!email) {
        if (emailErrorDiv) emailErrorDiv.textContent = 'Email is required';
        return;
    }
    if (!password) {
        if (passwordErrorDiv) passwordErrorDiv.textContent = 'Password is required';
        return;
    }
    if (password.length < 6) {
        if (passwordErrorDiv) passwordErrorDiv.textContent = 'Password must be at least 6 characters';
        return;
    }
    if (password !== confirmPassword) {
        if (confirmErrorDiv) confirmErrorDiv.textContent = 'Passwords do not match';
        return;
    }

    try {
        showLoading('Creating account...');

        if (!firebaseAuth) {
            throw new Error('Firebase Auth not initialized');
        }

        await firebaseAuth.signUpWithEmail(email, password);

        hideLoading();

        // Show verification notice
        const verificationNotice = document.getElementById('email-verification-notice');
        const verificationEmailDisplay = document.getElementById('verification-email-display');
        if (verificationNotice && verificationEmailDisplay) {
            verificationEmailDisplay.textContent = email;
            document.getElementById('panel-signup').hidden = true;
            verificationNotice.hidden = false;
        }

        // Clear form
        emailInput.value = '';
        passwordInput.value = '';
        if (confirmInput) confirmInput.value = '';

        showToast('Account created! Please check your email to verify your address.', 'success');

    } catch (error) {
        hideLoading();
        console.error('[App] Email sign-up failed:', error);
        if (emailErrorDiv) emailErrorDiv.textContent = error.message;
    }
}

/**
 * Handle Google Sign-In
 */
async function handleGoogleSignIn() {
    try {
        showLoading('Signing in with Google...');

        if (!firebaseAuth) {
            throw new Error('Firebase Auth not initialized');
        }

        const user = await firebaseAuth.signInWithGoogle();

        // Verify token with backend and create session (wait for this!)
        showLoading('Verifying session...');
        const idToken = await user.getIdToken();
        const response = await fetch(`${AUTH_BASE}/firebase/token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ id_token: idToken }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Session verification failed');
        }

        hideLoading();
        hideModal('auth-modal');
        showToast('Signed in successfully!', 'success');

        // Reload to update UI (session cookie is now set)
        setTimeout(() => window.location.reload(), 300);

    } catch (error) {
        hideLoading();
        console.error('[App] Google sign-in failed:', error);

        if (error.message.includes('popup')) {
            showToast('Sign-in popup was blocked. Please allow popups for this site.', 'error');
        } else {
            showToast(error.message, 'error');
        }
    }
}

/**
 * Handle resend verification email
 */
async function handleResendVerification() {
    try {
        showLoading('Sending verification email...');

        if (!firebaseAuth) {
            throw new Error('Firebase Auth not initialized');
        }

        await firebaseAuth.sendEmailVerification();
        hideLoading();
        showToast('Verification email sent! Please check your inbox.', 'success');

    } catch (error) {
        hideLoading();
        console.error('[App] Resend verification failed:', error);
        showToast(error.message, 'error');
    }
}

/**
 * Handle forgot password
 */
async function handleForgotPassword() {
    const emailInput = document.getElementById('signin-email');
    const email = emailInput ? emailInput.value.trim() : '';

    if (!email) {
        showToast('Please enter your email address first', 'error');
        return;
    }

    try {
        showLoading('Sending password reset email...');

        if (!firebaseAuth) {
            throw new Error('Firebase Auth not initialized');
        }

        await firebaseAuth.sendPasswordResetEmail(email);
        hideLoading();
        showToast('Password reset email sent! Please check your inbox.', 'success');

    } catch (error) {
        hideLoading();
        console.error('[App] Password reset failed:', error);
        showToast(error.message, 'error');
    }
}

/**
 * Show sign-in form (hide sign-up)
 */
function showSignInForm() {
    // Update panels
    const signinPanel = document.getElementById('panel-signin');
    const signupPanel = document.getElementById('panel-signup');
    if (signinPanel) {
        signinPanel.hidden = false;
    }
    if (signupPanel) {
        signupPanel.hidden = true;
    }

    // Update tabs
    const signinTab = document.getElementById('tab-signin');
    const signupTab = document.getElementById('tab-signup');
    if (signinTab) {
        signinTab.classList.add('auth-tab-active');
        signinTab.setAttribute('aria-selected', 'true');
    }
    if (signupTab) {
        signupTab.classList.remove('auth-tab-active');
        signupTab.setAttribute('aria-selected', 'false');
    }

    // Hide verification notice if shown
    const verificationNotice = document.getElementById('email-verification-notice');
    if (verificationNotice) {
        verificationNotice.hidden = true;
    }
}

/**
 * Show sign-up form (hide sign-in)
 */
function showSignUpForm() {
    // Update panels
    const signinPanel = document.getElementById('panel-signin');
    const signupPanel = document.getElementById('panel-signup');
    if (signinPanel) {
        signinPanel.hidden = true;
    }
    if (signupPanel) {
        signupPanel.hidden = false;
    }

    // Update tabs
    const signinTab = document.getElementById('tab-signin');
    const signupTab = document.getElementById('tab-signup');
    if (signinTab) {
        signinTab.classList.remove('auth-tab-active');
        signinTab.setAttribute('aria-selected', 'false');
    }
    if (signupTab) {
        signupTab.classList.add('auth-tab-active');
        signupTab.setAttribute('aria-selected', 'true');
    }

    // Hide verification notice if shown
    const verificationNotice = document.getElementById('email-verification-notice');
    if (verificationNotice) {
        verificationNotice.hidden = true;
    }
}

// ============================================
// Session Management Functions
// ============================================

/**
 * Handle start session button click - fetch games and show selection
 * IQS-66 FIX #3 & #4: Check for existing mode selection before applying tier defaults
 */
async function handleStartSession() {
    if (!AppState.isAuthenticated) {
        showToast('Please sign in to start a session', 'error');
        return;
    }

    showModal('setup-modal');

    // IQS-66 Issue #4: Check for existing mode selection before applying tier defaults
    const existingMode = safeStorageGet('improv_voice_mode')?.toLowerCase();

    if (existingMode === 'true' || existingMode === 'false') {
        // User has previous selection - restore it
        console.log('[IQS-66] Restoring previous mode selection:', existingMode === 'true' ? 'voice' : 'text');
        await handleModeSelection(existingMode === 'true' ? 'audio' : 'text');
    } else {
        // No previous selection - apply tier-based defaults
        const userTier = AppState.currentUser?.tier || 'free';
        if (userTier === 'premium' || userTier === 'freemium') {
            console.log('[IQS-66] Applying tier-based default: voice mode for', userTier);
            await handleModeSelection('audio');
        } else {
            console.log('[IQS-66] Applying tier-based default: text mode for', userTier);
            await handleModeSelection('text');
        }
    }

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
 * FIX: IQS-66 Issue #3 - Use event delegation instead of inline onclick to prevent XSS
 */
function displayGameSelectionGrid(games) {
    const grid = document.getElementById('game-selection-grid');
    if (!grid) return;

    if (!games || games.length === 0) {
        grid.innerHTML = '<p class="no-games">No games available</p>';
        return;
    }

    // IQS-66 SECURITY FIX: Remove inline onclick handlers, use data-* attributes instead
    // This prevents JavaScript injection even if game data is compromised
    const gameCards = games.map((game, index) => {
        const difficultyClass = `difficulty-${game.difficulty || 'beginner'}`;
        const fullDescription = game.description || '';
        const truncatedDesc = fullDescription.length > 80 ? fullDescription.substring(0, 80) + '...' : fullDescription;

        return `
            <button class="game-card ${difficultyClass}"
                    role="option"
                    aria-selected="false"
                    data-game-id="${escapeHtml(game.id)}"
                    data-game-name="${escapeHtml(game.name)}"
                    data-game-difficulty="${escapeHtml(game.difficulty || 'beginner')}"
                    data-game-index="${index}"
                    data-full-description="${escapeHtml(fullDescription)}"
                    aria-label="Select ${escapeHtml(game.name)} - ${escapeHtml(game.difficulty || 'beginner')} difficulty">
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
 * IQS-66 SECURITY FIX: Read data from data-* attributes instead of function parameters
 */
function handleGameCardKeyboard(event) {
    const cards = Array.from(document.querySelectorAll('.game-card'));
    const currentCard = event.target.closest('.game-card');
    const currentIndex = cards.indexOf(currentCard);

    switch (event.key) {
        case 'Enter':
        case ' ':
            event.preventDefault();
            // Read data from data-* attributes (secure against XSS)
            const gameId = currentCard.dataset.gameId;
            const gameName = currentCard.dataset.gameName;
            const difficulty = currentCard.dataset.gameDifficulty;
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
 * IQS-66: Now includes mode selection (text vs audio)
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
        safeStorageSet('improv_selected_game', JSON.stringify(AppState.selectedGame));

        // Store selected mode in sessionStorage (IQS-66)
        safeStorageSet('improv_voice_mode', AppState.isVoiceMode ? 'true' : 'false');
        console.log(`[App] Session created with mode: ${AppState.isVoiceMode ? 'audio' : 'text'}`);

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

/**
 * Handle mode selection (text vs audio) - IQS-66
 * FIX: IQS-66 Issue #1 - Check permissions BEFORE updating state to prevent race condition
 * FIX: IQS-66 Issue #3 - Apply tier-based defaults on modal initialization
 */
async function handleModeSelection(mode) {
    const textModeBtn = document.getElementById('text-mode-btn');
    const voiceModeBtn = document.getElementById('voice-mode-btn');
    const helperText = document.getElementById('mode-helper-text');
    const micWarning = document.getElementById('mic-permission-warning');

    // Update button states
    if (mode === 'text') {
        // Select text mode
        textModeBtn?.classList.add('mode-btn-active');
        textModeBtn?.setAttribute('aria-checked', 'true');
        voiceModeBtn?.classList.remove('mode-btn-active');
        voiceModeBtn?.setAttribute('aria-checked', 'false');

        // Update helper text
        if (helperText) {
            helperText.textContent = "You'll type your responses and read your partner's replies";
        }

        // Hide microphone warning
        if (micWarning) {
            micWarning.style.display = 'none';
        }

        // Update app state and storage immediately
        AppState.isVoiceMode = false;
        safeStorageSet('improv_voice_mode', 'false');

        // Announce to screen readers
        const announcement = "Text mode selected. You'll type your responses.";
        if (helperText) {
            helperText.setAttribute('aria-live', 'polite');
            helperText.textContent = announcement;
        }

    } else if (mode === 'audio') {
        // IQS-66 SECURITY FIX: Check microphone permissions FIRST before updating state
        // This prevents race condition where state shows voice mode but permissions are denied
        const permissionResult = await checkMicrophonePermissions();

        if (permissionResult.success) {
            // Permissions granted - enable voice mode
            voiceModeBtn?.classList.add('mode-btn-active');
            voiceModeBtn?.setAttribute('aria-checked', 'true');
            textModeBtn?.classList.remove('mode-btn-active');
            textModeBtn?.setAttribute('aria-checked', 'false');

            // Update helper text
            if (helperText) {
                helperText.textContent = "You'll speak and hear responses in real-time using your microphone";
            }

            // Hide microphone warning
            if (micWarning) {
                micWarning.style.display = 'none';
            }

            // Update app state and storage ONLY after successful permission check
            AppState.isVoiceMode = true;
            safeStorageSet('improv_voice_mode', 'true');

            // Announce to screen readers
            const announcement = "Voice mode selected. You'll speak into your microphone.";
            if (helperText) {
                helperText.setAttribute('aria-live', 'polite');
                helperText.textContent = announcement;
            }
        } else {
            // Permissions denied - revert to text mode and show detailed error
            AppState.isVoiceMode = false;
            safeStorageSet('improv_voice_mode', 'false');

            // Revert button states to text mode
            voiceModeBtn?.classList.remove('mode-btn-active');
            voiceModeBtn?.setAttribute('aria-checked', 'false');
            textModeBtn?.classList.add('mode-btn-active');
            textModeBtn?.classList.add('mode-btn-active');
            textModeBtn?.setAttribute('aria-checked', 'true');

            // Update helper text
            if (helperText) {
                helperText.textContent = "You'll type your responses and read your partner's replies";
            }

            // Show detailed error message in warning banner
            if (micWarning) {
                const warningText = micWarning.querySelector('p');
                if (warningText) {
                    warningText.textContent = permissionResult.message;
                }
                micWarning.style.display = 'flex';
            }

            // Announce error to screen readers
            if (helperText) {
                helperText.setAttribute('aria-live', 'assertive');
                helperText.textContent = permissionResult.message;
            }
        }
    }
}

/**
 * Handle keyboard navigation for mode selection - IQS-66
 */
function handleModeKeyboard(event) {
    const textModeBtn = document.getElementById('text-mode-btn');
    const voiceModeBtn = document.getElementById('voice-mode-btn');

    switch (event.key) {
        case 'ArrowLeft':
            event.preventDefault();
            handleModeSelection('text');
            textModeBtn?.focus();
            break;
        case 'ArrowRight':
            event.preventDefault();
            handleModeSelection('audio');
            voiceModeBtn?.focus();
            break;
        case ' ':
        case 'Enter':
            event.preventDefault();
            const mode = event.target.dataset.mode;
            if (mode) {
                handleModeSelection(mode);
            }
            break;
    }
}

/**
 * Check if microphone permissions are available - IQS-66
 * FIX: IQS-66 Issue #2 - Enhanced error handling with detailed user feedback
 * Returns an object with success status and user-friendly error messages
 */
async function checkMicrophonePermissions() {
    try {
        // Check if MediaDevices API is supported
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            console.warn('[App] MediaDevices API not available');
            return {
                success: false,
                error: 'unsupported',
                message: 'Your browser does not support voice mode. Please use a modern browser (Chrome, Firefox, Safari).'
            };
        }

        // Try to get microphone access (this will prompt user if not already granted)
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        // Stop the stream immediately - we just wanted to check permissions
        stream.getTracks().forEach(track => track.stop());

        return { success: true };

    } catch (error) {
        console.warn('[App] Microphone permission issue:', error);

        // Differentiate error types and provide specific user feedback
        if (error.name === 'NotAllowedError') {
            return {
                success: false,
                error: 'permission_denied',
                message: 'Microphone access denied. Please enable microphone permissions in your browser settings.'
            };
        } else if (error.name === 'NotFoundError') {
            return {
                success: false,
                error: 'no_microphone',
                message: 'No microphone found. Please connect a microphone to use voice mode.'
            };
        } else {
            return {
                success: false,
                error: 'unknown',
                message: 'Unable to access microphone. Please try again or use text mode.'
            };
        }
    }
}

// ============================================
// Chat Interface Functions
// ============================================

async function initializeAudioFeatures() {
    if (typeof AudioStreamManager === 'undefined' || typeof AudioUIController === 'undefined') {
        console.warn('[App] Audio modules not loaded');
        return;
    }
    // Voice mode is available for both freemium and premium users
    const hasVoiceAccess = ['premium', 'freemium'].includes(AppState.currentUser?.tier);
    AppState.audioManager = new AudioStreamManager();
    AppState.audioUI = new AudioUIController(AppState.audioManager);
    await AppState.audioUI.initialize(hasVoiceAccess);
    console.log('[App] Audio features initialized', { hasVoiceAccess, tier: AppState.currentUser?.tier });
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

    // IQS-66 Issue #1 & #2: Case-insensitive mode check with safe storage
    const preSelectedMode = safeStorageGet('improv_voice_mode')?.toLowerCase();
    if (preSelectedMode === 'true') {
        console.log('[IQS-66] User pre-selected voice mode, initializing audio');
        AppState.isVoiceMode = true;
    } else if (preSelectedMode === 'false') {
        console.log('[IQS-66] User pre-selected text mode, initializing text interface');
        AppState.isVoiceMode = false;
    } else {
        console.log('[IQS-66] No pre-selected mode, using tier default');
        // Default based on tier if no explicit selection
        const userTier = AppState.currentUser?.tier || 'free';
        AppState.isVoiceMode = (userTier === 'premium' || userTier === 'freemium');
    }

    // Check if we have a pre-selected game from the landing page
    const storedGame = safeStorageGet('improv_selected_game');
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

        // Store session ID in AppState for mode-lock check (IQS-66)
        AppState.sessionId = sessionId;

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
        // IQS-66 CRITICAL FIX: Pass autoActivate=false to prevent override of user's text mode selection
        // Only auto-activate if user explicitly selected voice mode
        if (AppState.selectedGame && AppState.audioUI) {
            const shouldAutoActivate = AppState.isVoiceMode; // Only if user pre-selected voice mode
            AppState.audioUI.enableVoiceModeButton(AppState.selectedGame, shouldAutoActivate);
            updateGameDisplay(AppState.selectedGame.name);
        }

        hideLoading();
        const mcWelcomeStatuses = ['initialized', 'mc_welcome', 'game_select', 'suggestion_phase'];

        // IQS-75 FIX: Skip HTTP MC welcome if voice mode is pre-selected with a game
        // Voice mode handles its own greeting via WebSocket
        const shouldSkipMCWelcome = AppState.isVoiceMode && AppState.selectedGame;

        if (mcWelcomeStatuses.includes(session.status) && !shouldSkipMCWelcome) {
            AppState.mcWelcomeComplete = false;
            console.log(`[App] Session status: ${session.status}, starting MC welcome phase`);

            // Show context message if resuming a session that's past the initial state
            if (session.status !== 'initialized') {
                const gameName = session.selected_game_name || AppState.selectedGame?.name;
                if (gameName) {
                    displaySystemMessage(`📍 Resuming session for "${gameName}"...`);
                }
            }

            await startMCWelcomePhase(sessionId);
        } else if (shouldSkipMCWelcome) {
            // IQS-75: Voice mode with pre-selected game - skip MC welcome, let audio handle it
            console.log('[IQS-75] Voice mode with pre-selected game, skipping HTTP MC welcome');
            AppState.mcWelcomeComplete = true;
            displaySystemMessage(`🎤 Voice mode activated! Starting scene with "${AppState.selectedGame.name}"...`);
        } else {
            AppState.mcWelcomeComplete = true;
            if (session.turn_count === 0) {
                const voiceHint = AppState.currentUser?.tier === 'premium' ? '' : ' Enable Voice Mode (Premium) for real-time audio.';
                displaySystemMessage(`Scene work is ready to begin! Enter your first line to start the improv scene.${voiceHint}`);
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
            // IQS-66: Respect user's pre-selected mode
            if (AppState.audioUI) {
                const shouldAutoActivate = AppState.isVoiceMode;
                AppState.audioUI.enableVoiceModeButton(response.selected_game, shouldAutoActivate);
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
            // Only show voice hint if user is in voice mode, not just because they're premium
            let voiceHintWelcome = '';
            if (AppState.isVoiceMode) {
                voiceHintWelcome = ' Voice Mode is activating...';
            } else if (AppState.currentUser?.tier !== 'premium') {
                voiceHintWelcome = ' Enable Voice Mode (Premium) for real-time audio.';
            }
            displaySystemMessage(`MC welcome complete! The scene is about to begin. Enter your first line when ready.${voiceHintWelcome}`);

            // Enable voice mode button now that game is selected
            // IQS-66: Respect user's pre-selected mode
            if (AppState.audioUI && AppState.selectedGame) {
                const shouldAutoActivate = AppState.isVoiceMode;
                AppState.audioUI.enableVoiceModeButton(AppState.selectedGame, shouldAutoActivate);
            }
        }

        // Auto-continue to get audience suggestion when in awaiting_suggestion phase
        // This happens when game is pre-selected and MC has asked for a suggestion
        if (response.phase === 'awaiting_suggestion' && !response.mc_welcome_complete) {
            console.log('[MC Welcome] Auto-continuing to get audience suggestion...');
            setTimeout(async () => {
                await continueToAudienceSuggestion(sessionId);
            }, 1500);
        }

    } catch (error) {
        hideTypingIndicator();
        showToast(`MC welcome failed: ${error.message}`, 'error');
    }
}

/**
 * Continue the MC welcome flow to get audience suggestion and complete setup.
 * This is called automatically when phase is 'awaiting_suggestion'.
 */
async function continueToAudienceSuggestion(sessionId) {
    try {
        showTypingIndicator();
        const suggestionResponse = await executeMCWelcome(sessionId, null);
        hideTypingIndicator();
        displayMCMessage(suggestionResponse.mc_response, suggestionResponse.timestamp);
        AppState.mcPhase = suggestionResponse.phase;

        if (suggestionResponse.audience_suggestion) {
            AppState.audienceSuggestion = suggestionResponse.audience_suggestion;
        }

        updateMCPhaseDisplay(suggestionResponse.phase);

        // Check if we need to continue to the final step (rules and start)
        if (!suggestionResponse.mc_welcome_complete && suggestionResponse.phase !== 'awaiting_suggestion') {
            console.log('[MC Welcome] Auto-continuing to rules and scene start...');
            setTimeout(async () => {
                await continueToSceneStart(sessionId);
            }, 1500);
        }

        // Check if suggestion phase completed the welcome
        if (suggestionResponse.mc_welcome_complete) {
            AppState.mcWelcomeComplete = true;
            let voiceHint = '';
            if (AppState.isVoiceMode) {
                voiceHint = ' Voice Mode is activating...';
            } else if (AppState.currentUser?.tier !== 'premium') {
                voiceHint = ' Enable Voice Mode (Premium) for real-time audio.';
            }
            displaySystemMessage(`🎭 The stage is set! Enter your first line to begin the scene.${voiceHint}`);

            if (AppState.audioUI && AppState.selectedGame) {
                const shouldAutoActivate = AppState.isVoiceMode;
                AppState.audioUI.enableVoiceModeButton(AppState.selectedGame, shouldAutoActivate);
            }
        }
    } catch (err) {
        hideTypingIndicator();
        console.error('[MC Welcome] Auto-continue to suggestion failed:', err);
        showToast('Failed to get audience suggestion. Please refresh.', 'error');
    }
}

/**
 * Continue to the final scene start phase (rules explanation and transition).
 */
async function continueToSceneStart(sessionId) {
    try {
        showTypingIndicator();
        const finalResponse = await executeMCWelcome(sessionId, null);
        hideTypingIndicator();
        displayMCMessage(finalResponse.mc_response, finalResponse.timestamp);
        AppState.mcPhase = finalResponse.phase;
        updateMCPhaseDisplay(finalResponse.phase);

        if (finalResponse.mc_welcome_complete) {
            AppState.mcWelcomeComplete = true;
            let voiceHint = '';
            if (AppState.isVoiceMode) {
                voiceHint = ' Voice Mode is activating...';
            } else if (AppState.currentUser?.tier !== 'premium') {
                voiceHint = ' Enable Voice Mode (Premium) for real-time audio.';
            }
            displaySystemMessage(`🎭 The stage is set! Enter your first line to begin the scene.${voiceHint}`);

            if (AppState.audioUI && AppState.selectedGame) {
                const shouldAutoActivate = AppState.isVoiceMode;
                AppState.audioUI.enableVoiceModeButton(AppState.selectedGame, shouldAutoActivate);
            }
        }
    } catch (err) {
        hideTypingIndicator();
        console.error('[MC Welcome] Auto-continue to scene start failed:', err);
        showToast('Failed to start scene. Please refresh.', 'error');
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
        // Display user message only if there's actual user input
        if (userInput && userInput.trim()) {
            displayUserMessage(userInput, new Date().toISOString());
        }

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
            // IQS-66: Respect user's pre-selected mode
            if (AppState.audioUI) {
                const shouldAutoActivate = AppState.isVoiceMode;
                AppState.audioUI.enableVoiceModeButton(response.selected_game, shouldAutoActivate);
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
            // Only show voice hint if user is in voice mode, not just because they're premium
            let voiceHintStage = '';
            if (AppState.isVoiceMode) {
                voiceHintStage = ' Voice Mode is activating...';
            } else if (AppState.currentUser?.tier !== 'premium') {
                voiceHintStage = ' Enable Voice Mode (Premium) for real-time audio.';
            }
            displaySystemMessage(`🎭 The stage is set! Enter your first line to begin the scene.${voiceHintStage}`);

            // Enable voice mode button now that game is selected
            // IQS-66: Respect user's pre-selected mode
            if (AppState.audioUI && AppState.selectedGame) {
                const shouldAutoActivate = AppState.isVoiceMode;
                AppState.audioUI.enableVoiceModeButton(AppState.selectedGame, shouldAutoActivate);
            }
        }

        // Auto-continue to get audience suggestion when in awaiting_suggestion phase
        // This allows the MC flow to proceed without requiring user input for the suggestion
        if (response.phase === 'awaiting_suggestion' && !response.mc_welcome_complete) {
            console.log('[MC Welcome] Auto-continuing to get audience suggestion...');
            setTimeout(async () => {
                await continueToAudienceSuggestion(AppState.currentSession.session_id);
            }, 1500);
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
 * IQS-66 Issue #3: Clear ALL session state including mode lock
 */
async function handleConfirmEndSession() {
    try {
        showLoading('Ending scene...');

        if (AppState.currentSession) {
            await closeSession(AppState.currentSession.session_id);
        }

        // IQS-66 Issue #3: Clear ALL session state
        clearStoredSessionId();
        AppState.sessionId = null;  // Clear mode lock
        AppState.currentSession = null;
        AppState.currentTurn = 0;

        // Clear mode selection so user can choose fresh on next session
        safeStorageRemove('improv_voice_mode');
        safeStorageRemove('improv_selected_game');

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
    // IQS-66 SECURITY FIX: Set up event delegation for game card clicks
    // This is more secure than inline onclick handlers and prevents XSS injection
    const gameGrid = document.getElementById('game-selection-grid');
    if (gameGrid) {
        // Click event delegation for game cards
        gameGrid.addEventListener('click', (event) => {
            const gameCard = event.target.closest('.game-card');
            if (gameCard) {
                const gameId = gameCard.dataset.gameId;
                const gameName = gameCard.dataset.gameName;
                const gameDifficulty = gameCard.dataset.gameDifficulty;

                handleGameSelection(gameId, gameName, gameDifficulty);
            }
        });

        // Keyboard event delegation for game cards
        gameGrid.addEventListener('keydown', (event) => {
            const gameCard = event.target.closest('.game-card');
            if (gameCard) {
                handleGameCardKeyboard(event);
            }
        });
    }

    // Auth buttons
    const loginBtn = document.getElementById('login-btn');
    const logoutBtn = document.getElementById('logout-btn');

    if (loginBtn) loginBtn.addEventListener('click', handleLogin);
    if (logoutBtn) logoutBtn.addEventListener('click', handleLogout);

    // Auth modal controls
    const closeAuthModal = document.getElementById('close-auth-modal');
    if (closeAuthModal) {
        closeAuthModal.addEventListener('click', () => hideModal('auth-modal'));
    }

    // Auth form submissions (new IDs from IQS-65 implementation)
    const signinForm = document.getElementById('signin-form');
    const signupForm = document.getElementById('signup-form');

    if (signinForm) {
        signinForm.addEventListener('submit', handleEmailSignIn);
    }

    if (signupForm) {
        signupForm.addEventListener('submit', handleEmailSignUp);
    }

    // Google sign-in/sign-up buttons
    const googleSignInBtn = document.getElementById('google-signin-btn');
    const googleSignUpBtn = document.getElementById('google-signup-btn');

    if (googleSignInBtn) {
        googleSignInBtn.addEventListener('click', handleGoogleSignIn);
    }

    if (googleSignUpBtn) {
        googleSignUpBtn.addEventListener('click', handleGoogleSignIn);
    }

    // Auth tab switching (IQS-65)
    const tabSignin = document.getElementById('tab-signin');
    const tabSignup = document.getElementById('tab-signup');

    if (tabSignin) {
        tabSignin.addEventListener('click', () => {
            showSignInForm();
        });
    }

    if (tabSignup) {
        tabSignup.addEventListener('click', () => {
            showSignUpForm();
        });
    }

    // Resend verification email button
    const resendVerificationBtn = document.getElementById('resend-verification-btn');
    if (resendVerificationBtn) {
        resendVerificationBtn.addEventListener('click', handleResendVerification);
    }

    // Forgot password link
    const forgotPasswordLink = document.getElementById('forgot-password-link');
    if (forgotPasswordLink) {
        forgotPasswordLink.addEventListener('click', handleForgotPassword);
    }

    // Close auth modal on overlay click
    const authModal = document.getElementById('auth-modal');
    if (authModal) {
        authModal.addEventListener('click', (e) => {
            if (e.target === authModal) {
                hideModal('auth-modal');
            }
        });
    }

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

    // Mode selection buttons (IQS-66)
    const textModeBtn = document.getElementById('text-mode-btn');
    const voiceModeBtn = document.getElementById('voice-mode-btn');

    if (textModeBtn) {
        textModeBtn.addEventListener('click', () => handleModeSelection('text'));
        textModeBtn.addEventListener('keydown', handleModeKeyboard);
    }

    if (voiceModeBtn) {
        voiceModeBtn.addEventListener('click', () => handleModeSelection('audio'));
        voiceModeBtn.addEventListener('keydown', handleModeKeyboard);
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
            hideModal('auth-modal');
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
                // Must be cancelable for event.preventDefault() to work in the handler
                chatForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
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

        // Initialize Firebase Auth (IQS-65)
        if (window.FIREBASE_CONFIG && window.firebaseAuthModule) {
            try {
                await window.firebaseAuthModule.initializeFirebaseAuth(window.FIREBASE_CONFIG);
                console.log('[App] Firebase Auth initialized');
            } catch (error) {
                console.error('[App] Firebase init failed:', error);
            }
        }
    }
}

// Run initialization when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}
