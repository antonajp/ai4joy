/**
 * Firebase Authentication Module (IQS-65 Phase 1)
 *
 * This module provides Firebase Authentication integration for the Improv Olympics frontend.
 *
 * Features:
 * - Email/password authentication (AC-AUTH-01)
 * - Google Sign-In via Firebase (AC-AUTH-02)
 * - Email verification enforcement (AC-AUTH-03)
 * - Firebase ID token verification with backend (AC-AUTH-04)
 * - Automatic token refresh before expiration
 * - Session cookie management
 *
 * Usage:
 *   import { initializeFirebaseAuth, signInWithGoogle, signInWithEmail, signUpWithEmail } from './firebase-auth.js';
 *   await initializeFirebaseAuth(firebaseConfig);
 */

// Firebase SDK imports (loaded from CDN in HTML)
// Assumes firebase-app and firebase-auth are loaded globally

const AUTH_BASE = '/auth';
const TOKEN_REFRESH_INTERVAL = 50 * 60 * 1000; // 50 minutes (tokens expire at 60 minutes)

/**
 * Firebase Auth state
 */
const FirebaseAuthState = {
    auth: null,
    currentUser: null,
    tokenRefreshInterval: null,
    initialized: false,
};

/**
 * Initialize Firebase Authentication
 *
 * @param {Object} firebaseConfig - Firebase configuration object
 * @returns {Promise<void>}
 */
export async function initializeFirebaseAuth(firebaseConfig) {
    if (FirebaseAuthState.initialized) {
        console.log('[Firebase Auth] Already initialized');
        return;
    }

    try {
        // Initialize Firebase app
        const app = firebase.initializeApp(firebaseConfig);

        // Initialize Firebase Auth
        FirebaseAuthState.auth = firebase.auth();

        // Set up auth state observer
        FirebaseAuthState.auth.onAuthStateChanged(async (user) => {
            await handleAuthStateChanged(user);
        });

        FirebaseAuthState.initialized = true;
        console.log('[Firebase Auth] Initialized successfully');
    } catch (error) {
        console.error('[Firebase Auth] Initialization failed:', error);
        throw new Error(`Firebase initialization failed: ${error.message}`);
    }
}

/**
 * Handle Firebase auth state changes
 *
 * @param {firebase.User|null} user - Firebase user object
 */
async function handleAuthStateChanged(user) {
    if (user) {
        FirebaseAuthState.currentUser = user;

        console.log('[Firebase Auth] User signed in:', {
            uid: user.uid,
            email: user.email,
            emailVerified: user.emailVerified,
        });

        // Check email verification (AC-AUTH-03)
        if (!user.emailVerified) {
            console.warn('[Firebase Auth] Email not verified');
            // Don't create session if email is not verified
            // Backend will also enforce this
            return;
        }

        // Get Firebase ID token and verify with backend
        try {
            const idToken = await user.getIdToken();
            await verifyTokenWithBackend(idToken);

            // Set up automatic token refresh
            setupTokenRefresh();
        } catch (error) {
            console.error('[Firebase Auth] Token verification failed:', error);
            // Sign out on verification failure
            await signOut();
        }
    } else {
        FirebaseAuthState.currentUser = null;
        console.log('[Firebase Auth] User signed out');

        // Clear token refresh interval
        if (FirebaseAuthState.tokenRefreshInterval) {
            clearInterval(FirebaseAuthState.tokenRefreshInterval);
            FirebaseAuthState.tokenRefreshInterval = null;
        }
    }
}

/**
 * Verify Firebase ID token with backend (AC-AUTH-04)
 *
 * @param {string} idToken - Firebase ID token
 * @returns {Promise<Object>} User data from backend
 */
async function verifyTokenWithBackend(idToken) {
    try {
        const response = await fetch(`${AUTH_BASE}/firebase/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include', // Include cookies
            body: JSON.stringify({ id_token: idToken }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Token verification failed');
        }

        const data = await response.json();
        console.log('[Firebase Auth] Token verified successfully:', data.user);

        return data.user;
    } catch (error) {
        console.error('[Firebase Auth] Backend token verification failed:', error);
        throw error;
    }
}

/**
 * Set up automatic token refresh
 * Refreshes Firebase ID token every 50 minutes (before 60-minute expiration)
 */
function setupTokenRefresh() {
    // Clear existing interval if any
    if (FirebaseAuthState.tokenRefreshInterval) {
        clearInterval(FirebaseAuthState.tokenRefreshInterval);
    }

    // Set up new interval
    FirebaseAuthState.tokenRefreshInterval = setInterval(async () => {
        if (FirebaseAuthState.currentUser) {
            try {
                console.log('[Firebase Auth] Refreshing token...');
                const idToken = await FirebaseAuthState.currentUser.getIdToken(true); // Force refresh
                await verifyTokenWithBackend(idToken);
                console.log('[Firebase Auth] Token refreshed successfully');
            } catch (error) {
                console.error('[Firebase Auth] Token refresh failed:', error);
                // Sign out on refresh failure
                await signOut();
            }
        }
    }, TOKEN_REFRESH_INTERVAL);

    console.log('[Firebase Auth] Token refresh scheduled (every 50 minutes)');
}

/**
 * Sign up with email and password (AC-AUTH-01)
 *
 * @param {string} email - User email
 * @param {string} password - User password
 * @returns {Promise<firebase.User>}
 */
export async function signUpWithEmail(email, password) {
    if (!FirebaseAuthState.auth) {
        throw new Error('Firebase Auth not initialized');
    }

    try {
        console.log('[Firebase Auth] Signing up with email:', email);

        const userCredential = await FirebaseAuthState.auth.createUserWithEmailAndPassword(
            email,
            password
        );

        // Send email verification
        await userCredential.user.sendEmailVerification();

        console.log('[Firebase Auth] Sign up successful, verification email sent');

        return userCredential.user;
    } catch (error) {
        console.error('[Firebase Auth] Sign up failed:', error);
        throw new Error(getFirebaseErrorMessage(error));
    }
}

/**
 * Sign in with email and password
 *
 * @param {string} email - User email
 * @param {string} password - User password
 * @returns {Promise<firebase.User>}
 */
export async function signInWithEmail(email, password) {
    if (!FirebaseAuthState.auth) {
        throw new Error('Firebase Auth not initialized');
    }

    try {
        console.log('[Firebase Auth] Signing in with email:', email);

        const userCredential = await FirebaseAuthState.auth.signInWithEmailAndPassword(
            email,
            password
        );

        console.log('[Firebase Auth] Sign in successful');

        return userCredential.user;
    } catch (error) {
        console.error('[Firebase Auth] Sign in failed:', error);
        throw new Error(getFirebaseErrorMessage(error));
    }
}

/**
 * Sign in with Google (AC-AUTH-02)
 *
 * @returns {Promise<firebase.User>}
 */
export async function signInWithGoogle() {
    if (!FirebaseAuthState.auth) {
        throw new Error('Firebase Auth not initialized');
    }

    try {
        console.log('[Firebase Auth] Signing in with Google...');

        const provider = new firebase.auth.GoogleAuthProvider();
        provider.setCustomParameters({
            prompt: 'select_account', // Always show account selection
        });

        const userCredential = await FirebaseAuthState.auth.signInWithPopup(provider);

        console.log('[Firebase Auth] Google sign in successful');

        return userCredential.user;
    } catch (error) {
        console.error('[Firebase Auth] Google sign in failed:', error);
        throw new Error(getFirebaseErrorMessage(error));
    }
}

/**
 * Sign out current user
 *
 * @returns {Promise<void>}
 */
export async function signOut() {
    if (!FirebaseAuthState.auth) {
        throw new Error('Firebase Auth not initialized');
    }

    try {
        console.log('[Firebase Auth] Signing out...');
        await FirebaseAuthState.auth.signOut();
        console.log('[Firebase Auth] Sign out successful');

        // Also clear backend session cookie
        await fetch(`${AUTH_BASE}/logout`, {
            credentials: 'include',
        });
    } catch (error) {
        console.error('[Firebase Auth] Sign out failed:', error);
        throw error;
    }
}

/**
 * Send email verification to current user
 *
 * @returns {Promise<void>}
 */
export async function sendEmailVerification() {
    if (!FirebaseAuthState.currentUser) {
        throw new Error('No user signed in');
    }

    try {
        console.log('[Firebase Auth] Sending email verification...');
        await FirebaseAuthState.currentUser.sendEmailVerification();
        console.log('[Firebase Auth] Verification email sent');
    } catch (error) {
        console.error('[Firebase Auth] Failed to send verification email:', error);
        throw new Error(getFirebaseErrorMessage(error));
    }
}

/**
 * Send password reset email
 *
 * @param {string} email - User email
 * @returns {Promise<void>}
 */
export async function sendPasswordResetEmail(email) {
    if (!FirebaseAuthState.auth) {
        throw new Error('Firebase Auth not initialized');
    }

    try {
        console.log('[Firebase Auth] Sending password reset email to:', email);
        await FirebaseAuthState.auth.sendPasswordResetEmail(email);
        console.log('[Firebase Auth] Password reset email sent');
    } catch (error) {
        console.error('[Firebase Auth] Failed to send password reset email:', error);
        throw new Error(getFirebaseErrorMessage(error));
    }
}

/**
 * Get current Firebase user
 *
 * @returns {firebase.User|null}
 */
export function getCurrentUser() {
    return FirebaseAuthState.currentUser;
}

/**
 * Check if user is authenticated
 *
 * @returns {boolean}
 */
export function isAuthenticated() {
    return FirebaseAuthState.currentUser !== null &&
           FirebaseAuthState.currentUser.emailVerified;
}

/**
 * Get user-friendly error message from Firebase error
 *
 * @param {Error} error - Firebase error
 * @returns {string} User-friendly error message
 */
function getFirebaseErrorMessage(error) {
    const errorCode = error.code;

    const errorMessages = {
        'auth/email-already-in-use': 'This email address is already registered. Please sign in instead.',
        'auth/invalid-email': 'Please enter a valid email address.',
        'auth/weak-password': 'Password must be at least 6 characters long.',
        'auth/user-not-found': 'No account found with this email address.',
        'auth/wrong-password': 'Incorrect password. Please try again.',
        'auth/too-many-requests': 'Too many failed attempts. Please try again later.',
        'auth/user-disabled': 'This account has been disabled.',
        'auth/popup-closed-by-user': 'Sign in cancelled. Please try again.',
        'auth/popup-blocked': 'Sign in popup was blocked. Please allow popups for this site.',
    };

    return errorMessages[errorCode] || error.message || 'An error occurred during authentication.';
}

/**
 * Wait for auth to be initialized
 * Useful for ensuring Firebase Auth is ready before performing operations
 *
 * @param {number} timeout - Timeout in milliseconds (default: 5000)
 * @returns {Promise<void>}
 */
export function waitForAuthInit(timeout = 5000) {
    return new Promise((resolve, reject) => {
        if (FirebaseAuthState.initialized) {
            resolve();
            return;
        }

        const startTime = Date.now();
        const checkInterval = setInterval(() => {
            if (FirebaseAuthState.initialized) {
                clearInterval(checkInterval);
                resolve();
            } else if (Date.now() - startTime > timeout) {
                clearInterval(checkInterval);
                reject(new Error('Firebase Auth initialization timeout'));
            }
        }, 100);
    });
}
