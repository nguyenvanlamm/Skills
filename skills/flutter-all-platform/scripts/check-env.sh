#!/usr/bin/env bash
# Phase 0 — which platforms can THIS machine build? Never installs. Exit 0 always.
#   bash check-env.sh            # human table + verdicts on stderr, JSON on stdout
# Verdict per platform: "buildable" or "blocked: <reason>". Copy them into the state file
# and into the final report — they are the only source for a ⚠️ vs ✅ decision.
set -uo pipefail

j() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

OS=$(uname -s)
IS_MAC=false; [ "$OS" = "Darwin" ] && IS_MAC=true

# --- Flutter / Dart -----------------------------------------------------------
FLUTTER_BIN=$(command -v flutter || true)
FLUTTER_VER=""; FLUTTER_CHANNEL=""; DART_VER=""
if [ -n "$FLUTTER_BIN" ]; then
  FV=$(flutter --version 2>/dev/null)
  FLUTTER_VER=$(printf '%s\n' "$FV" | sed -nE 's/^Flutter ([0-9.]+).*/\1/p' | head -1)
  FLUTTER_CHANNEL=$(printf '%s\n' "$FV" | grep -oE 'channel [a-z]+' | head -1 | awk '{print $2}')
  DART_VER=$(printf '%s\n' "$FV" | sed -nE 's/.*Dart ([0-9.]+).*/\1/p' | head -1)
fi
WEB_ENABLED=""; ANDROID_ENABLED=""; IOS_ENABLED=""
if [ -n "$FLUTTER_BIN" ]; then
  CFG=$(flutter config --list 2>/dev/null || true)
  # `flutter config --list` only prints keys that were explicitly set; unset means default (true).
  for k in web android ios; do
    val=$(printf '%s\n' "$CFG" | grep -oE "enable-$k: *(true|false)" | awk '{print $2}')
    case "$k" in
      web) WEB_ENABLED=${val:-true};;
      android) ANDROID_ENABLED=${val:-true};;
      ios) IOS_ENABLED=${val:-true};;
    esac
  done
fi

# --- Web: Chrome is only needed for `flutter run -d chrome`, not for `flutter build web`.
CHROME=""
for c in google-chrome google-chrome-stable chromium chromium-browser chrome "${CHROME_EXECUTABLE:-}"; do
  [ -n "$c" ] && command -v "$c" >/dev/null 2>&1 && { CHROME=$c; break; }
done
[ -z "$CHROME" ] && $IS_MAC && [ -d "/Applications/Google Chrome.app" ] && CHROME="/Applications/Google Chrome.app"

# --- Android -----------------------------------------------------------------
JAVA_VER=$(java -version 2>&1 | head -1 | grep -oE '"[0-9._]+"' | tr -d '"' || true)
JAVA_MAJOR=${JAVA_VER%%.*}; [ "$JAVA_MAJOR" = "1" ] && JAVA_MAJOR=$(printf '%s' "$JAVA_VER" | cut -d. -f2)
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
for cand in "$SDK" "$HOME/Android/Sdk" "$HOME/Library/Android/sdk"; do
  [ -n "$cand" ] && [ -d "$cand/platforms" ] && { SDK="$cand"; break; }
done
PLATFORMS=""; NDKS=""; HAS_36=false; NDK_OK=false
if [ -n "$SDK" ] && [ -d "$SDK" ]; then
  PLATFORMS=$(ls "$SDK/platforms" 2>/dev/null | sed 's/android-//' | sort -n | tr '\n' ' ' | sed 's/ $//')
  NDKS=$(ls "$SDK/ndk" 2>/dev/null | sort -V | tr '\n' ' ' | sed 's/ $//')
  printf ' %s ' "$PLATFORMS" | grep -q ' 36 ' && HAS_36=true
  for n in $NDKS; do [ "${n%%.*}" -ge 28 ] 2>/dev/null && NDK_OK=true; done
fi

# --- iOS ---------------------------------------------------------------------
XCODE_VER=""; POD_VER=""
if $IS_MAC; then
  XCODE_VER=$(xcodebuild -version 2>/dev/null | head -1 | awk '{print $2}' || true)
  POD_VER=$(pod --version 2>/dev/null || true)
fi

# --- Verdicts ----------------------------------------------------------------
web_v="buildable"; android_v="buildable"; ios_v="buildable"
[ -n "$FLUTTER_BIN" ] || { web_v="blocked: flutter not installed (flutter-init installs it)"; android_v="$web_v"; ios_v="$web_v"; }
if [ -n "$FLUTTER_BIN" ]; then
  [ "$WEB_ENABLED" = "false" ] && web_v="blocked: web disabled → flutter config --enable-web"
  if [ -z "$SDK" ]; then android_v="blocked: Android SDK not found (flutter-init installs it)"
  elif [ -z "$JAVA_VER" ]; then android_v="blocked: no JDK (need 17)"
  elif [ "$ANDROID_ENABLED" = "false" ]; then android_v="blocked: android disabled → flutter config --enable-android"
  fi
  if ! $IS_MAC; then ios_v="blocked: not macOS — iOS folder can be configured, build cannot run here"
  elif [ -z "$XCODE_VER" ]; then ios_v="blocked: Xcode not installed"
  elif [ -z "$POD_VER" ]; then ios_v="blocked: CocoaPods not installed (sudo gem install cocoapods)"
  fi
fi

W=()   # warnings that do not block a build but will bite later
[ -n "$FLUTTER_VER" ] && { MAJ=${FLUTTER_VER%%.*}; MIN=$(printf '%s' "$FLUTTER_VER" | cut -d. -f2)
  { [ "$MAJ" -lt 3 ] || { [ "$MAJ" -eq 3 ] && [ "$MIN" -lt 22 ]; }; } && W+=("flutter $FLUTTER_VER is old → flutter upgrade (≥3.22 for API 36 / NDK r28)"); }
[ -z "$JAVA_MAJOR" ] || [ "$JAVA_MAJOR" = "17" ] || W+=("java $JAVA_VER: AGP 8.x expects JDK 17")
[ -z "$SDK" ] || [ "$HAS_36" = true ] || W+=("platforms;android-36 missing → sdkmanager \"platforms;android-36\" \"build-tools;36.0.0\"")
[ -z "$SDK" ] || [ "$NDK_OK" = true ] || W+=("ndk r28+ missing → sdkmanager \"ndk;28.0.13004108\"")
[ -n "$CHROME" ] || W+=("no Chrome: 'flutter build web' works, 'flutter run -d chrome' will not")

{
  echo "OS            $OS"
  echo "Flutter       ${FLUTTER_VER:-NOT FOUND}${FLUTTER_CHANNEL:+ ($FLUTTER_CHANNEL)}  Dart ${DART_VER:--}"
  echo "Chrome        ${CHROME:-NOT FOUND}"
  echo "Java          ${JAVA_VER:-NOT FOUND}"
  echo "Android SDK   ${SDK:-NOT FOUND}"
  echo "  platforms   ${PLATFORMS:--}"
  echo "  ndk         ${NDKS:--}"
  echo "Xcode         ${XCODE_VER:-$($IS_MAC && echo NOT FOUND || echo 'n/a (not macOS)')}"
  echo "CocoaPods     ${POD_VER:-$($IS_MAC && echo NOT FOUND || echo 'n/a (not macOS)')}"
  echo
  echo "Verdict:"
  echo "  web       $web_v"
  echo "  android   $android_v"
  echo "  ios       $ios_v"
  if [ ${#W[@]} -gt 0 ]; then echo "Warnings:"; for w in "${W[@]}"; do echo "  - $w"; done; fi
} >&2

WJ=""; for w in "${W[@]+"${W[@]}"}"; do WJ="$WJ\"$(j "$w")\","; done; WJ="[${WJ%,}]"
cat <<EOF
{"os":"$(j "$OS")","flutter":"$(j "$FLUTTER_VER")","flutter_channel":"$(j "$FLUTTER_CHANNEL")","dart":"$(j "$DART_VER")",
 "chrome":"$(j "$CHROME")","java":"$(j "$JAVA_VER")","android_sdk":"$(j "$SDK")","android_platforms":"$(j "$PLATFORMS")",
 "ndk":"$(j "$NDKS")","xcode":"$(j "$XCODE_VER")","cocoapods":"$(j "$POD_VER")",
 "verdict":{"web":"$(j "$web_v")","android":"$(j "$android_v")","ios":"$(j "$ios_v")"},
 "warnings":$WJ}
EOF
exit 0
