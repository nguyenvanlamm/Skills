#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SLUG=""
OUTPUT_DIR=""
REGION="us-central"
PROJECT_ID=""
GOOGLE_CLIENT_ID="${GOOGLE_OAUTH_CLIENT_ID:-}"
GOOGLE_CLIENT_SECRET="${GOOGLE_OAUTH_CLIENT_SECRET:-}"

usage() {
  cat <<EOF
Usage: $0 --slug <slug> [options]
   or: $0 --project-id <existing-project> [options]

  --slug                  Base name; project id becomes <slug>-<rand4>
  --project-id            Reuse an existing Firebase/GCP project instead of creating one
                          (avoids the ~10-12 project quota; the project must already have Firebase enabled)
  --output <dir>          Output directory (default: \$PWD/firebase-output)
  --region <region>       Recorded in the output for downstream use (default: us-central)
  --google-client-id      OAuth 2.0 client id → enables Google sign-in
  --google-client-secret  OAuth 2.0 client secret (required with the id)
                          (also read from GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --slug) SLUG="$2"; shift 2 ;;
    --project-id) PROJECT_ID="$2"; shift 2 ;;
    --output) OUTPUT_DIR="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --google-client-id) GOOGLE_CLIENT_ID="$2"; shift 2 ;;
    --google-client-secret) GOOGLE_CLIENT_SECRET="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown arg: $1. Use --help for usage."; exit 1 ;;
  esac
done

if [ -z "$SLUG" ] && [ -z "$PROJECT_ID" ]; then
  echo "❌ --slug or --project-id is required. Use --help for usage."; exit 1
fi
if { [ -n "$GOOGLE_CLIENT_ID" ] && [ -z "$GOOGLE_CLIENT_SECRET" ]; } || { [ -z "$GOOGLE_CLIENT_ID" ] && [ -n "$GOOGLE_CLIENT_SECRET" ]; }; then
  echo "❌ --google-client-id and --google-client-secret must be given together."; exit 1
fi
[ -n "$OUTPUT_DIR" ] || OUTPUT_DIR="$PWD/firebase-output"
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"

echo ""
echo "═══════════════════════════════════════════════"
echo "  Firebase Auth Setup — ${PROJECT_ID:-$SLUG}"
echo "═══════════════════════════════════════════════"
echo ""

echo "◆ Step 1/5: Checking prerequisites..."
bash "$SCRIPT_DIR/check-prereqs.sh"
echo ""

echo "◆ Step 2/5: Firebase project..."
bash "$SCRIPT_DIR/create-project.sh" ${SLUG:+--slug "$SLUG"} ${PROJECT_ID:+--project-id "$PROJECT_ID"} \
  --output "$OUTPUT_DIR" --region "$REGION"
echo ""

PROJECT_ID=$(jq -r '.project_id // empty' "$OUTPUT_DIR/firebase-output.json" 2>/dev/null || true)
[ -n "$PROJECT_ID" ] || { echo "❌ Failed to get project_id from Step 2 output."; exit 1; }
PROJECT_NUMBER=$(jq -r '.project_number // empty' "$OUTPUT_DIR/firebase-output.json")

echo "◆ Step 3/5: Enabling Auth providers..."
bash "$SCRIPT_DIR/enable-auth.sh" --project "$PROJECT_ID" --output "$OUTPUT_DIR" \
  ${GOOGLE_CLIENT_ID:+--google-client-id "$GOOGLE_CLIENT_ID"} \
  ${GOOGLE_CLIENT_SECRET:+--google-client-secret "$GOOGLE_CLIENT_SECRET"}
echo ""

echo "◆ Step 4/5: Creating web app..."
bash "$SCRIPT_DIR/create-web-app.sh" --project "$PROJECT_ID" --output "$OUTPUT_DIR"
echo ""

echo "◆ Step 5/5: Creating service account..."
bash "$SCRIPT_DIR/create-service-account.sh" --project "$PROJECT_ID" \
  ${PROJECT_NUMBER:+--project-number "$PROJECT_NUMBER"} --output "$OUTPUT_DIR"
echo ""

# --- Local hygiene: the output dir holds an admin private key --------------
# Doing this here (not asking the user to) is the difference between "documented"
# and "done".
chmod 600 "$OUTPUT_DIR/service-account-key.json" 2>/dev/null || true
GITIGNORE=""
for d in "$OUTPUT_DIR" "$(dirname "$OUTPUT_DIR")"; do
  if git -C "$d" rev-parse --show-toplevel >/dev/null 2>&1; then GITIGNORE="$(git -C "$d" rev-parse --show-toplevel)/.gitignore"; break; fi
done
if [ -n "$GITIGNORE" ]; then
  REL=$(python3 -c "import os,sys;print(os.path.relpath(sys.argv[1], sys.argv[2]))" "$OUTPUT_DIR" "$(dirname "$GITIGNORE")" 2>/dev/null || basename "$OUTPUT_DIR")
  for pattern in "$REL/service-account-key.json" "$REL/firebase-output.json"; do
    grep -qxF "$pattern" "$GITIGNORE" 2>/dev/null || echo "$pattern" >> "$GITIGNORE"
  done
  echo "  ✅ Added key + output paths to $GITIGNORE"
else
  echo "  ⚠ Output dir is not inside a git repo — remember to gitignore service-account-key.json wherever it ends up"
fi

PROVIDERS=$(jq -r '.auth_providers | join(", ")' "$OUTPUT_DIR/firebase-output.json" 2>/dev/null || echo "?")

echo ""
echo "═══════════════════════════════════════════════"
echo "  ✅ Firebase Auth Setup Complete!"
echo "═══════════════════════════════════════════════"
echo ""
echo "  Project:    $PROJECT_ID"
echo "  Providers:  $PROVIDERS"
echo "  Output:     $OUTPUT_DIR"
echo ""
echo "  Files:"
echo "    firebase-output.json        — Full config (project, web app, service account, providers)"
echo "    firebase-web-config.json    — Web app config for the client"
echo "    service-account-key.json    — 🔒 admin private key, chmod 600, DO NOT COMMIT"
echo ""
echo "  Next steps:"
echo "    Server: pip install firebase-admin"
echo "            FIREBASE_PROJECT_ID=$PROJECT_ID"
echo "            GOOGLE_APPLICATION_CREDENTIALS=$OUTPUT_DIR/service-account-key.json"
echo "    Client: npm install firebase; copy firebase-web-config.json values to .env"
echo "            Read auth_providers before rendering a Google button — it is only there if you passed an OAuth client."
echo ""
echo "  Console:  https://console.firebase.google.com/project/$PROJECT_ID/authentication/providers"
echo ""
