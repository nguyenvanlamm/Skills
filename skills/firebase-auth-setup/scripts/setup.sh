#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Defaults ---
SLUG=""
OUTPUT_DIR=""
REGION="us-central"

# --- Parse args ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --slug) SLUG="$2"; shift 2 ;;
    --output) OUTPUT_DIR="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --help)
      echo "Usage: $0 --slug <slug> [--output <dir>] [--region <region>]"
      echo ""
      echo "Required:"
      echo "  --slug        Product slug (e.g. task-manager)"
      echo "Optional:"
      echo "  --output      Output directory (default: \$PWD/firebase-output)"
      echo "  --region      GCP region (default: us-central)"
      exit 0
      ;;
    *) echo "Unknown arg: $1. Use --help for usage."; exit 1 ;;
  esac
done

if [ -z "$SLUG" ]; then
  echo "❌ --slug is required. Use --help for usage."
  exit 1
fi
if [ -z "$OUTPUT_DIR" ]; then
  OUTPUT_DIR="$PWD/firebase-output"
fi

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"

echo ""
echo "═══════════════════════════════════════════════"
echo "  Firebase Auth Setup — $SLUG"
echo "═══════════════════════════════════════════════"
echo ""

# --- Step 1: Check Prerequisites ---
echo "◆ Step 1/5: Checking prerequisites..."
bash "$SCRIPT_DIR/check-prereqs.sh"
echo ""

# --- Step 2: Create Firebase Project ---
echo "◆ Step 2/5: Creating Firebase project..."
bash "$SCRIPT_DIR/create-project.sh" \
  --slug "$SLUG" \
  --output "$OUTPUT_DIR" \
  --region "$REGION"
echo ""

PROJECT_ID=""
if [ -f "$OUTPUT_DIR/firebase-output.json" ]; then
  PROJECT_ID=$(jq -r '.project_id // empty' "$OUTPUT_DIR/firebase-output.json")
fi

if [ -z "$PROJECT_ID" ]; then
  echo "❌ Failed to get project_id from Step 2 output."
  exit 1
fi

PROJECT_NUMBER=$(jq -r '.project_number // empty' "$OUTPUT_DIR/firebase-output.json")

# --- Step 3: Enable Auth Providers ---
echo "◆ Step 3/5: Enabling Auth providers..."
bash "$SCRIPT_DIR/enable-auth.sh" \
  --project "$PROJECT_ID" \
  --output "$OUTPUT_DIR"
echo ""

# --- Step 4: Create Web App ---
echo "◆ Step 4/5: Creating web app..."
bash "$SCRIPT_DIR/create-web-app.sh" \
  --project "$PROJECT_ID" \
  --output "$OUTPUT_DIR"
echo ""

# --- Step 5: Create Service Account ---
echo "◆ Step 5/5: Creating service account..."
bash "$SCRIPT_DIR/create-service-account.sh" \
  --project "$PROJECT_ID" \
  --project-number "$PROJECT_NUMBER" \
  --output "$OUTPUT_DIR"
echo ""

echo "═══════════════════════════════════════════════"
echo "  ✅ Firebase Auth Setup Complete!"
echo "═══════════════════════════════════════════════"
echo ""
echo "  Output directory: $OUTPUT_DIR"
echo ""
echo "  Files:"
echo "    firebase-output.json        — Full config (project, web, service account)"
echo "    firebase-web-config.json    — Web app config for React client"
echo "    service-account-key.json    — 🔒 Service account private key (DO NOT COMMIT)"
echo ""
echo "  Next steps:"
echo "    1. Server:"
echo "       - Install firebase-admin: pip install firebase-admin"
echo "       - Set env: FIREBASE_PROJECT_ID=$PROJECT_ID"
echo "       - Set env: GOOGLE_APPLICATION_CREDENTIALS=$OUTPUT_DIR/service-account-key.json"
echo "    2. Client:"
echo "       - Install firebase: npm install firebase"
echo "       - Copy firebase-web-config.json values to .env"
echo ""
echo "  Project:  https://console.firebase.google.com/project/$PROJECT_ID/overview"
echo ""
