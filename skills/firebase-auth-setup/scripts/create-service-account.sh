#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Parse args ---
PROJECT_ID=""
PROJECT_NUMBER=""
OUTPUT_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT_ID="$2"; shift 2 ;;
    --project-number) PROJECT_NUMBER="$2"; shift 2 ;;
    --output) OUTPUT_DIR="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [ -z "$PROJECT_ID" ]; then echo "❌ --project required"; exit 1; fi
if [ -z "$OUTPUT_DIR" ]; then echo "❌ --output required"; exit 1; fi

SA_NAME="firebase-adminsdk"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
KEY_FILE="$OUTPUT_DIR/service-account-key.json"

echo "🔑 Setting up service account..."

# Check if service account already exists
if gcloud iam service-accounts describe "$SA_EMAIL" --project "$PROJECT_ID" &>/dev/null 2>&1; then
  echo "  ⚠ Service account '$SA_EMAIL' already exists."
else
  echo "  Creating service account: $SA_EMAIL..."
  gcloud iam service-accounts create "$SA_NAME" \
    --display-name "Firebase Admin SDK Service Account" \
    --project "$PROJECT_ID" --quiet
  echo "  ✅ Service account created"
fi

# Grant Firebase Admin SDK role
echo "  Granting Firebase Admin SDK Administrator role..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/firebase.admin" \
  --quiet 2>/dev/null || true

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --quiet 2>/dev/null || true

echo "  ✅ Roles granted"

# Create/download key
if [ -f "$KEY_FILE" ]; then
  echo "  ⚠ Key file already exists at $KEY_FILE (keeping existing)"
else
  echo "  Creating and downloading key..."
  gcloud iam service-accounts keys create "$KEY_FILE" \
    --iam-account="$SA_EMAIL" \
    --project "$PROJECT_ID" --quiet
  echo "  ✅ Key downloaded to $KEY_FILE"
fi

# Verify key file
if [ -f "$KEY_FILE" ]; then
  KEY_PROJECT_ID=$(jq -r '.project_id // empty' "$KEY_FILE" 2>/dev/null || echo "")
  echo "  Key project_id: $KEY_PROJECT_ID"
fi

KEY_ABS_PATH="$(cd "$(dirname "$KEY_FILE")" && pwd)/$(basename "$KEY_FILE")"

# Merge into main output
if [ -f "$OUTPUT_DIR/firebase-output.json" ]; then
  TMP=$(mktemp)
  jq --arg email "$SA_EMAIL" \
     --arg keyPath "$KEY_ABS_PATH" \
     '.service_account = {
       "email": $email,
       "key_path": $keyPath
     }' "$OUTPUT_DIR/firebase-output.json" > "$TMP" && mv "$TMP" "$OUTPUT_DIR/firebase-output.json"
fi

echo "✅ Service account setup complete."
echo "   Email:   $SA_EMAIL"
echo "   Key:     $KEY_ABS_PATH"
