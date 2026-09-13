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
if [ -f "netlify.toml" ] && cmp -s netlify.toml "$TEMPLATES_DIR/netlify.toml"; then
  echo "  ✓ netlify.toml already matches the template"
elif [ -f "netlify.toml" ]; then
  # A project-specific netlify.toml (custom publish dir, headers, functions) is
  # the user's config, not ours to replace. Keep it; only make sure the SPA
  # fallback exists, which is the one thing this skill needs.
  echo "  ✓ Keeping existing netlify.toml"
  if ! grep -qE 'to *= *"/index.html"' netlify.toml; then
    printf '\n[[redirects]]\n  from = "/*"\n  to = "/index.html"\n  status = 200\n' >> netlify.toml
    echo "  ✅ Appended SPA redirect to existing netlify.toml"
  fi
else
  cp "$TEMPLATES_DIR/netlify.toml" ./netlify.toml
  echo "  ✅ netlify.toml created"
fi

# --- 2. _redirects ---
echo "  Creating _redirects..."
cp "$TEMPLATES_DIR/_redirects" ./public/_redirects 2>/dev/null || {
  mkdir -p public
  cp "$TEMPLATES_DIR/_redirects" ./public/_redirects
}
echo "  ✅ _redirects created (public/_redirects)"

# --- 3. .env.production (if api-url provided) ---
if [ -n "$API_URL" ]; then
  echo "  Setting VITE_API_URL in .env.production..."
  # Replace only our variable; other VITE_* values the project relies on stay.
  if [ -f .env.production ]; then
    grep -v '^VITE_API_URL=' .env.production > .env.production.tmp || true
    mv .env.production.tmp .env.production
  else
    echo "# Production environment" > .env.production
  fi
  echo "VITE_API_URL=$API_URL" >> .env.production
  echo "  ✅ .env.production updated (VITE_API_URL=$API_URL)"
else
  echo "  ⏭  No --api-url, skipping .env.production (static site only)"
fi

echo "✅ Client preparation complete."
