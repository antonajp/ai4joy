# IQS-65 Frontend Test Plan: Firebase Authentication with MFA and Freemium Tier

**Project**: Improv Olympics - Firebase Authentication Frontend
**Ticket**: IQS-65
**Test Framework**: Jest + Cypress (E2E)
**Automation Coverage Target**: 85% (15% manual UI/UX validation)

---

## Test Scope

**In Scope**:
- Firebase authentication UI flows (signup, login, MFA enrollment)
- Email verification enforcement
- MFA wizard keyboard navigation and screen reader compatibility
- Freemium session counter display and limits
- Upgrade modal/toast notifications
- Error handling and user feedback
- Cross-browser compatibility (Chrome, Firefox, Safari, Edge)

**Out of Scope**:
- Backend token validation (covered in backend tests)
- Firebase Admin SDK functionality
- Payment processing (future ticket)
- Multi-device session management

---

## Critical Test Cases

### 1. Firebase Authentication (AC-AUTH-01 to AC-AUTH-05)

#### AC-AUTH-01: Email/Password Signup
**Priority**: P0
**Automation**: Jest + Cypress E2E

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-AUTH-01-01 | Email signup form validation | 1. Navigate to signup page<br>2. Leave email blank<br>3. Enter invalid email format<br>4. Enter password < 6 chars | - Required field error shown<br>- "Invalid email" error shown<br>- "Password must be at least 6 characters" error | Automated |
| TC-FE-AUTH-01-02 | Successful email signup | 1. Enter valid email<br>2. Enter password ≥ 6 chars<br>3. Click "Sign Up"<br>4. Check console for Firebase call | - Firebase `createUserWithEmailAndPassword()` called<br>- Verification email sent<br>- Success message shown | Automated |
| TC-FE-AUTH-01-03 | Email already exists error | 1. Attempt signup with existing email | - Firebase error `auth/email-already-in-use` caught<br>- User-friendly message: "This email address is already registered" | Automated |
| TC-FE-AUTH-01-04 | Password strength enforcement | 1. Enter weak password (5 chars)<br>2. Submit form | - Firebase error `auth/weak-password`<br>- Message: "Password must be at least 6 characters long" | Automated |

#### AC-AUTH-02: Google Sign-In
**Priority**: P0
**Automation**: Jest (mocked) + Manual E2E

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-AUTH-02-01 | Google Sign-In popup opens | 1. Click "Sign in with Google"<br>2. Verify popup window | - `signInWithPopup()` called<br>- Google account selector shown<br>- `prompt: 'select_account'` parameter set | Manual |
| TC-FE-AUTH-02-02 | Google Sign-In success | 1. Complete Google OAuth flow | - User redirected to app<br>- Firebase user object created<br>- Token sent to backend | Manual |
| TC-FE-AUTH-02-03 | Google Sign-In popup blocked | 1. Simulate popup blocker<br>2. Trigger sign-in | - Error message: "Sign in popup was blocked. Please allow popups for this site." | Automated |
| TC-FE-AUTH-02-04 | User cancels Google Sign-In | 1. Click "Sign in with Google"<br>2. Close popup without selecting account | - Error caught: `auth/popup-closed-by-user`<br>- Message: "Sign in cancelled. Please try again." | Manual |

#### AC-AUTH-03: Email Verification Enforcement
**Priority**: P0
**Automation**: Jest + Cypress

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-AUTH-03-01 | Unverified email blocks access | 1. Sign up with email/password<br>2. Do NOT verify email<br>3. Attempt to access app | - Console warning: "Email not verified"<br>- No backend token verification call made<br>- Access denied message shown | Automated |
| TC-FE-AUTH-03-02 | Verified email grants access | 1. Sign up with email<br>2. Verify email (via Firebase Admin SDK in test)<br>3. Sign in | - `emailVerified: true` in user object<br>- Backend token verification called<br>- Session created | Automated |
| TC-FE-AUTH-03-03 | Resend verification email | 1. Sign up with unverified email<br>2. Click "Resend verification email" | - `sendEmailVerification()` called<br>- Success toast: "Verification email sent" | Automated |

#### AC-AUTH-04: Firebase ID Token Validation
**Priority**: P0
**Automation**: Jest + Cypress

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-AUTH-04-01 | Token sent to backend on login | 1. Sign in with valid credentials | - `POST /auth/firebase/token` called<br>- `id_token` in request body<br>- `credentials: 'include'` set | Automated |
| TC-FE-AUTH-04-02 | Backend token verification success | 1. Mock backend 200 response<br>2. Complete sign-in | - User data stored in session<br>- Redirect to app dashboard | Automated |
| TC-FE-AUTH-04-03 | Backend token verification failure | 1. Mock backend 400 response<br>2. Complete sign-in | - Error logged to console<br>- User signed out<br>- Error message shown | Automated |
| TC-FE-AUTH-04-04 | Automatic token refresh every 50min | 1. Sign in successfully<br>2. Mock time forward 50min | - `getIdToken(true)` called with force refresh<br>- New token sent to backend | Automated |
| TC-FE-AUTH-04-05 | Token refresh failure signs out user | 1. Sign in successfully<br>2. Mock token refresh failure | - User automatically signed out<br>- Session cleared<br>- Redirect to login | Automated |

#### AC-AUTH-05: OAuth User Migration
**Priority**: P1
**Automation**: Manual (requires existing OAuth users)

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-AUTH-05-01 | Existing OAuth user signs in with Firebase | 1. Sign in with Google (existing OAuth email)<br>2. Check backend logs | - Backend detects OAuth migration<br>- User tier preserved<br>- Firebase UID updated | Manual |

---

### 2. Multi-Factor Authentication (AC-MFA-01 to AC-MFA-07)

#### AC-MFA-01: Mandatory MFA Enrollment During Signup
**Priority**: P0
**Automation**: Cypress E2E

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-MFA-01-01 | MFA wizard shown after first login | 1. Complete email/password signup<br>2. Verify email<br>3. Sign in for first time | - MFA enrollment wizard modal displayed<br>- Cannot dismiss modal (no X button)<br>- Cannot bypass (no "Skip" button) | Automated |
| TC-FE-MFA-01-02 | MFA enrollment required message | 1. View MFA wizard | - Header: "Secure Your Account"<br>- Text: "Multi-factor authentication is required to protect your account" | Automated |
| TC-FE-MFA-01-03 | Cannot access app without MFA | 1. Attempt to close wizard<br>2. Try to navigate to app routes | - Modal remains open<br>- Routes blocked until MFA enrolled | Automated |

#### AC-MFA-02: TOTP-Based MFA Using Authenticator Apps
**Priority**: P0
**Automation**: Cypress + Manual

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-MFA-02-01 | Authenticator app setup instructions | 1. View MFA wizard step 1 | - Text: "Scan QR code with authenticator app"<br>- Supported apps listed (Google Authenticator, Authy, 1Password) | Automated |
| TC-FE-MFA-02-02 | TOTP code input field validation | 1. Enter non-numeric code<br>2. Enter code with wrong length | - Only 6-digit numeric input allowed<br>- Error: "Code must be 6 digits" | Automated |
| TC-FE-MFA-02-03 | Valid TOTP code accepted | 1. Scan QR code with authenticator app<br>2. Enter 6-digit TOTP code | - `POST /auth/mfa/verify-enrollment` called<br>- Code verified successfully | Manual |
| TC-FE-MFA-02-04 | Invalid TOTP code rejected | 1. Enter incorrect 6-digit code<br>2. Submit | - Error: "Invalid code. Please try again."<br>- Input field cleared<br>- Can retry | Automated |

#### AC-MFA-03: QR Code Display (Min 200x200px)
**Priority**: P0
**Automation**: Jest + Cypress

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-MFA-03-01 | QR code displayed on enrollment | 1. Start MFA enrollment<br>2. Check QR code element | - `<img>` or `<canvas>` element present<br>- `src` contains data URI: `data:image/png;base64,` | Automated |
| TC-FE-MFA-03-02 | QR code meets minimum size | 1. Measure QR code dimensions | - Width ≥ 200px<br>- Height ≥ 200px<br>- Aspect ratio 1:1 (square) | Automated |
| TC-FE-MFA-03-03 | QR code alt text for accessibility | 1. Inspect QR code element | - `alt` attribute: "Scan this QR code with your authenticator app" | Automated |
| TC-FE-MFA-03-04 | Manual entry secret shown | 1. View MFA wizard | - Text: "Can't scan? Enter this code manually:"<br>- Secret displayed in monospace font<br>- Copy button available | Automated |

#### AC-MFA-04: 8 Recovery Codes Provided During Setup
**Priority**: P0
**Automation**: Cypress

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-MFA-04-01 | Recovery codes displayed after enrollment | 1. Complete TOTP verification<br>2. Check recovery codes step | - Exactly 8 recovery codes shown<br>- Format: `XXXX-XXXX` (e.g., `A3F9-K2H7`)<br>- Codes use uppercase alphanumeric (no ambiguous chars) | Automated |
| TC-FE-MFA-04-02 | Recovery codes download button | 1. Click "Download codes" | - `.txt` file downloaded<br>- File name: `improv-olympics-recovery-codes-{timestamp}.txt`<br>- All 8 codes in file | Automated |
| TC-FE-MFA-04-03 | Recovery codes copy button | 1. Click "Copy to clipboard" | - Clipboard contains all 8 codes<br>- Success toast: "Recovery codes copied to clipboard" | Automated |

#### AC-MFA-05: User Must Confirm Recovery Codes Saved (Checkbox)
**Priority**: P0
**Automation**: Cypress

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-MFA-05-01 | Checkbox required to proceed | 1. View recovery codes step<br>2. Attempt to click "Continue" without checkbox | - "Continue" button disabled<br>- Or error: "Please confirm you have saved your recovery codes" | Automated |
| TC-FE-MFA-05-02 | Checkbox enables Continue button | 1. Check "I have saved my recovery codes"<br>2. Verify button state | - "Continue" button enabled<br>- Can proceed to app | Automated |
| TC-FE-MFA-05-03 | Checkbox label accessibility | 1. Inspect checkbox element | - `<label>` associated with checkbox via `for` attribute<br>- Label text: "I have saved my recovery codes securely" | Automated |

#### AC-MFA-06: MFA Verification Required on Every Login
**Priority**: P0
**Automation**: Cypress

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-MFA-06-01 | MFA prompt shown on returning login | 1. Sign out after MFA enrollment<br>2. Sign in again | - TOTP code input shown immediately after password<br>- Cannot bypass<br>- No "Remember this device" option | Automated |
| TC-FE-MFA-06-02 | Incorrect TOTP code rejected on login | 1. Enter correct email/password<br>2. Enter incorrect TOTP code | - Error: "Invalid verification code"<br>- Login denied<br>- Can retry | Automated |
| TC-FE-MFA-06-03 | Correct TOTP code grants access | 1. Enter correct email/password<br>2. Enter valid TOTP code | - Login successful<br>- Session created<br>- Redirect to app | Automated |

#### AC-MFA-07: Recovery Code Can Be Used If Authenticator Unavailable
**Priority**: P0
**Automation**: Cypress

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-MFA-07-01 | "Use recovery code" link visible | 1. View TOTP verification prompt | - Link: "Don't have your authenticator app?"<br>- Clicking switches to recovery code input | Automated |
| TC-FE-MFA-07-02 | Recovery code input format | 1. Click "Use recovery code"<br>2. View input field | - Input accepts format `XXXX-XXXX`<br>- Auto-formats with dash (optional)<br>- Case-insensitive | Automated |
| TC-FE-MFA-07-03 | Valid recovery code grants access | 1. Enter valid recovery code<br>2. Submit | - `POST /auth/mfa/verify-recovery` called<br>- Login successful<br>- Code consumed (single-use) | Manual |
| TC-FE-MFA-07-04 | Invalid recovery code rejected | 1. Enter invalid recovery code | - Error: "Invalid recovery code"<br>- Login denied | Automated |
| TC-FE-MFA-07-05 | Used recovery code cannot be reused | 1. Use recovery code successfully<br>2. Sign out and try same code again | - Error: "This recovery code has already been used" | Manual |

---

### 3. Freemium Tier (AC-FREEM-01 to AC-FREEM-07)

#### AC-FREEM-01: New Users Auto-Assigned Freemium Tier on First Login
**Priority**: P0
**Automation**: Cypress + Backend Inspection

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-FREEM-01-01 | New user profile shows freemium tier | 1. Complete signup as new user<br>2. Check `/auth/me` API response | - `tier: "freemium"`<br>- `premium_sessions_used: 0`<br>- `premium_sessions_limit: 2` | Automated |
| TC-FE-FREEM-01-02 | Freemium badge shown in UI | 1. Sign in as freemium user<br>2. Check header/profile section | - Badge or text: "Freemium"<br>- Session counter visible: "🎤 0/2" | Automated |

#### AC-FREEM-02: Freemium Users Limited to 2 Audio Sessions (Lifetime)
**Priority**: P0
**Automation**: Cypress

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-FREEM-02-01 | Session counter shows 0/2 initially | 1. Sign in as new freemium user<br>2. Check header | - Counter visible: "🎤 0/2"<br>- No warning messages | Automated |
| TC-FE-FREEM-02-02 | Session counter increments after 1st session | 1. Complete 1 audio session<br>2. Check counter | - Counter: "🎤 1/2"<br>- Warning toast: "You have 1 free audio session remaining" | Automated |
| TC-FE-FREEM-02-03 | Third audio session blocked | 1. Use 2 audio sessions<br>2. Attempt to start 3rd audio session | - Blocked with 429 status<br>- Counter: "🎤 2/2" | Automated |

#### AC-FREEM-03: Session Counter Visible in Header During Auth'd Pages
**Priority**: P1
**Automation**: Cypress

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-FREEM-03-01 | Counter visible on all authenticated pages | 1. Navigate to different routes while logged in | - Counter visible on: dashboard, settings, session page<br>- Counter NOT visible on: landing, login, signup | Automated |
| TC-FE-FREEM-03-02 | Counter updates in real-time | 1. Complete audio session<br>2. Check counter without page refresh | - Counter updates via WebSocket or API polling<br>- No page refresh required | Automated |
| TC-FE-FREEM-03-03 | Counter hidden for premium users | 1. Sign in as premium user | - No session counter visible<br>- Or shows "Unlimited" | Automated |

#### AC-FREEM-04: Toast Notification Appears After 2nd Session Used
**Priority**: P1
**Automation**: Cypress

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-FREEM-04-01 | Toast shown immediately after 2nd session | 1. Complete 2nd audio session<br>2. Check for toast notification | - Toast appears within 2 seconds<br>- Message: "You've used all 2 free audio sessions. Upgrade to Premium for unlimited access."<br>- Auto-dismisses after 8 seconds | Automated |
| TC-FE-FREEM-04-02 | Toast contains upgrade CTA button | 1. View toast notification | - Button: "Upgrade to Premium"<br>- Clicking opens pricing modal/page | Automated |
| TC-FE-FREEM-04-03 | Toast dismissible by user | 1. Click "X" on toast | - Toast closes immediately | Automated |

#### AC-FREEM-05: Modal Appears on 3rd Audio Session Attempt with Upgrade CTA
**Priority**: P0
**Automation**: Cypress

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-FREEM-05-01 | Upgrade modal blocks 3rd session | 1. Use 2 audio sessions<br>2. Click "Start Audio Session" | - Modal appears immediately<br>- Cannot start session<br>- Modal cannot be dismissed (no X button) | Automated |
| TC-FE-FREEM-05-02 | Modal content clear and actionable | 1. View upgrade modal | - Headline: "Upgrade to Premium"<br>- Message: "You've used all 2 free audio sessions."<br>- Benefits list shown<br>- CTA: "Upgrade Now" button | Automated |
| TC-FE-FREEM-05-03 | Modal shows pricing options | 1. View upgrade modal | - Monthly and annual pricing displayed<br>- Feature comparison table<br>- "Cancel" button (redirects to text mode) | Automated |

#### AC-FREEM-06: Text Mode Remains Unlimited After Audio Limit Reached
**Priority**: P0
**Automation**: Cypress

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-FREEM-06-01 | Text mode accessible after audio limit | 1. Use 2 audio sessions<br>2. Click "Start Text Session" | - Text session starts successfully<br>- No limit enforcement<br>- No upgrade modal shown | Automated |
| TC-FE-FREEM-06-02 | Text mode counter not shown | 1. Use multiple text sessions | - No "Text sessions used" counter<br>- Unlimited text sessions confirmed | Automated |

#### AC-FREEM-07: Premium Users Have Unlimited Audio (Existing Behavior)
**Priority**: P1
**Automation**: Cypress

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-FREEM-07-01 | Premium user has no session counter | 1. Sign in as premium user | - No "🎤 X/Y" counter visible<br>- Or shows "Unlimited" badge | Automated |
| TC-FE-FREEM-07-02 | Premium user can create unlimited sessions | 1. Create 10+ audio sessions | - All sessions start successfully<br>- No limits enforced | Automated |

---

### 4. Accessibility (AC-A11Y-01 to AC-A11Y-03)

#### AC-A11Y-01: MFA Setup Wizard Keyboard Navigable
**Priority**: P0
**Automation**: Cypress (Axe-core)

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-A11Y-01-01 | All interactive elements focusable via Tab | 1. Press Tab repeatedly through wizard | - Focus order logical: QR code → manual entry → TOTP input → Continue button<br>- Visible focus indicator on all elements | Automated |
| TC-FE-A11Y-01-02 | Enter key submits TOTP code | 1. Focus TOTP input field<br>2. Type 6-digit code<br>3. Press Enter | - Form submitted without clicking button | Automated |
| TC-FE-A11Y-01-03 | Esc key dismisses modal (if allowed) | 1. Press Esc key in wizard | - Modal remains open (cannot bypass MFA enrollment)<br>- Or closes if post-enrollment | Automated |
| TC-FE-A11Y-01-04 | Recovery code checkbox toggleable via Space | 1. Tab to "I have saved my codes" checkbox<br>2. Press Space | - Checkbox toggles on/off | Automated |

#### AC-A11Y-02: Screen Readers Announce MFA Steps Correctly
**Priority**: P0
**Automation**: Manual (NVDA/JAWS/VoiceOver)

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-A11Y-02-01 | MFA wizard has proper ARIA labels | 1. Inspect modal element | - `role="dialog"`<br>- `aria-labelledby` points to modal heading<br>- `aria-describedby` points to instructions | Automated |
| TC-FE-A11Y-02-02 | Step progress announced to screen readers | 1. Navigate through wizard with screen reader | - "Step 1 of 3: Scan QR Code"<br>- "Step 2 of 3: Verify Code"<br>- "Step 3 of 3: Save Recovery Codes" | Manual |
| TC-FE-A11Y-02-03 | Error messages announced immediately | 1. Enter invalid TOTP code<br>2. Trigger error | - `aria-live="assertive"` on error container<br>- Screen reader announces: "Error: Invalid code. Please try again." | Manual |
| TC-FE-A11Y-02-04 | QR code described for non-visual users | 1. Focus QR code area with screen reader | - Alt text: "QR code to scan with your authenticator app"<br>- Or hidden from screen reader with manual entry option announced | Manual |

#### AC-A11Y-03: All Form Inputs Have Proper Labels and Error States
**Priority**: P0
**Automation**: Cypress (Axe-core)

| Test ID | Description | Steps | Expected Result | Status |
|---------|-------------|-------|-----------------|--------|
| TC-FE-A11Y-03-01 | Email input has associated label | 1. Inspect email field | - `<label for="email">Email</label>` associated<br>- Or `aria-label="Email"` if using placeholder | Automated |
| TC-FE-A11Y-03-02 | Password input has associated label | 1. Inspect password field | - `<label for="password">Password</label>` associated<br>- Password strength indicator accessible | Automated |
| TC-FE-A11Y-03-03 | TOTP input has label and format hint | 1. Inspect TOTP field | - Label: "Verification Code"<br>- `aria-describedby` points to "Enter 6-digit code from your app" | Automated |
| TC-FE-A11Y-03-04 | Error states use aria-invalid | 1. Submit form with errors<br>2. Inspect invalid fields | - `aria-invalid="true"` set<br>- `aria-describedby` points to error message ID | Automated |
| TC-FE-A11Y-03-05 | Required fields marked with aria-required | 1. Inspect all form fields | - Required inputs have `aria-required="true"`<br>- Or visual "*" with `<span aria-label="required">*</span>` | Automated |

---

## Edge Cases and Error Scenarios

### Authentication Edge Cases

| Test ID | Description | Expected Behavior | Priority | Status |
|---------|-------------|-------------------|----------|--------|
| TC-EDGE-AUTH-01 | Network timeout during signup | Timeout error shown with retry button | P1 | Automated |
| TC-EDGE-AUTH-02 | Backend unavailable during token verification | Graceful degradation: "Service temporarily unavailable" | P1 | Automated |
| TC-EDGE-AUTH-03 | User closes browser during MFA enrollment | On return: enrollment session expired, restart wizard | P2 | Manual |
| TC-EDGE-AUTH-04 | Multiple tabs open during login | Session synced across tabs via localStorage events | P2 | Manual |
| TC-EDGE-AUTH-05 | Token refresh fails during active session | User signed out with clear message | P1 | Automated |

### MFA Edge Cases

| Test ID | Description | Expected Behavior | Priority | Status |
|---------|-------------|-------------------|----------|--------|
| TC-EDGE-MFA-01 | User scans QR code but enters wrong code 3 times | Rate limiting: "Too many failed attempts. Try again in 1 minute." | P1 | Automated |
| TC-EDGE-MFA-02 | User loses all recovery codes and authenticator | Support contact info shown: "Contact support@improvoly.com" | P2 | Manual |
| TC-EDGE-MFA-03 | QR code fails to load (image load error) | Fallback to manual entry displayed prominently | P1 | Automated |
| TC-EDGE-MFA-04 | User downloads recovery codes but doesn't check checkbox | "Continue" button remains disabled | P0 | Automated |
| TC-EDGE-MFA-05 | System clock skew (TOTP time mismatch) | Validation uses window=1 (±30 seconds tolerance) | P1 | Manual |

### Freemium Edge Cases

| Test ID | Description | Expected Behavior | Priority | Status |
|---------|-------------|-------------------|----------|--------|
| TC-EDGE-FREEM-01 | Concurrent session creation at limit | Firestore transaction prevents race condition | P1 | Automated |
| TC-EDGE-FREEM-02 | User at 1/2 sessions opens 2 tabs and starts sessions | Only 1 session succeeds, other shows limit reached | P1 | Manual |
| TC-EDGE-FREEM-03 | Session counter stuck at 1/2 after backend update | Frontend polls/WebSocket updates counter in real-time | P2 | Automated |
| TC-EDGE-FREEM-04 | Premium user downgraded to freemium mid-session | Current session completes, next session blocked | P2 | Manual |
| TC-EDGE-FREEM-05 | User manually increments counter via DevTools | Backend validates session count server-side (trusted source) | P0 | Manual |

---

## Manual Testing Procedures for UI/UX Flows

### Manual Test 1: Complete MFA Enrollment Flow (E2E)
**Estimated Time**: 10 minutes
**Prerequisites**: Firebase project configured, authenticator app installed

**Steps**:
1. Navigate to signup page
2. Create new account with email/password
3. Verify email via link (check inbox)
4. Sign in for first time
5. **MFA Wizard Step 1**: Scan QR code with Google Authenticator
6. Verify QR code size is at least 200x200px (use browser inspector)
7. **MFA Wizard Step 2**: Enter 6-digit TOTP code from app
8. **MFA Wizard Step 3**: View 8 recovery codes
9. Download codes as `.txt` file
10. Check "I have saved my recovery codes" checkbox
11. Click "Continue"
12. Verify redirect to dashboard

**Expected Results**:
- ✅ QR code scannable and correctly sized
- ✅ TOTP code accepted
- ✅ 8 recovery codes in format `XXXX-XXXX`
- ✅ Cannot proceed without checkbox
- ✅ Smooth wizard flow with clear instructions

**Failure Criteria**:
- ❌ QR code too small or blurry
- ❌ TOTP code rejected despite being correct
- ❌ Fewer/more than 8 recovery codes
- ❌ Can bypass wizard without completing steps

---

### Manual Test 2: Freemium Session Limit Enforcement (E2E)
**Estimated Time**: 15 minutes
**Prerequisites**: Freemium user account

**Steps**:
1. Sign in as freemium user
2. Verify session counter shows "🎤 0/2" in header
3. Start **first audio session**, complete 30-second scene
4. End session, verify counter updates to "🎤 1/2"
5. Verify toast notification: "You have 1 free audio session remaining"
6. Start **second audio session**, complete 30-second scene
7. End session, verify counter updates to "🎤 2/2"
8. Verify toast notification: "You've used all 2 free audio sessions. Upgrade to Premium for unlimited access."
9. Attempt to start **third audio session**
10. Verify upgrade modal appears and blocks session creation
11. Click "Cancel" on modal
12. Start **text session** (should succeed)
13. Complete text session (unlimited, no blocking)

**Expected Results**:
- ✅ Counter accurate after each session
- ✅ Toast notifications appear at correct times
- ✅ Upgrade modal blocks 3rd audio session
- ✅ Text mode remains unlimited

**Failure Criteria**:
- ❌ Counter not updating correctly
- ❌ Can start 3rd audio session
- ❌ Text mode also blocked

---

### Manual Test 3: MFA Login with Recovery Code
**Estimated Time**: 5 minutes
**Prerequisites**: Account with MFA enabled, recovery codes saved

**Steps**:
1. Sign out
2. Sign in with email/password
3. At TOTP verification prompt, click "Don't have your authenticator app?"
4. Verify recovery code input field appears
5. Enter one of the saved recovery codes (format: `XXXX-XXXX`)
6. Submit code
7. Verify successful login
8. Sign out and sign in again
9. Attempt to use the same recovery code again
10. Verify error: "This recovery code has already been used"

**Expected Results**:
- ✅ Recovery code link visible and clickable
- ✅ Recovery code input accepts format
- ✅ First use of code grants access
- ✅ Second use of same code rejected (single-use enforcement)

**Failure Criteria**:
- ❌ Recovery code can be reused
- ❌ Valid recovery code rejected

---

### Manual Test 4: Screen Reader Compatibility (NVDA/JAWS)
**Estimated Time**: 15 minutes
**Prerequisites**: NVDA or JAWS installed

**Steps**:
1. Enable screen reader
2. Navigate to signup page
3. **Tab through form fields**: email, password, confirm password, submit button
4. Verify labels announced correctly
5. Trigger validation error (e.g., invalid email)
6. Verify error message announced immediately
7. Complete signup, proceed to **MFA wizard**
8. Navigate through wizard steps with Tab key only
9. Verify step progress announced: "Step 1 of 3: Scan QR Code"
10. Verify QR code has descriptive alt text
11. Verify TOTP input field labeled correctly
12. Submit invalid TOTP code
13. Verify error announced immediately
14. Navigate to **recovery codes step**
15. Verify recovery codes readable in list format

**Expected Results**:
- ✅ All interactive elements focusable and labeled
- ✅ Error messages announced with `aria-live`
- ✅ MFA wizard step progress announced
- ✅ Recovery codes accessible via list navigation

**Failure Criteria**:
- ❌ Unlabeled form fields
- ❌ Errors not announced
- ❌ Focus order illogical

---

## Cross-Browser Compatibility Testing

**Test on**: Chrome (latest), Firefox (latest), Safari (latest), Edge (latest)

| Feature | Chrome | Firefox | Safari | Edge | Priority |
|---------|--------|---------|--------|------|----------|
| Email/password signup | ✓ | ✓ | ✓ | ✓ | P0 |
| Google Sign-In popup | ✓ | ✓ | ✓ | ✓ | P0 |
| QR code rendering | ✓ | ✓ | ✓ | ✓ | P0 |
| TOTP input auto-focus | ✓ | ✓ | ✓ | ✓ | P1 |
| Session counter display | ✓ | ✓ | ✓ | ✓ | P1 |
| Toast notifications | ✓ | ✓ | ✓ | ✓ | P1 |
| Modal overlay styling | ✓ | ✓ | ✓ | ✓ | P1 |
| Clipboard copy (recovery codes) | ✓ | ✓ | ✓ | ✓ | P2 |
| Download recovery codes | ✓ | ✓ | ✓ | ✓ | P2 |

---

## Test Environment Setup

### Frontend Test Stack

```bash
# Install test dependencies
npm install --save-dev \
  jest \
  @testing-library/react \
  @testing-library/jest-dom \
  @testing-library/user-event \
  cypress \
  @cypress/code-coverage \
  axe-core \
  cypress-axe

# Run unit tests
npm run test:unit

# Run E2E tests
npm run test:e2e

# Run accessibility tests
npm run test:a11y
```

### Test Data Setup

**Create test users in Firebase Authentication**:
```javascript
// tests/fixtures/test-users.js
export const TEST_USERS = {
  freemium: {
    email: 'freemium-test@improvoly.com',
    password: 'TestPassword123!',
    tier: 'freemium',
    sessions_used: 0
  },
  premium: {
    email: 'premium-test@improvoly.com',
    password: 'TestPassword123!',
    tier: 'premium'
  },
  mfa_enrolled: {
    email: 'mfa-test@improvoly.com',
    password: 'TestPassword123!',
    mfa_secret: 'JBSWY3DPEHPK3PXP', // Fixed TOTP secret for testing
    recovery_codes: [
      'A3F9-K2H7',
      'B8D2-M4N6',
      // ... 6 more codes
    ]
  }
};
```

---

## Test Execution Commands

```bash
# Run all frontend tests
npm run test

# Run specific test suites
npm run test:auth          # Firebase auth tests
npm run test:mfa           # MFA wizard tests
npm run test:freemium      # Freemium tier tests
npm run test:a11y          # Accessibility tests

# Run E2E tests in headless mode (CI)
npm run test:e2e:ci

# Run E2E tests with interactive UI (local development)
npm run test:e2e:open

# Generate test coverage report
npm run test:coverage

# Run tests in watch mode (TDD)
npm run test:watch
```

---

## Success Criteria

**Test execution must meet the following criteria for release approval**:

1. ✅ **85% automated test coverage** across all acceptance criteria
2. ✅ **All P0 tests passing** in at least Chrome and Firefox
3. ✅ **All accessibility tests passing** (WCAG 2.1 AA compliance)
4. ✅ **Manual E2E flows completed** by QA engineer with no critical issues
5. ✅ **Cross-browser compatibility verified** on all 4 major browsers
6. ✅ **No critical (P0) or high (P1) severity bugs** remaining unresolved
7. ✅ **Performance baseline met**: Page load < 3 seconds, MFA wizard renders < 500ms

---

## Test Gap Analysis

**Current Coverage vs. Requirements**:

| Category | Backend Tests | Frontend Tests Needed | Gap |
|----------|---------------|----------------------|-----|
| Firebase Auth (AC-AUTH-01 to 05) | ✅ Complete | ❌ Missing E2E flows | **High priority** |
| MFA Logic (AC-MFA-01 to 07) | ✅ Complete | ⚠️ Partial (no UI tests) | **High priority** |
| Freemium Tier (AC-FREEM-01 to 07) | ✅ Complete | ❌ Missing UI/UX tests | **Medium priority** |
| Accessibility (AC-A11Y-01 to 03) | N/A | ❌ Missing entirely | **High priority** |
| Cross-browser compatibility | N/A | ❌ Missing | **Medium priority** |

**Recommended Test Implementation Order**:
1. **Priority 1 (Week 1)**: Firebase auth E2E flows (TC-FE-AUTH-*)
2. **Priority 2 (Week 1)**: MFA wizard UI tests (TC-FE-MFA-*)
3. **Priority 3 (Week 2)**: Freemium session counter and modals (TC-FE-FREEM-*)
4. **Priority 4 (Week 2)**: Accessibility automated tests (TC-FE-A11Y-*)
5. **Priority 5 (Week 3)**: Manual E2E flows and cross-browser testing

---

## Known Risks and Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Firebase Authentication SDK breaking changes | High | Pin Firebase SDK version, monitor release notes |
| QR code rendering issues on mobile | Medium | Test on actual devices (iOS Safari, Android Chrome) |
| TOTP time synchronization issues | Medium | Use window=1 for tolerance, educate users |
| Recovery code single-use not enforced client-side | High | Backend validation is source of truth (already implemented) |
| Session counter out of sync | Medium | Implement WebSocket real-time updates |
| Accessibility failures in MFA wizard | High | Run Axe-core on every wizard step, manual NVDA testing |

---

## Appendix: Test Automation Code Examples

### Example: Jest Test for Email Signup Form Validation

```javascript
// tests/unit/firebase-auth.test.js
import { signUpWithEmail } from '../../app/static/firebase-auth.js';

describe('Email Signup Form Validation (TC-FE-AUTH-01-01)', () => {
  it('should reject invalid email format', async () => {
    const invalidEmail = 'not-an-email';
    const password = 'ValidPass123!';

    await expect(signUpWithEmail(invalidEmail, password))
      .rejects
      .toThrow('Please enter a valid email address.');
  });

  it('should reject weak password', async () => {
    const email = 'test@example.com';
    const weakPassword = '12345'; // < 6 characters

    await expect(signUpWithEmail(email, weakPassword))
      .rejects
      .toThrow('Password must be at least 6 characters long.');
  });
});
```

### Example: Cypress Test for MFA QR Code Size

```javascript
// cypress/e2e/mfa-enrollment.cy.js
describe('MFA QR Code Display (TC-FE-MFA-03-02)', () => {
  it('should display QR code with minimum 200x200px dimensions', () => {
    // Sign up and trigger MFA enrollment
    cy.visit('/signup');
    cy.get('#email').type('test@example.com');
    cy.get('#password').type('TestPass123!');
    cy.get('button[type="submit"]').click();

    // Wait for MFA wizard
    cy.get('[data-testid="mfa-wizard"]').should('be.visible');

    // Check QR code dimensions
    cy.get('[data-testid="mfa-qr-code"]')
      .should('be.visible')
      .and(($img) => {
        expect($img.width()).to.be.at.least(200);
        expect($img.height()).to.be.at.least(200);
      });
  });
});
```

### Example: Cypress Accessibility Test with Axe

```javascript
// cypress/e2e/accessibility.cy.js
import 'cypress-axe';

describe('MFA Wizard Accessibility (TC-FE-A11Y-01-01)', () => {
  it('should have no accessibility violations', () => {
    cy.visit('/signup');
    // Complete signup...

    // Wait for MFA wizard
    cy.get('[data-testid="mfa-wizard"]').should('be.visible');

    // Run axe accessibility scan
    cy.injectAxe();
    cy.checkA11y('[data-testid="mfa-wizard"]', {
      rules: {
        'color-contrast': { enabled: true },
        'label': { enabled: true },
        'aria-required-attr': { enabled: true }
      }
    });
  });
});
```

---

**Document Version**: 1.0
**Last Updated**: 2025-12-02
**Next Review**: After Week 1 test implementation completion
