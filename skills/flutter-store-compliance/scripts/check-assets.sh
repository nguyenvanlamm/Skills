#!/usr/bin/env bash
# Mechanical store-listing checks (group 4) + the code↔listing cross-check (step 3).
#
#   bash check-assets.sh [--project .] [--store-dir store-metadata] [--out store-metadata/checks-mechanical.json]
#
# Emits a JSON array of checks {id, group, verdict, summary, evidence, fix} in the
# same shape compliance-report.json uses, so the agent copies rows instead of
# re-deriving them. Verdicts: PASS · WARN · FAIL · SKIP. Exit 0 always (the report
# decides the overall verdict); exit 2 on usage error.
#
# Judgement calls (restricted content, description claims vs features, Data Safety
# answers) are NOT here — they need reading, not measuring.
set -uo pipefail

PROJECT="."; STORE="store-metadata"; OUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --store-dir) STORE="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done
cd "$PROJECT" || exit 2
command -v jq >/dev/null || { echo "❌ jq required" >&2; exit 2; }
if command -v magick >/dev/null; then IDENT="magick identify"; elif command -v identify >/dev/null; then IDENT="identify"; else IDENT=""; fi
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CHECKS="[]"
add() {  # add <id> <group> <verdict> <summary> <evidence> <fix>
  CHECKS=$(jq --arg id "$1" --arg g "$2" --arg v "$3" --arg s "$4" --arg e "$5" --arg f "$6" \
    '. + [{id:$id, group:$g, verdict:$v, summary:$s, evidence:$e, fix:$f}]' <<<"$CHECKS")
  printf '  %-6s %-28s %s\n' "$3" "$1" "$4" >&2
}
dims() { [ -n "$IDENT" ] && $IDENT -format '%wx%h' "$1[0]" 2>/dev/null; }
chans() { [ -n "$IDENT" ] && $IDENT -format '%[channels]' "$1[0]" 2>/dev/null; }
chars() { python3 -c "import sys;print(len(open(sys.argv[1],encoding='utf-8').read().strip()))" "$1" 2>/dev/null || wc -m < "$1" | tr -d ' '; }

LISTING="$STORE/store-listing.json"
echo "◆ mechanical checks — $STORE" >&2

# --- 4. store listing assets ------------------------------------------------
ICON="$STORE/icon/icon-512.png"
if [ ! -f "$ICON" ]; then add listing.icon store-listing FAIL "icon-512.png missing" "$ICON" "flutter-store-metadata Step 2"
elif [ -z "$IDENT" ]; then add listing.icon store-listing WARN "cannot measure (ImageMagick missing)" "$ICON" "install imagemagick"
else D=$(dims "$ICON"); [ "$D" = "512x512" ] && add listing.icon store-listing PASS "512×512" "$ICON" "" || add listing.icon store-listing FAIL "icon is $D, must be 512x512" "$ICON" "regenerate at exactly 512×512"; fi

FG="$STORE/icon/feature-graphic.png"; [ -f "$FG" ] || FG="$STORE/icon/feature-graphic.jpg"
if [ ! -f "$FG" ]; then add listing.feature_graphic store-listing FAIL "feature graphic missing — required for every listing" "$STORE/icon/" "flutter-store-metadata Step 3"
elif [ -z "$IDENT" ]; then add listing.feature_graphic store-listing WARN "cannot measure" "$FG" "install imagemagick"
else
  D=$(dims "$FG"); C=$(chans "$FG")
  if [ "$D" != "1024x500" ]; then add listing.feature_graphic store-listing FAIL "is $D, must be 1024x500" "$FG" "resize to exactly 1024×500"
  elif printf '%s' "$C" | grep -qi 'a$'; then add listing.feature_graphic store-listing FAIL "has an alpha channel ($C) — Play rejects it" "$FG" "magick in.png -alpha remove -alpha off out.png"
  else add listing.feature_graphic store-listing PASS "1024×500, no alpha" "$FG" ""; fi
fi

SHOTS=$(ls "$STORE"/screenshots/phone/*.{png,jpg,jpeg} 2>/dev/null | sort)
N=$(printf '%s\n' "$SHOTS" | grep -c . || true)
if [ "$N" -lt 2 ]; then add listing.screenshots.count store-listing FAIL "$N phone screenshots (need 2–8)" "$STORE/screenshots/phone/" "capture from a running build"
elif [ "$N" -gt 8 ]; then add listing.screenshots.count store-listing FAIL "$N phone screenshots (max 8)" "$STORE/screenshots/phone/" "remove extras"
else add listing.screenshots.count store-listing PASS "$N phone screenshots" "$STORE/screenshots/phone/" ""; fi
if [ -n "$IDENT" ] && [ "$N" -gt 0 ]; then
  BAD=""
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    D=$(dims "$f"); W=${D%x*}; H=${D#*x}; C=$(chans "$f")
    [ "$W" -ge 320 ] && [ "$W" -le 3840 ] && [ "$H" -ge 320 ] && [ "$H" -le 3840 ] || BAD="$BAD $(basename "$f")=$D(size)"
    MAX=$(( W > H ? W : H )); MIN=$(( W > H ? H : W )); [ $((MAX)) -le $((MIN*2)) ] || BAD="$BAD $(basename "$f")=$D(aspect>2:1)"
    printf '%s' "$C" | grep -qi 'a$' && BAD="$BAD $(basename "$f")(alpha)"
  done <<<"$SHOTS"
  [ -z "$BAD" ] && add listing.screenshots.format store-listing PASS "all within 320–3840 px, ≤2:1, no alpha" "" "" \
                || add listing.screenshots.format store-listing FAIL "bad screenshots:$BAD" "$STORE/screenshots/phone/" "resize / strip alpha"
fi

if [ -f "$LISTING" ]; then
  PH=$(jq '[.assets.screenshots[]?[]? | select(.placeholder==true)] | length' "$LISTING" 2>/dev/null || echo 0)
  UN=$(jq '.unresolved | length' "$LISTING" 2>/dev/null || echo 0)
  if [ "$PH" -gt 0 ] || [ "$UN" -gt 0 ]; then add listing.screenshots.authentic store-listing FAIL "$PH placeholder screenshots, $UN unresolved items" "store-listing.json unresolved[]" "capture real screenshots; resolve every unresolved entry"
  else add listing.screenshots.authentic store-listing PASS "no placeholders, unresolved empty" "store-listing.json" ""; fi
  NAME=$(jq -r '.app_name // ""' "$LISTING"); L=$(printf '%s' "$NAME" | python3 -c "import sys;print(len(sys.stdin.read()))" 2>/dev/null || printf '%s' "$NAME" | wc -m)
  [ "$L" -le 30 ] && [ "$L" -gt 0 ] && add listing.app_name store-listing PASS "$L/30 chars" "store-listing.json" "" || add listing.app_name store-listing FAIL "app_name is $L chars (1–30)" "store-listing.json" "shorten"
  DEFAULT=$(jq -r '.default_locale // "en-US"' "$LISTING")
  for loc in $(jq -r '.locales[]? // empty' "$LISTING"); do
    SD="$STORE/description/$loc/short_description.txt"; FD="$STORE/description/$loc/full_description.txt"
    if [ -f "$SD" ]; then n=$(chars "$SD"); [ "$n" -le 80 ] && [ "$n" -gt 0 ] && add "listing.short.$loc" store-listing PASS "$n/80" "$SD" "" || add "listing.short.$loc" store-listing FAIL "short description $n chars (1–80)" "$SD" "shorten"
    else add "listing.short.$loc" store-listing FAIL "missing" "$SD" "write it"; fi
    if [ -f "$FD" ]; then n=$(chars "$FD"); [ "$n" -le 4000 ] && [ "$n" -gt 0 ] && add "listing.full.$loc" store-listing PASS "$n/4000" "$FD" "" || add "listing.full.$loc" store-listing FAIL "full description $n chars (1–4000)" "$FD" "shorten"
    else add "listing.full.$loc" store-listing FAIL "missing" "$FD" "write it"; fi
  done
  CAT=$(jq -r '.category // ""' "$LISTING"); [ -n "$CAT" ] && add listing.category store-listing PASS "$CAT" "store-listing.json" "" || add listing.category store-listing WARN "category not set" "store-listing.json" "choose a Play category"
  PP=$(jq -r '.privacy_policy_url // ""' "$LISTING")
  if printf '%s' "$PP" | grep -qE '^https://'; then
    CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 -L "$PP" 2>/dev/null || echo 000)
    [ "$CODE" = "200" ] && add privacy.url privacy PASS "reachable (200)" "$PP" "" || add privacy.url privacy FAIL "privacy policy URL returned HTTP $CODE" "$PP" "host it publicly; the reviewer must be able to open it"
  else add privacy.url privacy FAIL "no public HTTPS privacy policy URL" "store-listing.json privacy_policy_url" "host store-metadata/privacy-policy/privacy-policy.html and set the URL"; fi
else
  add listing.json store-listing FAIL "store-listing.json missing" "$LISTING" "run flutter-store-metadata"
fi

# --- 3A. privacy policy document --------------------------------------------
PPMD="$STORE/privacy-policy/privacy-policy.md"
if [ -f "$PPMD" ]; then
  U=$(grep -c 'UNRESOLVED' "$PPMD" || true)
  [ "$U" -eq 0 ] && add privacy.document privacy PASS "no UNRESOLVED markers" "$PPMD" "" || add privacy.document privacy FAIL "$U UNRESOLVED markers — incomplete legal document" "$PPMD" "answer each marker; never fill with a default"
else add privacy.document privacy FAIL "privacy-policy.md missing (required for every app)" "$PPMD" "flutter-store-metadata Step 6"; fi

# --- Cross-check: code ↔ store-listing.derived -------------------------------
DERIVE="$HERE/../../flutter-store-metadata/scripts/derive-facts.sh"
[ -f "$DERIVE" ] || DERIVE="$(dirname "$HERE")/../flutter-store-metadata/scripts/derive-facts.sh"
if [ -f "$DERIVE" ]; then
  NOW=$(bash "$DERIVE" --project . 2>/dev/null)
  if [ -f "$LISTING" ] && jq -e '.derived' "$LISTING" >/dev/null 2>&1; then
    DIFF=""
    for k in has_ads has_iap has_login collects_data; do
      # `//` treats false as missing — use an explicit null test so has_ads=false compares correctly.
      a=$(jq -r "if .derived.$k == null then \"?\" else .derived.$k end" "$LISTING"); b=$(jq -r ".$k" <<<"$NOW")
      [ "$a" = "$b" ] || DIFF="$DIFF $k(listing=$a,code=$b)"
    done
    [ -z "$DIFF" ] && add crosscheck.derived privacy PASS "listing.derived matches code" "derive-facts.sh vs store-listing.json" "" \
                   || add crosscheck.derived privacy FAIL "listing contradicts code:$DIFF" "derive-facts.sh vs store-listing.json" "re-run flutter-store-metadata; a listing that contradicts the app is a policy violation"
  fi
  LBL=$(jq -r '.identity.android_label // ""' <<<"$NOW"); LN=$(jq -r '.app_name // ""' "$LISTING" 2>/dev/null)
  if [ -n "$LBL" ] && [ -n "$LN" ]; then [ "$LBL" = "$LN" ] && add crosscheck.label store-listing PASS "app_name == android:label" "\"$LBL\"" "" || add crosscheck.label store-listing WARN "app_name \"$LN\" ≠ android:label \"$LBL\"" "AndroidManifest.xml" "make them match — mismatch reads as misleading metadata"; fi
  R=$(jq -r '[.restricted_permissions[].permission]|join(",")' <<<"$NOW")
  [ -z "$R" ] && add permissions.restricted privacy PASS "no restricted permissions" "manifest" "" || add permissions.restricted privacy FAIL "restricted permissions: $R" "manifest" "remove, or file the Permissions Declaration Form — publish blocked until approved"
  UNK=$(jq -r '[.unknown_sdks[].package]|join(",")' <<<"$NOW")
  [ -z "$UNK" ] && add sdks.unknown sdks PASS "all dependencies classified" "pubspec.yaml" "" || add sdks.unknown sdks WARN "unknown SDKs: $UNK — state what each collects" "pubspec.yaml" "classify each in Data Safety"
  if jq -e '.has_login' <<<"$NOW" >/dev/null; then
    grep -rqE 'delete(Account|User)\(|\.delete\(\)' lib 2>/dev/null && add privacy.deletion_route privacy PASS "account-deletion call found in lib/" "grep lib/" "" \
      || add privacy.deletion_route privacy FAIL "login present but no account-deletion route found in lib/" "grep -r delete lib/" "Play requires in-app + web account deletion for apps with account creation"
  fi
  if jq -e '.has_ads' <<<"$NOW" >/dev/null && [ -f "$LISTING" ]; then
    jq -e '.derived.has_ads==true' "$LISTING" >/dev/null || add sdks.ads_declared sdks FAIL "ad SDK in code but listing says has_ads=false" "pubspec.yaml vs store-listing.json" "declare ads"
  fi
else
  add crosscheck.derived privacy WARN "derive-facts.sh not found (flutter-store-metadata skill not installed beside this one)" "$DERIVE" "install flutter-store-metadata or derive facts manually per references/evidence.md"
fi

# --- 6. functionality evidence --------------------------------------------------
if [ -f build/release/build-info.json ]; then
  T=$(jq -r '.target_sdk // empty' build/release/build-info.json)
  add functionality.build functionality PASS "release build verified (build-info.json, targetSdk ${T:-?})" "build/release/build-info.json" ""
  if [ -n "$T" ]; then
    TODAY=$(date +%Y%m%d)
    if [ "$T" -ge 36 ]; then add privacy.target_api privacy PASS "targetSdk $T" "build-info.json" ""
    elif [ "$T" -eq 35 ] && [ "$TODAY" -lt 20260831 ]; then add privacy.target_api privacy WARN "targetSdk 35 — required 36 from 2026-08-31" "build-info.json" "bump targetSdk"
    else add privacy.target_api privacy FAIL "targetSdk $T below the Play floor" "build-info.json" "set targetSdk 36, rebuild"; fi
  else add privacy.target_api privacy WARN "targetSdk not recorded — could not determine" "build-info.json" "re-run flutter-build v2.1+"; fi
else add functionality.build functionality FAIL "no build/release/build-info.json — nothing verified to submit" "build/release/" "run flutter-build"; fi

[ -z "$OUT" ] || { mkdir -p "$(dirname "$OUT")"; printf '%s\n' "$CHECKS" > "$OUT"; }
printf '%s\n' "$CHECKS"
echo "  → $(jq '[.[]|select(.verdict=="PASS")]|length' <<<"$CHECKS") pass · $(jq '[.[]|select(.verdict=="WARN")]|length' <<<"$CHECKS") warn · $(jq '[.[]|select(.verdict=="FAIL")]|length' <<<"$CHECKS") fail (mechanical only — judgement checks still needed)" >&2
