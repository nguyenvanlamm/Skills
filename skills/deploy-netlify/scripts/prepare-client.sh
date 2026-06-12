#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="$(cd "$SCRIPT_DIR/../templates" && pwd)"

CLIENT_DIR=""
SLUG=""
API_URL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --client-dir) CLIENT_DIR="$2"; shift 2 ;;
    --slug) SLUG="$2"; shift 2 ;;
    --api-url) API_URL="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [ -z "$CLIENT_DIR" ]; then echo "❌ --client-dir required"; exit 1; fi
if [ -z "$SLUG" ]; then echo "❌ --slug required"; exit 1; fi

echo "◆ Preparing client code in $CLIENT_DIR..."
cd "$CLIENT_DIR"

# --- 1. netlify.toml ---
echo "  Creating netlify.toml..."
if [ -f "netlify.toml" ]; then
  echo "  ⚠ netlify.toml already exists, backing up..."
  cp netlify.toml netlify.toml.bak
fi
cp "$TEMPLATES_DIR/netlify.toml" ./netlify.toml
echo "  ✅ netlify.toml created"

# --- 2. _redirects ---
echo "  Creating _redirects..."
cp "$TEMPLATES_DIR/_redirects" ./public/_redirects 2>/dev/null || {
  mkdir -p public
  cp "$TEMPLATES_DIR/_redirects" ./public/_redirects
}
echo "  ✅ _redirects created (public/_redirects)"

# --- 3. .env.production (if api-url provided) ---
if [ -n "$API_URL" ]; then
  echo "  Creating .env.production with VITE_API_URL..."
  cat > .env.production <<EOF
# Production environment
VITE_API_URL=$API_URL
EOF
  echo "  ✅ .env.production created (VITE_API_URL=$API_URL)"
else
  echo "  ⏭  No --api-url, skipping .env.production (static site only)"
fi

echo "✅ Client preparation complete."
