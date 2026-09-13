#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CLIENT_DIR=""
SLUG=""
API_URL=""
GH_USER=""
OUTPUT_DIR=""
VISIBILITY_FLAG=""
SKIP_GITHUB=false

usage() {
  cat <<EOF
Usage: $0 --client-dir <path> --slug <slug> [options]

Required:
  --client-dir   Vite/React project directory
  --slug         Netlify site name (globally unique on Netlify)
Optional:
  --api-url      Production server URL → VITE_API_URL baked into the build
  --gh-user      GitHub account (default: gh api user)
  --public       Create the GitHub repo public (default: private)
  --skip-github  Do not create/push a GitHub repo (deploy only)
  --output       Directory for netlify-output.json (default: client-dir)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --client-dir) CLIENT_DIR="$2"; shift 2 ;;
    --slug) SLUG="$2"; shift 2 ;;
    --api-url) API_URL="$2"; shift 2 ;;
    --gh-user) GH_USER="$2"; shift 2 ;;
    --output) OUTPUT_DIR="$2"; shift 2 ;;
    --public) VISIBILITY_FLAG="--public"; shift ;;
    --skip-github) SKIP_GITHUB=true; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown arg: $1"; usage; exit 1 ;;
  esac
done

[ -n "$CLIENT_DIR" ] || { echo "❌ --client-dir required"; exit 1; }
[ -n "$SLUG" ]       || { echo "❌ --slug required"; exit 1; }
[ -n "$OUTPUT_DIR" ] || OUTPUT_DIR="$CLIENT_DIR"

CLIENT_DIR="$(cd "$CLIENT_DIR" 2>/dev/null && pwd)" || { echo "❌ Directory not found: $CLIENT_DIR"; exit 1; }
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"

# --- Fail early on anything the later steps need -----------------------------
# Finding out about a missing `gh` after the build has run wastes the build.
for cmd in curl jq npm; do
  command -v "$cmd" >/dev/null || { echo "❌ Missing required command: $cmd"; exit 1; }
done
if [ "$SKIP_GITHUB" = false ]; then
  command -v gh >/dev/null || { echo "❌ gh CLI not found — https://cli.github.com (or pass --skip-github)"; exit 1; }
fi
[ -f "$CLIENT_DIR/package.json" ] || { echo "❌ No package.json in $CLIENT_DIR — not a Node project"; exit 1; }
if ! jq -e '.scripts.build' "$CLIENT_DIR/package.json" >/dev/null; then
  echo "❌ package.json has no \"build\" script — this skill deploys Vite/React builds only"; exit 1
fi
if ! ls "$CLIENT_DIR"/vite.config.* >/dev/null 2>&1; then
  echo "⚠ No vite.config.* found — the netlify.toml template assumes Vite output in dist/. Continuing."
fi
if [ -n "$API_URL" ] && ! printf '%s' "$API_URL" | grep -qE '^https?://'; then
  echo "❌ --api-url must start with http:// or https:// (got: $API_URL)"; exit 1
fi

echo ""
echo "═══════════════════════════════════════════════"
echo "  Deploy Netlify — $SLUG"
echo "═══════════════════════════════════════════════"
echo ""

echo "◆ Step 1/3: Preparing client code..."
bash "$SCRIPT_DIR/prepare-client.sh" --client-dir "$CLIENT_DIR" --slug "$SLUG" ${API_URL:+--api-url "$API_URL"}
echo ""

if [ "$SKIP_GITHUB" = true ]; then
  echo "◆ Step 2/3: Skipping GitHub (--skip-github)"
else
  echo "◆ Step 2/3: Pushing to GitHub..."
  bash "$SCRIPT_DIR/push-to-github.sh" --client-dir "$CLIENT_DIR" --slug "$SLUG" \
    ${GH_USER:+--gh-user "$GH_USER"} ${VISIBILITY_FLAG}
fi
echo ""

echo "◆ Step 3/3: Deploying to Netlify..."
bash "$SCRIPT_DIR/netlify-client.sh" --client-dir "$CLIENT_DIR" --slug "$SLUG" \
  ${API_URL:+--api-url "$API_URL"} --output "$OUTPUT_DIR"
echo ""

echo "═══════════════════════════════════════════════"
echo "  ✅ Deploy Netlify Complete!"
echo "═══════════════════════════════════════════════"
echo ""
echo "  Output: $OUTPUT_DIR/netlify-output.json"
echo ""
