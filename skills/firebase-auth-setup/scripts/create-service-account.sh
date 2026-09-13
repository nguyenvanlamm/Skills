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

# Roles — least privilege for what this skill sets up (Authentication only):
#   roles/firebaseauth.admin           manage users, verify/revoke tokens
#   roles/iam.serviceAccountTokenCreator  mint custom tokens
# roles/firebase.admin (the old grant) also covers Firestore, Storage, Hosting…
# which this skill explicitly does not configure. If the backend later needs
# Firestore, add roles/datastore.user then — do not pre-grant everything.
echo "  Granting Firebase Authentication Admin + Token Creator..."
for role in roles/firebaseauth.admin roles/iam.serviceAccountTokenCreator; do
  if gcloud projects add-iam-policy-binding "$PROJECT_ID" \
       --member="serviceAccount:${SA_EMAIL}" --role="$role" --quiet >/dev/null 2>&1; then
    echo "  ✅ $role"
  else
    echo "  ⚠ Could not grant $role — the active account may lack resourcemanager.projects.setIamPolicy"
  fi
done

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
chmod 600 "$KEY_FILE" 2>/dev/null || true

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
