# IQS-75 Test Coverage: Audio/Voice Mode Selection Persistence

## Overview

This document describes the comprehensive test suite written for the `interaction_mode` functionality. The tests follow TDD (Test-Driven Development) principles and are ready to validate the implementation once the feature is developed.

## Test Files Created

### 1. Model Tests: `tests/test_models/test_session.py`

**Location:** `/home/jantona/Documents/code/ai4joy/tests/test_models/test_session.py`

**Test Coverage:**

#### TestInteractionMode Class
- `test_tc_model_session_01_interaction_mode_values`: Verifies InteractionMode enum has TEXT and AUDIO values
- `test_interaction_mode_from_string`: Tests enum creation from string values
- `test_interaction_mode_invalid_value`: Validates rejection of invalid mode values

#### TestSessionCreate Class
- `test_tc_model_session_02_session_create_accepts_interaction_mode`: Verifies SessionCreate accepts interaction_mode field
- `test_tc_model_session_03_session_create_defaults_to_text`: Tests default to TEXT mode when not specified
- `test_tc_model_session_05_session_create_validates_enum`: Validates enum value conversion
- `test_session_create_with_all_fields`: Tests SessionCreate with all optional fields
- `test_session_create_text_mode_with_game_selection`: Tests TEXT mode with pre-selected game

#### TestSession Class
- `test_tc_model_session_04_session_stores_interaction_mode`: Verifies Session model stores interaction_mode
- `test_tc_model_session_06_session_serialization_includes_mode`: Tests serialization includes interaction_mode
- `test_session_defaults_to_text_mode`: Tests default to TEXT mode
- `test_session_with_text_mode_and_mc_welcome`: Tests TEXT mode with MC welcome fields
- `test_session_with_audio_mode_active_status`: Tests AUDIO mode goes to ACTIVE status
- `test_session_json_mode_serialization`: Tests JSON serialization

#### TestSessionResponse Class
- `test_session_response_includes_interaction_mode`: Documents SessionResponse behavior

**Status:** ✅ All 15 tests pass with implemented models

### 2. Service Tests: `tests/test_services/test_session_manager_adk.py`

**Location:** `/home/jantona/Documents/code/ai4joy/tests/test_services/test_session_manager_adk.py`

**Test Coverage:**

#### IQS-75 Specific Tests
- `test_tc_mgr_01_create_session_stores_text_mode`: Session creation stores TEXT mode in Firestore
- `test_tc_mgr_01_create_session_stores_audio_mode`: Session creation stores AUDIO mode in Firestore
- `test_tc_mgr_03_default_mode_is_text`: Default mode is TEXT when not specified
- `test_tc_mgr_02_get_session_returns_text_mode`: Session retrieval returns correct TEXT mode
- `test_tc_mgr_04_audio_mode_stored_and_retrieved`: AUDIO mode is correctly stored and retrieved
- `test_session_with_text_mode_has_mc_welcome_fields`: TEXT mode sessions can have MC welcome fields
- `test_session_with_audio_mode_direct_to_active`: AUDIO mode sessions can go directly to ACTIVE

**Status:** ⚠️ Tests written but require implementation

### 3. Router Tests: `tests/test_routers/test_session_router.py`

**Location:** `/home/jantona/Documents/code/ai4joy/tests/test_routers/test_session_router.py`

**Test Coverage:**

#### TestSessionStartEndpoint Class
- `test_tc_api_session_01_accepts_text_mode`: POST /session/start accepts TEXT mode
- `test_tc_api_session_01_accepts_audio_mode`: POST /session/start accepts AUDIO mode
- `test_tc_api_session_02_response_includes_session`: Response includes session details
- `test_tc_api_session_05_defaults_to_text_mode`: Defaults to TEXT when not specified
- `test_tc_api_session_03_text_mode_with_game_selection`: TEXT mode with pre-selected game
- `test_tc_api_session_04_audio_mode_for_premium`: AUDIO mode for premium users

#### TestGetSessionEndpoint Class
- `test_tc_api_session_07_get_returns_text_mode`: GET /session/{id} returns TEXT mode
- `test_tc_api_session_07_get_returns_audio_mode`: GET /session/{id} returns AUDIO mode

#### TestInteractionModeValidation Class
- `test_tc_api_session_06_invalid_mode_rejected`: Invalid mode values are rejected
- `test_valid_mode_string_converted_to_enum`: Valid mode string converted to enum

**Status:** ⚠️ Tests written but require implementation

## Implementation Requirements

To make all tests pass, the following implementation is required:

### 1. Add InteractionMode Enum to `app/models/session.py`

```python
class InteractionMode(str, Enum):
    """Session interaction mode.

    TEXT: Traditional text-based mode with MC welcome flow
    AUDIO: Real-time audio/voice mode (premium only)
    """
    TEXT = "text"
    AUDIO = "audio"
```

### 2. Update SessionCreate Model

Add `interaction_mode` field to `SessionCreate`:

```python
class SessionCreate(BaseModel):
    """Request model for creating new session"""

    user_name: Optional[str] = Field(None, description="Optional display name")
    selected_game_id: Optional[str] = Field(None, description="Pre-selected game ID")
    selected_game_name: Optional[str] = Field(
        None, description="Pre-selected game name"
    )
    interaction_mode: InteractionMode = Field(
        default=InteractionMode.TEXT,
        description="Session interaction mode (text or audio)"
    )
```

### 3. Update Session Model

Add `interaction_mode` field to `Session`:

```python
class Session(BaseModel):
    """Session state model"""

    session_id: str
    user_id: str
    user_email: str
    user_name: Optional[str] = None

    status: SessionStatus = SessionStatus.INITIALIZED
    interaction_mode: InteractionMode = Field(
        default=InteractionMode.TEXT,
        description="Session interaction mode (text or audio)"
    )

    # ... rest of fields
```

### 4. Update Session Manager (if needed)

The session manager at line 111 already tries to log `interaction_mode`, so it may need to be updated to handle the case where the enum is already a string (due to Pydantic's `use_enum_values = True`):

```python
# In SessionManager.create_session()
logger.info(
    "Session created successfully",
    session_id=session_id,
    user_id=user_id,
    user_email=user_email,
    interaction_mode=session.interaction_mode.value if isinstance(session.interaction_mode, InteractionMode) else session.interaction_mode,
)
```

## Test Execution

### Run All IQS-75 Tests

```bash
# Model tests
python -m pytest tests/test_models/test_session.py -v

# Service tests
python -m pytest tests/test_services/test_session_manager_adk.py -k "tc_mgr" -v

# Router tests
python -m pytest tests/test_routers/test_session_router.py -v

# All IQS-75 tests
python -m pytest tests/test_models/test_session.py tests/test_routers/test_session_router.py -v
python -m pytest tests/test_services/test_session_manager_adk.py -k "tc_mgr or audio_mode or text_mode" -v
```

### Current Test Status

- **Model Tests:** ✅ 15/15 passing (implementation exists)
- **Service Tests:** ⚠️ 2/7 passing (requires full implementation)
- **Router Tests:** ⚠️ Not yet run (requires implementation)

## Edge Cases Covered

1. **Default Behavior:** TEXT mode is default when not specified
2. **Enum Validation:** Invalid mode values are rejected
3. **String Conversion:** Valid mode strings ("text", "audio") convert to enum
4. **Persistence:** Mode is stored in Firestore and retrieved correctly
5. **Serialization:** Mode is included in JSON serialization
6. **TEXT Mode Flow:** Works with MC welcome, game selection, and suggestions
7. **AUDIO Mode Flow:** Can bypass MC welcome and go directly to ACTIVE
8. **Premium Features:** AUDIO mode works for premium users

## Integration Points

### Firestore Schema

Sessions collection will include:
```json
{
  "session_id": "sess_abc123",
  "interaction_mode": "text",  // or "audio"
  // ... other fields
}
```

### API Request/Response

Session creation request:
```json
{
  "user_name": "Test User",
  "interaction_mode": "audio"  // optional, defaults to "text"
}
```

Session response includes mode information through the session object.

## Testing Best Practices Followed

1. **Descriptive Test Names:** Each test clearly indicates what it's testing
2. **Test Case IDs:** TC-MODEL-SESSION-XX, TC-MGR-XX, TC-API-SESSION-XX for traceability
3. **Fixtures:** Reusable fixtures for mock objects and test data
4. **Edge Cases:** Tests cover defaults, invalid values, and boundary conditions
5. **Isolation:** Each test is independent and can run in any order
6. **Mocking:** External dependencies (Firestore, ADK) are properly mocked
7. **Documentation:** Clear docstrings explain what each test validates

## Next Steps

1. **Implement InteractionMode enum and fields** in `app/models/session.py`
2. **Run all tests** to verify implementation
3. **Fix any failing tests** and iterate
4. **Integration testing** with actual Firestore and ADK
5. **Update API documentation** to include interaction_mode parameter

## Questions or Issues

If tests fail after implementation:
1. Check that InteractionMode enum has correct values ("text", "audio")
2. Verify SessionCreate has default=InteractionMode.TEXT
3. Ensure Session model includes interaction_mode field
4. Check Pydantic Config has use_enum_values = True
5. Verify session manager handles enum/string conversion properly
