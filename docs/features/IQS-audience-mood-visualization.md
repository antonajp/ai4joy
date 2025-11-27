# Audience Mood Visualization Feature

## Overview

Add visual audience mood indication through dynamic background colors in the chat interface for the improv scene experience.

## Mood-to-Color Mapping (UX-Reviewed)

Based on emotional arousal theory, the color palette uses a warm-to-cool energy spectrum designed for:
- Emotional alignment with mood states
- Colorblind accessibility (no red/green pairing)
- Cultural neutrality

| Mood State | Color | Hex Codes | Behavior |
|------------|-------|-----------|----------|
| Neutral | Soft Lavender | `#E6E6FA` | Starting state, signals system active |
| Negative/Disengaged | Cool Gray-Blue | `#B0BEC5` → `#78909C` | Low energy, brightness scales with intensity |
| Excited/Anticipatory | Warm Amber | `#FFE4B5` → `#FFB74D` | High energy, brightness scales with intensity |
| Laughter | Vibrant Coral | `#FFE0D6` → `#FF8A65` | Flash on detection (450ms), sustained holds coral |

## Requirements

### Functional Requirements

1. **FR1**: Background color transitions smoothly (1.5s) based on audience mood
2. **FR2**: Neutral mood displays soft lavender background (`#E6E6FA`)
3. **FR3**: Negative sentiment displays cool gray-blue background with intensity scaling
4. **FR4**: Excited/anticipatory mood displays warm amber background with intensity scaling
5. **FR5**: Laughter triggers vibrant coral flash (450ms) then returns to mood color
6. **FR6**: Sustained laughter holds coral and increases brightness

### Non-Functional Requirements

1. **NFR1**: Message bubbles remain readable on all background colors (0.98 opacity)
2. **NFR2**: Transitions are GPU-accelerated (CSS transitions)
3. **NFR3**: No performance impact on turn processing
4. **NFR4**: Graceful degradation for unsupported browsers
5. **NFR5**: ARIA live region announces mood state changes for screen readers

### Acceptance Criteria

- [x] AC1: Scene starts with soft lavender background (neutral mood)
- [x] AC2: Negative sentiment (-0.2 to -1.0) shows cool gray-blue background
- [x] AC3: Positive sentiment (>0.3) + high engagement (>0.6) shows warm amber background
- [x] AC4: Laughter keywords trigger 450ms coral flash
- [x] AC5: Sustained laughter (3+ consecutive detections) maintains coral
- [x] AC6: All message bubbles remain readable with 0.98 opacity
- [x] AC7: Background transitions are smooth (1.5s ease-in-out)
- [x] AC8: Flash rate limited to minimum 1.5s intervals (WCAG 2.3.1)
- [x] AC9: Respects prefers-reduced-motion user preference
- [x] AC10: ARIA announcements for mood state changes

## Technical Architecture

### Data Flow

```
RoomAgent (sentiment_analysis)
    → TurnOrchestrator (parse mood_metrics)
    → API Response (include mood_metrics in room_vibe)
    → Frontend (MoodVisualizer.update())
    → CSS Variable (--mood-bg-color)
    → Chat Container Background
    → ARIA Region (mood state announcement)
```

### Files Modified

| File | Change Type | Description |
|------|-------------|-------------|
| `/app/services/turn_orchestrator.py` | Modified | Added `_extract_mood_metrics()` with input validation |
| `/app/static/app.js` | Modified | Integrated MoodVisualizer calls in `displayRoomMessage()` |
| `/app/static/chat.html` | Modified | Added script tag for mood-visualizer.js |
| `/app/static/styles.css` | Modified | Added mood background styles, 0.98 opacity bubbles |

### Files Created

| File | Description |
|------|-------------|
| `/app/static/mood-visualizer.js` | MoodVisualizer class with UX-reviewed color calculations |
| `/tests/test_services/test_mood_metrics.py` | 23 TDD tests for mood metrics extraction |

### Mood Metrics Structure

```javascript
{
    sentiment_score: -1.0 to 1.0,    // Negative to positive
    engagement_score: 0.0 to 1.0,    // Low to high engagement
    laughter_detected: boolean       // True if laughter keywords found
}
```

### Color Calculation Logic (UX-Reviewed)

```javascript
// Neutral - Soft Lavender (#E6E6FA)
// Default starting state
return { r: 230, g: 230, b: 250 };

// Negative mood - Cool Gray-Blue spectrum
// #B0BEC5 (176, 190, 197) → #78909C (120, 144, 156)
if (sentiment_score < -0.2) {
    const intensity = Math.abs(sentiment_score);
    return {
        r: Math.floor(176 - (56 * intensity)),
        g: Math.floor(190 - (46 * intensity)),
        b: Math.floor(197 - (41 * intensity))
    };
}

// Excited - Warm Amber spectrum
// #FFE4B5 (255, 228, 181) → #FFB74D (255, 183, 77)
if (sentiment_score > 0.3 && engagement_score > 0.6) {
    const intensity = (sentiment_score + engagement_score) / 2;
    return {
        r: 255,
        g: Math.floor(228 - (45 * intensity)),
        b: Math.floor(181 - (104 * intensity))
    };
}

// Laughter - Vibrant Coral
// #FFE0D6 (255, 224, 214) → #FF8A65 (255, 138, 101)
if (laughter_detected) {
    return {
        r: 255,
        g: Math.floor(224 - (86 * intensity)),
        b: Math.floor(214 - (113 * intensity))
    };
}
```

## Accessibility Features

| Feature | Implementation |
|---------|----------------|
| Colorblind safe | No red/green pairing, warm-to-cool spectrum |
| Flash rate limiting | Minimum 1.5s between flashes (WCAG 2.3.1) |
| Reduced motion | Respects `prefers-reduced-motion` media query |
| Screen readers | ARIA live region announces mood state changes |
| Contrast | Message bubbles at 0.98 opacity with backdrop blur |

## Test Plan

### Unit Tests (23 tests in `test_mood_metrics.py`)

| ID | Test Case | Expected Result |
|----|-----------|-----------------|
| T1 | calculateMoodColor with sentiment=0, engagement=0.5 | Returns lavender (230,230,250) |
| T2 | calculateMoodColor with sentiment=-0.8 | Returns gray-blue tint |
| T3 | calculateMoodColor with sentiment=0.6, engagement=0.8 | Returns amber tint |
| T4 | flashLaughter called | Background flashes coral for 450ms |
| T5 | update with laughter_detected=true | Triggers flash, returns to mood |
| T6 | reset() | Returns to lavender background |

### Integration Tests

| ID | Test Case | Expected Result |
|----|-----------|-----------------|
| IT1 | API response includes mood_metrics | Frontend receives metrics |
| IT2 | Room vibe with negative keywords | Gray-blue background applied |
| IT3 | Room vibe with laughter keywords | Coral flash triggered |
| IT4 | Rapid mood changes | Smooth transitions, no jank |

### Accessibility Tests

| ID | Test Case | Expected Result |
|----|-----------|-----------------|
| A1 | Text contrast on gray-blue background | Ratio >= 4.5:1 |
| A2 | Text contrast on amber background | Ratio >= 4.5:1 |
| A3 | Text contrast on coral background | Ratio >= 4.5:1 |
| A4 | Flash frequency | Max 1 flash per 1.5s |
| A5 | Screen reader announces mood change | ARIA region updated |

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Readability degradation | High | Semi-transparent bubbles (0.98 opacity) |
| Performance issues | Medium | CSS transitions (GPU-accelerated) |
| Seizure risk from flashes | High | Rate limit to 1.5s minimum intervals |
| Colorblind accessibility | High | Warm-to-cool spectrum, no red/green |
| Browser incompatibility | Low | Feature detection, lavender fallback |
| Screen reader support | Medium | ARIA live region for mood announcements |
