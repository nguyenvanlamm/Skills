#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID=""
OUTPUT_DIR=""
GOOGLE_CLIENT_ID="${GOOGLE_OAUTH_CLIENT_ID:-}"
GOOGLE_CLIENT_SECRET="${GOOGLE_OAUTH_CLIENT_SECRET:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT_ID="$2"; shift 2 ;;
    --output) OUTPUT_DIR="$2"; shift 2 ;;
    --google-client-id) GOOGLE_CLIENT_ID="$2"; shift 2 ;;
    --google-client-secret) GOOGLE_CLIENT_SECRET="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

[ -n "$PROJECT_ID" ] || { echo "❌ --project required"; exit 1; }
[ -n "$OUTPUT_DIR" ] || { echo "❌ --output required"; exit 1; }
command -v jq >/dev/null || { echo "❌ jq required"; exit 1; }

echo "🔑 Configuring Authentication providers..."

gcloud services enable identitytoolkit.googleapis.com --project "$PROJECT_ID" --quiet
gcloud services enable firebase.googleapis.com --project "$PROJECT_ID" --quiet 2>/dev/null || true
echo "  ✅ Identity Toolkit API enabled"

ACCESS_TOKEN=$(gcloud auth print-access-token 2>/dev/null || true)
if [ -z "$ACCESS_TOKEN" ]; then
  echo "❌ No OAuth2 access token. Run: gcloud auth login"
  exit 1
fi

API="https://identitytoolkit.googleapis.com/v2/projects/$PROJECT_ID"

# Pass the token through the environment, never on the command line or inside
# an interpolated script: argv is world-readable via `ps`, and a token or
# payload containing a quote would break an interpolated heredoc outright.
export ACCESS_TOKEN

call() {  # call <method> <url> [json-body] -> prints "<http_code>\n<body>"
  local method="$1" url="$2" body="${3:-}"
  if [ -n "$body" ]; then
    curl -sS -w '\n%{http_code}' -X "$method" "$url" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json" -d "$body"
  else
    curl -sS -w '\n%{http_code}' -X "$method" "$url" \
      -H "Authorization: Bearer $ACCESS_TOKEN"
  fi
}

split_code() { printf '%s' "${1##*$'\n'}"; }
split_body() { printf '%s' "${1%$'\n'*}"; }

# --- Email/Password -------------------------------------------------------
# Identity Platform config shape: signIn.email.{enabled,passwordRequired}
echo "  Enabling Email/Password..."
RESP=$(call PATCH "$API/config?updateMask=signIn.email.enabled,signIn.email.passwordRequired" \
  '{"signIn":{"email":{"enabled":true,"passwordRequired":true}}}')
CODE=$(split_code "$RESP"); BODY=$(split_body "$RESP")
if [ "$CODE" != "200" ]; then
  echo "❌ Email/Password could not be enabled (HTTP $CODE)"
  echo "   $(printf '%s' "$BODY" | jq -r '.error.message // .' 2>/dev/null | head -3)"
  echo "   Most common cause: Identity Platform is not initialised for this project."
  echo "   Open the Firebase Console → Authentication → Get started once, then re-run."
  exit 1
fi
EMAIL_OK=true
echo "  ✅ Email/Password enabled"

# --- Google sign-in -------------------------------------------------------
# Google is a *federated IdP*, not a config flag: it requires an OAuth 2.0
# client ID and secret, which cannot be minted from this API. Without them the
# provider cannot be enabled — say so instead of issuing a call that 400s.
GOOGLE_OK=false
if [ -n "$GOOGLE_CLIENT_ID" ] && [ -n "$GOOGLE_CLIENT_SECRET" ]; then
  echo "  Enabling Google sign-in..."
  BODY_JSON=$(jq -n --arg id "$GOOGLE_CLIENT_ID" --arg secret "$GOOGLE_CLIENT_SECRET" \
    '{enabled:true, clientId:$id, clientSecret:$secret}')
  RESP=$(call POST "$API/defaultSupportedIdpConfigs?idpId=google.com" "$BODY_JSON")
  CODE=$(split_code "$RESP"); BODY=$(split_body "$RESP")
  if [ "$CODE" = "409" ] || printf '%s' "$BODY" | grep -qi "already exists"; then
    RESP=$(call PATCH "$API/defaultSupportedIdpConfigs/google.com?updateMask=enabled,clientId,clientSecret" "$BODY_JSON")
    CODE=$(split_code "$RESP"); BODY=$(split_body "$RESP")
  fi
  if [ "$CODE" = "200" ]; then
    GOOGLE_OK=true
    echo "  ✅ Google sign-in enabled"
  else
    echo "  ⚠ Google sign-in failed (HTTP $CODE): $(printf '%s' "$BODY" | jq -r '.error.message // .' 2>/dev/null | head -2)"
  fi
else
  cat <<'MSG'
  ⏭  Google sign-in NOT enabled — no OAuth client supplied.

     Google sign-in needs an OAuth 2.0 client ID and secret. Create one at
     Google Cloud Console → APIs & Services → Credentials → OAuth client ID
     (type: Web application), then re-run with:

       --google-client-id <id> --google-client-secret <secret>

     Or enable it in Firebase Console → Authentication → Sign-in method →
     Google, which creates the client for you.
MSG
fi

# --- Record what is actually enabled --------------------------------------
PROVIDERS=$(jq -n --argjson email "$EMAIL_OK" --argjson google "$GOOGLE_OK" \
  '[ (if $email then "email" else empty end), (if $google then "google" else empty end) ]')

OUT="$OUTPUT_DIR/firebase-output.json"
if [ -f "$OUT" ]; then
  TMP=$(mktemp)
  jq --argjson p "$PROVIDERS" '.auth_providers = $p' "$OUT" > "$TMP" && mv "$TMP" "$OUT"
fi

echo "✅ Auth configuration complete — providers: $(printf '%s' "$PROVIDERS" | jq -r 'join(", ")')"
