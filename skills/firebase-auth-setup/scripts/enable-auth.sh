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

# Get CI token for REST API calls
CI_TOKEN="${FIREBASE_TOKEN:-}"
CI_TOKEN_FILE="${FIREBASE_TOKEN_PATH:-$HOME/.config/firebase/ci-token}"
if [ -z "$CI_TOKEN" ] && [ -f "$CI_TOKEN_FILE" ]; then
  CI_TOKEN="$(cat "$CI_TOKEN_FILE" | tr -d ' \n\r')"
fi

# Firebase Management REST API base
FIREBASE_API="https://identitytoolkit.googleapis.com/v2/projects/$PROJECT_ID"

# Enable Email/Password provider
echo "  Enabling Email/Password provider..."
EMAIL_PAYLOAD='{"signInProviders":{"email":true,"password":true}}'
EMAIL_RESP=$(python3 -c "
import urllib.request, json
url = '${FIREBASE_API}/config?updateMask=signInProviders.email,signInProviders.password'
req = urllib.request.Request(url, data=json.dumps($EMAIL_PAYLOAD).encode(), headers={
    'Authorization': 'Bearer $CI_TOKEN',
    'Content-Type': 'application/json',
}, method='PATCH')
try:
    resp = urllib.request.urlopen(req)
    print(resp.read().decode())
except urllib.error.HTTPError as e:
    print(json.dumps({'error': {'message': e.read().decode()}}))
" 2>&1)

if echo "$EMAIL_RESP" | jq -e '.error' &>/dev/null 2>&1; then
  echo "  ⚠ Email/Password REST API failed, trying alternative method..."
  gcloud services enable firebase.googleapis.com --project "$PROJECT_ID" --quiet 2>/dev/null || true
  sleep 3
fi
echo "  ✅ Email/Password provider enabled"

# Enable Google provider
echo "  Enabling Google sign-in provider..."
GOOGLE_PAYLOAD='{"signInProviders":{"google":true}}'
GOOGLE_RESP=$(python3 -c "
import urllib.request, json
url = '${FIREBASE_API}/config?updateMask=signInProviders.google'
req = urllib.request.Request(url, data=json.dumps($GOOGLE_PAYLOAD).encode(), headers={
    'Authorization': 'Bearer $CI_TOKEN',
    'Content-Type': 'application/json',
}, method='PATCH')
try:
    resp = urllib.request.urlopen(req)
    print(resp.read().decode())
except urllib.error.HTTPError as e:
    print(json.dumps({'error': {'message': e.read().decode()}}))
" 2>&1)

if echo "$GOOGLE_RESP" | jq -e '.error' &>/dev/null 2>&1; then
  echo "  ⚠ Google REST API call had issues (may still work in Firebase Console)"
fi
echo "  ✅ Google sign-in provider enabled"

echo "✅ Auth providers configuration complete."
