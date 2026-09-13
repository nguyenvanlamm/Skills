#!/usr/bin/env bash
# Verify a built AAB/APK the way Play will: manifest facts, signing, debuggable,
# 16 KB alignment, size. Emits JSON on stdout, a table on stderr.
#
#   bash verify-artifact.sh --artifact build/app/outputs/bundle/release/app-release.aab [--started-at <epoch>]
#                           [--min-target-sdk 36] [--out build/release/verify.json]
#
# Exit 0 = no BLOCK. Exit 1 = at least one BLOCK. Exit 2 = tooling/usage error.
# Verdict vocabulary: OK · WARN · BLOCK · UNVERIFIED (tool missing — never counted as OK).
#
# Used by flutter-build (Step 6) and flutter-publish (preflight); shared so the two
# never disagree about what "signed" or "aligned" means.
set -uo pipefail

ART=""; STARTED=""; MIN_TARGET=36; OUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --artifact) ART="$2"; shift 2 ;;
    --started-at) STARTED="$2"; shift 2 ;;
    --min-target-sdk) MIN_TARGET="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -n "$ART" ] && [ -f "$ART" ] || { echo "❌ --artifact <file> required and must exist" >&2; exit 2; }
command -v jq >/dev/null || { echo "❌ jq required" >&2; exit 2; }

case "$ART" in *.aab) KIND=aab ;; *.apk) KIND=apk ;; *) echo "❌ artifact must be .aab or .apk" >&2; exit 2 ;; esac

# Portable stat/mtime and readelf (GNU binutils on Linux; llvm-readelf on macOS via brew llvm).
mtime() { stat -c %Y "$1" 2>/dev/null || stat -f %m "$1"; }
fsize() { stat -c %s "$1" 2>/dev/null || stat -f %z "$1"; }
READELF=$(command -v readelf || command -v llvm-readelf || command -v greadelf || true)
BT=""; if command -v bundletool >/dev/null; then BT="bundletool"; elif [ -f "$HOME/bundletool.jar" ]; then BT="java -jar $HOME/bundletool.jar"; fi
APKSIGNER=$(command -v apksigner || ls "${ANDROID_HOME:-$HOME/Android/Sdk}"/build-tools/*/apksigner 2>/dev/null | sort -V | tail -1 || true)

CHECKS="[]"
add() {  # add <id> <verdict> <value> <detail>
  CHECKS=$(jq --arg id "$1" --arg v "$2" --arg val "$3" --arg d "$4" '. + [{id:$id, verdict:$v, value:$val, detail:$d}]' <<<"$CHECKS")
  printf '  %-14s %-10s %-28s %s\n' "$1" "$2" "${3:0:28}" "$4" >&2
}

echo "◆ verify $ART" >&2

# --- freshness ------------------------------------------------------------
if [ -n "$STARTED" ]; then
  M=$(mtime "$ART")
  if [ "$M" -ge "$STARTED" ]; then add freshness OK "mtime>=start" "artifact produced by this build"
  else add freshness BLOCK "stale" "artifact predates the build start — the build did not produce it"; fi
fi

# --- manifest facts -------------------------------------------------------
PKG=""; VCODE=""; VNAME=""; TSDK=""; DEBUGGABLE=""
if [ "$KIND" = aab ]; then
  if [ -n "$BT" ]; then
    MF() { $BT dump manifest --bundle="$ART" --xpath="$1" 2>/dev/null | tr -d '\r\n'; }
    PKG=$(MF "/manifest/@package"); VCODE=$(MF "/manifest/@android:versionCode"); VNAME=$(MF "/manifest/@android:versionName")
    TSDK=$(MF "/manifest/uses-sdk/@android:targetSdkVersion"); DEBUGGABLE=$(MF "/manifest/application/@android:debuggable")
  else
    add manifest UNVERIFIED "no bundletool" "install bundletool (brew install bundletool | ~/bundletool.jar) — AAB manifest is protobuf"
  fi
else
  AAPT=$(command -v aapt2 || ls "${ANDROID_HOME:-$HOME/Android/Sdk}"/build-tools/*/aapt2 2>/dev/null | sort -V | tail -1 || true)
  if [ -n "$AAPT" ]; then
    B=$("$AAPT" dump badging "$ART" 2>/dev/null)
    PKG=$(printf '%s' "$B" | sed -nE "s/.*package: name='([^']+)'.*/\1/p" | head -1)
    VCODE=$(printf '%s' "$B" | sed -nE "s/.*versionCode='([0-9]+)'.*/\1/p" | head -1)
    VNAME=$(printf '%s' "$B" | sed -nE "s/.*versionName='([^']+)'.*/\1/p" | head -1)
    TSDK=$(printf '%s' "$B" | sed -nE "s/.*targetSdkVersion:'([0-9]+)'.*/\1/p" | head -1)
    printf '%s' "$B" | grep -q "application-debuggable" && DEBUGGABLE=true
  else
    add manifest UNVERIFIED "no aapt2" "install build-tools for aapt2"
  fi
fi

if [ -n "$PKG" ]; then
  case "$PKG" in
    com.example.*) add applicationId BLOCK "$PKG" "Play rejects com.example.* permanently" ;;
    com.myapp.*|com.tenapp.*|com.test.*|com.app.*) add applicationId BLOCK "$PKG" "placeholder prefix — permanent once published; use a domain you own" ;;
    *test*|*demo*|*temp*) add applicationId WARN "$PKG" "contains test/demo/temp — permanent once published" ;;
    *) add applicationId OK "$PKG" "" ;;
  esac
fi
if [ -n "$TSDK" ]; then
  TODAY=$(date +%Y%m%d)
  if [ "$TSDK" -ge "$MIN_TARGET" ]; then add targetSdk OK "$TSDK" ""
  elif [ "$TSDK" -eq $((MIN_TARGET-1)) ] && [ "$TODAY" -lt 20260831 ]; then add targetSdk WARN "$TSDK" "API $MIN_TARGET required from 2026-08-31 — bump now"
  else add targetSdk BLOCK "$TSDK" "below the current Play floor ($MIN_TARGET)"; fi
fi
if [ -n "$PKG" ]; then
  if [ -z "$DEBUGGABLE" ] || [ "$DEBUGGABLE" = false ]; then add debuggable OK "false" ""
  else add debuggable BLOCK "true" "android:debuggable=true is a policy violation"; fi
fi
[ -z "$VCODE" ] || { [ "$VCODE" -le 2100000000 ] && add versionCode OK "$VCODE ($VNAME)" "" || add versionCode BLOCK "$VCODE" "exceeds Play max 2,100,000,000"; }

# --- signing --------------------------------------------------------------
if [ "$KIND" = aab ]; then
  if command -v jarsigner >/dev/null; then
    if jarsigner -verify "$ART" 2>/dev/null | grep -q "jar verified"; then
      OWNER=$(keytool -printcert -jarfile "$ART" 2>/dev/null | grep -m1 Owner | sed 's/^Owner: //')
      if printf '%s' "$OWNER" | grep -q "CN=Android Debug"; then add signing BLOCK "debug key" "signed with the debug keystore — run flutter-signing"
      else add signing OK "${OWNER:0:40}" ""; fi
      UNTIL=$(keytool -printcert -jarfile "$ART" 2>/dev/null | grep -m1 -oE 'until: .*' | sed 's/until: //')
      if [ -n "$UNTIL" ]; then
        EXP=$(date -d "$UNTIL" +%s 2>/dev/null || date -j -f "%a %b %d %T %Z %Y" "$UNTIL" +%s 2>/dev/null || echo 0)
        [ "$EXP" -gt 0 ] && [ "$EXP" -lt $(( $(date +%s) + 365*86400 )) ] && add certExpiry WARN "$UNTIL" "certificate expires within a year"
      fi
    else add signing BLOCK "unsigned" "jarsigner: not verified — key.properties missing or storeFile unresolvable"; fi
  else add signing UNVERIFIED "no jarsigner" "install a JDK"; fi
else
  if [ -n "$APKSIGNER" ]; then
    S=$("$APKSIGNER" verify --print-certs "$ART" 2>&1)
    if [ $? -eq 0 ]; then
      printf '%s' "$S" | grep -q "CN=Android Debug" && add signing BLOCK "debug key" "debug-signed" || add signing OK "$(printf '%s' "$S" | grep -m1 -oE 'CN=[^,]+')" ""
    else add signing BLOCK "unsigned" "apksigner verify failed"; fi
  else add signing UNVERIFIED "no apksigner" "jarsigner cannot read v2+ APK signatures; install build-tools"; fi
fi

# --- 16 KB page alignment ------------------------------------------------
if [ -n "$READELF" ]; then
  W=$(mktemp -d); unzip -qo "$ART" -d "$W" 2>/dev/null
  BAD=""; N=0
  while IFS= read -r so; do
    N=$((N+1))
    AL=$("$READELF" -lW "$so" 2>/dev/null | awk '$1=="LOAD"{print $NF}' | sort -u | tail -1)
    case "$AL" in 0x4000|0x8000|0x10000|0x20000|0x40000) ;; "") ;; *) BAD="$BAD ${so#$W/}($AL)";; esac
  done < <(find "$W" -name '*.so' 2>/dev/null)
  rm -rf "$W"
  if [ "$N" -eq 0 ]; then add alignment16k OK "no native libs" ""
  elif [ -z "$BAD" ]; then add alignment16k OK "$N .so aligned" ""
  else add alignment16k BLOCK "misaligned" "$(printf '%s' "$BAD" | head -c 200) — plugin with 4 KB .so; NDK r28+ / upgrade the plugin"; fi
else add alignment16k UNVERIFIED "no readelf" "install binutils (Linux) or llvm (macOS: brew install llvm)"; fi

# --- size -----------------------------------------------------------------
SZ=$(fsize "$ART"); MB=$((SZ/1048576))
if [ "$MB" -gt 500 ]; then add size BLOCK "${MB} MB" "over the 500 MB base module limit"
elif [ "$MB" -gt 200 ]; then add size WARN "${MB} MB" "Play warns users on mobile data above 200 MB"
elif [ "$MB" -gt 60 ]; then add size WARN "${MB} MB" "large for a Flutter app — check uncompressed assets"
else add size OK "${MB} MB" ""; fi

# --- summary ----------------------------------------------------------------
BLOCKS=$(jq '[.[]|select(.verdict=="BLOCK")]|length' <<<"$CHECKS")
WARNS=$(jq '[.[]|select(.verdict=="WARN")]|length' <<<"$CHECKS")
UNV=$(jq '[.[]|select(.verdict=="UNVERIFIED")]|length' <<<"$CHECKS")
OVERALL=$([ "$BLOCKS" -gt 0 ] && echo BLOCK || { [ "$UNV" -gt 0 ] && echo UNVERIFIED || { [ "$WARNS" -gt 0 ] && echo WARN || echo OK; }; })
SHA=$(sha256sum "$ART" 2>/dev/null | cut -d' ' -f1 || shasum -a 256 "$ART" | cut -d' ' -f1)
RESULT=$(jq -n --arg a "$ART" --arg k "$KIND" --arg sha "$SHA" --arg pkg "$PKG" --arg vc "$VCODE" --arg vn "$VNAME" --arg t "$TSDK" \
  --argjson size "$SZ" --arg overall "$OVERALL" --argjson checks "$CHECKS" \
  '{artifact:$a, kind:$k, sha256:$sha, package:$pkg, version_code:($vc|if .=="" then null else tonumber end), version_name:$vn,
    target_sdk:($t|if .=="" then null else tonumber end), size_bytes:$size, overall:$overall, checks:$checks}')
[ -z "$OUT" ] || { mkdir -p "$(dirname "$OUT")"; printf '%s\n' "$RESULT" > "$OUT"; }
printf '%s\n' "$RESULT"
echo "  → $OVERALL ($BLOCKS block, $WARNS warn, $UNV unverified)" >&2
[ "$BLOCKS" -eq 0 ]
