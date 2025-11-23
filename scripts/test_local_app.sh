#!/bin/bash
# Local Application Testing Script
# Tests all endpoints with mock IAP headers

set -e

BASE_URL="${BASE_URL:-http://localhost:8080}"
USER_EMAIL="accounts.google.com:test@example.com"
USER_ID="accounts.google.com:123456789"

echo "=========================================="
echo "Improv Olympics - Local Application Test"
echo "=========================================="
echo ""
echo "Base URL: $BASE_URL"
echo ""

echo "1. Testing Health Check (no auth)..."
curl -s "$BASE_URL/health" | jq '.'
echo ""

echo "2. Testing Readiness Check (no auth)..."
curl -s "$BASE_URL/ready" | jq '.'
echo ""

echo "3. Testing User Limits (with IAP headers)..."
curl -s "$BASE_URL/api/v1/user/limits" \
  -H "X-Goog-Authenticated-User-Email: $USER_EMAIL" \
  -H "X-Goog-Authenticated-User-ID: $USER_ID" | jq '.'
echo ""

echo "4. Creating Session (with IAP headers)..."
SESSION_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/session/start" \
  -H "Content-Type: application/json" \
  -H "X-Goog-Authenticated-User-Email: $USER_EMAIL" \
  -H "X-Goog-Authenticated-User-ID: $USER_ID" \
  -d '{"location": "Mars Colony Breakroom", "user_name": "Test User"}')

echo "$SESSION_RESPONSE" | jq '.'
SESSION_ID=$(echo "$SESSION_RESPONSE" | jq -r '.session_id')
echo ""

if [ "$SESSION_ID" != "null" ] && [ -n "$SESSION_ID" ]; then
  echo "5. Getting Session Info..."
  curl -s "$BASE_URL/api/v1/session/$SESSION_ID" \
    -H "X-Goog-Authenticated-User-Email: $USER_EMAIL" \
    -H "X-Goog-Authenticated-User-ID: $USER_ID" | jq '.'
  echo ""

  echo "6. Closing Session..."
  curl -s -X POST "$BASE_URL/api/v1/session/$SESSION_ID/close" \
    -H "X-Goog-Authenticated-User-Email: $USER_EMAIL" \
    -H "X-Goog-Authenticated-User-ID: $USER_ID" | jq '.'
  echo ""
fi

echo "7. Testing Agent Info..."
curl -s "$BASE_URL/api/v1/agent/info" \
  -H "X-Goog-Authenticated-User-Email: $USER_EMAIL" \
  -H "X-Goog-Authenticated-User-ID: $USER_ID" | jq '.'
echo ""

echo "8. Testing Agent Connectivity..."
curl -s "$BASE_URL/api/v1/agent/test" \
  -H "X-Goog-Authenticated-User-Email: $USER_EMAIL" \
  -H "X-Goog-Authenticated-User-ID: $USER_ID" | jq '.'
echo ""

echo "=========================================="
echo "Testing Complete!"
echo "=========================================="
