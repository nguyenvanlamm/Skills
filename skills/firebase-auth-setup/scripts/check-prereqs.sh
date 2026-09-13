#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Checking prerequisites..."
FAILED=0

need() {  # need <cmd> <version-cmd> <install-hint>
  if command -v "$1" &>/dev/null; then
    echo "  ✓ $1: $(eval "$2" 2>&1 | head -1)"
  else
    echo "  ✗ $1: not found"; echo "    → $3"; FAILED=1
  fi
}

need firebase "firebase --version" "npm install -g firebase-tools"
need gcloud   "gcloud --version"   "https://cloud.google.com/sdk/docs/install"
need jq       "jq --version"       "apt install jq / brew install jq"
need curl     "curl --version"     "apt install curl / brew install curl"

# Ambient auth is all the scripts use: firebase-tools for project/app creation,
# gcloud for the Identity Toolkit REST calls and IAM. A `firebase login:ci`
# token is NOT required — an older version demanded one and never used it.
if command -v gcloud &>/dev/null; then
  ACCOUNT=$(gcloud auth list --format="value(account)" --filter=status:ACTIVE 2>/dev/null | head -1 || true)
  if [ -n "$ACCOUNT" ]; then
    echo "  ✓ gcloud active account: $ACCOUNT"
  else
    echo "  ✗ gcloud: no active account"; echo "    → gcloud auth login"; FAILED=1
  fi
fi

if command -v firebase &>/dev/null; then
  # `firebase login:list` prints the logged-in accounts; empty or error means not logged in.
  if firebase login:list 2>/dev/null | grep -qE '@'; then
    echo "  ✓ firebase-tools: logged in"
  elif [ -n "${FIREBASE_TOKEN:-}" ]; then
    echo "  ✓ firebase-tools: using \$FIREBASE_TOKEN (CI mode)"
  else
    echo "  ✗ firebase-tools: not logged in"; echo "    → firebase login   (or export FIREBASE_TOKEN for CI)"; FAILED=1
  fi
fi

echo ""
if [ "$FAILED" -eq 1 ]; then
  echo "❌ Prerequisites check FAILED. Fix the items above and retry."
  exit 1
fi
echo "✅ All prerequisites satisfied."
