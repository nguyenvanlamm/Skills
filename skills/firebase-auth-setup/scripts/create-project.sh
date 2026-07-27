#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Parse args ---
SLUG=""
OUTPUT_DIR=""
REGION="us-central"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --slug) SLUG="$2"; shift 2 ;;
    --output) OUTPUT_DIR="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [ -z "$SLUG" ]; then echo "❌ --slug required"; exit 1; fi
if [ -z "$OUTPUT_DIR" ]; then OUTPUT_DIR="$PWD/firebase-output"; fi

mkdir -p "$OUTPUT_DIR"
echo "📦 Creating Firebase project..."

# Generate a unique project name
RAND_SUFFIX="$(LC_ALL=C tr -dc 'a-z0-9' < /dev/urandom | head -c 4 2>/dev/null || echo "$(date +%s | tail -c 5)")"
PROJECT_NAME="${SLUG}-${RAND_SUFFIX}"
PROJECT_ID="${PROJECT_NAME}"  # project ID = project name for firebase

# GCP project IDs: 6-30 chars, lowercase letter first, then letters/digits/hyphens.
# A slug that violates this fails with an opaque API error, so check it here.
if ! printf '%s' "$PROJECT_ID" | grep -Eq '^[a-z][a-z0-9-]{5,29}$'; then
  echo "❌ Invalid project id derived from --slug: '$PROJECT_ID'"
  echo "   Needs 6-30 chars, start with a lowercase letter, only a-z 0-9 and '-'."
  echo "   Use a shorter, lowercase --slug."
  exit 1
fi

# Check if project already exists
if firebase projects:list --json 2>/dev/null | jq -e --arg id "$PROJECT_ID" '.result[] | select(.projectId == $id)' &>/dev/null; then
  echo "  ⚠ Project '$PROJECT_ID' already exists. Using existing project."
else
  echo "  Creating project: $PROJECT_NAME"
  # firebase projects:create requires a unique project ID
  CREATE_OUTPUT=$(firebase projects:create "$PROJECT_NAME" --display-name "$PROJECT_NAME" --json 2>&1 || true)

  # Check if error is "already taken" — retry with new suffix
  if echo "$CREATE_OUTPUT" | jq -e '.error | select(.message | test("already exists|already taken|PROJECT_INTERNAL_ERROR"))' &>/dev/null 2>&1; then
    echo "  ⚠ Project name taken, retrying with new suffix..."
    RAND_SUFFIX="$(LC_ALL=C tr -dc 'a-z0-9' < /dev/urandom | head -c 4 2>/dev/null || echo "$(date +%s | tail -c 5)")"
    PROJECT_NAME="${SLUG}-${RAND_SUFFIX}"
    PROJECT_ID="$PROJECT_NAME"
    CREATE_OUTPUT=$(firebase projects:create "$PROJECT_NAME" --display-name "$PROJECT_NAME" --json 2>&1)
  fi

  # Retry up to 3 times
  RETRIES=0
  while echo "$CREATE_OUTPUT" | jq -e '.error' &>/dev/null 2>&1; do
    RETRIES=$((RETRIES + 1))
    if [ "$RETRIES" -ge 3 ]; then
      echo "❌ Failed to create project after 3 attempts."
      echo "   Last error: $(echo "$CREATE_OUTPUT" | jq -r '.error.message // "unknown"')"
      exit 1
    fi
    echo "  ⚠ Retry $RETRIES/3..."
    RAND_SUFFIX="$(LC_ALL=C tr -dc 'a-z0-9' < /dev/urandom | head -c 4 2>/dev/null || echo "$(date +%s | tail -c 5)")"
    PROJECT_NAME="${SLUG}-${RAND_SUFFIX}"
    PROJECT_ID="$PROJECT_NAME"
    sleep 2
    CREATE_OUTPUT=$(firebase projects:create "$PROJECT_NAME" --display-name "$PROJECT_NAME" --json 2>&1)
  done

  echo "  ✅ Project created: $PROJECT_ID"
fi

# Get project number
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)" 2>/dev/null || echo "")
echo "  Project number: $PROJECT_NUMBER"

# Write intermediate output
cat > "$OUTPUT_DIR/firebase-output.json" <<EOF
{
  "project_id": "$PROJECT_ID",
  "project_number": "$PROJECT_NUMBER",
  "region": "$REGION",
  "auth_providers": []
}
EOF

echo "✅ Project step complete. Project ID: $PROJECT_ID"
