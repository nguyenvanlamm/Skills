#!/usr/bin/env bash
# Derive what a Flutter app actually does from its code — never from user input.
#
#   bash derive-facts.sh [--project .] [--out store-metadata/derived.json]
#
# Emits the `derived` block used by store-listing.json (flutter-store-metadata) and
# re-derived by flutter-store-compliance for its cross-check. Every fact carries the
# evidence line that produced it. Unknown packages are listed, not classified.
# Exit 0 always (facts are facts); exit 2 when the project is not a Flutter project.
set -uo pipefail

PROJECT="."; OUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done
cd "$PROJECT" || exit 2
[ -f pubspec.yaml ] || { echo "❌ no pubspec.yaml in $PWD" >&2; exit 2; }
command -v jq >/dev/null || { echo "❌ jq required" >&2; exit 2; }

# --- dependencies (direct, non-dev) -----------------------------------------
# Lines between `dependencies:` and the next top-level key, indented exactly two spaces.
DEPS=$(awk '
  /^dependencies:/ {on=1; next}
  /^[A-Za-z_]/ {on=0}
  on && /^  [A-Za-z0-9_]+:/ { sub(/^  /,""); sub(/:.*/,""); print }
' pubspec.yaml | grep -vE '^(flutter|flutter_localizations|cupertino_icons)$')

has_dep() { printf '%s\n' "$DEPS" | grep -qx "$1"; }
dep_line() { grep -nE "^  $1:" pubspec.yaml | head -1 | sed 's/^\([0-9]*\):/pubspec.yaml:\1 /'; }

classify() {  # classify <fact> <pkg...> → sets FACT_<fact>=true and appends evidence
  local fact="$1"; shift
  for p in "$@"; do
    if has_dep "$p"; then
      eval "FACT_$fact=true"
      EVID=$(jq --arg f "$fact" --arg e "$(dep_line "$p")" '.[$f] += [$e]' <<<"$EVID")
    fi
  done
}

EVID='{}'
FACT_has_ads=false; FACT_has_iap=false; FACT_has_login=false; FACT_collects_data=false
FACT_crash_reporting=false; FACT_push=false; FACT_location=false; FACT_camera=false; FACT_contacts=false; FACT_network=false
classify has_ads google_mobile_ads applovin_max unity_ads facebook_audience_network ironsource_mediation
classify has_iap in_app_purchase purchases_flutter flutter_inapp_purchase
classify has_login firebase_auth google_sign_in sign_in_with_apple supabase_flutter amplify_auth_cognito
classify collects_data firebase_analytics amplitude_flutter mixpanel_flutter posthog_flutter segment_analytics
classify crash_reporting firebase_crashlytics sentry_flutter bugsnag_flutter
classify push firebase_messaging onesignal_flutter
classify location geolocator location
classify camera image_picker camera
classify contacts contacts_service flutter_contacts
classify network http dio web_socket_channel graphql_flutter chopper retrofit

# Crash reporting and analytics both count as data collection for Data Safety.
[ "$FACT_crash_reporting" = true ] && FACT_collects_data=true

# --- permissions (all manifests under android/app/src — plugins merge theirs at build) ---
PERMS=$(grep -rhoE 'android:name="android\.permission\.[A-Z_]+"' android/app/src 2>/dev/null \
        | sed -E 's/.*android\.permission\.([A-Z_]+).*/\1/' | sort -u)
PERM_FILE() { grep -rlE "android\.permission\.$1\"" android/app/src 2>/dev/null | head -1; }
RESTRICTED="SEND_SMS RECEIVE_SMS READ_SMS READ_CALL_LOG WRITE_CALL_LOG PROCESS_OUTGOING_CALLS"
SENSITIVE="ACCESS_FINE_LOCATION ACCESS_COARSE_LOCATION ACCESS_BACKGROUND_LOCATION CAMERA RECORD_AUDIO READ_CONTACTS WRITE_CONTACTS MANAGE_EXTERNAL_STORAGE QUERY_ALL_PACKAGES READ_MEDIA_IMAGES READ_MEDIA_VIDEO READ_MEDIA_AUDIO BODY_SENSORS ACTIVITY_RECOGNITION"
R_LIST="[]"; S_LIST="[]"; N_LIST="[]"
for p in $PERMS; do
  src=$(PERM_FILE "$p")
  if printf ' %s ' "$RESTRICTED" | grep -q " $p "; then R_LIST=$(jq --arg p "$p" --arg s "$src" '. + [{permission:$p, evidence:$s}]' <<<"$R_LIST")
  elif printf ' %s ' "$SENSITIVE" | grep -q " $p "; then S_LIST=$(jq --arg p "$p" --arg s "$src" '. + [{permission:$p, evidence:$s}]' <<<"$S_LIST")
  else N_LIST=$(jq --arg p "$p" '. + [$p]' <<<"$N_LIST"); fi
done
printf '%s\n' "$PERMS" | grep -qx INTERNET && FACT_network=true
printf '%s\n' "$PERMS" | grep -qE '^ACCESS_(FINE|COARSE|BACKGROUND)_LOCATION$' && FACT_location=true
printf '%s\n' "$PERMS" | grep -qx CAMERA && FACT_camera=true
printf '%s\n' "$PERMS" | grep -qx READ_CONTACTS && FACT_contacts=true

# --- identity ---------------------------------------------------------------
LABEL=$(grep -hoE 'android:label="[^"]*"' android/app/src/main/AndroidManifest.xml 2>/dev/null | head -1 | sed 's/android:label="//; s/"$//')
APPID=$(grep -hoE 'applicationId[[:space:]=]+"[^"]+"' android/app/build.gradle* 2>/dev/null | head -1 | grep -oE '"[^"]+"' | tr -d '"')
VERSION=$(sed -nE 's/^version:[[:space:]]*(.*)$/\1/p' pubspec.yaml | head -1)
NAME=$(sed -nE 's/^name:[[:space:]]*([A-Za-z0-9_]+).*/\1/p' pubspec.yaml | head -1)

# --- unknown SDKs: anything not in the known-benign or classified lists -------
KNOWN_BENIGN="provider flutter_riverpod riverpod bloc flutter_bloc get_it go_router auto_route intl shared_preferences path_provider path sqflite hive hive_flutter isar drift equatable freezed_annotation json_annotation collection uuid url_launcher share_plus package_info_plus device_info_plus connectivity_plus permission_handler flutter_svg cached_network_image shimmer lottie rive flutter_animate google_fonts flutter_launcher_icons flutter_native_splash flutter_secure_storage local_auth flutter_local_notifications webview_flutter video_player audioplayers just_audio file_picker image_cropper photo_view fl_chart syncfusion_flutter_charts table_calendar flutter_slidable pull_to_refresh infinite_scroll_pagination flutter_dotenv logger dartz rxdart async meta characters vector_math crypto convert archive"
CLASSIFIED="google_mobile_ads applovin_max unity_ads facebook_audience_network ironsource_mediation in_app_purchase purchases_flutter flutter_inapp_purchase firebase_auth google_sign_in sign_in_with_apple supabase_flutter amplify_auth_cognito firebase_analytics amplitude_flutter mixpanel_flutter posthog_flutter segment_analytics firebase_crashlytics sentry_flutter bugsnag_flutter firebase_messaging onesignal_flutter geolocator location image_picker camera contacts_service flutter_contacts http dio web_socket_channel graphql_flutter chopper retrofit firebase_core cloud_firestore firebase_storage firebase_remote_config firebase_performance"
UNKNOWN="[]"
for d in $DEPS; do
  printf ' %s ' "$KNOWN_BENIGN $CLASSIFIED" | grep -q " $d " || UNKNOWN=$(jq --arg d "$d" --arg e "$(dep_line "$d")" '. + [{package:$d, evidence:$e}]' <<<"$UNKNOWN")
done

# --- local-only? ---------------------------------------------------------------
LOCAL_ONLY=false
if [ "$FACT_network" = false ] && [ "$FACT_collects_data" = false ] && [ "$FACT_has_login" = false ] && [ "$FACT_has_ads" = false ]; then LOCAL_ONLY=true; fi

RESULT=$(jq -n \
  --arg name "$NAME" --arg label "$LABEL" --arg appid "$APPID" --arg version "$VERSION" \
  --argjson has_ads $FACT_has_ads --argjson has_iap $FACT_has_iap --argjson has_login $FACT_has_login \
  --argjson collects_data $FACT_collects_data --argjson crash $FACT_crash_reporting --argjson push $FACT_push \
  --argjson location $FACT_location --argjson camera $FACT_camera --argjson contacts $FACT_contacts \
  --argjson network $FACT_network --argjson local_only $LOCAL_ONLY \
  --argjson restricted "$R_LIST" --argjson sensitive "$S_LIST" --argjson normal "$N_LIST" \
  --argjson unknown "$UNKNOWN" --argjson evidence "$EVID" \
  --arg deps "$(printf '%s' "$DEPS" | tr '\n' ' ')" \
  '{
     identity: {pubspec_name:$name, android_label:$label, application_id:$appid, version:$version},
     has_ads:$has_ads, has_iap:$has_iap, has_login:$has_login, collects_data:$collects_data,
     crash_reporting:$crash, push_notifications:$push, uses_location:$location, uses_camera:$camera,
     uses_contacts:$contacts, network_access:$network, local_only:$local_only,
     restricted_permissions:$restricted, sensitive_permissions:$sensitive, normal_permissions:$normal,
     unknown_sdks:$unknown, dependencies:($deps|split(" ")|map(select(.!=""))), evidence:$evidence,
     derived_at: (now|todate)
   }')
[ -z "$OUT" ] || { mkdir -p "$(dirname "$OUT")"; printf '%s\n' "$RESULT" > "$OUT"; }
printf '%s\n' "$RESULT"
{
  echo "◆ derived facts — $APPID ($LABEL) v$VERSION"
  echo "  ads=$FACT_has_ads iap=$FACT_has_iap login=$FACT_has_login collects_data=$FACT_collects_data crash=$FACT_crash_reporting push=$FACT_push network=$FACT_network local_only=$LOCAL_ONLY"
  echo "  restricted perms: $(jq -r 'map(.permission)|join(",")' <<<"$R_LIST")  sensitive: $(jq -r 'map(.permission)|join(",")' <<<"$S_LIST")"
  echo "  unknown SDKs: $(jq -r 'map(.package)|join(",")' <<<"$UNKNOWN")"
} >&2
