#!/usr/bin/env bash
# Preflight gates for a Play upload. Emits one JSON table; exit 1 on any BLOCK.
#
#   bash preflight.sh [--project .] [--aab <path>] [--out store-metadata/preflight.json]
#
# Gates (references/preflight.md): provenance (Gate 0), compliance verdict (1),
# artifact checks via flutter-build/scripts/verify-artifact.sh (2,3,4,6,7,8),
# version code vs publish-state (5), committed credentials (9), store assets (10).
# Verdicts: OK · WARN · BLOCK · UNVERIFIED (tool missing — never OK).
set -uo pipefail

PROJECT="."; AAB=""; OUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --aab) AAB="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done
cd "$PROJECT" || exit 2
command -v jq >/dev/null || { echo "❌ jq required" >&2; exit 2; }
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GATES="[]"
add() { GATES=$(jq --arg g "$1" --arg v "$2" --arg val "$3" --arg d "$4" '. + [{gate:$g, verdict:$v, value:$val, detail:$d}]' <<<"$GATES"); printf '  %-16s %-10s %-24s %s\n' "$1" "$2" "${3:0:24}" "$4" >&2; }

# --- artifact selection: never silently take the first --------------------
if [ -z "$AAB" ]; then
  CANDS=$(find build/release build/app/outputs -name '*.aab' -type f 2>/dev/null | sort -u)
  N=$(printf '%s\n' "$CANDS" | grep -c . || true)
  if [ "$N" -eq 0 ]; then echo "❌ no .aab found under build/ — run flutter-build" >&2; exit 2
  elif [ "$N" -gt 1 ] && [ -f build/release/app-release.aab ]; then AAB=build/release/app-release.aab; echo "  multiple AABs; using build/release/app-release.aab (flutter-build's copy). Pass --aab to override." >&2
  elif [ "$N" -gt 1 ]; then echo "❌ multiple AABs found — pass --aab:" >&2; printf '%s\n' "$CANDS" | while read -r f; do echo "   $(du -h "$f" | cut -f1)  $(date -r "$f" +%F' '%T 2>/dev/null)  $f" >&2; done; exit 2
  else AAB="$CANDS"; fi
fi
[ -f "$AAB" ] || { echo "❌ $AAB not found" >&2; exit 2; }
echo "◆ preflight $AAB" >&2

# --- Gate 0: provenance ------------------------------------------------------
SHA=$(sha256sum "$AAB" 2>/dev/null | cut -d' ' -f1 || shasum -a 256 "$AAB" | cut -d' ' -f1)
if [ -f build/release/build-info.json ]; then
  BSHA=$(jq -r '.sha256 // ""' build/release/build-info.json); DIRTY=$(jq -r '.git.dirty // false' build/release/build-info.json)
  if [ "$BSHA" = "$SHA" ]; then add provenance OK "matches build-info" "$(jq -r '.git.sha // "?"' build/release/build-info.json | cut -c1-12) on $(jq -r '.git.branch // "?"' build/release/build-info.json)"
  else add provenance WARN "sha mismatch" "this AAB is not the one build-info.json describes — every gate below runs from scratch"; fi
  [ "$DIRTY" = true ] && add provenance.dirty WARN "dirty tree" "built from uncommitted work; not reproducible from any commit"
else add provenance WARN "no build-info.json" "provenance unknown (flutter-build v1 or manual build)"; fi

# --- Gate 1: compliance verdict -----------------------------------------------
if [ -f store-metadata/compliance-report.json ]; then
  OV=$(jq -r '.overall // "?"' store-metadata/compliance-report.json)
  FAILS=$(jq -r '[.checks[]|select(.verdict=="FAIL")|.id]|join(", ")' store-metadata/compliance-report.json)
  case "$OV" in
    PASS) add compliance OK PASS "" ;;
    WARN) add compliance WARN WARN "$(jq -r '[.checks[]|select(.verdict=="WARN")|.id]|join(", ")' store-metadata/compliance-report.json)" ;;
    FAIL) add compliance BLOCK FAIL "$FAILS" ;;
    *) add compliance WARN "$OV" "unrecognised overall verdict" ;;
  esac
elif [ -f store-metadata/compliance-report.md ]; then
  L=$(grep -m1 -E 'OVERALL:|COMPLIANCE —' store-metadata/compliance-report.md || true)
  if printf '%s' "$L" | grep -q FAIL; then add compliance BLOCK "FAIL (v1 md)" "re-run flutter-store-compliance for a gateable JSON verdict"
  elif printf '%s' "$L" | grep -qE 'WITH ISSUES|PARTIAL|WARN'; then add compliance WARN "WARN (v1 md)" "re-run for JSON"
  elif printf '%s' "$L" | grep -q PASS; then add compliance OK "PASS (v1 md)" "re-run for JSON"
  else add compliance WARN "unparseable" "re-run flutter-store-compliance"; fi
else add compliance WARN "not run" "the audit never ran — publishing unaudited is the user's call"; fi

# --- Gates 2,3,4,6,7,8: the artifact itself ------------------------------------
VERIFY="$HERE/../../flutter-build/scripts/verify-artifact.sh"
if [ -f "$VERIFY" ]; then
  V=$(bash "$VERIFY" --artifact "$AAB" 2>/dev/null)
  PKG=$(jq -r '.package // ""' <<<"$V"); VCODE=$(jq -r '.version_code // empty' <<<"$V")
  while IFS=$'\t' read -r id verdict val det; do add "artifact.$id" "$verdict" "$val" "$det"; done < <(jq -r '.checks[] | select(.id!="freshness") | [.id,.verdict,.value,.detail] | @tsv' <<<"$V")
else
  add artifact UNVERIFIED "no verify-artifact.sh" "install flutter-build beside this skill, or run its Step 6 commands by hand"
  PKG=""; VCODE=""
fi

# --- Gate 5: version code vs publish-state ------------------------------------
STATE=store-metadata/publish-state.json
if [ -f "$STATE" ]; then
  LAST=$(jq -r '.last_uploaded.version_code // empty' "$STATE"); SID=$(jq -r '.app_id // ""' "$STATE"); PEND=$(jq -r '.pending_upload.version_code // empty' "$STATE")
  if [ -n "$PKG" ] && [ -n "$SID" ] && [ "$PKG" != "$SID" ]; then add app_id.state BLOCK "$PKG ≠ $SID" "applicationId differs from publish-state — a different app on Play, not an update"; fi
  if [ -n "$VCODE" ] && [ -n "$LAST" ]; then
    [ "$VCODE" -gt "$LAST" ] && add version_code OK "$VCODE > $LAST" "" || add version_code BLOCK "$VCODE ≤ $LAST" "Play refuses a reused/lower version code — bump pubspec build number and rebuild"
  elif [ -n "$VCODE" ]; then add version_code WARN "$VCODE (no baseline)" "state has no last_uploaded — confirm the app is really new"; fi
  [ -n "$PEND" ] && [ "$PEND" = "$VCODE" ] && add version_code.pending WARN "pending $PEND" "a previous run prepared this code and the upload was never confirmed — ask whether it landed"
else add version_code WARN "${VCODE:-?} (no state file)" "missing state is not proof of a first release — ask whether the app exists on Play"; fi

# --- Gate 9: committed credentials ---------------------------------------------
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  TRACKED=$(git ls-files | grep -E 'service-account.*\.json$|\.jks$|\.keystore$|(^|/)key\.properties$' || true)
  HIST=$(git log --all --oneline -- '*service-account*.json' '*.jks' '*.keystore' 'android/key.properties' 2>/dev/null | head -3 || true)
  if [ -n "$TRACKED" ]; then add credentials BLOCK "tracked" "$(printf '%s' "$TRACKED" | tr '\n' ' ') — remove from index, gitignore, ROTATE the key"
  elif [ -n "$HIST" ]; then add credentials BLOCK "in history" "credential files appear in git history — rotate; history rewrite is the user's call"
  else add credentials OK "none tracked" ""; fi
else add credentials WARN "not a git repo" "cannot check for committed credentials"; fi

# --- Gate 10: store assets -------------------------------------------------------
MISSING=""
[ -f store-metadata/icon/icon-512.png ] || MISSING="$MISSING icon-512.png"
ls store-metadata/icon/feature-graphic.* >/dev/null 2>&1 || MISSING="$MISSING feature-graphic"
NS=$(ls store-metadata/screenshots/phone/* 2>/dev/null | wc -l | tr -d ' '); [ "$NS" -ge 2 ] || MISSING="$MISSING screenshots(${NS}/2)"
DL=$(jq -r '.default_locale // "en-US"' store-metadata/store-listing.json 2>/dev/null || echo en-US)
[ -f "store-metadata/description/$DL/short_description.txt" ] || MISSING="$MISSING short_description($DL)"
[ -f "store-metadata/description/$DL/full_description.txt" ]  || MISSING="$MISSING full_description($DL)"
ls store-metadata/privacy-policy/privacy-policy.* >/dev/null 2>&1 || MISSING="$MISSING privacy-policy"
UNRES=$(jq '.unresolved|length' store-metadata/store-listing.json 2>/dev/null || echo 0)
[ "$UNRES" -eq 0 ] || MISSING="$MISSING unresolved($UNRES)"
[ -z "$MISSING" ] && add store_assets OK "complete" "" || add store_assets WARN "missing:$MISSING" "Play blocks submission (not upload) on these"

# --- summary ------------------------------------------------------------------------
B=$(jq '[.[]|select(.verdict=="BLOCK")]|length' <<<"$GATES"); W=$(jq '[.[]|select(.verdict=="WARN")]|length' <<<"$GATES"); U=$(jq '[.[]|select(.verdict=="UNVERIFIED")]|length' <<<"$GATES")
OVERALL=$([ "$B" -gt 0 ] && echo BLOCK || { [ "$U" -gt 0 ] && echo UNVERIFIED || { [ "$W" -gt 0 ] && echo WARN || echo OK; }; })
RESULT=$(jq -n --arg aab "$AAB" --arg sha "$SHA" --arg pkg "$PKG" --arg vc "$VCODE" --arg overall "$OVERALL" --argjson gates "$GATES" \
  '{aab:$aab, sha256:$sha, package:$pkg, version_code:($vc|if .=="" then null else tonumber end), overall:$overall, gates:$gates, checked_at:(now|todate)}')
[ -z "$OUT" ] || { mkdir -p "$(dirname "$OUT")"; printf '%s\n' "$RESULT" > "$OUT"; }
printf '%s\n' "$RESULT"
echo "  → $OVERALL ($B block · $W warn · $U unverified)" >&2
[ "$B" -eq 0 ]
