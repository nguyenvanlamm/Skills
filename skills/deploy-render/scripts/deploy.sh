#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SERVER_DIR=""
SLUG=""
GH_USER=""
OUTPUT_DIR=""

# --- Parse args ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --server-dir) SERVER_DIR="$2"; shift 2 ;;
    --slug) SLUG="$2"; shift 2 ;;
    --gh-user) GH_USER="$2"; shift 2 ;;
    --output) OUTPUT_DIR="$2"; shift 2 ;;
    --help)
      echo "Usage: $0 --server-dir <path> --slug <slug> [--gh-user <user>] [--output <dir>]"
      echo ""
      echo "Required:"
      echo "  --server-dir   Path to server project directory"
      echo "  --slug         Product slug (e.g. task-manager)"
      echo "Optional:"
      echo "  --gh-user      GitHub username (auto-detected if omitted)"
      echo "  --output       Output directory for deploy-output.json (default: server-dir)"
      exit 0
      ;;
    *) echo "Unknown arg: $1. Use --help for usage."; exit 1 ;;
  esac
done

if [ -z "$SERVER_DIR" ]; then echo "❌ --server-dir required"; exit 1; fi
if [ -z "$SLUG" ]; then echo "❌ --slug required"; exit 1; fi
SERVER_DIR="$(cd "$SERVER_DIR" 2>/dev/null && pwd)" || {
  echo "❌ Server directory not found: $SERVER_DIR"
  exit 1
}
if [ -z "$OUTPUT_DIR" ]; then OUTPUT_DIR="$SERVER_DIR"; fi
mkdir -p "$OUTPUT_DIR"

echo ""
echo "═══════════════════════════════════════════════"
echo "  Deploy Render — $SLUG"
echo "═══════════════════════════════════════════════"
echo ""

# --- Step 1: Prepare Server ---
echo "◆ Step 1/3: Preparing server code..."
bash "$SCRIPT_DIR/prepare-server.sh" \
  --server-dir "$SERVER_DIR" \
  --slug "$SLUG"
echo ""

# --- Step 2: Push to GitHub ---
echo "◆ Step 2/3: Pushing to GitHub..."
bash "$SCRIPT_DIR/push-to-github.sh" \
  --server-dir "$SERVER_DIR" \
  --slug "$SLUG" \
  ${GH_USER:+--gh-user "$GH_USER"}
echo ""

# --- Determine GH_USER if not set ---
if [ -z "$GH_USER" ]; then
  if [ -f "$SERVER_DIR/render.yaml" ]; then
    GH_USER=$(grep -oP 'github\.com/\K[^/]+' "$SERVER_DIR/render.yaml" 2>/dev/null | head -1 || true)
  fi
  if [ -z "$GH_USER" ]; then
    GH_USER=$(gh auth status 2>&1 | grep -oP 'Logged in to github\.com as \K\S+' || true)
  fi
  if [ -z "$GH_USER" ]; then
    echo "❌ Cannot determine GitHub user for Render deploy."
    exit 1
  fi
fi

# --- Step 3: Deploy to Render ---
echo "◆ Step 3/3: Deploying to Render..."
bash "$SCRIPT_DIR/render-client.sh" \
  --slug "$SLUG" \
  --gh-user "$GH_USER" \
  --output "$OUTPUT_DIR"
echo ""

echo "═══════════════════════════════════════════════"
echo "  ✅ Deploy Render Complete!"
echo "═══════════════════════════════════════════════"
echo ""
echo "  Output: $OUTPUT_DIR/deploy-output.json"
echo ""
