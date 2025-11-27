/**
 * MoodVisualizer - Dynamic Background Color Visualization for Audience Mood
 *
 * This module provides visual feedback for audience mood during improv scenes:
 * - Neutral (white): Starting state
 * - Negative (red): Brightness increases with mood intensity
 * - Excited/Anticipatory (blue): Brightness increases with engagement
 * - Laughter (green): Flash on detection, sustained with intensity
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
        this.flashDuration = 800; // ms for laughter flash
        this.sustainedLaughterCount = 0;
        this.maxSustainedCount = 3; // After this many consecutive laughs, hold green

        // Flash rate limiting for seizure prevention (WCAG 2.3.1)
        this.lastFlashTime = 0;
        this.minFlashInterval = 1000; // Minimum 1 second between flashes

        // Respect user preferences for reduced motion
        this.flashEnabled = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;

        // Initialize CSS variables
        this.initializeStyles();
    }

    /**
     * Initialize CSS custom properties for mood visualization
     */
    initializeStyles() {
        const root = document.documentElement;
        root.style.setProperty('--mood-bg-color', 'rgb(255, 255, 255)');
        root.style.setProperty('--mood-transition', `background-color ${this.transitionDuration}ms ease-in-out`);
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
     * Mood Color Mapping:
     * - Neutral (white): sentiment near 0, moderate engagement
     * - Negative (red): sentiment < -0.2
     * - Excited (blue): sentiment > 0.3 && engagement > 0.6
     * - Laughter (green): laughter_detected = true
     */
    calculateMoodColor() {
        const { sentiment_score, engagement_score } = this.currentMood;

        // Sustained laughter - hold green
        if (this.sustainedLaughterCount >= this.maxSustainedCount) {
            const intensity = Math.min(engagement_score, 1.0);
            return {
                r: Math.floor(255 * (1 - intensity * 0.5)),
                g: 255,
                b: Math.floor(255 * (1 - intensity * 0.4)),
                intensity: intensity
            };
        }

        // Negative mood (red spectrum)
        if (sentiment_score < -0.2) {
            const intensity = Math.min(Math.abs(sentiment_score), 1.0);
            return {
                r: 255,
                g: Math.floor(255 * (1 - intensity * 0.5)),
                b: Math.floor(255 * (1 - intensity * 0.5)),
                intensity: intensity
            };
        }

        // Positive + High engagement = Excited (blue spectrum)
        if (sentiment_score > 0.3 && engagement_score > 0.6) {
            const intensity = Math.min((sentiment_score + engagement_score) / 2, 1.0);
            return {
                r: Math.floor(255 * (1 - intensity * 0.4)),
                g: Math.floor(255 * (1 - intensity * 0.2)),
                b: 255,
                intensity: intensity
            };
        }

        // Moderate positive (light blue tint)
        if (sentiment_score > 0.2) {
            const intensity = sentiment_score * 0.4;
            return {
                r: Math.floor(255 * (1 - intensity * 0.2)),
                g: Math.floor(255 * (1 - intensity * 0.1)),
                b: 255,
                intensity: intensity
            };
        }

        // Default to neutral (white)
        return { r: 255, g: 255, b: 255, intensity: 0 };
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
     * Flash green for laughter moments
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

        // Calculate green intensity based on engagement and sustained count
        const baseIntensity = Math.min(this.currentMood.engagement_score, 1.0);
        const sustainBoost = Math.min(this.sustainedLaughterCount * 0.1, 0.3);
        const intensity = Math.min(baseIntensity + sustainBoost, 1.0);

        const green = {
            r: Math.floor(255 * (1 - intensity * 0.5)),
            g: 255,
            b: Math.floor(255 * (1 - intensity * 0.4))
        };

        const greenRgb = `rgb(${green.r}, ${green.g}, ${green.b})`;

        // Apply green immediately with fast transition
        document.documentElement.style.setProperty('--mood-bg-color', greenRgb);

        const chatContainer = document.querySelector('.chat-container');
        if (chatContainer) {
            chatContainer.style.transition = 'background-color 200ms ease-in';
            chatContainer.style.backgroundColor = greenRgb;
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
     * Reset to neutral state
     */
    reset() {
        this.currentMood = {
            sentiment_score: 0,
            engagement_score: 0.5,
            laughter_detected: false
        };
        this.sustainedLaughterCount = 0;

        if (this.flashTimeout) {
            clearTimeout(this.flashTimeout);
            this.flashTimeout = null;
        }

        this.updateBackgroundColor();
    }

    /**
     * Get current mood state (for debugging)
     */
    getCurrentState() {
        return {
            mood: this.currentMood,
            sustainedLaughterCount: this.sustainedLaughterCount,
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
