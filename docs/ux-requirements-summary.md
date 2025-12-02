# UX Requirements Summary: Firebase Auth Migration

**Status:** Ready for Review
**Full Document:** See `ux-requirements-firebase-auth-mfa.md`

---

## Critical Design Decisions

### 1. Authentication Flow

**Recommendation: Dual authentication methods**
- **Email/Password:** Primary signup method for new users
- **Google OAuth:** Maintained for user convenience (via Firebase)
- **Both require MFA:** No exceptions for security

**Rationale:**
- Reduces friction (users can choose preferred method)
- Firebase supports both natively
- Maintains existing Google OAuth users

---

### 2. MFA Enrollment Timing

**Recommendation: Immediate enrollment during signup**

**Flow:**
```
Signup → Account Created → MFA Setup (MANDATORY) → Dashboard
```

**Rationale:**
- Users expect security setup during account creation
- Prevents interruption mid-session later
- Higher completion rates when done immediately
- Clear user expectation: "Setup security to continue"

---

### 3. MFA Method

**Recommendation: TOTP (Authenticator Apps) as primary, SMS as optional enhancement**

**TOTP First:**
- More secure (no SIM swapping)
- No per-use cost
- Works offline
- Industry best practice

**SMS Backup (Optional for MVP):**
- Can add later based on user feedback
- Higher cost, lower security
- Convenience for non-technical users

---

### 4. Freemium Model

**Recommendation: 2 voice sessions per week, then unlimited text**

**Structure:**
```
FREE TIER:
- 2 voice (audio) sessions per week
- Unlimited text sessions
- Weekly reset (Monday 00:00 UTC)

PREMIUM TIER:
- Unlimited voice sessions
- Priority support
- Advanced features
```

**Rationale:**
- Generous enough to experience value
- Weekly reset encourages habit formation
- Clear upgrade incentive (unlimited audio)
- Text sessions remain free (accessibility)

---

### 5. Session Limit UX

**Recommendation: Non-intrusive warnings, clear upgrade path**

**Approach:**
1. **First session (2→1):** No warning, just update counter
2. **Second session (1→0):** Toast notification after session ends
3. **Third session attempt:** Interstitial modal with upgrade prompt

**Key Principle:** Never punish users. Always offer "Continue with Text" option.

---

## Strengths of Current Design to Preserve

1. **WCAG 2.1 AA Compliance**
   - Excellent color contrast
   - Keyboard navigation
   - Screen reader support
   - Skip links

2. **Mobile-First Design**
   - Responsive breakpoints
   - Touch-friendly targets (44x44px)
   - Clean, uncluttered UI

3. **Progressive Disclosure**
   - Information revealed when needed
   - Reduces cognitive load
   - Clear visual hierarchy

---

## Critical UX Issues to Address

### Issue 1: MFA Code Entry on Mobile

**Problem:** Small separate input boxes difficult to tap accurately on mobile

**Solution:**
```
Desktop: [1][2][3][4][5][6]  (6 separate boxes)
Mobile:  [  1  2  3  4  5  6  ]  (single large input, visual separation)
```

- Single input field with auto-formatting
- Numeric keyboard on mobile
- Min-height: 56px for easy tapping

---

### Issue 2: Password Requirements Visibility

**Problem:** Users don't know requirements until after they fail validation

**Solution:**
- Progressive disclosure: Show requirements on focus
- Real-time validation as user types
- Visual password strength indicator
- Clear error messages inline

---

### Issue 3: Session Counter Placement

**Problem:** Where to display session counter without cluttering UI?

**Solution: Dual placement**
- **Header (persistent):** Condensed version "🎤 1/2 [Upgrade]"
- **Dashboard card:** Detailed progress bar and explanation

Mobile optimization:
```
Desktop: "🎤 Voice Sessions: 1 / 2 remaining"
Tablet:  "🎤 1 / 2 Voice"
Mobile:  "🎤 1/2 [Premium]"
```

---

### Issue 4: Recovery Code Storage

**Problem:** Users lose access if they don't save recovery codes

**Solution:**
- MANDATORY checkbox: "I have saved these codes in a secure place"
- Multiple download options: Download file + Copy to clipboard
- Clear warning: "Save these now, you won't see them again"
- Generate 8 codes (industry standard)

---

## Accessibility Highlights

### WCAG 2.1 AA Compliance Checklist

**Perceivable:**
- ✓ 4.5:1 contrast ratio for all text
- ✓ Alt text on all images/icons
- ✓ Error states use icon + color + text (not color alone)

**Operable:**
- ✓ 100% keyboard accessible
- ✓ Focus visible (3px outline)
- ✓ No keyboard traps in modals
- ✓ 44x44px touch targets

**Understandable:**
- ✓ Clear error messages with specific actions
- ✓ Form labels properly associated
- ✓ Consistent UI patterns

**Robust:**
- ✓ Semantic HTML5
- ✓ ARIA labels and roles
- ✓ Screen reader tested

---

## User Flows Summary

### New User Signup (Happy Path)

```
Landing Page
  ↓
"Create Free Account" clicked
  ↓
Signup Modal (email/password OR Google OAuth)
  ↓
Account created in Firebase
  ↓
MFA Setup Wizard
  ├─ Step 1: Choose method (TOTP/SMS)
  ├─ Step 2: Scan QR code or enter phone
  ├─ Step 3: Verify code
  └─ Step 4: Save recovery codes (MANDATORY)
  ↓
Success screen (3 seconds)
  ↓
Dashboard
  ↓
Counter shows: "🎤 2 / 2 remaining"
  ↓
Start first session
```

---

### Freemium User Journey

```
Dashboard: "🎤 2 / 2 remaining"
  ↓
User completes 1st voice session
  ↓
Counter updates: "🎤 1 / 2 remaining" (no warning)
  ↓
User completes 2nd voice session
  ↓
Counter updates: "🎤 0 / 2 remaining"
Toast: "Voice session limit reached. Upgrade or continue with text."
  ↓
User attempts 3rd voice session
  ↓
Interstitial Modal:
  "Voice Session Limit Reached

   [Upgrade to Premium - $9.99/month]
   [Continue with Text Sessions]"
  ↓
User chooses:
  ├─ Upgrade → Payment → Session starts with voice
  └─ Text → Session starts without voice
```

---

## State Definitions

### Loading States
- "Signing you in..."
- "Generating your security codes..."
- "Checking your session availability..."
- Minimum 300ms display (prevent flash)

### Success States
- ✓ Green checkmark (48x48px)
- "Account created successfully!"
- "Your Account is Secure!"
- Auto-dismiss after 2-3 seconds

### Error States
- ❌ Red icon with specific message
- "Incorrect email or password"
- "Invalid verification code - Attempts remaining: 2 of 3"
- "Voice session limit reached"
- Always actionable (provide next steps)

---

## Mobile Responsiveness Key Points

### Breakpoints
```css
--breakpoint-sm: 640px;   /* Large phones */
--breakpoint-md: 768px;   /* Tablets */
--breakpoint-lg: 1024px;  /* Desktop */
```

### Mobile Optimizations
1. **Modal fills screen** (<640px) with 24px padding
2. **Input fields:** Min-height 48px for touch
3. **MFA code entry:** Single large input (56px height)
4. **Session counter:** Condensed to "🎤 1/2 [Premium]"
5. **Buttons:** All 44x44px minimum touch targets

---

## Implementation Priority

### Phase 1: MVP (Must Have)
1. Email/password signup and login
2. Google OAuth via Firebase
3. MFA setup wizard (TOTP only)
4. MFA verification on login
5. Recovery codes
6. Session counter display
7. Freemium limit enforcement (2 sessions)
8. Upgrade modal

### Phase 2: Enhancements (Nice to Have)
1. SMS MFA support
2. "Remember this device" (30 days)
3. Email notifications on security events
4. Biometric authentication (WebAuthn)
5. Advanced password strength feedback

---

## Key Metrics to Track

### Authentication
- Signup conversion rate (landing → completed)
- MFA setup completion rate (target: 90%+)
- Login success rate (target: 95%+)
- Account lockout frequency

### Freemium Model
- Session limit reached frequency
- Upgrade conversion rate (target: 5% week 1, 15% month 1)
- Text session usage after limit reached
- Upgrade CTA click-through rate

### User Experience
- Average MFA setup time
- Form validation error frequency
- Mobile vs desktop completion rates
- Support tickets related to auth (target: <5%)

---

## Open Questions for Product Review

1. **SMS MFA:** Include in MVP or defer? (Cost implications)
2. **Session Reset:** Weekly (recommended) or monthly?
3. **Premium Pricing:** Confirm $9.99/month or different tier?
4. **Recovery Codes:** Allow regeneration? (Recommended: yes, with re-auth)
5. **Mobile App:** Native app planned? (Affects MFA implementation)

---

## Next Steps

1. **Design Review:** Product team review UX requirements
2. **Technical Spec:** Backend team define Firebase integration
3. **UI Mockups:** Create high-fidelity mockups for all screens
4. **Prototyping:** Interactive prototype for user testing
5. **Implementation:** Frontend + backend development
6. **Testing:** WCAG audit, screen reader testing, mobile testing
7. **Launch:** Phased rollout with metrics monitoring

---

## Success Criteria

### Launch Ready
- ✓ All WCAG 2.1 AA requirements met
- ✓ Mobile responsive on all screens
- ✓ MFA setup functional (TOTP)
- ✓ Session limits enforced
- ✓ Upgrade flow complete
- ✓ <2% authentication error rate

### Post-Launch (Month 1)
- 15%+ freemium → premium conversion
- 90%+ MFA setup completion rate
- 95%+ login success rate
- <5% auth-related support tickets
- Zero critical security incidents

---

**Document:** `/home/jantona/Documents/code/ai4joy/docs/ux-requirements-firebase-auth-mfa.md`
**Summary:** `/home/jantona/Documents/code/ai4joy/docs/ux-requirements-summary.md`
