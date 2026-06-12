#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "🔍 Checking prerequisites..."

FAILED=0

# firebase-tools
if command -v firebase &>/dev/null; then
  echo "  ✓ firebase-tools: $(firebase --version 2>&1 | head -1)"
else
  echo "  ✗ firebase-tools: not found"
  echo "    → Install: npm install -g firebase-tools"
  FAILED=1
fi

# gcloud
if command -v gcloud &>/dev/null; then
  echo "  ✓ gcloud: $(gcloud --version 2>&1 | head -1)"
else
  echo "  ✗ gcloud: not found"
  echo "    → Install: https://cloud.google.com/sdk/docs/install"
  FAILED=1
fi

# jq
if command -v jq &>/dev/null; then
  echo "  ✓ jq: $(jq --version 2>&1)"
else
  echo "  ✗ jq: not found"
  echo "    → Install: apt install jq / brew install jq"
  FAILED=1
fi

# Firebase CI token
CI_TOKEN_FILE="${FIREBASE_TOKEN_PATH:-$HOME/.config/firebase/ci-token}"
CI_TOKEN=""
if [ -f "$CI_TOKEN_FILE" ]; then
  CI_TOKEN="$(cat "$CI_TOKEN_FILE" | tr -d ' \n\r')"
fi
if [ -n "$CI_TOKEN" ]; then
  echo "  ✓ Firebase CI token: $CI_TOKEN_FILE"
elif [ -n "${FIREBASE_TOKEN:-}" ]; then
  echo "  ✓ Firebase CI token: \$FIREBASE_TOKEN env var"
else
  echo "  ✗ Firebase CI token: not found"
  echo "    → Run: firebase login:ci --no-localhost"
  echo "    → Then save token to: $CI_TOKEN_FILE"
  echo "    → Or set: export FIREBASE_TOKEN=<token>"
  FAILED=1
fi

# gcloud auth
if gcloud auth list --format="value(account)" 2>/dev/null | grep -q .; then
  ACCOUNT=$(gcloud auth list --format="value(account)" --filter=status:ACTIVE 2>/dev/null | head -1)
  echo "  ✓ gcloud active account: $ACCOUNT"
else
  echo "  ✗ gcloud: no active account"
  echo "    → Run: gcloud auth login"
  FAILED=1
fi

echo ""
if [ "$FAILED" -eq 1 ]; then
  echo "❌ Prerequisites check FAILED. Fix errors above and retry."
  exit 1
else
  echo "✅ All prerequisites satisfied."
fi
