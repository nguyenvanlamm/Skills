#!/usr/bin/env bash
set -euo pipefail

SLUG=""
GH_USER=""
OUTPUT_DIR=""
NO_DB=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --slug) SLUG="$2"; shift 2 ;;
    --gh-user) GH_USER="$2"; shift 2 ;;
    --output) OUTPUT_DIR="$2"; shift 2 ;;
    --no-db) NO_DB=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [ -z "$SLUG" ]; then echo "❌ --slug required"; exit 1; fi
if [ -z "$GH_USER" ]; then echo "❌ --gh-user required"; exit 1; fi
if [ -z "$OUTPUT_DIR" ]; then OUTPUT_DIR="$PWD"; fi

mkdir -p "$OUTPUT_DIR"

# Read Render API key
RENDER_API_KEY="${RENDER_API_KEY:-}"
RENDER_KEY_FILE="${RENDER_KEY_FILE:-$HOME/.config/render/api-key}"
if [ -z "$RENDER_API_KEY" ] && [ -f "$RENDER_KEY_FILE" ]; then
  RENDER_API_KEY="$(cat "$RENDER_KEY_FILE" | tr -d ' \n\r')"
fi

if [ -z "$RENDER_API_KEY" ]; then
  echo "❌ RENDER_API_KEY not set."
  echo "   Get it from: Render Dashboard → Account Settings → API Keys"
  echo "   Then: echo '<key>' > ~/.config/render/api-key"
  echo "   Or: export RENDER_API_KEY=<key>"
  exit 1
fi

RENDER_API="https://api.render.com/v1"
REPO_URL="https://github.com/$GH_USER/${SLUG}-server"
OUTPUT_FILE="$OUTPUT_DIR/deploy-output.json"

echo "◆ Deploying to Render..."
TOTAL_STEPS=3
if [ "$NO_DB" = false ]; then TOTAL_STEPS=4; fi

CURRENT=1

# --- Step 1: Create PostgreSQL database (skip if --no-db) ---
DB_ID=""
if [ "$NO_DB" = true ]; then
  echo "  ⏭  --no-db: skipping PostgreSQL creation"
else
  echo "  $CURRENT/$TOTAL_STEPS Creating PostgreSQL database..."
  CURRENT=$((CURRENT + 1))
  DB_RESP=$(curl -s -X POST "$RENDER_API/postgres" \
    -H "Authorization: Bearer $RENDER_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"${SLUG}-db\",
      \"plan\": \"free\",
      \"region\": \"oregon\",
      \"version\": \"16\"
    }")

  DB_ID=$(echo "$DB_RESP" | jq -r '.id // .database.id // empty' 2>/dev/null)

  if [ -n "$DB_ID" ]; then
    echo "  ✅ PostgreSQL database created: $DB_ID"
  else
    echo "  ⚠ Could not parse DB creation response. Listing existing databases..."
    EXISTING_DB=$(curl -s -H "Authorization: Bearer $RENDER_API_KEY" "$RENDER_API/postgres" | \
      jq -r --arg name "${SLUG}-db" '.[] | select(.name == $name) | .id // .database.id' 2>/dev/null | head -1)
    if [ -n "$EXISTING_DB" ]; then
      DB_ID="$EXISTING_DB"
      echo "  Using existing database: $DB_ID"
    else
      echo "  ⚠ Database creation may have failed. Check Render Dashboard."
      echo "  Response: $(echo "$DB_RESP" | head -c 500)"
    fi
  fi
fi

# --- Step 2 (or 1): Sync Blueprint ---
echo "  $CURRENT/$TOTAL_STEPS Syncing Render Blueprint..."
CURRENT=$((CURRENT + 1))

if [ "$NO_DB" = true ]; then
  BLUEPRINT_DATA="{
    \"repoUrl\": \"$REPO_URL\",
    \"branch\": \"main\"
  }"
else
  BLUEPRINT_DATA="{
    \"repoUrl\": \"$REPO_URL\",
    \"branch\": \"main\",
    \"serviceOverrides\": [
      {
        \"type\": \"web\",
        \"envVars\": [
          {
            \"key\": \"DATABASE_URL\",
            \"fromDatabase\": {
              \"name\": \"${SLUG}-db\"
            }
          }
        ]
      }
    ]
  }"
fi

BLUEPRINT_RESP=$(curl -s -X POST "$RENDER_API/blueprints/sync" \
  -H "Authorization: Bearer $RENDER_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$BLUEPRINT_DATA")

SERVICE_ID=$(echo "$BLUEPRINT_RESP" | jq -r '.service.id // .serviceId // (.services[0].id // empty)' 2>/dev/null)
DEPLOY_ID=$(echo "$BLUEPRINT_RESP" | jq -r '.deploy.id // .deployId // (.deploys[0].id // empty)' 2>/dev/null)

if [ -z "$SERVICE_ID" ]; then
  SERVICE_ID=$(echo "$BLUEPRINT_RESP" | jq -r '.[0].id // .[0].service.id // empty' 2>/dev/null)
fi

if [ -n "$SERVICE_ID" ]; then
  echo "  ✅ Blueprint synced: Service $SERVICE_ID"
else
  echo "  ⚠ Blueprint sync response, trying to find service..."
  SERVICE_ID=$(curl -s -H "Authorization: Bearer $RENDER_API_KEY" "$RENDER_API/services" | \
    jq -r --arg name "${SLUG}-server" '.[] | select(.name == $name) | .id // .service.id' 2>/dev/null | head -1)
  if [ -z "$SERVICE_ID" ]; then
    echo "  ⚠ Warning: Could not find/create service. Deploy may need manual setup."
    echo "  Response: $(echo "$BLUEPRINT_RESP" | head -c 300)"
  else
    echo "  Found existing service: $SERVICE_ID"
  fi
fi

# --- Step 3 (or 2): Poll deploy status ---
if [ -n "$SERVICE_ID" ]; then
  echo "  $CURRENT/$TOTAL_STEPS Waiting for deploy to complete..."
  CURRENT=$((CURRENT + 1))

  if [ -z "$DEPLOY_ID" ]; then
    echo "  Triggering new deploy..."
    DEPLOY_RESP=$(curl -s -X POST "$RENDER_API/services/$SERVICE_ID/deploys" \
      -H "Authorization: Bearer $RENDER_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{}')
    DEPLOY_ID=$(echo "$DEPLOY_RESP" | jq -r '.id // .deploy.id // empty' 2>/dev/null)
  fi

  if [ -n "$DEPLOY_ID" ]; then
    echo "  Deploy ID: $DEPLOY_ID"
    echo "  Polling (this may take 3-5 minutes)..."
    
    MAX_POLLS=90
    POLL=0
    while [ "$POLL" -lt "$MAX_POLLS" ]; do
      STATUS_RESP=$(curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
        "$RENDER_API/services/$SERVICE_ID/deploys/$DEPLOY_ID")
      STATUS=$(echo "$STATUS_RESP" | jq -r '.status // .deploy.status // "unknown"' 2>/dev/null)
      
      case "$STATUS" in
        "live")
          echo "  ✅ Deploy LIVE!"
          break
          ;;
        "failed")
          echo "  ❌ Deploy failed."
          echo "  Logs: $(echo "$STATUS_RESP" | jq -r '.message // .deploy.message // "No details"' 2>/dev/null | head -c 500)"
          break
          ;;
        "canceled")
          echo "  ⚠ Deploy canceled."
          break
          ;;
        *)
          printf "  Status: %s (%ds)\n" "$STATUS" $((POLL * 10))
          sleep 10
          POLL=$((POLL + 1))
          ;;
      esac
    done

    if [ "$POLL" -ge "$MAX_POLLS" ]; then
      echo "  ⏰ Timeout waiting for deploy. Check Render Dashboard."
    fi
  else
    echo "  ⚠ No deploy ID. Waiting for auto-deploy..."
    sleep 30
  fi
fi

# --- Step 4 (or 3): Get service URL ---
echo "  $CURRENT/$TOTAL_STEPS Getting service URL..."
CURRENT=$((CURRENT + 1))
SERVICE_URL=""
if [ -n "$SERVICE_ID" ]; then
  SVC_RESP=$(curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
    "$RENDER_API/services/$SERVICE_ID")
  SERVICE_URL=$(echo "$SVC_RESP" | jq -r '.serviceDetails.url // .url // .service.url // empty' 2>/dev/null)
fi

if [ -z "$SERVICE_URL" ]; then
  SERVICE_URL="https://${SLUG}-server.onrender.com"
  echo "  ⚠ Could not fetch URL from API. Using default: $SERVICE_URL"
else
  echo "  ✅ Service URL: $SERVICE_URL"
fi

# --- Write output ---
if [ "$NO_DB" = true ]; then
  cat > "$OUTPUT_FILE" <<EOF
{
  "url": "$SERVICE_URL",
  "service_id": "${SERVICE_ID:-unknown}",
  "repo_url": "$REPO_URL",
  "status": "${STATUS:-unknown}",
  "has_db": false
}
EOF
else
  cat > "$OUTPUT_FILE" <<EOF
{
  "url": "$SERVICE_URL",
  "database_id": "${DB_ID:-unknown}",
  "service_id": "${SERVICE_ID:-unknown}",
  "repo_url": "$REPO_URL",
  "status": "${STATUS:-unknown}",
  "has_db": true
}
EOF
fi

echo "✅ Output written to $OUTPUT_FILE"
echo ""
echo "═══════════════════════════════════════════════"
echo "  🌐 Deploy to Render complete!"
echo "═══════════════════════════════════════════════"
echo ""
echo "  URL:        $SERVICE_URL"
echo "  API docs:   $SERVICE_URL/docs"
echo "  Repo:       $REPO_URL"
echo "  Database:   $([ "$NO_DB" = true ] && echo 'None' || echo "Created ($DB_ID)")"
echo ""
