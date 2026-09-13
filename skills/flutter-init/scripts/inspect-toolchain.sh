#!/usr/bin/env bash
# Report what the machine has, as JSON, before installing anything.
#   bash inspect-toolchain.sh            # human table on stderr, JSON on stdout
# Never installs. Exit 0 always (the caller decides what to do with the findings).
set -uo pipefail

j() { printf '%s' "$1" | sed 's/"/\\"/g'; }

OS=$(uname -s)
FLUTTER_BIN=$(command -v flutter || true)
FLUTTER_VER=""; FLUTTER_CHANNEL=""
if [ -n "$FLUTTER_BIN" ]; then
  FV=$(flutter --version 2>/dev/null | head -2)
  FLUTTER_VER=$(printf '%s' "$FV" | sed -nE 's/^Flutter ([0-9.]+).*/\1/p')
  FLUTTER_CHANNEL=$(printf '%s' "$FV" | grep -oE 'channel [a-z]+' | awk '{print $2}')
fi
JAVA_VER=$(java -version 2>&1 | head -1 | grep -oE '"[0-9._]+"' | tr -d '"' || true)
JAVA_MAJOR=${JAVA_VER%%.*}; [ "$JAVA_MAJOR" = "1" ] && JAVA_MAJOR=$(printf '%s' "$JAVA_VER" | cut -d. -f2)

SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
for cand in "$SDK" "$HOME/Android/Sdk" "$HOME/Library/Android/sdk"; do
  [ -n "$cand" ] && [ -d "$cand/platforms" ] && { SDK="$cand"; break; }
done
PLATFORMS=""; BUILD_TOOLS=""; NDKS=""; SDKMANAGER=""; ADB=""
if [ -n "$SDK" ] && [ -d "$SDK" ]; then
  PLATFORMS=$(ls "$SDK/platforms" 2>/dev/null | sed 's/android-//' | sort -n | tr '\n' ' ' | sed 's/ $//')
  BUILD_TOOLS=$(ls "$SDK/build-tools" 2>/dev/null | sort -V | tr '\n' ' ' | sed 's/ $//')
  NDKS=$(ls "$SDK/ndk" 2>/dev/null | sort -V | tr '\n' ' ' | sed 's/ $//')
  [ -x "$SDK/cmdline-tools/latest/bin/sdkmanager" ] && SDKMANAGER="$SDK/cmdline-tools/latest/bin/sdkmanager"
  [ -x "$SDK/platform-tools/adb" ] && ADB="$SDK/platform-tools/adb"
fi
[ -n "$ADB" ] || ADB=$(command -v adb || true)
DEVICES=0; [ -n "$ADB" ] && DEVICES=$("$ADB" devices 2>/dev/null | tail -n +2 | grep -c 'device$' || true)

HAS_36=false; printf ' %s ' "$PLATFORMS" | grep -q ' 36 ' && HAS_36=true
NDK_OK=false; for n in $NDKS; do [ "${n%%.*}" -ge 28 ] 2>/dev/null && NDK_OK=true; done

# Verdicts, one per line, so the caller can print them verbatim.
V=()
[ -n "$FLUTTER_BIN" ] || V+=("flutter: NOT FOUND → install (references/toolchain.md § Flutter)")
if [ -n "$FLUTTER_VER" ]; then
  MAJ=${FLUTTER_VER%%.*}; MIN=$(printf '%s' "$FLUTTER_VER" | cut -d. -f2)
  if [ "$MAJ" -lt 3 ] || { [ "$MAJ" -eq 3 ] && [ "$MIN" -lt 22 ]; }; then V+=("flutter $FLUTTER_VER: OLD → flutter upgrade (16 KB pages + current AGP need ≥3.22)"); fi
fi
[ -n "$JAVA_VER" ] || V+=("java: NOT FOUND → install OpenJDK 17")
[ -z "$JAVA_MAJOR" ] || [ "$JAVA_MAJOR" = "17" ] || V+=("java $JAVA_VER: AGP 8.x expects JDK 17 → pin org.gradle.java.home to a JDK 17")
[ -n "$SDK" ] || V+=("android sdk: NOT FOUND → install cmdline-tools at <sdk>/cmdline-tools/latest/")
[ -z "$SDK" ] || [ -n "$SDKMANAGER" ] || V+=("sdkmanager: not at cmdline-tools/latest/bin → fix layout (references/toolchain.md § 2)")
[ -z "$SDK" ] || [ "$HAS_36" = true ] || V+=("platforms;android-36: missing → sdkmanager \"platforms;android-36\" \"build-tools;36.0.0\"")
[ -z "$SDK" ] || [ "$NDK_OK" = true ] || V+=("ndk r28+: missing → sdkmanager \"ndk;28.0.13004108\" (16 KB page alignment)")
[ -n "$ADB" ] || V+=("adb: NOT FOUND → sdkmanager platform-tools (needed later for screenshots)")

{
  echo "OS            $OS"
  echo "Flutter       ${FLUTTER_VER:-NOT FOUND}${FLUTTER_CHANNEL:+ ($FLUTTER_CHANNEL)}"
  echo "Java          ${JAVA_VER:-NOT FOUND}"
  echo "Android SDK   ${SDK:-NOT FOUND}"
  echo "  platforms   ${PLATFORMS:--}"
  echo "  build-tools ${BUILD_TOOLS:--}"
  echo "  ndk         ${NDKS:--}"
  echo "  sdkmanager  ${SDKMANAGER:-missing}"
  echo "adb           ${ADB:-NOT FOUND}  devices: $DEVICES"
  echo
  if [ ${#V[@]} -eq 0 ]; then echo "Verdict: toolchain ready — skip Steps 2–3"; else echo "Verdict:"; printf '  - %s\n' "${V[@]}"; fi
} >&2

VJSON=$(printf '%s\n' "${V[@]:-}" | sed '/^$/d' | sed 's/"/\\"/g; s/^/"/; s/$/"/' | paste -sd, -)
cat <<EOF
{
  "os": "$(j "$OS")",
  "flutter": {"path": "$(j "$FLUTTER_BIN")", "version": "$(j "$FLUTTER_VER")", "channel": "$(j "$FLUTTER_CHANNEL")"},
  "java": {"version": "$(j "$JAVA_VER")", "major": "$(j "$JAVA_MAJOR")"},
  "android_sdk": {"path": "$(j "$SDK")", "platforms": "$(j "$PLATFORMS")", "build_tools": "$(j "$BUILD_TOOLS")", "ndk": "$(j "$NDKS")",
                  "sdkmanager": "$(j "$SDKMANAGER")", "has_platform_36": $HAS_36, "has_ndk_r28": $NDK_OK},
  "adb": {"path": "$(j "$ADB")", "devices": $DEVICES},
  "verdicts": [${VJSON}]
}
EOF
