#!/usr/bin/env bash
set -euo pipefail

CLIENT_DIR=""
SLUG=""
API_URL=""
OUTPUT_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --client-dir) CLIENT_DIR="$2"; shift 2 ;;
    --slug) SLUG="$2"; shift 2 ;;
    --api-url) API_URL="$2"; shift 2 ;;
    --output) OUTPUT_DIR="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [ -z "$CLIENT_DIR" ]; then echo "❌ --client-dir required"; exit 1; fi
if [ -z "$SLUG" ]; then echo "❌ --slug required"; exit 1; fi
if [ -z "$OUTPUT_DIR" ]; then OUTPUT_DIR="$CLIENT_DIR"; fi
mkdir -p "$OUTPUT_DIR"

# Read Netlify token
NETLIFY_AUTH_TOKEN="${NETLIFY_AUTH_TOKEN:-}"
TOKEN_FILE="${NETLIFY_TOKEN_PATH:-$HOME/.config/netlify/token}"
if [ -z "$NETLIFY_AUTH_TOKEN" ] && [ -f "$TOKEN_FILE" ]; then
  NETLIFY_AUTH_TOKEN="$(cat "$TOKEN_FILE" | tr -d ' \n\r')"
fi

if [ -z "$NETLIFY_AUTH_TOKEN" ]; then
  echo "❌ NETLIFY_AUTH_TOKEN not set."
  echo "   Get it from: Netlify Dashboard → User Settings → Applications → Personal access tokens"
  echo "   Then: echo '<token>' > ~/.config/netlify/token"
  exit 1
fi

echo "◆ Deploying to Netlify..."

# --- Step 1: Create site ---
echo "  1/3 Creating Netlify site..."
CREATE_RESP=$(curl -s -X POST "https://api.netlify.com/api/v1/sites" \
  -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"$SLUG\",\"ssl\":true}")

SITE_ID=$(echo "$CREATE_RESP" | jq -r '.id // .site_id // empty' 2>/dev/null)
SITE_NAME=$(echo "$CREATE_RESP" | jq -r '.name // .site.name // empty' 2>/dev/null)
SITE_URL=$(echo "$CREATE_RESP" | jq -r '.ssl_url // .url // .site.ssl_url // empty' 2>/dev/null)

if [ -n "$SITE_ID" ]; then
  echo "  ✅ Site created: $SITE_NAME (ID: $SITE_ID)"
else
  # Check if site name exists — Netlify may return existing site
  SITE_ID=$(echo "$CREATE_RESP" | jq -r '.id // empty' 2>/dev/null)
  SITE_NAME=$(echo "$CREATE_RESP" | jq -r '.name // empty' 2>/dev/null)
  if [ -n "$SITE_ID" ]; then
    echo "  ✅ Using existing site: $SITE_NAME"
  else
    echo "  ⚠ Site creation response: $(echo "$CREATE_RESP" | head -c 300)"
    echo "  Trying to list existing sites..."
    SITE_ID=$(curl -s -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
      "https://api.netlify.com/api/v1/sites?filter=all" | \
      jq -r --arg name "$SLUG" '.[] | select(.name == $name) | .id' 2>/dev/null | head -1)
    if [ -n "$SITE_ID" ]; then
      echo "  Found existing site: $SITE_ID"
    else
      echo "❌ Failed to create site. Check API response."
      exit 1
    fi
  fi
  SITE_URL="https://${SITE_NAME:-$SLUG}.netlify.app"
fi

# --- Step 2: Set env vars (if api-url provided) ---
if [ -n "$API_URL" ]; then
  echo "  2/3 Setting environment variables..."
  ENV_RESP=$(curl -s -X PUT "https://api.netlify.com/api/v1/sites/$SITE_ID/env" \
    -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"key\":\"VITE_API_URL\",\"value\":\"$API_URL\",\"scopes\":[\"builds\",\"functions\"]}")

  ENV_KEY=$(echo "$ENV_RESP" | jq -r '.key // empty' 2>/dev/null)
  if [ "$ENV_KEY" = "VITE_API_URL" ]; then
    echo "  ✅ VITE_API_URL set to $API_URL"
  else
    echo "  ⚠ Env var response: $(echo "$ENV_RESP" | head -c 200)"
  fi
else
  echo "  2/3 No API URL, skipping env vars"
fi

# --- Step 3: Build & deploy ---
echo "  3/3 Building and deploying..."
cd "$CLIENT_DIR"

echo "  Building..."
BUILD_OUTPUT=$(npm run build 2>&1) || {
  echo "❌ Build failed:"
  echo "$BUILD_OUTPUT"
  exit 1
}
echo "  ✅ Build complete"

echo "  Deploying..."
DEPLOY_OUTPUT=$(npx netlify-cli deploy \
  --dir=dist \
  --prod \
  --site="$SITE_ID" \
  --auth="$NETLIFY_AUTH_TOKEN" 2>&1) || {
  echo "❌ Deploy failed:"
  echo "$DEPLOY_OUTPUT"
  exit 1
}

DEPLOY_URL=$(echo "$DEPLOY_OUTPUT" | grep -oP 'https://[^\s]+netlify\.app' | head -1 || true)
DEPLOY_ID=$(echo "$DEPLOY_OUTPUT" | grep -oP 'Deploy ID: \K\S+' || true)
FINAL_URL="${SITE_URL:-$DEPLOY_URL}"
FINAL_URL="${FINAL_URL:-https://${SLUG}.netlify.app}"

echo "  ✅ Deploy complete"

# --- Write output ---
OUTPUT_FILE="$OUTPUT_DIR/netlify-output.json"
cat > "$OUTPUT_FILE" <<EOF
{
  "url": "$FINAL_URL",
  "site_id": "$SITE_ID",
  "site_name": "${SITE_NAME:-$SLUG}",
  "deploy_id": "${DEPLOY_ID:-unknown}"
}
EOF

echo "✅ Output written to $OUTPUT_FILE"
echo ""
echo "═══════════════════════════════════════════════"
echo "  🌐 Deploy to Netlify complete!"
echo "═══════════════════════════════════════════════"
echo ""
echo "  URL:    $FINAL_URL"
echo "  Site:   $SITE_ID"
echo ""
