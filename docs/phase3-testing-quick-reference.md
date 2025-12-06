# Phase 3 Freemium Testing Quick Reference

## Quick Test Scenarios

### Scenario 1: New User Journey
```bash
# Expected: Auto-provisioned with freemium tier

1. Create new Firebase account
2. Sign in to Improv Olympics
3. Check Firestore: tier should be "freemium"
4. Start audio session → Should succeed
5. Complete session → premium_sessions_used: 1
6. Start 2nd audio session → Should succeed (with warning)
7. Complete session → premium_sessions_used: 2
8. Attempt 3rd audio session → Should fail (429 error)
9. Start text session → Should succeed (unlimited)
```

### Scenario 2: Existing Premium User
```bash
# Expected: No changes, unlimited audio

1. Login as existing premium user
2. Check Firestore: tier should remain "premium"
3. Complete 5+ audio sessions
4. Check premium_sessions_used → Should remain 0 (not tracked)
5. Verify unlimited audio access continues
```

### Scenario 3: Session Limit Enforcement
```bash
# Expected: Hard limit at 2 sessions

Freemium user (sessions_used: 2):
- GET /api/audio/access-check → allowed: false, status: 429
- WebSocket /ws/audio/{session_id} → Close code 4003
- Error message: "You've used all 2 free audio sessions..."
```

### Scenario 4: Text Mode Fallback
```bash
# Expected: Text mode always available

Freemium user at limit:
- POST /api/v1/session/start (text mode) → 201 Created
- POST /api/v1/session/{id}/turn → 200 OK
- Complete unlimited text sessions
- premium_sessions_used → Unchanged
```

## API Testing

### Check Session Status
```bash
curl -X GET https://api.improvolympics.com/api/audio/access-check \
  -H "Cookie: session_token=YOUR_TOKEN"

# Freemium with 1 session remaining:
{
  "allowed": true,
  "remaining_seconds": null,
  "warning": "This is your last free audio session!"
}

# Freemium at limit:
{
  "allowed": false,
  "error": "You've used all 2 free audio sessions...",
  "fallback_mode": "text",
  "fallback_message": "Upgrade to Premium for unlimited access..."
}
```

### Firestore Queries

```javascript
// Check user tier and session count
db.collection('users')
  .where('email', '==', 'test@example.com')
  .get()
  .then(snapshot => {
    snapshot.docs.forEach(doc => {
      const data = doc.data();
      console.log(`Tier: ${data.tier}`);
      console.log(`Sessions used: ${data.premium_sessions_used}`);
      console.log(`Sessions limit: ${data.premium_sessions_limit}`);
    });
  });

// Count freemium users
db.collection('users')
  .where('tier', '==', 'freemium')
  .count()
  .get();

// Find users at session limit
db.collection('users')
  .where('tier', '==', 'freemium')
  .where('premium_sessions_used', '>=', 2)
  .get();
```

## Expected Behaviors

### Session Counting
| User Tier | Audio Session | Count Incremented? | Notes |
|-----------|---------------|-------------------|-------|
| FREEMIUM  | Audio         | ✅ Yes             | On disconnect |
| FREEMIUM  | Text          | ❌ No              | No audio used |
| PREMIUM   | Audio         | ❌ No              | Unlimited |
| PREMIUM   | Text          | ❌ No              | N/A |
| FREE      | Audio         | ❌ No              | No access |
| FREE      | Text          | ❌ No              | N/A |

### Access Control
| User Tier | Sessions Used | Audio Access | Text Access | Status Code |
|-----------|---------------|--------------|-------------|-------------|
| FREEMIUM  | 0/2           | ✅ Allow      | ✅ Allow     | 200 |
| FREEMIUM  | 1/2           | ✅ Allow      | ✅ Allow     | 200 (warning) |
| FREEMIUM  | 2/2           | ❌ Deny       | ✅ Allow     | 429 |
| PREMIUM   | Any           | ✅ Allow      | ✅ Allow     | 200 |
| FREE      | Any           | ❌ Deny       | ✅ Allow     | 403 |

## Debugging Tips

### Check Logs
```bash
# Session tracking
grep "Session completion tracked" /var/log/improv-olympics/app.log

# Freemium enforcement
grep "Freemium session limit" /var/log/improv-olympics/app.log

# Auto-provisioning
grep "FREEMIUM tier" /var/log/improv-olympics/app.log
```

### Common Issues

**Issue:** Session count not incrementing
- **Check:** Is WebSocket disconnect being called?
- **Check:** Is user tier actually "freemium"?
- **Check:** Are there Firestore permission errors?
- **Solution:** Review `websocket_handler.py:disconnect()` logs

**Issue:** Premium users being limited
- **Check:** User tier in Firestore (should be "premium" not "freemium")
- **Check:** `check_session_limit()` returning correct status
- **Solution:** Verify tier assignment logic

**Issue:** New users not getting freemium
- **Check:** `firebase_auth_service.py` using `UserTier.FREEMIUM`
- **Check:** User creation logs show correct tier
- **Solution:** Verify Firebase auth flow

## Manual Verification Checklist

- [ ] New Firebase user → tier: "freemium"
- [ ] Freemium user → 1st session succeeds
- [ ] Freemium user → 2nd session succeeds (warning shown)
- [ ] Freemium user → 3rd session blocked (429)
- [ ] Freemium user → Text mode always works
- [ ] Premium user → Unlimited audio (no limits)
- [ ] Premium user → Sessions NOT tracked
- [ ] Existing premium → Tier preserved
- [ ] Session counter UI → Shows "🎤 X/2" for freemium
- [ ] Toast notification → Shown after 2nd session
- [ ] Upgrade modal → Shown on 3rd attempt

## Performance Benchmarks

Expected performance metrics:

- **Session Start:** < 200ms (no change)
- **Session End:** < 250ms (+50ms for Firestore write)
- **Access Check:** < 50ms (in-memory check)
- **User Creation:** < 500ms (meets AC-PROV-04)

## Monitoring Queries

```sql
-- Freemium adoption rate
SELECT
  tier,
  COUNT(*) as user_count,
  AVG(premium_sessions_used) as avg_sessions
FROM users
WHERE tier = 'freemium'
GROUP BY tier;

-- Users at session limit
SELECT
  email,
  premium_sessions_used,
  tier_assigned_at
FROM users
WHERE tier = 'freemium'
  AND premium_sessions_used >= 2;

-- Conversion opportunities
SELECT
  COUNT(*) as at_limit_count
FROM users
WHERE tier = 'freemium'
  AND premium_sessions_used >= 2
  AND last_login_at > NOW() - INTERVAL '7 days';
```

## Rollback Commands

If needed, rollback to previous state:

```bash
# 1. Stop deployment
kubectl rollout undo deployment/improv-olympics

# 2. Revert tier assignment (temporary)
# Update firebase_auth_service.py: FREEMIUM → FREE

# 3. Monitor for issues
kubectl logs -f deployment/improv-olympics | grep -i freemium

# 4. If needed, manually update user tiers
# (Use Firestore console to change tier field)
```

## Success Criteria

✅ **Backend Complete:**
- New users auto-assigned freemium
- Session limiting works (2 sessions)
- Premium users unaffected
- Text mode unlimited for all

⚠️ **Frontend Pending:**
- Session counter UI
- Toast notification after 2nd session
- Upgrade modal on 3rd attempt
- Upgrade flow integration

## Next Steps

1. Deploy backend changes
2. Monitor Firestore for new freemium users
3. Implement frontend session counter
4. Implement toast/modal UI
5. Add analytics tracking
6. Monitor conversion metrics
