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

echo "🌐 Creating Firebase Web App..."

# Check if web app already exists
EXISTING_APPS=$(firebase apps:list WEB --json --project "$PROJECT_ID" 2>/dev/null || echo '{"result":[]}')
EXISTING_APP=$(echo "$EXISTING_APPS" | jq -r '.result[0].appId // empty' 2>/dev/null)

if [ -n "$EXISTING_APP" ]; then
  echo "  ⚠ Web app already exists (appId: $EXISTING_APP). Using existing app."
  APP_ID="$EXISTING_APP"
else
  echo "  Creating new web app..."
  CREATE_OUTPUT=$(firebase apps:create WEB "$PROJECT_ID-client" --project "$PROJECT_ID" --json 2>&1)
  APP_ID=$(echo "$CREATE_OUTPUT" | jq -r '.result.appId // .appId // empty' 2>/dev/null)

  if [ -z "$APP_ID" ]; then
    echo "❌ Failed to create web app."
    echo "   Output: $CREATE_OUTPUT"
    exit 1
  fi
  echo "  ✅ Web app created: $APP_ID"
fi

# Get web app config
echo "  Fetching web app config..."
# firebase apps:sdkconfig returns the config object
CONFIG_OUTPUT=$(firebase apps:sdkconfig WEB "$APP_ID" --project "$PROJECT_ID" --json 2>&1)
CONFIG_JSON=$(echo "$CONFIG_OUTPUT" | jq -r '.result.sdkConfig // .sdkConfig // empty' 2>/dev/null)

if [ -z "$CONFIG_JSON" ]; then
  # Try to parse from the output differently
  CONFIG_JSON=$(echo "$CONFIG_OUTPUT" | jq -r '.' 2>/dev/null || echo "$CONFIG_OUTPUT")
  echo "  ⚠ Falling back to raw config extraction..."
fi

# Extract config values
API_KEY=$(echo "$CONFIG_JSON" | jq -r '.apiKey // .apiKey // empty' 2>/dev/null)
AUTH_DOMAIN=$(echo "$CONFIG_JSON" | jq -r '.authDomain // .projectId + ".firebaseapp.com"' 2>/dev/null)
STORAGE_BUCKET=$(echo "$CONFIG_JSON" | jq -r '.storageBucket // .projectId + ".appspot.com"' 2>/dev/null)
MESSAGING_SENDER_ID=$(echo "$CONFIG_JSON" | jq -r '.messagingSenderId // .projectId // empty' 2>/dev/null)
APP_URL="https://${PROJECT_ID}.web.app"

# If API_KEY is still empty, try alternative extraction
if [ -z "$API_KEY" ]; then
  echo "  ⚠ SDK config extraction failed, trying direct API call..."
  CI_TOKEN="${FIREBASE_TOKEN:-}"
  CI_TOKEN_FILE="${FIREBASE_TOKEN_PATH:-$HOME/.config/firebase/ci-token}"
  if [ -z "$CI_TOKEN" ] && [ -f "$CI_TOKEN_FILE" ]; then
    CI_TOKEN="$(cat "$CI_TOKEN_FILE" | tr -d ' \n\r')"
  fi

  API_RESP=$(curl -s -H "Authorization: Bearer $CI_TOKEN" \
    "https://firebase.googleapis.com/v1beta1/projects/${PROJECT_ID}/webApps/${APP_ID}/config" 2>/dev/null)

  API_KEY=$(echo "$API_RESP" | jq -r '.apiKey // .apiKey' 2>/dev/null)
  AUTH_DOMAIN=$(echo "$API_RESP" | jq -r '.authDomain // empty' 2>/dev/null)
  STORAGE_BUCKET=$(echo "$API_RESP" | jq -r '.storageBucket // empty' 2>/dev/null)
  MESSAGING_SENDER_ID=$(echo "$API_RESP" | jq -r '.messagingSenderId // empty' 2>/dev/null)
fi

# Set defaults for empty values
AUTH_DOMAIN="${AUTH_DOMAIN:-${PROJECT_ID}.firebaseapp.com}"
STORAGE_BUCKET="${STORAGE_BUCKET:-${PROJECT_ID}.appspot.com}"
MESSAGING_SENDER_ID="${MESSAGING_SENDER_ID:-}"

echo "  apiKey:           ${API_KEY:0:15}..."
echo "  authDomain:       $AUTH_DOMAIN"
echo "  storageBucket:    $STORAGE_BUCKET"

# Write web config as separate file
cat > "$OUTPUT_DIR/firebase-web-config.json" <<EOF
{
  "apiKey": "$API_KEY",
  "authDomain": "$AUTH_DOMAIN",
  "projectId": "$PROJECT_ID",
  "storageBucket": "$STORAGE_BUCKET",
  "messagingSenderId": "$MESSAGING_SENDER_ID",
  "appId": "$APP_ID"
}
EOF

# Merge into main output
if [ -f "$OUTPUT_DIR/firebase-output.json" ]; then
  TMP=$(mktemp)
  jq --arg apiKey "$API_KEY" \
     --arg authDomain "$AUTH_DOMAIN" \
     --arg storageBucket "$STORAGE_BUCKET" \
     --arg messagingSenderId "$MESSAGING_SENDER_ID" \
     --arg appId "$APP_ID" \
     --arg appUrl "$APP_URL" \
     '.web_app = {
       "app_id": $appId,
       "api_key": $apiKey,
       "auth_domain": $authDomain,
       "storage_bucket": $storageBucket,
       "messaging_sender_id": $messagingSenderId,
       "app_url": $appUrl
     }' "$OUTPUT_DIR/firebase-output.json" > "$TMP" && mv "$TMP" "$OUTPUT_DIR/firebase-output.json"
fi

echo "✅ Web app setup complete. Config saved to $OUTPUT_DIR/firebase-web-config.json"
