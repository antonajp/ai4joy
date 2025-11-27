/**
 * MoodVisualizer - Dynamic Background Color Visualization for Audience Mood
 *
 * This module provides visual feedback for audience mood during improv scenes
 * using a warm-to-cool energy-based color spectrum (UX-reviewed):
 * - Neutral: Soft Lavender (#E6E6FA) - calm baseline, signals system active
 * - Negative/Disengaged: Cool Gray-Blue (#B0BEC5 → #78909C) - low energy
 * - Excited/Anticipatory: Warm Amber (#FFE4B5 → #FFB74D) - high energy
 * - Laughter: Vibrant Coral (#FFE0D6 → #FF8A65) - warm, playful
 *
 * Color palette designed for:
 * - Emotional arousal theory alignment
 * - Colorblind accessibility (no red/green pairing)
 * - Cultural neutrality
 *
 * @see IQS-56 for feature specification
 */

class MoodVisualizer {
    constructor() {
        this.currentMood = {
            sentiment_score: 0,
            engagement_score: 0.5,
            laughter_detected: false
        };

        this.flashTimeout = null;
        this.transitionDuration = 1500; // ms for smooth transitions
        this.flashDuration = 450; // ms for laughter flash (reduced from 800ms per UX review)
        this.sustainedLaughterCount = 0;
        this.maxSustainedCount = 3; // After this many consecutive laughs, hold coral

        // Flash rate limiting for seizure prevention (WCAG 2.3.1)
        this.lastFlashTime = 0;
        this.minFlashInterval = 1500; // Minimum 1.5 seconds between flashes (increased per UX review)

        // Respect user preferences for reduced motion
        this.flashEnabled = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;

        // Track previous mood state for ARIA announcements
        this.previousMoodState = 'neutral';

        // Initialize CSS variables and ARIA region
        this.initializeStyles();
        this.initializeAriaRegion();
    }

    /**
     * Initialize CSS custom properties for mood visualization
     */
    initializeStyles() {
        const root = document.documentElement;
        // Neutral: Soft Lavender (#E6E6FA)
        root.style.setProperty('--mood-bg-color', 'rgb(230, 230, 250)');
        root.style.setProperty('--mood-transition', `background-color ${this.transitionDuration}ms ease-in-out`);
    }

    /**
     * Initialize ARIA live region for mood state announcements
     */
    initializeAriaRegion() {
        // Check if ARIA region already exists
        if (document.getElementById('mood-status')) return;

        const ariaRegion = document.createElement('div');
        ariaRegion.id = 'mood-status';
        ariaRegion.className = 'sr-only';
        ariaRegion.setAttribute('role', 'status');
        ariaRegion.setAttribute('aria-live', 'polite');
        ariaRegion.setAttribute('aria-atomic', 'true');
        ariaRegion.textContent = 'Audience mood: Neutral';
        document.body.appendChild(ariaRegion);
    }

    /**
     * Announce mood state change to screen readers
     * @param {string} moodState - The current mood state name
     */
    announceMoodState(moodState) {
        if (moodState === this.previousMoodState) return;

        const ariaRegion = document.getElementById('mood-status');
        if (ariaRegion) {
            const moodLabels = {
                'neutral': 'Neutral',
                'negative': 'Low energy',
                'excited': 'Excited',
                'laughter': 'Laughter detected'
            };
            ariaRegion.textContent = `Audience mood: ${moodLabels[moodState] || moodState}`;
        }
        this.previousMoodState = moodState;
    }

    /**
     * Update mood visualization based on new metrics
     * @param {Object} moodMetrics - { sentiment_score, engagement_score, laughter_detected }
     */
    update(moodMetrics) {
        if (!moodMetrics) return;

        this.currentMood = { ...this.currentMood, ...moodMetrics };

        // Track sustained laughter
        if (moodMetrics.laughter_detected) {
            this.sustainedLaughterCount++;
        } else {
            this.sustainedLaughterCount = 0;
        }

        // Handle laughter flash (highest priority)
        if (moodMetrics.laughter_detected) {
            this.flashLaughter();
        } else {
            this.updateBackgroundColor();
        }
    }

    /**
     * Calculate background color based on mood state
     *
     * UX-Reviewed Color Palette (warm-to-cool energy spectrum):
     * - Neutral: Soft Lavender #E6E6FA - rgb(230, 230, 250)
     * - Negative: Cool Gray-Blue #B0BEC5 → #78909C
     * - Excited: Warm Amber #FFE4B5 → #FFB74D
     * - Sustained Laughter: Vibrant Coral #FFE0D6 → #FF8A65
     */
    calculateMoodColor() {
        const { sentiment_score, engagement_score } = this.currentMood;

        // Sustained laughter - hold Vibrant Coral
        if (this.sustainedLaughterCount >= this.maxSustainedCount) {
            const intensity = Math.min(engagement_score, 1.0);
            this.announceMoodState('laughter');
            // Coral: #FFE0D6 (255, 224, 214) → #FF8A65 (255, 138, 101)
            return {
                r: 255,
                g: Math.floor(224 - (86 * intensity)),   // 224 → 138
                b: Math.floor(214 - (113 * intensity)),  // 214 → 101
                intensity: intensity
            };
        }

        // Negative mood - Cool Gray-Blue spectrum
        if (sentiment_score < -0.2) {
            const intensity = Math.min(Math.abs(sentiment_score), 1.0);
            this.announceMoodState('negative');
            // Gray-Blue: #B0BEC5 (176, 190, 197) → #78909C (120, 144, 156)
            return {
                r: Math.floor(176 - (56 * intensity)),   // 176 → 120
                g: Math.floor(190 - (46 * intensity)),   // 190 → 144
                b: Math.floor(197 - (41 * intensity)),   // 197 → 156
                intensity: intensity
            };
        }

        // Positive + High engagement = Excited - Warm Amber spectrum
        if (sentiment_score > 0.3 && engagement_score > 0.6) {
            const intensity = Math.min((sentiment_score + engagement_score) / 2, 1.0);
            this.announceMoodState('excited');
            // Amber: #FFE4B5 (255, 228, 181) → #FFB74D (255, 183, 77)
            return {
                r: 255,
                g: Math.floor(228 - (45 * intensity)),   // 228 → 183
                b: Math.floor(181 - (104 * intensity)),  // 181 → 77
                intensity: intensity
            };
        }

        // Moderate positive - Light Amber tint
        if (sentiment_score > 0.2) {
            const intensity = sentiment_score * 0.4;
            this.announceMoodState('neutral');
            // Subtle amber tint from lavender base
            return {
                r: Math.floor(230 + (25 * intensity)),   // 230 → 255
                g: Math.floor(230 - (2 * intensity)),    // 230 → 228
                b: Math.floor(250 - (69 * intensity)),   // 250 → 181
                intensity: intensity
            };
        }

        // Default to neutral - Soft Lavender (#E6E6FA)
        this.announceMoodState('neutral');
        return { r: 230, g: 230, b: 250, intensity: 0 };
    }

    /**
     * Update background color smoothly
     */
    updateBackgroundColor() {
        const color = this.calculateMoodColor();
        const rgb = `rgb(${color.r}, ${color.g}, ${color.b})`;

        document.documentElement.style.setProperty('--mood-bg-color', rgb);

        // Apply to chat container for smooth effect
        const chatContainer = document.querySelector('.chat-container');
        if (chatContainer) {
            chatContainer.style.transition = `background-color ${this.transitionDuration}ms ease-in-out`;
            chatContainer.style.backgroundColor = rgb;
        }
    }

    /**
     * Flash Vibrant Coral for laughter moments
     * Includes rate limiting for seizure prevention (WCAG 2.3.1)
     */
    flashLaughter() {
        // Clear any existing flash timeout
        if (this.flashTimeout) {
            clearTimeout(this.flashTimeout);
        }

        // Check if flash is enabled (respects prefers-reduced-motion)
        if (!this.flashEnabled) {
            // Just update color smoothly instead of flashing
            this.updateBackgroundColor();
            return;
        }

        // Rate limit: Prevent flashing too frequently (seizure prevention)
        const now = Date.now();
        const timeSinceLastFlash = now - this.lastFlashTime;

        if (timeSinceLastFlash < this.minFlashInterval) {
            // Skip flash, just update color smoothly
            this.updateBackgroundColor();
            return;
        }

        this.lastFlashTime = now;
        this.announceMoodState('laughter');

        // Calculate coral intensity based on engagement and sustained count
        const baseIntensity = Math.min(this.currentMood.engagement_score, 1.0);
        const sustainBoost = Math.min(this.sustainedLaughterCount * 0.1, 0.3);
        const intensity = Math.min(baseIntensity + sustainBoost, 1.0);

        // Vibrant Coral: #FFE0D6 (255, 224, 214) → #FF8A65 (255, 138, 101)
        const coral = {
            r: 255,
            g: Math.floor(224 - (86 * intensity)),   // 224 → 138
            b: Math.floor(214 - (113 * intensity))   // 214 → 101
        };

        const coralRgb = `rgb(${coral.r}, ${coral.g}, ${coral.b})`;

        // Apply coral immediately with fast transition
        document.documentElement.style.setProperty('--mood-bg-color', coralRgb);

        const chatContainer = document.querySelector('.chat-container');
        if (chatContainer) {
            chatContainer.style.transition = 'background-color 150ms ease-in';
            chatContainer.style.backgroundColor = coralRgb;
        }

        // If sustained laughter, don't return to mood color
        if (this.sustainedLaughterCount >= this.maxSustainedCount) {
            return;
        }

        // Return to calculated mood color after flash duration
        this.flashTimeout = setTimeout(() => {
            this.updateBackgroundColor();
        }, this.flashDuration);
    }

    /**
     * Reset to neutral state (Soft Lavender)
     */
    reset() {
        this.currentMood = {
            sentiment_score: 0,
            engagement_score: 0.5,
            laughter_detected: false
        };
        this.sustainedLaughterCount = 0;
        this.previousMoodState = 'neutral';

        if (this.flashTimeout) {
            clearTimeout(this.flashTimeout);
            this.flashTimeout = null;
        }

        this.updateBackgroundColor();
        this.announceMoodState('neutral');
    }

    /**
     * Get current mood state (for debugging)
     */
    getCurrentState() {
        return {
            mood: this.currentMood,
            sustainedLaughterCount: this.sustainedLaughterCount,
            moodState: this.previousMoodState,
            color: this.calculateMoodColor()
        };
    }
}

// Create singleton instance
const moodVisualizer = new MoodVisualizer();

// Export for module usage (if using ES modules in future)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { MoodVisualizer, moodVisualizer };
}
