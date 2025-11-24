# OAuth Implementation Change: IAP to Application-Level OAuth

**Date**: November 24, 2024
**Status**: Implemented and Ready for Deployment

## Executive Summary

We successfully implemented **application-level Google OAuth 2.0** authentication instead of GCP Identity-Aware Proxy (IAP) due to the requirement that IAP needs a GCP Organization, which personal/free-tier projects don't have.

**Impact**: All functionality remains the same from a user perspective. Authentication is secure, rate limiting works, and access control is maintained via email whitelist.

---

## Why We Changed from IAP to Application-Level OAuth

### Original Plan (IAP)
- Use GCP's Identity-Aware Proxy at the load balancer level
- Zero code changes needed for authentication
- IAP injects headers: `X-Goog-Authenticated-User-Email`, `X-Goog-Authenticated-User-ID`
- Access control via `iap_allowed_users` in terraform

### The Blocker
- **IAP requires a GCP Organization**
- Personal projects cannot use IAP
- OAuth consent screen alone is insufficient for IAP

### The Solution
- Implement application-level OAuth 2.0 using Google Sign-In
- Use `authlib` library for OAuth flow
- Secure session management with httponly cookies
- Email whitelist for access control

---

## Technical Differences

| Component | IAP Approach | Application OAuth |
|-----------|--------------|-------------------|
| **Middleware** | IAPAuthMiddleware | OAuthSessionMiddleware |
| **Auth Endpoints** | None (IAP handles it) | /auth/login, /auth/callback, /auth/logout |
| **Session Storage** | Stateless headers | Secure signed cookies |
| **Access Control** | iap_allowed_users | ALLOWED_USERS env var |
| **Dependencies** | None | authlib, itsdangerous |

---

## Deployment Changes

### Secret Manager Setup (Already Done)
- oauth-client-id
- oauth-client-secret  
- session-secret-key

### Terraform Configuration
Set `allowed_users` in terraform.tfvars with comma-separated emails.

### Deploy Commands
```bash
cd infrastructure/terraform && terraform apply
cd ../.. && ./scripts/deploy.sh
```

---

## Security Comparison

Both approaches are secure. Application OAuth uses:
- httponly cookies (XSS protection)
- secure flag (HTTPS only)
- samesite=lax (CSRF protection)
- Signed tokens from Secret Manager
- 24-hour expiration

**Access Control**: Email whitelist checked after OAuth (double verification)

---

## References
- OAuth Middleware: `app/middleware/oauth_auth.py`
- Auth Endpoints: `app/routers/auth.py`
- Terraform: `infrastructure/terraform/main.tf`
