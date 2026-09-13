#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SERVER_DIR=""
SLUG=""
GH_USER=""
OUTPUT_DIR=""
NO_DB=false
REGION="${RENDER_REGION:-oregon}"
HEALTH_PATH="${RENDER_HEALTH_PATH:-/docs}"
VISIBILITY_FLAG=""

usage() {
  cat <<EOF
Usage: $0 --server-dir <path> --slug <slug> [options]

Required:
  --server-dir    Path to the FastAPI server root (contains main.py)
  --slug          Product slug → service <slug>-server, database <slug>-db
Optional:
  --gh-user       GitHub account (default: gh api user)
  --public        Create the GitHub repo public (default: private)
  --output        Directory for deploy-output.json (default: server-dir)
  --no-db         Skip PostgreSQL; keep SQLite
  --region        Render region (default: $REGION; also RENDER_REGION)
  --health-path   Path curl-ed to verify the deploy (default: $HEALTH_PATH; also RENDER_HEALTH_PATH)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --server-dir) SERVER_DIR="$2"; shift 2 ;;
    --slug) SLUG="$2"; shift 2 ;;
    --gh-user) GH_USER="$2"; shift 2 ;;
    --output) OUTPUT_DIR="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --health-path) HEALTH_PATH="$2"; shift 2 ;;
    --no-db) NO_DB=true; shift ;;
    --public) VISIBILITY_FLAG="--public"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown arg: $1. Use --help for usage."; exit 1 ;;
  esac
done

[ -n "$SERVER_DIR" ] || { echo "❌ --server-dir required"; exit 1; }
[ -n "$SLUG" ]       || { echo "❌ --slug required"; exit 1; }
SERVER_DIR="$(cd "$SERVER_DIR" 2>/dev/null && pwd)" || { echo "❌ Server directory not found: $SERVER_DIR"; exit 1; }
[ -n "$OUTPUT_DIR" ] || OUTPUT_DIR="$SERVER_DIR"
mkdir -p "$OUTPUT_DIR"; OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"

# Render service names: lowercase letters, digits, hyphens. Anything else is a
# confusing API error three minutes in.
printf '%s' "$SLUG" | grep -qE '^[a-z0-9][a-z0-9-]{0,50}$' || {
  echo "❌ --slug must be lowercase letters, digits and hyphens (got: $SLUG)"; exit 1; }
printf '%s' "$HEALTH_PATH" | grep -q '^/' || { echo "❌ --health-path must start with / (got: $HEALTH_PATH)"; exit 1; }

# Everything the three steps need, checked once, up front.
for cmd in curl jq git gh; do
  command -v "$cmd" >/dev/null || { echo "❌ Missing required command: $cmd"; exit 1; }
done
[ -f "$SERVER_DIR/main.py" ] || { echo "❌ No main.py in $SERVER_DIR — not a FastAPI server root"; exit 1; }
KEY_FILE="${RENDER_KEY_FILE:-$HOME/.config/render/api-key}"
if [ -z "${RENDER_API_KEY:-}" ] && [ ! -s "$KEY_FILE" ]; then
  echo "❌ RENDER_API_KEY not set and $KEY_FILE missing."
  echo "   Render Dashboard → Account Settings → API Keys → Create, then:"
  echo "   mkdir -p ~/.config/render && echo '<key>' > ~/.config/render/api-key && chmod 600 ~/.config/render/api-key"
  exit 1
fi

NO_DB_FLAG=""; [ "$NO_DB" = true ] && NO_DB_FLAG="--no-db"
DB_LABEL="with PostgreSQL"; [ "$NO_DB" = true ] && DB_LABEL="without database"

echo ""
echo "═══════════════════════════════════════════════"
echo "  Deploy Render — $SLUG ($DB_LABEL, $REGION)"
echo "═══════════════════════════════════════════════"
echo ""

echo "◆ Step 1/3: Preparing server code..."
bash "$SCRIPT_DIR/prepare-server.sh" --server-dir "$SERVER_DIR" --slug "$SLUG" \
  --region "$REGION" --health-path "$HEALTH_PATH" $NO_DB_FLAG
echo ""

echo "◆ Step 2/3: Pushing to GitHub..."
bash "$SCRIPT_DIR/push-to-github.sh" --server-dir "$SERVER_DIR" --slug "$SLUG" \
  ${GH_USER:+--gh-user "$GH_USER"} ${VISIBILITY_FLAG}
echo ""

# push-to-github.sh resolved the owner and wrote it into render.yaml; read it
# back from there so both steps agree on the repo URL.
if [ -z "$GH_USER" ]; then
  GH_USER=$(sed -n 's|.*github\.com/\([^/]*\)/.*|\1|p' "$SERVER_DIR/render.yaml" 2>/dev/null | head -1 || true)
  [ -n "$GH_USER" ] || GH_USER=$(gh api user --jq .login 2>/dev/null || true)
  [ -n "$GH_USER" ] || { echo "❌ Cannot determine GitHub user for Render deploy."; exit 1; }
fi
BRANCH=$(git -C "$SERVER_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)

echo "◆ Step 3/3: Deploying to Render..."
bash "$SCRIPT_DIR/render-client.sh" --slug "$SLUG" --gh-user "$GH_USER" --branch "$BRANCH" \
  --region "$REGION" --health-path "$HEALTH_PATH" --output "$OUTPUT_DIR" $NO_DB_FLAG
echo ""

echo "═══════════════════════════════════════════════"
echo "  ✅ Deploy Render Complete!"
echo "═══════════════════════════════════════════════"
echo ""
echo "  Output: $OUTPUT_DIR/deploy-output.json"
echo ""
