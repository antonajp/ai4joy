# UX Requirements: Firebase Authentication Migration with MFA & Freemium Model

**Document Version:** 1.0
**Date:** 2025-12-02
**Status:** Draft for Review

---

## Executive Summary

This document defines the user experience requirements for migrating from Google OAuth to Firebase Authentication with mandatory MFA and implementing a freemium tier with session limits.

### Current State Analysis

**Authentication:**
- Simple Google OAuth flow via `/auth/login` → Google consent screen → `/auth/callback`
- Session-based authentication using secure httponly cookies (24-hour expiration)
- Binary access control: authenticated users can access all features
- Clean, accessible landing page at `/static/index.html` with "Sign In" button

**User Tiers (Existing):**
- FREE, REGULAR, PREMIUM tiers defined in `UserProfile` model
- Premium users get audio (voice mode) access
- No session limits currently enforced on freemium users
- Tier information stored in Firestore `users` collection

**Current UX Strengths to Preserve:**
- WCAG 2.1 AA compliant design with excellent keyboard navigation
- Mobile-first responsive design
- Clear visual hierarchy and accessible focus indicators
- Skip links and screen reader support
- Clean, uncluttered interface with progressive disclosure

---

## 1. Sign Up / Login Flow Updates

### 1.1 Landing Page Changes

**Current Behavior:**
- Single "Sign In" button that redirects to Google OAuth

**New Behavior:**
- **Dual Entry Points:**
  - "Sign In" button for existing users
  - "Create Account" button for new signups
  - Maintain visual hierarchy: "Create Account" as primary CTA, "Sign In" as secondary

**Visual Design:**

```
┌─────────────────────────────────────────────────┐
│  Improv Olympics                    [Sign In]   │
└─────────────────────────────────────────────────┘

        Practice Collaboration Through AI Improv

        Rebuild your social confidence in a safe,
        judgment-free environment.

        ┌────────────────────────────────┐
        │    [Create Free Account]       │  ← Primary CTA
        │                                 │
        │    Already have an account?     │
        │    [Sign In]                    │  ← Secondary CTA
        └────────────────────────────────┘
```

**Acceptance Criteria:**
- [ ] Two distinct CTAs visible on landing page
- [ ] "Create Account" uses primary button styling (--primary color)
- [ ] "Sign In" uses secondary button styling
- [ ] Both buttons meet WCAG 2.1 AA contrast requirements (4.5:1)
- [ ] Both buttons have minimum 44x44px touch targets
- [ ] Clear visual separation between signup and login paths
- [ ] Buttons remain accessible via keyboard navigation (Tab order: Create Account → Sign In)

---

### 1.2 Authentication Modal Design

**Modal Structure:**

Instead of redirecting to external pages, use a modal overlay for auth flows to maintain context.

```
┌─────────────────────────────────────────────────────────┐
│                                                     [×]  │
│  Create Your Free Account                               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━                            │
│                                                          │
│  Email                                                   │
│  ┌────────────────────────────────────────────┐        │
│  │ your.email@example.com                     │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  Password                                                │
│  ┌────────────────────────────────────────────┐        │
│  │ ••••••••••••                [👁]          │        │
│  └────────────────────────────────────────────┘        │
│  ↳ 8+ characters, 1 number, 1 special character        │
│                                                          │
│  Confirm Password                                        │
│  ┌────────────────────────────────────────────┐        │
│  │ ••••••••••••                [👁]          │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │     [Create Account & Set Up Security]     │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  ──────────────── OR ────────────────                  │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │  [G] Continue with Google                  │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  By creating an account, you agree to our               │
│  Terms of Service and Privacy Policy                    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Login Modal (Simpler):**

```
┌─────────────────────────────────────────────────────────┐
│                                                     [×]  │
│  Sign In to Improv Olympics                             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━                            │
│                                                          │
│  Email                                                   │
│  ┌────────────────────────────────────────────┐        │
│  │ your.email@example.com                     │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  Password                                                │
│  ┌────────────────────────────────────────────┐        │
│  │ ••••••••••••                [👁]          │        │
│  └────────────────────────────────────────────┘        │
│  [Forgot password?]                                     │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │          [Sign In]                          │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  ──────────────── OR ────────────────                  │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │  [G] Continue with Google                  │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  Don't have an account? [Create one]                    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Design Decisions:**

1. **Keep Google OAuth Option:** Yes, support both email/password AND Google OAuth via Firebase
   - Reduces friction for users who prefer OAuth
   - Firebase supports multiple authentication providers
   - Users still required to set up MFA after OAuth sign-in

2. **Password Requirements:**
   - Minimum 8 characters
   - At least 1 number
   - At least 1 special character
   - Real-time validation with inline feedback
   - Show password strength indicator (Weak/Fair/Strong/Very Strong)

3. **Progressive Disclosure:**
   - Don't show password requirements until user focuses on password field
   - Use aria-describedby to associate requirements with input

**Acceptance Criteria:**

**Signup Form:**
- [ ] Email input with type="email" for built-in validation
- [ ] Password field with show/hide toggle (accessibility: aria-label="Show password")
- [ ] Confirm password field with real-time matching validation
- [ ] Password strength indicator updates as user types
- [ ] All validation errors displayed inline with aria-live="polite"
- [ ] Form validation prevents submission until all requirements met
- [ ] Google OAuth button maintains consistent styling
- [ ] Clear visual separator between email/password and OAuth options
- [ ] Terms of Service and Privacy Policy links (WCAG requires accessible links)

**Login Form:**
- [ ] Email and password inputs with appropriate autocomplete attributes
- [ ] "Forgot password?" link clearly visible
- [ ] Google OAuth option available
- [ ] "Create account" link for users who need to sign up
- [ ] All error messages displayed in aria-live region

**Accessibility:**
- [ ] Modal has role="dialog" and aria-modal="true"
- [ ] Modal has aria-labelledby pointing to modal title
- [ ] Focus trapped within modal while open
- [ ] Escape key closes modal
- [ ] Clicking overlay closes modal
- [ ] Focus returns to triggering element on close
- [ ] All form labels properly associated with inputs
- [ ] Error messages announced to screen readers

**Mobile Responsiveness:**
- [ ] Modal fills screen on mobile (<768px) with comfortable padding
- [ ] Input fields have min-height: 44px for touch targets
- [ ] Password toggle buttons are easily tappable (44x44px)
- [ ] Keyboard doesn't obscure critical UI elements on mobile
- [ ] Form remains usable in landscape orientation

---

## 2. MFA Enrollment Experience

### 2.1 Timing Decision: When to Require MFA Setup

**Recommendation: Immediate enrollment after signup, delayed for OAuth users**

**Rationale:**
1. **Security-first approach:** Users expect security setup during account creation
2. **Cognitive freshness:** User is already in "setup mode" during signup
3. **Reduced friction:** Don't interrupt users mid-session later
4. **Clear user flow:** Signup → Security setup → Start using app

**User Flow:**

```
New User (Email/Password)
  ↓
Signup Form Submitted
  ↓
Account Created in Firebase
  ↓
MFA Setup Wizard (MANDATORY)
  ↓
MFA Verified
  ↓
Redirect to Dashboard/Landing Page (authenticated)

OAuth User (Google)
  ↓
OAuth Consent Screen
  ↓
Account Created/Linked
  ↓
MFA Status Check
  ├─ MFA Already Set Up → Redirect to MFA Verification
  └─ MFA Not Set Up → MFA Setup Wizard (MANDATORY)
```

---

### 2.2 MFA Method Selection

**Recommendation: TOTP (Authenticator Apps) as primary, SMS as backup**

**Rationale:**
1. **Security:** TOTP is more secure than SMS (SIM swapping attacks)
2. **Cost:** TOTP has no per-use cost, SMS does
3. **User Preference:** Power users prefer authenticator apps
4. **Accessibility:** Authenticator apps work without cellular service

**MFA Setup Wizard - Step 1: Choose Method**

```
┌─────────────────────────────────────────────────────────┐
│                                                          │
│  Set Up Two-Factor Authentication                        │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                      │
│                                                          │
│  Two-factor authentication adds an extra layer of        │
│  security to your account. Choose your preferred method: │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  📱 Authenticator App (Recommended)              │  │
│  │     Use Google Authenticator, Authy, or similar  │  │
│  │     [Select]                                     │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  💬 Text Message (SMS)                           │  │
│  │     Receive codes via text message               │  │
│  │     [Select]                                     │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  Progress: Step 1 of 3                                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

### 2.3 TOTP Setup Flow

**Step 2: Scan QR Code**

```
┌─────────────────────────────────────────────────────────┐
│                                                     [×]  │
│  Set Up Authenticator App                               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━                            │
│                                                          │
│  1. Open your authenticator app                         │
│     (Google Authenticator, Authy, 1Password, etc.)      │
│                                                          │
│  2. Scan this QR code:                                  │
│                                                          │
│     ┌─────────────────────────────┐                     │
│     │                             │                     │
│     │    [QR CODE IMAGE]          │                     │
│     │                             │                     │
│     └─────────────────────────────┘                     │
│                                                          │
│  Can't scan? [Enter setup key manually]                 │
│                                                          │
│  ──────────────────────────────────────                 │
│                                                          │
│  Setup Key (for manual entry):                          │
│  ABCD EFGH IJKL MNOP QRST UVWX YZ12                    │
│  [Copy]                                                 │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │             [Continue]                      │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  Progress: Step 2 of 3                                   │
│  [← Back]                                                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Step 3: Verify Code**

```
┌─────────────────────────────────────────────────────────┐
│                                                     [×]  │
│  Verify Your Setup                                       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━                            │
│                                                          │
│  Enter the 6-digit code from your authenticator app:    │
│                                                          │
│  ┌───┬───┬───┬───┬───┬───┐                             │
│  │ 1 │ 2 │ 3 │ 4 │ 5 │ 6 │                             │
│  └───┴───┴───┴───┴───┴───┘                             │
│                                                          │
│  Code refreshes in: 25 seconds                          │
│                                                          │
│  ✓ Code verified successfully!                          │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │        [Continue to Recovery Codes]         │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  Progress: Step 3 of 4                                   │
│  [← Back]                                                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Step 4: Save Recovery Codes**

```
┌─────────────────────────────────────────────────────────┐
│                                                     [×]  │
│  Save Your Recovery Codes                                │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━                            │
│                                                          │
│  ⚠️ Important: Save these codes in a secure place       │
│                                                          │
│  If you lose access to your authenticator app, you      │
│  can use these codes to sign in. Each code can only     │
│  be used once.                                          │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │  1.  ABCD-EFGH-IJKL                        │        │
│  │  2.  MNOP-QRST-UVWX                        │        │
│  │  3.  YZ12-3456-7890                        │        │
│  │  4.  ABCD-EFGH-IJKL                        │        │
│  │  5.  MNOP-QRST-UVWX                        │        │
│  │  6.  YZ12-3456-7890                        │        │
│  │  7.  ABCD-EFGH-IJKL                        │        │
│  │  8.  MNOP-QRST-UVWX                        │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │     [Download Codes]    [Copy to Clipboard]│        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  ☑ I have saved these codes in a secure place          │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │          [Complete Setup]                   │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  Progress: Step 4 of 4                                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Success State:**

```
┌─────────────────────────────────────────────────────────┐
│                                                          │
│                    ✓                                     │
│                                                          │
│            Your Account is Secure!                       │
│                                                          │
│  Two-factor authentication has been enabled.             │
│  You'll be prompted for a code each time you sign in.   │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │       [Start Your First Session]            │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

### 2.4 SMS Setup Flow (Alternative)

**Step 2: Verify Phone Number**

```
┌─────────────────────────────────────────────────────────┐
│                                                     [×]  │
│  Verify Your Phone Number                               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━                            │
│                                                          │
│  Enter your mobile phone number:                        │
│                                                          │
│  Country                                                 │
│  ┌────────────────────────────────────────────┐        │
│  │  🇺🇸 United States (+1)           [▼]     │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  Phone Number                                            │
│  ┌────────────────────────────────────────────┐        │
│  │  (555) 123-4567                             │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  Standard message and data rates may apply.              │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │          [Send Verification Code]           │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  Progress: Step 2 of 3                                   │
│  [← Back]                                                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Step 3: Enter SMS Code**

```
┌─────────────────────────────────────────────────────────┐
│                                                     [×]  │
│  Enter Verification Code                                │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━                            │
│                                                          │
│  We sent a 6-digit code to:                             │
│  (555) 123-4567  [Edit]                                 │
│                                                          │
│  ┌───┬───┬───┬───┬───┬───┐                             │
│  │ 1 │ 2 │ 3 │ 4 │ 5 │ 6 │                             │
│  └───┴───┴───┴───┴───┴───┘                             │
│                                                          │
│  Didn't receive the code? [Resend] (Available in 45s)  │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │             [Verify Code]                   │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  Progress: Step 3 of 3                                   │
│  [← Back]                                                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

### 2.5 MFA Login Experience (Returning Users)

**After Entering Email/Password:**

```
┌─────────────────────────────────────────────────────────┐
│                                                     [×]  │
│  Two-Factor Authentication                               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━                            │
│                                                          │
│  📱 Enter the 6-digit code from your authenticator app: │
│                                                          │
│  ┌───┬───┬───┬───┬───┬───┐                             │
│  │   │   │   │   │   │   │                             │
│  └───┴───┴───┴───┴───┴───┘                             │
│                                                          │
│  ☑ Trust this device for 30 days                       │
│                                                          │
│  Lost your device? [Use recovery code]                  │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │             [Verify & Sign In]              │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  [← Back to Sign In]                                    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Using Recovery Code:**

```
┌─────────────────────────────────────────────────────────┐
│                                                     [×]  │
│  Use Recovery Code                                       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━                            │
│                                                          │
│  Enter one of your 8 backup recovery codes:              │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │  ABCD-EFGH-IJKL                             │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  ⚠️ Note: Each recovery code can only be used once      │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │         [Verify & Sign In]                  │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  [← Back to Two-Factor Authentication]                  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

### 2.6 MFA Error States

**Invalid Code:**

```
┌─────────────────────────────────────────────────────────┐
│  ❌ Invalid verification code                           │
│     Please check your authenticator app and try again.  │
│                                                          │
│  ┌───┬───┬───┬───┬───┬───┐                             │
│  │   │   │   │   │   │   │  ← Input border red         │
│  └───┴───┴───┴───┴───┴───┘                             │
│                                                          │
│  Attempts remaining: 2 of 3                             │
└─────────────────────────────────────────────────────────┘
```

**Too Many Failed Attempts:**

```
┌─────────────────────────────────────────────────────────┐
│  ⚠️ Account Temporarily Locked                          │
│                                                          │
│  Too many failed verification attempts.                 │
│  Please try again in 15 minutes, or use a recovery code.│
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │       [Use Recovery Code Instead]           │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  Need help? [Contact Support]                           │
└─────────────────────────────────────────────────────────┘
```

---

### 2.7 MFA Acceptance Criteria

**Setup Flow:**
- [ ] User cannot skip MFA setup during initial signup
- [ ] Clear progress indicator shows current step (Step X of Y)
- [ ] QR code is at least 200x200px for easy scanning
- [ ] Manual entry key is displayed in monospace font with clear spacing
- [ ] Copy button provides visual feedback ("Copied!") for 2 seconds
- [ ] Recovery codes use monospace font with consistent formatting
- [ ] "Download Codes" generates .txt file with clear filename (improv-olympics-recovery-codes-YYYY-MM-DD.txt)
- [ ] Checkbox confirmation required before completing setup
- [ ] Setup cannot be completed without saving recovery codes

**Login Flow:**
- [ ] MFA prompt appears immediately after password verification
- [ ] Code input auto-advances between digits
- [ ] Code input auto-submits when 6th digit entered
- [ ] "Trust this device" option clearly explained with duration
- [ ] Recovery code option clearly visible and accessible
- [ ] Failed attempts counter displayed to user

**Accessibility:**
- [ ] All wizard steps have proper heading hierarchy (h2 for main heading)
- [ ] Progress indicator has aria-label describing current step
- [ ] QR code has alt text: "QR code to set up two-factor authentication"
- [ ] Manual entry key is selectable for screen reader users
- [ ] Recovery code list has proper list markup (ul/ol)
- [ ] All error messages announced via aria-live="assertive"
- [ ] Code input fields have aria-label="Digit 1 of 6", etc.

**Mobile Responsiveness:**
- [ ] QR code remains scannable at reduced sizes (min 180x180px on mobile)
- [ ] Code input fields are large enough for touch (min 44x44px)
- [ ] Manual entry key wraps appropriately on narrow screens
- [ ] All buttons remain accessible (min 44x44px)
- [ ] Recovery codes display in scrollable container on small screens

---

## 3. Freemium User Experience

### 3.1 Tier Structure

**Current Implementation:**
- FREE tier: No audio access (text-only sessions)
- REGULAR tier: No audio access (text-only sessions)
- PREMIUM tier: 1 hour audio per reset period

**New Freemium Model:**
- **Freemium tier:** 2 premium (audio) sessions maximum, then unlimited text sessions
- **Premium tier:** Unlimited audio sessions

### 3.2 Session Counter Display

**Location:** Persistent UI element visible after authentication

**Visual Design - Header Implementation:**

```
┌─────────────────────────────────────────────────────────┐
│  Improv Olympics                                         │
│                                                          │
│  🎤 Voice Sessions: 1 / 2 remaining   [Upgrade]  [👤]  │
└─────────────────────────────────────────────────────────┘
```

**Alternative: Dashboard Card (Landing Page)**

```
┌─────────────────────────────────────────────────────────┐
│  Your Practice Plan                                      │
│  ━━━━━━━━━━━━━━━━━━━                                    │
│                                                          │
│  Free Tier                                               │
│                                                          │
│  🎤 Voice Sessions                                      │
│  ████████░░░░░░░░░░░░  1 of 2 used                     │
│                                                          │
│  💬 Text Sessions                                        │
│  Unlimited                                               │
│                                                          │
│  [Upgrade to Premium] for unlimited voice sessions       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Mobile Implementation:**

```
┌─────────────────────────┐
│  Improv Olympics    [≡] │
│                         │
│  🎤 1/2 Voice  [Premium]│
└─────────────────────────┘
```

**Acceptance Criteria:**
- [ ] Session counter visible on all authenticated pages
- [ ] Counter updates immediately after session completion
- [ ] Visual distinction between used and remaining sessions (progress bar)
- [ ] Counter displays "0 of 2" when no sessions remain (not hidden)
- [ ] "Upgrade" CTA always visible, becomes more prominent when 0 sessions remain
- [ ] Counter has aria-live="polite" for screen reader announcements
- [ ] Mobile version maintains readability (condensed format)

---

### 3.3 Session Limit Warning Flow

**First Session (2 remaining → 1 remaining):**

No intrusive warning, just update the counter. User can see they have 1 session left.

**Second Session (1 remaining → 0 remaining):**

Show toast notification after session ends:

```
┌─────────────────────────────────────────────────────────┐
│  ℹ️ Voice Session Limit Reached                         │
│                                                          │
│  You've used your 2 free voice sessions.                │
│  You can still practice with unlimited text sessions.    │
│                                                          │
│  [View Upgrade Options]  [Continue with Text]           │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Attempting Third Session (0 remaining):**

**Interstitial Modal (Blocks Action):**

```
┌─────────────────────────────────────────────────────────┐
│                                                     [×]  │
│  Voice Session Limit Reached                             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━                            │
│                                                          │
│  🎤 You've used all 2 of your free voice sessions.      │
│                                                          │
│  You have two options:                                   │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │  ✨ Upgrade to Premium                      │        │
│  │     • Unlimited voice sessions              │        │
│  │     • Priority support                      │        │
│  │     • Advanced features                     │        │
│  │                                             │        │
│  │     [Upgrade to Premium - $9.99/month]      │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │  💬 Continue with Text Sessions (Free)      │        │
│  │     • Unlimited text-based practice         │        │
│  │     • All improv games available            │        │
│  │                                             │        │
│  │     [Start Text Session]                    │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

### 3.4 Upgrade Prompts and Messaging

**Principles:**
1. **Non-intrusive:** Don't interrupt sessions or nag repeatedly
2. **Value-focused:** Emphasize benefits, not limitations
3. **Clear pricing:** No hidden fees or confusing tiers
4. **Easy dismissal:** User can always choose "Continue with Text"

**Upgrade CTA Locations:**

1. **Header (always visible):** Small "Upgrade" button next to session counter
2. **Session limit reached:** Modal shown when attempting 3rd voice session
3. **Post-session:** Optional tooltip after 2nd session: "Enjoying voice mode? Upgrade for unlimited access"

**Upgrade Modal - Detailed:**

```
┌─────────────────────────────────────────────────────────┐
│                                                     [×]  │
│  Upgrade to Premium                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━                            │
│                                                          │
│  Unlock unlimited voice sessions and more:               │
│                                                          │
│  ✓ Unlimited voice (audio) sessions                     │
│  ✓ Priority support                                     │
│  ✓ Advanced analytics and feedback                      │
│  ✓ Custom practice scenarios                            │
│  ✓ Download session transcripts                         │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │         $9.99 / month                       │        │
│  │         Cancel anytime                      │        │
│  │                                             │        │
│  │    [Upgrade to Premium]                     │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  [No thanks, continue with text sessions]               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Acceptance Criteria:**
- [ ] Pricing clearly displayed with no hidden fees
- [ ] "Cancel anytime" messaging prominent
- [ ] Benefits listed in bullet format
- [ ] Clear value proposition (what user gets)
- [ ] Easy dismissal option (doesn't feel like dark pattern)
- [ ] Upgrade button uses primary CTA styling
- [ ] "Continue with text" uses secondary styling (not hidden/deemphasized)

---

### 3.5 Session Counter Backend Requirements

**Data Model Updates:**

```python
@dataclass
class UserProfile:
    # ... existing fields ...

    # New fields for freemium model
    audio_sessions_used: int = 0  # Count of audio sessions used
    audio_sessions_reset_at: Optional[datetime] = None  # When to reset counter
    audio_sessions_limit: int = 2  # Default limit for freemium users

    @property
    def audio_sessions_remaining(self) -> int:
        """Calculate remaining audio sessions for freemium users."""
        if self.tier == UserTier.PREMIUM:
            return -1  # Unlimited (represented as -1)
        return max(0, self.audio_sessions_limit - self.audio_sessions_used)

    @property
    def can_use_audio(self) -> bool:
        """Check if user can start an audio session."""
        if self.tier == UserTier.PREMIUM:
            return True
        return self.audio_sessions_remaining > 0
```

**API Endpoint:**

```
GET /api/v1/user/limits

Response:
{
  "tier": "free",
  "audio_sessions_used": 1,
  "audio_sessions_limit": 2,
  "audio_sessions_remaining": 1,
  "can_use_audio": true,
  "reset_at": "2025-12-09T00:00:00Z"  // Weekly reset
}
```

**Session Creation Logic:**

```python
async def create_session(user: UserProfile, use_audio: bool):
    if use_audio and not user.can_use_audio:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "AUDIO_LIMIT_REACHED",
                "message": "You have reached your voice session limit",
                "sessions_used": user.audio_sessions_used,
                "sessions_limit": user.audio_sessions_limit,
                "upgrade_url": "/upgrade"
            }
        )

    # Create session...

    if use_audio and user.tier != UserTier.PREMIUM:
        # Increment counter for freemium users
        await increment_audio_sessions(user.email)
```

---

### 3.6 Reset Period

**Recommendation: Weekly reset (every Monday at 00:00 UTC)**

**Rationale:**
1. **User-friendly:** Predictable, easy to understand
2. **Sustainable:** Prevents abuse while being generous
3. **Encourages habit:** Users return weekly for new sessions
4. **Industry standard:** Common pattern in freemium apps

**Alternative: No reset (lifetime limit)**

- More restrictive, encourages immediate upgrade
- Simpler to implement
- May frustrate users who want to "try before they buy"

**Acceptance Criteria:**
- [ ] Reset date displayed in user dashboard
- [ ] Counter resets automatically at specified time
- [ ] Reset notification sent via email (optional: in-app toast)
- [ ] Counter never goes negative
- [ ] Premium users bypass counter entirely (unlimited)

---

## 4. State Definitions

### 4.1 Loading States

**Authentication Loading:**

```
┌─────────────────────────────────────────────────────────┐
│                                                          │
│               [Spinner Animation]                        │
│                                                          │
│               Signing you in...                          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**MFA Setup Loading:**

```
┌─────────────────────────────────────────────────────────┐
│                                                          │
│               [Spinner Animation]                        │
│                                                          │
│        Generating your security codes...                 │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Session Limit Check:**

```
┌─────────────────────────────────────────────────────────┐
│                                                          │
│               [Spinner Animation]                        │
│                                                          │
│          Checking your session availability...           │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Acceptance Criteria:**
- [ ] Loading overlays prevent duplicate form submissions
- [ ] Spinner has aria-label describing action
- [ ] Loading message is concise and specific
- [ ] Minimum display time: 300ms (prevents flash for fast operations)
- [ ] Maximum without progress indicator: 5 seconds (then show detailed message)
- [ ] Loading states use role="status" aria-live="polite"

---

### 4.2 Success States

**Signup Success:**

Toast notification (3 seconds):
```
✓ Account created successfully! Setting up security...
```

**MFA Setup Success:**

Full-screen confirmation (3 seconds, then auto-dismiss):
```
┌─────────────────────────────────────────────────────────┐
│                                                          │
│                    ✓                                     │
│                                                          │
│            Your Account is Secure!                       │
│                                                          │
│  Two-factor authentication has been enabled.             │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Login Success:**

Toast notification (2 seconds):
```
✓ Welcome back!
```

**Acceptance Criteria:**
- [ ] Success messages use green color (--success variable)
- [ ] Checkmark icon visible and large (48x48px minimum)
- [ ] Message displays for appropriate duration (not too fast, not too slow)
- [ ] Success state announced to screen readers via aria-live="polite"
- [ ] Auto-dismiss after timeout (user doesn't need to click)

---

### 4.3 Error States

**Authentication Failed:**

```
┌─────────────────────────────────────────────────────────┐
│  ❌ Sign In Failed                                      │
│                                                          │
│  Incorrect email or password.                           │
│  Please check your credentials and try again.           │
│                                                          │
│  [Forgot password?]                                     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**MFA Verification Failed:**

```
┌─────────────────────────────────────────────────────────┐
│  ❌ Invalid verification code                           │
│                                                          │
│  The code you entered is incorrect or has expired.      │
│  Please try again.                                      │
│                                                          │
│  Attempts remaining: 2 of 3                             │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Session Limit Reached:**

```
┌─────────────────────────────────────────────────────────┐
│  ⚠️ Voice Session Limit Reached                         │
│                                                          │
│  You've used all 2 of your free voice sessions.         │
│  Upgrade to Premium for unlimited access, or continue   │
│  with text sessions.                                    │
│                                                          │
│  [Upgrade to Premium]  [Continue with Text]             │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Network Error:**

```
┌─────────────────────────────────────────────────────────┐
│  ⚠️ Connection Error                                    │
│                                                          │
│  Unable to connect to the server.                       │
│  Please check your internet connection and try again.   │
│                                                          │
│  [Retry]  [Continue Offline]                            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Email Already Exists:**

```
┌─────────────────────────────────────────────────────────┐
│  ℹ️ Email Already Registered                            │
│                                                          │
│  An account with this email already exists.             │
│                                                          │
│  [Sign In Instead]  [Reset Password]                    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Weak Password:**

```
Email
┌────────────────────────────────────────────┐
│ user@example.com                            │
└────────────────────────────────────────────┘

Password
┌────────────────────────────────────────────┐
│ weak            [👁]                       │
└────────────────────────────────────────────┘
❌ Password must be at least 8 characters
❌ Password must contain at least 1 number
❌ Password must contain at least 1 special character

Strength: ████░░░░░░░░ Weak
```

**Acceptance Criteria:**

**Error Message Principles:**
- [ ] Specific: Tell user exactly what went wrong
- [ ] Actionable: Provide clear next steps or solutions
- [ ] Polite: Never blame the user ("You entered..." vs "The system...")
- [ ] Timely: Display immediately when error occurs
- [ ] Visible: Use red color (--danger variable) with icon
- [ ] Accessible: Announced via aria-live="assertive" for critical errors

**Error Display Requirements:**
- [ ] Error messages use 16px font size (readable)
- [ ] Error icon visible and appropriate (❌ for failures, ⚠️ for warnings)
- [ ] Error messages persist until user takes action
- [ ] Inline validation errors appear below relevant input field
- [ ] Form-level errors appear at top of form with link to affected field
- [ ] Error messages have sufficient color contrast (4.5:1 minimum)
- [ ] Multiple errors are numbered or bulleted for clarity

---

## 5. User Flows

### 5.1 New User Signup Flow

```
Landing Page
  ↓
[Create Free Account] button clicked
  ↓
Signup Modal Opens
  ↓
User enters email, password, confirms password
  ↓
[Google OAuth] OR [Email/Password Signup]
  ├─ Google OAuth Path:
  │    ↓
  │  Google Consent Screen
  │    ↓
  │  Account created/linked in Firebase
  │    ↓
  │  Check MFA status
  │    ├─ MFA not set up → MFA Setup Wizard
  │    └─ MFA already set up → MFA Verification
  │         ↓
  │       Dashboard
  │
  └─ Email/Password Path:
       ↓
     Form validation passes
       ↓
     Firebase creates user account
       ↓
     MFA Setup Wizard (MANDATORY)
       ↓
     Step 1: Choose MFA method (TOTP or SMS)
       ↓
     Step 2: Scan QR code (TOTP) or Enter phone (SMS)
       ↓
     Step 3: Verify code
       ↓
     Step 4: Save recovery codes
       ↓
     Success screen (3 seconds)
       ↓
     Redirect to Dashboard
       ↓
     Session counter shows: "🎤 Voice Sessions: 2 / 2 remaining"
       ↓
     User clicks "Start Your Scene"
       ↓
     Game selection modal
       ↓
     First session begins
```

---

### 5.2 Returning User Login Flow

```
Landing Page
  ↓
[Sign In] button clicked
  ↓
Login Modal Opens
  ↓
User enters email and password
  ↓
Firebase verifies credentials
  ↓
Success → MFA Verification Screen
  ↓
User enters 6-digit TOTP code
  ↓
Code verified
  ↓
[Optional] "Trust this device" selected
  ↓
Redirect to Dashboard
  ↓
Session counter displays current usage
  ↓
User starts session
```

**Alternative: Recovery Code Path**

```
MFA Verification Screen
  ↓
User clicks "Lost your device? Use recovery code"
  ↓
Recovery Code Modal
  ↓
User enters recovery code
  ↓
Code verified (single-use, marks as used)
  ↓
User logged in
  ↓
Toast: "⚠️ Recovery code used. Set up a new authenticator app in settings."
```

---

### 5.3 Freemium User Session Experience

**First Voice Session (2 → 1 remaining):**

```
Dashboard - Counter shows: "🎤 2 / 2 remaining"
  ↓
User clicks "Start Your Scene"
  ↓
Game selection modal
  ↓
User selects game
  ↓
Session setup: [Enable Voice Mode] toggle available
  ↓
User enables voice mode
  ↓
Session starts with audio
  ↓
Session ends after 10 turns
  ↓
Counter updates: "🎤 1 / 2 remaining"
  ↓
No intrusive message (user can see counter)
```

**Second Voice Session (1 → 0 remaining):**

```
Dashboard - Counter shows: "🎤 1 / 2 remaining"
  ↓
User starts another voice session
  ↓
Session ends
  ↓
Counter updates: "🎤 0 / 2 remaining"
  ↓
Toast notification appears:
  "ℹ️ Voice Session Limit Reached
   You've used your 2 free voice sessions.
   You can still practice with unlimited text sessions.

   [View Upgrade Options]  [Continue with Text]"
  ↓
User dismisses toast
  ↓
Dashboard shows "🎤 0 / 2 remaining" with prominent "Upgrade" button
```

**Attempting Third Voice Session (0 remaining):**

```
Dashboard - Counter shows: "🎤 0 / 2 remaining"
  ↓
User clicks "Start Your Scene"
  ↓
Game selection modal opens
  ↓
User selects game
  ↓
User attempts to toggle [Enable Voice Mode]
  ↓
Interstitial Modal appears (blocks action):

  "Voice Session Limit Reached

   You've used all 2 of your free voice sessions.

   ✨ Upgrade to Premium
   • Unlimited voice sessions
   • Priority support
   • Advanced features
   [Upgrade to Premium - $9.99/month]

   💬 Continue with Text Sessions (Free)
   • Unlimited text-based practice
   • All improv games available
   [Start Text Session]"

  ↓
User chooses:
  ├─ [Upgrade to Premium] → Payment flow → Session starts with voice
  └─ [Start Text Session] → Session starts without voice (text-only)
```

---

### 5.4 Upgrade Flow When Limit Reached

```
Interstitial Modal (limit reached)
  ↓
User clicks [Upgrade to Premium]
  ↓
Payment Modal Opens
  ↓
Payment form (Stripe integration)
  ├─ Credit card details
  ├─ Billing address
  └─ Confirm purchase
  ↓
Processing payment...
  ↓
Payment successful
  ↓
User tier updated in Firestore: tier="premium"
  ↓
Success toast: "✓ Welcome to Premium! Unlimited voice sessions unlocked."
  ↓
Session counter changes to: "🎤 Premium - Unlimited"
  ↓
User redirected back to game selection
  ↓
Voice mode automatically enabled
  ↓
Session starts
```

---

## 6. Mobile Responsiveness

### 6.1 Breakpoints

```css
/* Mobile-first approach */
:root {
  --breakpoint-sm: 640px;   /* Large phones */
  --breakpoint-md: 768px;   /* Tablets */
  --breakpoint-lg: 1024px;  /* Desktop */
  --breakpoint-xl: 1280px;  /* Large desktop */
}
```

---

### 6.2 Login/Signup Modal Adaptations

**Desktop (768px+):**
- Modal width: 500px
- Centered on screen with overlay
- Close button (×) in top-right
- Generous padding: 48px

**Tablet (640px - 768px):**
- Modal width: 80% of screen
- Maintained centering
- Same padding

**Mobile (<640px):**
- Modal fills 100% width
- Small top/bottom margins (16px)
- Reduced padding: 24px
- Larger input fields (min-height: 48px)
- Larger buttons (min-height: 48px)
- Font sizes slightly increased for readability

**Example Mobile Signup:**

```
┌─────────────────────────┐
│  Create Account     [×] │
│  ─────────────          │
│                         │
│  Email                  │
│  ┌─────────────────┐   │
│  │ you@email.com   │   │
│  └─────────────────┘   │
│                         │
│  Password               │
│  ┌─────────────────┐   │
│  │ ••••••••  [👁] │   │
│  └─────────────────┘   │
│  ↳ 8+ chars, 1 number   │
│                         │
│  Confirm Password       │
│  ┌─────────────────┐   │
│  │ ••••••••  [👁] │   │
│  └─────────────────┘   │
│                         │
│  ┌─────────────────┐   │
│  │ [Create Account]│   │
│  └─────────────────┘   │
│                         │
│  ──── OR ────          │
│                         │
│  ┌─────────────────┐   │
│  │ [G] Google      │   │
│  └─────────────────┘   │
│                         │
│  Terms & Privacy Policy │
│                         │
└─────────────────────────┘
```

---

### 6.3 MFA Code Entry on Mobile

**Challenge:** Small code input boxes are hard to tap accurately

**Solution: Large, merged input field with auto-formatting**

**Desktop (separate boxes):**
```
┌───┬───┬───┬───┬───┬───┐
│ 1 │ 2 │ 3 │ 4 │ 5 │ 6 │
└───┴───┴───┴───┴───┴───┘
```

**Mobile (single large input with visual separation):**
```
┌─────────────────────────┐
│                         │
│   1   2   3   4   5   6 │
│                         │
└─────────────────────────┘
```

Implementation:
- Single `<input>` element with `type="tel"` `inputmode="numeric"`
- Auto-format as user types: "123456" → "1 2 3 4 5 6"
- Min-height: 56px for easy tapping
- Font-size: 24px for visibility
- Auto-submit when 6 digits entered

**Acceptance Criteria:**
- [ ] Input field has min-height: 56px on mobile
- [ ] Numeric keyboard appears on mobile
- [ ] Auto-formatting adds spaces between digits
- [ ] Backspace removes last digit
- [ ] Paste support (removes non-numeric characters)
- [ ] Auto-submit on 6th digit
- [ ] Clear visual feedback on focus

---

### 6.4 Session Counter Mobile Optimization

**Desktop Header:**
```
Improv Olympics                 🎤 Voice Sessions: 1 / 2 remaining   [Upgrade]  [👤]
```

**Tablet Header:**
```
Improv Olympics          🎤 1 / 2 Voice   [Upgrade]  [👤]
```

**Mobile Header (collapsed):**
```
┌─────────────────────────┐
│ Improv Olympics    [≡] │
│ 🎤 1/2  [Premium]      │
└─────────────────────────┘
```

**Mobile Dashboard Card (expanded view):**
```
┌─────────────────────────┐
│ Your Practice Plan      │
│ ─────────────────       │
│ Free Tier               │
│                         │
│ 🎤 Voice Sessions      │
│ ████░░  1 of 2 used    │
│                         │
│ 💬 Text Sessions       │
│ Unlimited               │
│                         │
│ [Upgrade to Premium]    │
└─────────────────────────┘
```

**Acceptance Criteria:**
- [ ] Counter remains visible on mobile (never hidden)
- [ ] Text truncates gracefully on small screens
- [ ] Progress bar maintains visual clarity
- [ ] "Upgrade" button accessible (min 44x44px)
- [ ] Counter updates without page reload
- [ ] Sufficient color contrast maintained

---

### 6.5 Mobile-Specific Interactions

**Scroll Behavior:**
- Lock body scroll when modal is open
- Prevent scroll-behind (iOS Safari)
- Restore scroll position after modal closes

**Touch Gestures:**
- Swipe down to dismiss modals (optional enhancement)
- Pull-to-refresh disabled on auth pages
- Prevent accidental double-taps on buttons

**Keyboard Handling:**
- Inputs scroll into view when focused (prevent keyboard covering)
- Next/Previous buttons in keyboard toolbar (iOS)
- "Done" button closes keyboard (iOS)

**Acceptance Criteria:**
- [ ] Body scroll locked when modal open
- [ ] Scroll position restored after modal closes
- [ ] Inputs visible when keyboard appears
- [ ] Double-tap protection on form submit
- [ ] Touch targets 44x44px minimum
- [ ] Landscape orientation supported

---

## 7. Implementation Checklist

### 7.1 Frontend Components

**New Components to Create:**
- [ ] `<SignupModal>` - Email/password signup form
- [ ] `<LoginModal>` - Email/password login form
- [ ] `<MFASetupWizard>` - Multi-step MFA setup flow
- [ ] `<MFAVerificationModal>` - Code entry for login
- [ ] `<RecoveryCodeModal>` - Recovery code entry
- [ ] `<SessionLimitModal>` - Upgrade prompt when limit reached
- [ ] `<UpgradeModal>` - Detailed upgrade flow with pricing
- [ ] `<SessionCounter>` - Persistent session usage display
- [ ] `<PasswordStrengthIndicator>` - Visual password strength feedback

**Existing Components to Modify:**
- [ ] `app.js` - Update `checkAuthStatus()` to handle Firebase auth
- [ ] `index.html` - Add "Create Account" button
- [ ] Navigation header - Add session counter
- [ ] Loading overlays - Add specific loading messages

---

### 7.2 Backend API Endpoints

**New Endpoints:**
```
POST   /api/v1/auth/signup               # Email/password signup
POST   /api/v1/auth/login                # Email/password login
POST   /api/v1/auth/mfa/setup            # Initialize MFA setup
POST   /api/v1/auth/mfa/verify           # Verify MFA code during setup
POST   /api/v1/auth/mfa/challenge        # Get MFA challenge for login
POST   /api/v1/auth/mfa/verify-login     # Verify MFA code during login
POST   /api/v1/auth/recovery/verify      # Verify recovery code
GET    /api/v1/user/limits               # Get session limits
POST   /api/v1/session/start             # Check limits before starting
POST   /api/v1/session/end               # Increment counter on audio session end
POST   /api/v1/payment/upgrade           # Initiate upgrade flow
```

**Modified Endpoints:**
- [ ] `/auth/user` - Return tier and session limits
- [ ] `/api/v1/session/start` - Validate audio access before creating session

---

### 7.3 Database Schema Updates

**Firestore `users` Collection:**
```javascript
{
  user_id: string,
  email: string,
  tier: "free" | "regular" | "premium",

  // MFA fields
  mfa_enabled: boolean,
  mfa_method: "totp" | "sms",
  mfa_secret: string,  // Encrypted TOTP secret
  mfa_phone: string | null,  // For SMS
  recovery_codes: string[],  // Hashed recovery codes
  trusted_devices: [{
    device_id: string,
    expires_at: timestamp,
    created_at: timestamp
  }],

  // Session limit fields
  audio_sessions_used: number,
  audio_sessions_limit: number,
  audio_sessions_reset_at: timestamp,

  // Existing fields
  created_at: timestamp,
  last_login_at: timestamp,
  tier_assigned_at: timestamp,
  audio_usage_seconds: number,
  // ...
}
```

---

### 7.4 Security Considerations

**Password Security:**
- [ ] Use Firebase Authentication password hashing (bcrypt)
- [ ] Enforce password complexity requirements client and server-side
- [ ] Implement rate limiting on login attempts (max 5 per 15 minutes)
- [ ] Log failed login attempts for security monitoring

**MFA Security:**
- [ ] TOTP secrets encrypted at rest
- [ ] Recovery codes hashed (bcrypt) before storage
- [ ] Single-use recovery codes (mark as used)
- [ ] Rate limit MFA verification attempts (max 3 per 5 minutes)
- [ ] Lock account after 10 failed MFA attempts in 24 hours

**Session Security:**
- [ ] Maintain existing httponly, secure, samesite cookies
- [ ] Rotate session tokens on privilege escalation (tier upgrade)
- [ ] Invalidate sessions on password change
- [ ] Log all authentication events

**Data Privacy:**
- [ ] Store minimal user data (email, tier, usage only)
- [ ] Encrypt sensitive fields (MFA secrets, phone numbers)
- [ ] Implement GDPR-compliant data export/deletion
- [ ] Clear session data on logout

---

## 8. Accessibility Validation

### 8.1 WCAG 2.1 AA Requirements

**Perceivable:**
- [ ] All text has 4.5:1 contrast ratio minimum (normal text)
- [ ] Large text (18pt+) has 3:1 contrast ratio minimum
- [ ] Non-text content (icons, images) has alt text
- [ ] Color is not the only means of conveying information
- [ ] Error states use icons + color + text

**Operable:**
- [ ] All functionality accessible via keyboard
- [ ] Focus visible on all interactive elements (3px outline)
- [ ] No keyboard traps in modals or forms
- [ ] Touch targets minimum 44x44px
- [ ] No timing constraints on form completion

**Understandable:**
- [ ] Clear, concise language in all error messages
- [ ] Consistent navigation and UI patterns
- [ ] Form labels clearly associated with inputs
- [ ] Instructions provided before inputs (password requirements)
- [ ] Validation errors specific and actionable

**Robust:**
- [ ] Valid HTML5 semantic markup
- [ ] ARIA labels and roles used correctly
- [ ] Screen reader tested with NVDA/JAWS
- [ ] Works in multiple browsers (Chrome, Firefox, Safari)
- [ ] Degradation gracefully without JavaScript (error message shown)

---

### 8.2 Screen Reader Testing Script

**Signup Flow:**
1. Tab to "Create Account" button
2. Hear: "Create Account, button"
3. Press Enter to activate
4. Hear: "Create Your Free Account, dialog, Email, edit, type text"
5. Enter email and tab
6. Hear: "Password, edit, type text, 8 plus characters, 1 number, 1 special character"
7. Continue through form...

**MFA Setup:**
1. Reach QR code step
2. Hear: "QR code to set up two-factor authentication, graphic"
3. Tab to manual entry
4. Hear: "Setup key for manual entry, A B C D E F G H..."
5. Tab to copy button
6. Hear: "Copy setup key, button"

**Session Counter:**
1. Load dashboard
2. Hear: "Voice Sessions: 1 of 2 remaining"
3. Counter updates after session
4. Hear (aria-live): "Voice Sessions: 0 of 2 remaining"

---

## 9. Analytics and Monitoring

### 9.1 Key Metrics to Track

**Authentication:**
- [ ] Signup conversion rate (landing → completed signup)
- [ ] OAuth vs email/password signup ratio
- [ ] MFA setup completion rate
- [ ] MFA setup abandonment rate (which step)
- [ ] Login success rate
- [ ] MFA verification success rate
- [ ] Recovery code usage frequency
- [ ] Account lockout frequency

**Freemium Model:**
- [ ] Session limit reached frequency
- [ ] Upgrade conversion rate (limit reached → upgrade)
- [ ] Upgrade CTA click-through rate (header vs modal)
- [ ] Average sessions used before upgrade
- [ ] Text session usage after limit reached
- [ ] Upgrade abandonment rate (payment page)

**User Experience:**
- [ ] Average MFA setup time
- [ ] Form validation error frequency (by field)
- [ ] Modal abandonment rate
- [ ] Mobile vs desktop completion rates
- [ ] Browser/device compatibility issues

---

### 9.2 Event Tracking

**Firebase Analytics Events:**
```javascript
// Signup events
logEvent('signup_started', { method: 'email' | 'google' });
logEvent('signup_completed', { method: 'email' | 'google' });
logEvent('signup_failed', { reason: string });

// MFA events
logEvent('mfa_setup_started', { method: 'totp' | 'sms' });
logEvent('mfa_setup_completed', { method: 'totp' | 'sms', time_seconds: number });
logEvent('mfa_setup_abandoned', { step: number });
logEvent('mfa_verification_failed', { attempts: number });

// Session limit events
logEvent('session_limit_reached', { tier: 'free' });
logEvent('upgrade_prompt_shown', { source: 'header' | 'modal' | 'toast' });
logEvent('upgrade_started', { source: string });
logEvent('upgrade_completed', { tier: 'premium', amount: number });
logEvent('upgrade_abandoned', { step: 'pricing' | 'payment' });

// Session events
logEvent('session_started', { has_audio: boolean, sessions_remaining: number });
logEvent('session_blocked', { reason: 'audio_limit_reached' });
```

---

## 10. User Testing Scenarios

### 10.1 New User Journey

**Test Case 1: Happy Path**
1. User lands on homepage
2. Clicks "Create Free Account"
3. Enters email and password
4. Completes MFA setup (TOTP)
5. Saves recovery codes
6. Starts first voice session
7. Completes session successfully

**Expected:** 100% completion, no confusion, clear guidance at each step

---

### 10.2 Freemium Limit Testing

**Test Case 2: Reaching Session Limit**
1. Freemium user completes 2 voice sessions
2. Counter shows 0 remaining
3. User attempts to start 3rd voice session
4. Modal appears with upgrade prompt
5. User clicks "Continue with Text"
6. Text session starts successfully

**Expected:** User understands limitations, doesn't feel frustrated

---

### 10.3 Error Recovery

**Test Case 3: Lost Authenticator Device**
1. User logs in with email/password
2. MFA screen appears
3. User doesn't have authenticator
4. Clicks "Use recovery code"
5. Enters valid recovery code
6. Logs in successfully
7. Sees prompt to set up new MFA

**Expected:** User can recover access without contacting support

---

## 11. Open Questions for Product/Design Review

1. **MFA Enforcement:**
   - Should we allow "skip for now" option, or make MFA strictly mandatory?
   - **Recommendation:** Strictly mandatory for security

2. **Session Limit Reset Period:**
   - Weekly (every Monday)? Monthly (1st of month)? Or lifetime limit?
   - **Recommendation:** Weekly (more generous, encourages habit)

3. **Upgrade Pricing:**
   - What is the actual Premium tier price?
   - Monthly vs annual pricing options?
   - **Placeholder used:** $9.99/month

4. **Recovery Codes:**
   - How many codes to generate? (Currently: 8)
   - Should we allow regenerating codes?
   - **Recommendation:** 8 codes, allow regeneration with re-auth

5. **Session Counter Placement:**
   - Header (persistent) vs dashboard card (less intrusive)?
   - **Recommendation:** Both - condensed in header, detailed in dashboard

6. **OAuth Providers:**
   - Support Google only, or add GitHub, Apple, etc.?
   - **Recommendation:** Start with Google only, add others based on user requests

7. **SMS MFA:**
   - Do we want to support SMS at all? (Security vs convenience)
   - What are the cost implications?
   - **Recommendation:** TOTP only for MVP, SMS as future enhancement

8. **Mobile App:**
   - Is a native mobile app planned?
   - How does MFA work with native apps?
   - **Recommendation:** Focus on responsive web for MVP

---

## 12. Success Criteria

### 12.1 Launch Readiness

**Must Have:**
- [ ] Email/password signup and login functional
- [ ] Google OAuth maintained and functional
- [ ] MFA setup wizard complete (TOTP only)
- [ ] MFA verification on login working
- [ ] Recovery codes generated and validated
- [ ] Session counter displays correctly
- [ ] Freemium limit enforced (2 sessions)
- [ ] Upgrade modal appears when limit reached
- [ ] All WCAG 2.1 AA requirements met
- [ ] Mobile responsive on all screens

**Nice to Have:**
- [ ] SMS MFA support
- [ ] Biometric authentication (WebAuthn)
- [ ] "Remember this device" for 30 days
- [ ] Email notifications on security events
- [ ] Advanced password strength feedback

---

### 12.2 Post-Launch Metrics

**Week 1 Targets:**
- [ ] 90%+ MFA setup completion rate
- [ ] <2% authentication error rate
- [ ] 80%+ mobile usability (no critical issues)
- [ ] 5%+ upgrade conversion rate

**Month 1 Targets:**
- [ ] 15%+ freemium → premium conversion
- [ ] <5% support tickets related to auth
- [ ] 95%+ login success rate
- [ ] Zero critical security incidents

---

## Appendix A: Design Assets Needed

1. **Icons:**
   - QR code placeholder (200x200px)
   - Authenticator app icons (Google Authenticator, Authy, 1Password)
   - Password strength indicators (weak/fair/strong)
   - Checkmark (success state)
   - Warning/error icons
   - Lock icon (security)

2. **Illustrations:**
   - MFA setup success (celebration)
   - Session limit reached (friendly, not punitive)
   - Upgrade benefits (value-focused)

3. **Copy:**
   - Terms of Service (link)
   - Privacy Policy (link)
   - Email templates (verification, security alerts)

---

## Appendix B: Technical Dependencies

**Frontend:**
- Firebase JavaScript SDK (authentication)
- QR code generation library (qrcode.js)
- OTP input component (react-otp-input or custom)
- Stripe SDK (payment processing)

**Backend:**
- Firebase Admin SDK (user management)
- TOTP library (pyotp for Python)
- SMS provider API (Twilio, if implementing SMS MFA)
- Payment processor (Stripe)

---

## Document Change Log

| Version | Date       | Author | Changes                                  |
|---------|------------|--------|------------------------------------------|
| 1.0     | 2025-12-02 | UX     | Initial draft based on codebase analysis |

---

**END OF DOCUMENT**
