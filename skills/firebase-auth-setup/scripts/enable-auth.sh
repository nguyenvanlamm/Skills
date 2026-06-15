#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Parse args ---
PROJECT_ID=""
OUTPUT_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT_ID="$2"; shift 2 ;;
    --output) OUTPUT_DIR="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [ -z "$PROJECT_ID" ]; then echo "❌ --project required"; exit 1; fi
if [ -z "$OUTPUT_DIR" ]; then echo "❌ --output required"; exit 1; fi

echo "🔑 Enabling Authentication providers..."

# Enable Identity Toolkit API
echo "  Enabling Identity Toolkit API..."
gcloud services enable identitytoolkit.googleapis.com --project "$PROJECT_ID" --quiet
echo "  ✅ Identity Toolkit API enabled"

# Enable Firebase Management API (required for REST calls)
gcloud services enable firebase.googleapis.com --project "$PROJECT_ID" --quiet 2>/dev/null || true

# Get Google OAuth2 access token (required for REST API calls)
echo "  Getting OAuth2 access token..."
ACCESS_TOKEN=$(gcloud auth application-default print-access-token 2>/dev/null || \
              gcloud auth print-access-token 2>/dev/null || true)
if [ -z "$ACCESS_TOKEN" ]; then
  echo "❌ Failed to get OAuth2 access token. Run: gcloud auth application-default login"
  exit 1
fi
echo "  ✅ OAuth2 access token obtained"

# Firebase Management REST API base
FIREBASE_API="https://identitytoolkit.googleapis.com/v2/projects/$PROJECT_ID"

# Enable Email/Password provider
echo "  Enabling Email/Password provider..."
EMAIL_PAYLOAD='{"signInProviders":{"email":true,"password":true}}'
EMAIL_RESP=$(python3 -c "
import urllib.request, json
url = '${FIREBASE_API}/config?updateMask=signInProviders.email,signInProviders.password'
req = urllib.request.Request(url, data=json.dumps($EMAIL_PAYLOAD).encode(), headers={
    'Authorization': 'Bearer $ACCESS_TOKEN',
    'Content-Type': 'application/json',
}, method='PATCH')
try:
    resp = urllib.request.urlopen(req)
    print(resp.status)
    print(resp.read().decode())
except urllib.error.HTTPError as e:
    print(e.code)
    print(e.read().decode())
" 2>&1)

EMAIL_STATUS=$(echo "$EMAIL_RESP" | head -1)
EMAIL_BODY=$(echo "$EMAIL_RESP" | tail -n +2)

if [ "$EMAIL_STATUS" != "200" ]; then
  echo "❌ Failed to enable Email/Password provider (HTTP $EMAIL_STATUS)"
  echo "   Response: $EMAIL_BODY"
  echo "   Run: gcloud auth application-default login"
  exit 1
fi
echo "  ✅ Email/Password provider enabled"

# Enable Google provider
echo "  Enabling Google sign-in provider..."
GOOGLE_PAYLOAD='{"signInProviders":{"google":true}}'
GOOGLE_RESP=$(python3 -c "
import urllib.request, json
url = '${FIREBASE_API}/config?updateMask=signInProviders.google'
req = urllib.request.Request(url, data=json.dumps($GOOGLE_PAYLOAD).encode(), headers={
    'Authorization': 'Bearer $ACCESS_TOKEN',
    'Content-Type': 'application/json',
}, method='PATCH')
try:
    resp = urllib.request.urlopen(req)
    print(resp.status)
    print(resp.read().decode())
except urllib.error.HTTPError as e:
    print(e.code)
    print(e.read().decode())
" 2>&1)

GOOGLE_STATUS=$(echo "$GOOGLE_RESP" | head -1)
GOOGLE_BODY=$(echo "$GOOGLE_RESP" | tail -n +2)

if [ "$GOOGLE_STATUS" != "200" ]; then
  echo "❌ Failed to enable Google sign-in provider (HTTP $GOOGLE_STATUS)"
  echo "   Response: $GOOGLE_BODY"
  exit 1
fi
echo "  ✅ Google sign-in provider enabled"

echo "✅ Auth providers configuration complete."
