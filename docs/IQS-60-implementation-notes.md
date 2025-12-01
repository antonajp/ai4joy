# IQS-60: Audience (Room Agent) Audio Integration Implementation

## Overview
Implemented the foundational infrastructure for Room Agent audio integration in the ai4joy improv comedy app. The Room Agent now triggers after Partner/User turn completions to provide ambient commentary.

## Changes Made

### 1. Turn Manager Updates (`app/audio/turn_manager.py`)
- **Added "room" agent type** to `AgentType` literal type
- **Added `start_room_turn()` method** for activating Room Agent
- **Updated `switch_to_agent()` method** to handle room agent switching
- Room turns are designed as brief, non-blocking background reactions

### 2. Audio Orchestrator Updates (`app/audio/audio_orchestrator.py`)

#### Session State Tracking
- Added `last_user_input` and `last_agent_response` fields to `AudioSession` dataclass
- These track recent transcriptions for ambient context

#### Transcription Tracking
- Modified `_process_event()` to capture and store:
  - User input transcriptions (when `is_final=True`)
  - Partner agent response transcriptions (when `is_final=True` and `agent_type="partner"`)

#### Audience Reaction Logic
- **Added `trigger_audience_reaction()` method**:
  - Analyzes sentiment and energy from recent conversation
  - Uses simple heuristics for sentiment detection (positive/negative word matching)
  - Calculates energy level based on text length and punctuation
  - Checks `should_trigger_ambient()` to respect cooldown (15 seconds)
  - Calls `_send_audience_prompt()` if triggered

- **Added `_send_audience_prompt()` method**:
  - Generates appropriate prompt using `get_ambient_prompt()`
  - Creates ADK Content object with the prompt
  - Logs the prompt generation for debugging
  - **NOTE**: Currently logs only - actual Room Agent audio streaming not yet implemented

#### Stream Integration
- Modified `stream_responses()` to trigger audience reactions:
  - After `turn_complete` event when `current_agent == "partner"`
  - Uses `asyncio.create_task()` for non-blocking execution
  - Emits `audience_reaction_triggered` event to frontend
  - Passes `last_user_input` and `last_agent_response` as context

## Current Flow

### Before (Broken)
```
MC greets → Partner scenes with user → (audience missing) → back to Partner
```

### After (Foundation Implemented)
```
MC greets → Partner scenes with user →
  [Turn Complete] →
    Audience reaction triggered (logged, not yet audio) →
  Partner continues → User →
    [Turn Complete] →
      Audience reaction triggered (logged, not yet audio) →
  ...
```

## Key Features

### Sentiment Analysis (Simple Heuristics)
- **Positive detection**: "great", "awesome", "love", "yes", "amazing", "perfect"
- **Negative detection**: "no", "stop", "bad", "wrong", "difficult"
- Default: "neutral"

### Energy Level Calculation
- Based on text length: `min(1.0, len(context) / 200.0)`
- Boosted by punctuation: +0.2 if "!" or "?" present
- Range: 0.0 to 1.0

### Trigger Conditions (from `AmbientAudioTrigger`)
1. Very positive or very negative sentiment
2. High energy (≥0.75)
3. Non-neutral sentiment with moderate energy (≥0.4)
4. Respects 15-second cooldown between triggers

### Commentary Prompts (from `ambient_audio.py`)
- Templates vary by sentiment level
- Examples:
  - **Very Positive**: "The energy is electric! Capture this moment with excitement."
  - **Positive**: "Good energy in the room. Acknowledge the positive momentum."
  - **Neutral**: "Steady energy. The room is attentive."
  - **Negative**: "There's tension in the air. Acknowledge it subtly."

## Limitations & TODOs

### ⚠️ Room Agent Audio Streaming NOT Yet Implemented
The current implementation:
- ✅ Detects when audience should react
- ✅ Generates appropriate prompts
- ✅ Logs trigger events
- ❌ **Does NOT yet play Room Agent audio**

### Next Steps for Full Implementation

**Option 1: Separate run_live Session**
- Create a dedicated `LiveRequestQueue` for Room Agent
- Run a parallel `run_live()` stream for ambient commentary
- Mix Room audio at 30% volume using `AudioMixer`
- Requires managing multiple concurrent streams

**Option 2: Dynamic Agent Switching**
- Switch to Room Agent temporarily for commentary
- Generate brief audio response
- Switch back to Partner/MC for main flow
- Requires careful queue management and state tracking

**Option 3: Pre-generated Audio Clips**
- Create library of sentiment-based audio clips
- Trigger appropriate clip based on sentiment/energy
- Fastest to implement but least dynamic
- Limited variety and context awareness

### Recommended Approach
**Option 1 (Separate run_live Session)** is recommended because:
- Most flexible and dynamic
- Room Agent can generate contextual commentary
- AudioMixer already configured for 30% Room volume
- Allows true ambient background presence
- Aligns with multi-agent architecture

## Frontend Integration

### New Event Type
```typescript
{
  type: "audience_reaction_triggered",
  session_id: string,
  turn_count: number
}
```

Frontend should:
1. Display visual indicator when audience is "reacting"
2. Eventually play mixed audio when Room Agent audio is implemented
3. Show Room Agent label/avatar during ambient commentary

## Testing Notes

### Current Behavior
- Audience reaction triggers are logged but produce no audio
- Check logs for messages like:
  - `"Triggering audience reaction after Partner turn"`
  - `"Room Agent ambient prompt generated"`
  - `"Ambient trigger conditions not met"` (when cooldown active)

### Future Testing (Once Audio Implemented)
- Verify Room Agent audio plays at 30% volume
- Test sentiment detection accuracy
- Verify cooldown timing (15 seconds between reactions)
- Test energy level calculations
- Ensure Room Agent doesn't interrupt Partner/User flow

## Files Modified
1. `/app/audio/turn_manager.py` - Added "room" agent type support
2. `/app/audio/audio_orchestrator.py` - Added audience reaction logic

## Files Referenced (Not Modified)
1. `/app/audio/ambient_audio.py` - Existing trigger logic
2. `/app/agents/room_agent.py` - Existing Room Agent definition
3. `/app/audio/audio_mixer.py` - Existing mixing infrastructure (30% Room volume)

## Deployment Notes
- No database migrations required
- No environment variable changes
- Backward compatible (Room Agent audio is additive)
- Can be deployed safely - will log triggers but not affect audio until streaming implemented

## Success Metrics (Once Audio Implemented)
- Room Agent reacts 2-4 times per scene (with 15s cooldown)
- Reactions align with scene energy/sentiment
- Audio remains at 30% volume relative to Partner/MC
- No blocking or interruption of main conversation flow
- User feedback indicates enhanced atmosphere

---

**Implementation Date**: 2025-11-30
**Ticket**: IQS-60
**Status**: Foundation Complete - Audio Streaming Pending
