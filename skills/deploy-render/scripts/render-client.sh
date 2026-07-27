#!/usr/bin/env bash
set -euo pipefail

SLUG=""
GH_USER=""
OUTPUT_DIR=""
NO_DB=false
REGION="${RENDER_REGION:-oregon}"
HEALTH_PATH="${RENDER_HEALTH_PATH:-/docs}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --slug) SLUG="$2"; shift 2 ;;
    --gh-user) GH_USER="$2"; shift 2 ;;
    --output) OUTPUT_DIR="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --health-path) HEALTH_PATH="$2"; shift 2 ;;
    --no-db) NO_DB=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

[ -n "$SLUG" ] || { echo "❌ --slug required"; exit 1; }
if [ -z "$GH_USER" ]; then
  GH_USER=$(gh api user --jq .login 2>/dev/null || true)
  [ -n "$GH_USER" ] || { echo "❌ --gh-user required (or run 'gh auth login')"; exit 1; }
fi
[ -n "$OUTPUT_DIR" ] || OUTPUT_DIR="$PWD"
mkdir -p "$OUTPUT_DIR"

for cmd in curl jq; do
  command -v "$cmd" >/dev/null || { echo "❌ Missing required command: $cmd"; exit 1; }
done

# --- Auth ---
RENDER_API_KEY="${RENDER_API_KEY:-}"
RENDER_KEY_FILE="${RENDER_KEY_FILE:-$HOME/.config/render/api-key}"
if [ -z "$RENDER_API_KEY" ] && [ -f "$RENDER_KEY_FILE" ]; then
  RENDER_API_KEY="$(tr -d ' \n\r' < "$RENDER_KEY_FILE")"
fi
if [ -z "$RENDER_API_KEY" ]; then
  echo "❌ RENDER_API_KEY not set."
  echo "   Render Dashboard → Account Settings → API Keys → Create"
  echo "   Then: echo '<key>' > ~/.config/render/api-key && chmod 600 ~/.config/render/api-key"
  exit 1
fi

RENDER_API="https://api.render.com/v1"
REPO_URL="https://github.com/$GH_USER/${SLUG}-server"
OUTPUT_FILE="$OUTPUT_DIR/deploy-output.json"

# api <method> <path> [body] — retries on 429/5xx, prints body, returns non-zero on HTTP error
api() {
  local method="$1" path="$2" body="${3:-}" attempt=1 code resp
  while :; do
    if [ -n "$body" ]; then
      resp=$(curl -sS -w '\n%{http_code}' -X "$method" "$RENDER_API$path" \
        -H "Authorization: Bearer $RENDER_API_KEY" \
        -H "Content-Type: application/json" -d "$body")
    else
      resp=$(curl -sS -w '\n%{http_code}' -X "$method" "$RENDER_API$path" \
        -H "Authorization: Bearer $RENDER_API_KEY")
    fi
    code="${resp##*$'\n'}"
    body_out="${resp%$'\n'*}"
    case "$code" in
      2*) printf '%s' "$body_out"; return 0 ;;
      429|5*)
        if [ "$attempt" -ge 3 ]; then
          echo "API $method $path failed after $attempt attempts (HTTP $code)" >&2
          printf '%s' "$body_out" >&2; return 1
        fi
        echo "  ⏳ HTTP $code — retrying in 30s (attempt $attempt/3)" >&2
        sleep 30; attempt=$((attempt + 1)) ;;
      *)
        echo "API $method $path → HTTP $code" >&2
        printf '%s' "$body_out" >&2; return 1 ;;
    esac
  done
}

fail() { echo ""; echo "❌ $*"; echo "   Output: $OUTPUT_FILE"; }

echo "◆ Deploying to Render — $SLUG"
[ "$NO_DB" = true ] || cat <<'WARN'

  ⚠ Free PostgreSQL on Render expires 30 days after creation. There is a
    14-day grace period to upgrade, after which the database and all its
    data are deleted. Plan for that before putting anything real in it.
WARN

# --- 1. PostgreSQL --------------------------------------------------------
DB_ID=""; DB_STATUS="skipped"
if [ "$NO_DB" = false ]; then
  echo "  1. PostgreSQL '${SLUG}-db'..."
  EXISTING=$(api GET "/postgres?limit=100" 2>/dev/null \
    | jq -r --arg n "${SLUG}-db" '[.[] | (.postgres // .) | select(.name == $n)][0].id // empty' 2>/dev/null || true)
  if [ -n "$EXISTING" ]; then
    DB_ID="$EXISTING"; DB_STATUS="existing"
    echo "     ✅ Reusing $DB_ID"
  else
    DB_RESP=$(api POST "/postgres" \
      "{\"name\":\"${SLUG}-db\",\"plan\":\"free\",\"region\":\"$REGION\",\"version\":\"16\"}") || {
      fail "Could not create the database. The response above is what Render returned."
      exit 1
    }
    DB_ID=$(jq -r '.id // .postgres.id // empty' <<<"$DB_RESP")
    [ -n "$DB_ID" ] || { fail "Database create returned 2xx but no id: $(head -c 300 <<<"$DB_RESP")"; exit 1; }
    DB_STATUS="created"
    echo "     ✅ Created $DB_ID"
  fi
fi

# --- 2. Blueprint sync ----------------------------------------------------
# The service is defined by render.yaml in the repo (see prepare-server.sh).
echo "  2. Syncing blueprint from $REPO_URL ..."
if [ "$NO_DB" = true ]; then
  BP="{\"repoUrl\":\"$REPO_URL\",\"branch\":\"main\"}"
else
  BP="{\"repoUrl\":\"$REPO_URL\",\"branch\":\"main\",\"serviceOverrides\":[{\"type\":\"web\",\"envVars\":[{\"key\":\"DATABASE_URL\",\"fromDatabase\":{\"name\":\"${SLUG}-db\"}}]}]}"
fi

SERVICE_ID=""; DEPLOY_ID=""
if BP_RESP=$(api POST "/blueprints/sync" "$BP" 2>/dev/null); then
  SERVICE_ID=$(jq -r '[.. | objects | select(has("id")) | select((.type? // "") == "web_service" or (.serviceDetails? != null)) | .id][0] // empty' <<<"$BP_RESP" 2>/dev/null || true)
  DEPLOY_ID=$(jq -r '.deploy.id // .deployId // empty' <<<"$BP_RESP" 2>/dev/null || true)
fi

if [ -z "$SERVICE_ID" ]; then
  echo "     Blueprint sync did not return a service; looking one up by name..."
  SERVICE_ID=$(api GET "/services?limit=100" 2>/dev/null \
    | jq -r --arg n "${SLUG}-server" '[.[] | (.service // .) | select(.name == $n)][0].id // empty' 2>/dev/null || true)
fi

if [ -z "$SERVICE_ID" ]; then
  fail "No service could be created or found for '${SLUG}-server'.
   Render's Blueprint API is the least stable part of this flow. Create the
   service once from the Dashboard (New → Blueprint, pick $REPO_URL); after
   that this script finds it by name and every later run works."
  exit 1
fi
echo "     ✅ Service $SERVICE_ID"

# --- 3. Deploy ------------------------------------------------------------
echo "  3. Deploying (3–5 minutes on the free plan)..."
if [ -z "$DEPLOY_ID" ]; then
  DEPLOY_RESP=$(api POST "/services/$SERVICE_ID/deploys" '{}') || { fail "Could not trigger a deploy."; exit 1; }
  DEPLOY_ID=$(jq -r '.id // .deploy.id // empty' <<<"$DEPLOY_RESP")
fi
[ -n "$DEPLOY_ID" ] || { fail "No deploy id returned."; exit 1; }

STATUS="unknown"; POLL=0; MAX_POLLS=90
while [ "$POLL" -lt "$MAX_POLLS" ]; do
  SR=$(api GET "/services/$SERVICE_ID/deploys/$DEPLOY_ID" 2>/dev/null || echo '{}')
  STATUS=$(jq -r '.status // .deploy.status // "unknown"' <<<"$SR")
  case "$STATUS" in
    live) echo "     ✅ live"; break ;;
    build_failed|update_failed|failed|canceled|deactivated)
      echo "     ❌ $STATUS"
      jq -r '.message // .deploy.message // empty' <<<"$SR" | head -c 800
      echo ""
      echo "     Full log: https://dashboard.render.com/web/$SERVICE_ID/deploys/$DEPLOY_ID"
      break ;;
    *) printf '     %s (%ds)\n' "$STATUS" $((POLL * 10)); sleep 10; POLL=$((POLL + 1)) ;;
  esac
done
[ "$POLL" -lt "$MAX_POLLS" ] || { STATUS="timeout"; echo "     ⏰ Timed out after 15 minutes."; }

# --- 4. URL and verification ---------------------------------------------
echo "  4. Resolving URL..."
SERVICE_URL=$(api GET "/services/$SERVICE_ID" 2>/dev/null \
  | jq -r '.serviceDetails.url // .service.serviceDetails.url // .url // empty' 2>/dev/null || true)

VERIFIED=false; HTTP_CODE="n/a"
if [ -z "$SERVICE_URL" ]; then
  # Do not invent a URL — a guessed hostname written into deploy-output.json
  # is consumed by deploy-netlify as --api-url, pointing the client at nothing.
  echo "     ⚠ Render did not return a URL for this service."
else
  echo "     $SERVICE_URL"
  echo "  5. Verifying ${SERVICE_URL}${HEALTH_PATH} ..."
  # First request after a cold start can take ~60s on the free plan.
  HTTP_CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 90 -L "${SERVICE_URL}${HEALTH_PATH}" || echo "000")
  if [ "$HTTP_CODE" = "200" ]; then
    VERIFIED=true; echo "     ✅ HTTP 200"
  else
    echo "     ⚠ HTTP $HTTP_CODE — deploy reported '$STATUS' but the app did not answer."
  fi
fi

# --- Output ---------------------------------------------------------------
jq -n \
  --arg url "${SERVICE_URL:-}" --arg service_id "$SERVICE_ID" --arg deploy_id "$DEPLOY_ID" \
  --arg database_id "${DB_ID:-}" --arg db_status "$DB_STATUS" --arg repo_url "$REPO_URL" \
  --arg status "$STATUS" --arg http_code "$HTTP_CODE" \
  --argjson has_db "$([ "$NO_DB" = true ] && echo false || echo true)" \
  --argjson verified "$VERIFIED" \
  '{url:$url, service_id:$service_id, deploy_id:$deploy_id, database_id:$database_id,
    database_status:$db_status, repo_url:$repo_url, status:$status,
    http_code:$http_code, has_db:$has_db, verified:$verified}' > "$OUTPUT_FILE"

echo ""
if [ "$VERIFIED" = true ]; then
  echo "✅ Deploy live and verified"
  echo "   URL:  $SERVICE_URL"
  echo "   Docs: ${SERVICE_URL}/docs"
  [ "$NO_DB" = true ] || echo "   DB:   $DB_ID  (free plan — expires in 30 days)"
  echo "   Out:  $OUTPUT_FILE"
  exit 0
else
  echo "❌ Deploy did not verify — status '$STATUS', HTTP $HTTP_CODE"
  echo "   Dashboard: https://dashboard.render.com/web/$SERVICE_ID"
  echo "   Out:       $OUTPUT_FILE  (verified: false)"
  exit 2
fi
