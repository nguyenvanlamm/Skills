#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CLIENT_DIR=""
SLUG=""
API_URL=""
GH_USER=""
OUTPUT_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --client-dir) CLIENT_DIR="$2"; shift 2 ;;
    --slug) SLUG="$2"; shift 2 ;;
    --api-url) API_URL="$2"; shift 2 ;;
    --gh-user) GH_USER="$2"; shift 2 ;;
    --output) OUTPUT_DIR="$2"; shift 2 ;;
    --help)
      echo "Usage: $0 --client-dir <path> --slug <slug> [--api-url <url>] [--gh-user <user>]"
      exit 0 ;;
    *) echo "Unknown: $1"; exit 1 ;;
  esac
done

if [ -z "$CLIENT_DIR" ]; then echo "❌ --client-dir required"; exit 1; fi
if [ -z "$SLUG" ]; then echo "❌ --slug required"; exit 1; fi
if [ -z "$OUTPUT_DIR" ]; then OUTPUT_DIR="$CLIENT_DIR"; fi

CLIENT_DIR="$(cd "$CLIENT_DIR" 2>/dev/null && pwd)" || {
  echo "❌ Directory not found: $CLIENT_DIR"; exit 1
}
mkdir -p "$OUTPUT_DIR"

echo ""
echo "═══════════════════════════════════════════════"
echo "  Deploy Netlify — $SLUG"
echo "═══════════════════════════════════════════════"
echo ""

# Step 1
echo "◆ Step 1/3: Preparing client code..."
bash "$SCRIPT_DIR/prepare-client.sh" \
  --client-dir "$CLIENT_DIR" \
  --slug "$SLUG" \
  ${API_URL:+--api-url "$API_URL"}
echo ""

# Step 2
echo "◆ Step 2/3: Pushing to GitHub..."
bash "$SCRIPT_DIR/push-to-github.sh" \
  --client-dir "$CLIENT_DIR" \
  --slug "$SLUG" \
  ${GH_USER:+--gh-user "$GH_USER"}
echo ""

# Step 3
echo "◆ Step 3/3: Deploying to Netlify..."
bash "$SCRIPT_DIR/netlify-client.sh" \
  --client-dir "$CLIENT_DIR" \
  --slug "$SLUG" \
  ${API_URL:+--api-url "$API_URL"} \
  --output "$OUTPUT_DIR"
echo ""

echo "═══════════════════════════════════════════════"
echo "  ✅ Deploy Netlify Complete!"
echo "═══════════════════════════════════════════════"
echo ""
echo "  Output: $OUTPUT_DIR/netlify-output.json"
echo ""
