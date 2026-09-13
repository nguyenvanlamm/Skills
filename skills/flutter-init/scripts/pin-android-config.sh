#!/usr/bin/env bash
# Pin compileSdk / targetSdk / minSdk / ndkVersion explicitly in android/app/build.gradle(.kts).
#
#   bash pin-android-config.sh [--project .] [--compile-sdk 36] [--target-sdk 36] [--min-sdk 23] [--ndk <version>]
#
# `flutter create` leaves these as `flutter.compileSdkVersion` etc., which silently
# follow the Flutter SDK. flutter-build then reports "cannot verify" and
# flutter-store-compliance cannot audit them. This script replaces those
# indirections with literals — in either Groovy or Kotlin DSL — and refuses to
# guess when the file does not look like a Flutter template.
#
# --ndk defaults to the newest r28+ NDK installed under $ANDROID_HOME/ndk; if none,
# the ndkVersion line is left alone and a warning is printed.
set -euo pipefail

PROJECT="."; COMPILE=36; TARGET=36; MIN=23; NDK=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --compile-sdk) COMPILE="$2"; shift 2 ;;
    --target-sdk) TARGET="$2"; shift 2 ;;
    --min-sdk) MIN="$2"; shift 2 ;;
    --ndk) NDK="$2"; shift 2 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done
cd "$PROJECT"
[ -f pubspec.yaml ] || { echo "❌ Not a Flutter project"; exit 1; }

if [ -f android/app/build.gradle.kts ]; then FILE=android/app/build.gradle.kts; KTS=true
elif [ -f android/app/build.gradle ]; then FILE=android/app/build.gradle; KTS=false
else echo "❌ No android/app/build.gradle(.kts)"; exit 1; fi

if [ -z "$NDK" ]; then
  SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Android/Sdk}}"
  NDK=$(ls "$SDK/ndk" 2>/dev/null | awk -F. '$1>=28' | sort -V | tail -1 || true)
fi

cp "$FILE" "$FILE.bak"
# One sed expression per property. Anchored on the Flutter template shapes:
#   Groovy: compileSdk flutter.compileSdkVersion | compileSdk = flutter.compileSdkVersion | compileSdkVersion 34
#   Kotlin: compileSdk = flutter.compileSdkVersion | compileSdk = 34
pin() {  # pin <key> <value> [quoted]
  local key="$1" val="$2" q="${3:-}"
  local repl; if [ "$KTS" = true ]; then repl="\\1$key = $q$val$q"; else repl="\\1$key = $q$val$q"; fi
  # Groovy accepts both `key value` and `key = value`; the `=` form works in both DSLs.
  sed -E -i.tmp "s/^([[:space:]]*)${key}(Version)?[[:space:]]*=?[[:space:]]*[^\n]*$/$repl/" "$FILE"
  rm -f "$FILE.tmp"
}
pin compileSdk "$COMPILE"
pin targetSdk "$TARGET"
pin minSdk "$MIN"
if [ -n "$NDK" ]; then pin ndkVersion "$NDK" '"'; else echo "  ⚠ no NDK r28+ found under \$ANDROID_HOME/ndk — ndkVersion left unchanged"; fi

echo "◆ $FILE — pinned values now:"
grep -nE '^\s*(compileSdk|targetSdk|minSdk|ndkVersion)\b' "$FILE" | sed 's/^/  /'

for k in compileSdk targetSdk minSdk; do
  grep -qE "^\s*$k\s*=\s*[0-9]+" "$FILE" || { echo "❌ $k did not pin — the file does not match the Flutter template; edit by hand (backup at $FILE.bak)"; exit 1; }
done
grep -qE 'flutter\.(compileSdk|targetSdk|minSdk)Version' "$FILE" && { echo "⚠ some flutter.*Version references remain:"; grep -nE 'flutter\.[a-zA-Z]+Version' "$FILE"; }
echo "✅ pinned (backup: $FILE.bak — delete it once flutter build passes)"
