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

[ -n "$CLIENT_DIR" ] || { echo "❌ --client-dir required"; exit 1; }
[ -n "$SLUG" ]       || { echo "❌ --slug required"; exit 1; }
[ -n "$OUTPUT_DIR" ] || OUTPUT_DIR="$CLIENT_DIR"
mkdir -p "$OUTPUT_DIR"

for cmd in curl jq npm; do
  command -v "$cmd" >/dev/null || { echo "❌ Missing required command: $cmd"; exit 1; }
done

# --- Auth ---
NETLIFY_AUTH_TOKEN="${NETLIFY_AUTH_TOKEN:-}"
TOKEN_FILE="${NETLIFY_TOKEN_PATH:-$HOME/.config/netlify/token}"
if [ -z "$NETLIFY_AUTH_TOKEN" ] && [ -f "$TOKEN_FILE" ]; then
  NETLIFY_AUTH_TOKEN="$(tr -d ' \n\r' < "$TOKEN_FILE")"
fi
if [ -z "$NETLIFY_AUTH_TOKEN" ]; then
  echo "❌ NETLIFY_AUTH_TOKEN not set."
  echo "   Netlify Dashboard → User settings → Applications → Personal access tokens"
  echo "   Then: echo '<token>' > ~/.config/netlify/token && chmod 600 ~/.config/netlify/token"
  exit 1
fi
export NETLIFY_AUTH_TOKEN

api() {  # api <method> <path> [json-body]
  local method="$1" path="$2" body="${3:-}"
  if [ -n "$body" ]; then
    curl -sS -X "$method" "https://api.netlify.com/api/v1$path" \
      -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
      -H "Content-Type: application/json" -d "$body"
  else
    curl -sS -X "$method" "https://api.netlify.com/api/v1$path" \
      -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN"
  fi
}

echo "◆ Deploying to Netlify..."

# --- 1. Find or create the site -------------------------------------------
# Look first. Netlify site names are globally unique, so a create call for a
# taken name errors — and a blind retry would leave us pointing at whatever
# site the API decided to name instead.
echo "  1/3 Resolving site '$SLUG'..."
SITE_JSON=$(api GET "/sites?filter=all" | jq -r --arg n "$SLUG" '[.[] | select(.name == $n)][0] // empty')

if [ -z "$SITE_JSON" ]; then
  SITE_JSON=$(api POST "/sites" "{\"name\":\"$SLUG\",\"ssl\":true}")
  if [ -z "$(jq -r '.id // empty' <<<"$SITE_JSON")" ]; then
    echo "❌ Could not create site '$SLUG':"
    jq -r '.message // .errors // .' <<<"$SITE_JSON" 2>/dev/null | head -5
    echo "   Netlify site names are globally unique — try a more specific --slug."
    exit 1
  fi
  echo "  ✅ Created site"
else
  echo "  ✅ Reusing existing site"
fi

SITE_ID=$(jq -r '.id' <<<"$SITE_JSON")
SITE_NAME=$(jq -r '.name' <<<"$SITE_JSON")
ACCOUNT_ID=$(jq -r '.account_id // .account_slug // empty' <<<"$SITE_JSON")
SITE_URL=$(jq -r '.ssl_url // .url // empty' <<<"$SITE_JSON")
[ -n "$SITE_URL" ] || SITE_URL="https://${SITE_NAME}.netlify.app"
echo "     $SITE_NAME ($SITE_ID)"

# --- 2. Environment variable ----------------------------------------------
# The build below runs locally, so Vite inlines VITE_API_URL from
# .env.production — that is the value that actually reaches the browser.
# Mirroring it into Netlify only matters if the repo is later linked for
# Netlify-side builds. Failure here is not a deploy failure.
if [ -n "$API_URL" ]; then
  echo "  2/3 Mirroring VITE_API_URL into Netlify site config..."
  if [ -n "$ACCOUNT_ID" ]; then
    ENV_RESP=$(api POST "/accounts/$ACCOUNT_ID/env?site_id=$SITE_ID" \
      "[{\"key\":\"VITE_API_URL\",\"scopes\":[\"builds\",\"runtime\"],\"values\":[{\"context\":\"all\",\"value\":\"$API_URL\"}]}]")
    if jq -e 'type=="array" and any(.[]; .key=="VITE_API_URL")' <<<"$ENV_RESP" >/dev/null 2>&1; then
      echo "  ✅ Mirrored (the build-time value comes from .env.production)"
    else
      echo "  ⚠ Could not mirror env var — harmless for this deploy:"
      jq -r '.message // .' <<<"$ENV_RESP" 2>/dev/null | head -3
    fi
  else
    echo "  ⚠ No account id on the site record; skipping mirror (harmless for this deploy)"
  fi
else
  echo "  2/3 No --api-url; static site, nothing to configure"
fi

# --- 3. Build and deploy ---------------------------------------------------
echo "  3/3 Building and deploying..."
cd "$CLIENT_DIR"

npm run build 2>&1 | tail -20 || { echo "❌ Build failed (see output above)"; exit 1; }
[ -d dist ] || { echo "❌ Build produced no dist/ directory"; exit 1; }
echo "  ✅ Build complete"

DEPLOY_JSON=$(npx --yes netlify-cli deploy \
  --dir=dist --prod --site="$SITE_ID" --json 2>/dev/null) || {
  echo "❌ Deploy failed. Re-run without --json for detail:"
  echo "   npx netlify-cli deploy --dir=dist --prod --site=$SITE_ID"
  exit 1
}

DEPLOY_ID=$(jq -r '.deploy_id // .deployId // empty' <<<"$DEPLOY_JSON")
DEPLOY_URL=$(jq -r '.deploy_url // empty' <<<"$DEPLOY_JSON")
FINAL_URL=$(jq -r '.url // empty' <<<"$DEPLOY_JSON")
[ -n "$FINAL_URL" ] || FINAL_URL="$SITE_URL"
echo "  ✅ Deploy complete"

# --- Verify it actually serves --------------------------------------------
echo "◆ Verifying $FINAL_URL ..."
HTTP_CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 30 -L "$FINAL_URL" || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
  VERIFIED=true;  echo "  ✅ HTTP 200"
else
  VERIFIED=false; echo "  ⚠ HTTP $HTTP_CODE — deploy was accepted but the site did not serve a 200."
fi

# --- Output ---------------------------------------------------------------
OUTPUT_FILE="$OUTPUT_DIR/netlify-output.json"
jq -n \
  --arg url "$FINAL_URL" --arg site_id "$SITE_ID" --arg site_name "$SITE_NAME" \
  --arg deploy_id "${DEPLOY_ID:-}" --arg deploy_url "${DEPLOY_URL:-}" \
  --argjson verified "$VERIFIED" \
  '{url:$url, site_id:$site_id, site_name:$site_name, deploy_id:$deploy_id, deploy_preview_url:$deploy_url, verified:$verified}' \
  > "$OUTPUT_FILE"

echo ""
echo "  URL:      $FINAL_URL   ($([ "$VERIFIED" = true ] && echo 'verified 200' || echo "unverified — HTTP $HTTP_CODE"))"
echo "  Site:     $SITE_NAME ($SITE_ID)"
echo "  Output:   $OUTPUT_FILE"
echo ""

[ "$VERIFIED" = true ] || exit 2
