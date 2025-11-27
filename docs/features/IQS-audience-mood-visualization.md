# Audience Mood Visualization Feature

## Overview

Add visual audience mood indication through dynamic background colors in the chat interface for the improv scene experience.

## Mood-to-Color Mapping

| Mood State | Color | Behavior |
|------------|-------|----------|
| Neutral | White | Starting state, baseline |
| Negative | Red | Brightness increases with intensity |
| Excited/Anticipatory | Blue | Brightness increases with intensity |
| Laughter | Green | Flash on detection, sustained with intensity |

## Requirements

### Functional Requirements

1. **FR1**: Background color transitions smoothly (1.5s) based on audience mood
2. **FR2**: Neutral mood displays white background
3. **FR3**: Negative sentiment displays red background with intensity scaling
4. **FR4**: Excited/anticipatory mood displays blue background with intensity scaling
5. **FR5**: Laughter triggers green flash (800ms) then returns to mood color
6. **FR6**: Sustained laughter holds green and increases brightness

### Non-Functional Requirements

1. **NFR1**: Message bubbles remain readable on all background colors (semi-transparent)
2. **NFR2**: Transitions are GPU-accelerated (CSS transitions)
3. **NFR3**: No performance impact on turn processing
4. **NFR4**: Graceful degradation for unsupported browsers

### Acceptance Criteria

- [ ] AC1: Scene starts with white background (neutral mood)
- [ ] AC2: Negative sentiment (-0.5 to -1.0) shows red background with proportional brightness
- [ ] AC3: Positive sentiment (>0.3) + high engagement (>0.7) shows blue background
- [ ] AC4: Laughter keywords trigger 800ms green flash
- [ ] AC5: Sustained laughter (multiple consecutive detections) maintains green
- [ ] AC6: All message bubbles remain readable with contrast ratio >= 4.5:1
- [ ] AC7: Background transitions are smooth (1.5s ease-in-out)

## Technical Architecture

### Data Flow

```
RoomAgent (sentiment_analysis)
    → TurnOrchestrator (parse mood_metrics)
    → API Response (include mood_metrics in room_vibe)
    → Frontend (MoodVisualizer.update())
    → CSS Variable (--mood-bg-color)
    → Chat Container Background
```

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `/app/services/turn_orchestrator.py` | Modify | Add mood_metrics extraction |
| `/app/static/app.js` | Modify | Integrate MoodVisualizer calls |
| `/app/static/chat.html` | Modify | Add script tag |
| `/app/static/styles.css` | Modify | Add mood background styles |

### Files to Create

| File | Description |
|------|-------------|
| `/app/static/mood-visualizer.js` | MoodVisualizer class for color calculations |

### Mood Metrics Structure

```javascript
{
    sentiment_score: -1.0 to 1.0,    // Negative to positive
    engagement_score: 0.0 to 1.0,    // Low to high engagement
    laughter_detected: boolean       // True if laughter keywords found
}
```

### Color Calculation Logic

```javascript
// Negative mood (red spectrum)
if (sentiment_score < -0.2) {
    intensity = Math.abs(sentiment_score);
    color = rgb(255, 255*(1-intensity*0.6), 255*(1-intensity*0.6));
}

// Excited (blue spectrum)
if (sentiment_score > 0.3 && engagement_score > 0.7) {
    intensity = (sentiment_score + engagement_score) / 2;
    color = rgb(255*(1-intensity*0.5), 255*(1-intensity*0.3), 255);
}

// Laughter (green flash)
if (laughter_detected) {
    color = rgb(255*(1-intensity*0.7), 255, 255*(1-intensity*0.5));
}
```

## Test Plan

### Unit Tests

| ID | Test Case | Expected Result |
|----|-----------|-----------------|
| T1 | calculateMoodColor with sentiment=0, engagement=0.5 | Returns white (255,255,255) |
| T2 | calculateMoodColor with sentiment=-0.8 | Returns red tint |
| T3 | calculateMoodColor with sentiment=0.6, engagement=0.8 | Returns blue tint |
| T4 | flashLaughter called | Background flashes green for 800ms |
| T5 | update with laughter_detected=true | Triggers flash, returns to mood |
| T6 | reset() | Returns to white background |

### Integration Tests

| ID | Test Case | Expected Result |
|----|-----------|-----------------|
| IT1 | API response includes mood_metrics | Frontend receives metrics |
| IT2 | Room vibe with negative keywords | Red background applied |
| IT3 | Room vibe with laughter keywords | Green flash triggered |
| IT4 | Rapid mood changes | Smooth transitions, no jank |

### Accessibility Tests

| ID | Test Case | Expected Result |
|----|-----------|-----------------|
| A1 | Text contrast on red background | Ratio >= 4.5:1 |
| A2 | Text contrast on blue background | Ratio >= 4.5:1 |
| A3 | Text contrast on green background | Ratio >= 4.5:1 |
| A4 | Flash frequency | Max 1 flash per 800ms |

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Readability degradation | High | Semi-transparent bubbles (0.95 opacity) |
| Performance issues | Medium | CSS transitions (GPU-accelerated) |
| Seizure risk from flashes | High | Debounce to max 1 flash per 800ms |
| Browser incompatibility | Low | Feature detection, white fallback |
