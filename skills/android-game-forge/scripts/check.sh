#!/usr/bin/env bash
# android-game-forge verification gate.
# Measures what a self-report cannot be trusted on. Run from the project root.
#   bash check.sh [--no-build]
# Exit 0 = every mechanical check passed. Exit 1 = at least one FAIL.
set -uo pipefail

NO_BUILD=0
[ "${1:-}" = "--no-build" ] && NO_BUILD=1

SRC=$(find app/src/main/java app/src/main/kotlin -type d -path '*/ui/theme' 2>/dev/null | head -1 | sed 's|/ui/theme$||')
if [ -z "${SRC:-}" ] || [ ! -d "$SRC" ]; then
  echo "FATAL: cannot locate the Kotlin source root (expected app/src/main/java/**/ui/theme)."
  exit 1
fi
SCREENS="$SRC/ui/screens"
COMPONENTS="$SRC/ui/components"
THEME="$SRC/ui/theme"
RES=app/src/main/res

pass=0; fail=0; manual=0
declare -A CAT_PASS CAT_FAIL
for c in A B C D E F; do CAT_PASS[$c]=0; CAT_FAIL[$c]=0; done

ok()   { printf '  \033[32mPASS\033[0m  %s\n' "$2"; pass=$((pass+1)); CAT_PASS[$1]=$(( ${CAT_PASS[$1]} + 1 )); }
no()   { printf '  \033[31mFAIL\033[0m  %s\n' "$2"; [ -n "${3:-}" ] && printf '        %s\n' "$3"; fail=$((fail+1)); CAT_FAIL[$1]=$(( ${CAT_FAIL[$1]} + 1 )); }
man()  { printf '  \033[33mMANUAL\033[0m %s\n' "$1"; manual=$((manual+1)); }
# check CAT "label" <condition-cmd...>  — passes when the command finds NOTHING
none() { local cat=$1 label=$2; shift 2
         local hits; hits=$("$@" 2>/dev/null | head -5)
         if [ -z "$hits" ]; then ok "$cat" "$label"; else no "$cat" "$label" "$(echo "$hits" | tr '\n' ' ')"; fi; }

echo "═══ A · BUILD ═══"

# A1 — compile (the only check that proves imports resolve)
if [ $NO_BUILD -eq 1 ]; then
  man "A1 compile — skipped (--no-build); report as CODE ONLY, never OK"
elif [ ! -x ./gradlew ]; then
  no A "A1 compile" "no ./gradlew wrapper in project root"
else
  START=$(date +%s)
  if ./gradlew assembleDebug >/tmp/agf-build.log 2>&1; then
    APK=$(ls -t app/build/outputs/apk/debug/*.apk 2>/dev/null | head -1)
    if [ -z "$APK" ]; then
      no A "A1 compile" "gradle reported success but produced no APK"
    elif [ "$(stat -c %Y "$APK" 2>/dev/null || echo 0)" -lt "$START" ]; then
      no A "A1 compile" "STALE APK from an earlier run — this build produced nothing"
    else
      ok A "A1 compile — $(du -h "$APK" | cut -f1) $(basename "$APK")"
    fi
  else
    no A "A1 compile" "$(grep -hoE '^e: .*|error: .*' /tmp/agf-build.log | head -3 | tr '\n' ' ')"
  fi
fi

# A2 — every R.* reference resolves to a file on disk
missing=""
for ref in $(grep -rhoE 'R\.(raw|font|drawable|mipmap)\.[A-Za-z0-9_]+' "$SRC" 2>/dev/null | sort -u); do
  kind=$(echo "$ref" | cut -d. -f2); nm=$(echo "$ref" | cut -d. -f3)
  case $kind in
    raw|font) [ -n "$(find $RES/$kind -name "$nm.*" 2>/dev/null)" ] || missing="$missing $ref";;
    drawable) [ -n "$(find $RES -path "*drawable*" -name "$nm.*" 2>/dev/null)" ] || missing="$missing $ref";;
    mipmap)   [ -n "$(find $RES -path "*mipmap*" -name "$nm.*" 2>/dev/null)" ] || missing="$missing $ref";;
  esac
done
[ -z "$missing" ] && ok A "A2 no dangling R.* references" || no A "A2 no dangling R.* references" "$missing"

# A3 — versions consistent: no hardcoded version on a BOM-managed Compose artifact
none A "A3 Compose versions come from the BOM" \
     grep -rnE 'androidx\.compose[^"]*:[0-9]+\.[0-9]' app/build.gradle.kts

# A4 — package identity agrees everywhere
NS=$(grep -oE 'namespace *= *"[^"]+"' app/build.gradle.kts 2>/dev/null | head -1 | cut -d'"' -f2)
APPID=$(grep -oE 'applicationId *= *"[^"]+"' app/build.gradle.kts 2>/dev/null | head -1 | cut -d'"' -f2)
BADPKG=$(grep -rhoE '^package +[a-zA-Z0-9_.]+' "$SRC" 2>/dev/null | awk '{print $2}' | grep -v "^${NS:-__none__}" | sort -u)
if [ "$NS" != "$APPID" ]; then
  no A "A4 package identity" "namespace '$NS' != applicationId '$APPID'"
elif [ -n "$BADPKG" ]; then
  no A "A4 package identity" "files outside namespace: $(echo "$BADPKG" | tr '\n' ' ')"
elif echo "$APPID" | grep -qE '^com\.(example|myapp|test|app|tenapp)\.'; then
  no A "A4 package identity" "'$APPID' is a placeholder — Play rejects or permanently locks it"
else
  ok A "A4 package identity — $APPID"
fi

# A5 — no reachable TODO/FIXME/NotImplemented
none A "A5 no unfinished code" \
     grep -rnE 'TODO\(|FIXME|NotImplementedError|throw +NotImplemented' "$SRC"

echo "═══ B · LAYOUT ═══"

nscreens=$(ls "$SCREENS"/*.kt 2>/dev/null | wc -l)
if [ -f "$COMPONENTS/ScreenScaffold.kt" ] && grep -q 'safeDrawing' "$COMPONENTS/ScreenScaffold.kt"; then
  bare=$(grep -LE 'ScreenScaffold|safeDrawing' "$SCREENS"/*.kt 2>/dev/null | tr '\n' ' ')
  [ -z "$bare" ] && ok B "B1 safeDrawing on all $nscreens screens (via ScreenScaffold)" \
                 || no B "B1 safeDrawing on all screens" "not scaffolded: $bare"
else
  hits=$(grep -l 'safeDrawing' "$SCREENS"/*.kt 2>/dev/null | wc -l)
  [ "$hits" -eq "$nscreens" ] && [ "$nscreens" -gt 0 ] \
    && ok B "B1 safeDrawing on all $nscreens screens" \
    || no B "B1 safeDrawing on all screens" "$hits/$nscreens screens; no ScreenScaffold to centralise it"
fi

grep -qE '\b20\.dp|Spacing\.(gutter|screen)' "$COMPONENTS/ScreenScaffold.kt" 2>/dev/null \
  && ok B "B2 20dp gutter centralised" \
  || no B "B2 20dp gutter centralised" "ScreenScaffold does not apply the 20dp screen gutter"

if [ -f "$COMPONENTS/GameButton.kt" ] && grep -qE '(56|min).*dp|minHeight' "$COMPONENTS/GameButton.kt"; then
  ok B "B3 touch targets ≥48dp in components"
else
  no B "B3 touch targets ≥48dp in components" "GameButton has no 56dp/minHeight constraint"
fi
man "B4 layout survives 320dp width — verify in a preview or emulator"

echo "═══ C · DESIGN SYSTEM ═══"

none C "C1 zero colour literals outside theme" \
     grep -rn --include=*.kt -E '0x[0-9A-Fa-f]{8}' "$SRC/ui/screens" "$SRC/ui/components" "$SRC/game" "$SRC/platform"

RAWDP=$(grep -rnE '\b[0-9]+(\.[0-9]+)?\.dp\b' "$SCREENS" 2>/dev/null | grep -vE '\b[01]\.dp\b' | head -5)
[ -z "$RAWDP" ] && ok C "C2 zero raw dp in screens" || no C "C2 zero raw dp in screens" "$(echo "$RAWDP" | tr '\n' ' ')"

none C "C3 zero raw Material buttons in screens" \
     grep -rnE '(^|[^A-Za-z0-9_.])(Button|OutlinedButton|TextButton|ElevatedButton|FilledTonalButton)\(' "$SCREENS"

none C "C3b zero inline text styling in screens" \
     grep -rnE 'fontSize *=|color *= *Color\(' "$SCREENS"

PRESETS=$(grep -rhoE '\b(NeonPalette|SpacePalette|PaperPalette|CandyPalette|NEON|SPACE|PAPER|CANDY)\b' "$THEME/Theme.kt" "$SRC/MainActivity.kt" 2>/dev/null | sort -u | wc -l)
[ "$PRESETS" -eq 1 ] && ok C "C4 exactly one palette preset wired" \
                     || no C "C4 exactly one palette preset wired" "$PRESETS presets referenced — pick one"

FONTS=$(grep -oE 'FontFamily\(' "$THEME/Type.kt" 2>/dev/null | wc -l)
[ "$FONTS" -le 2 ] && ok C "C5 at most 2 font families ($FONTS)" \
                   || no C "C5 at most 2 font families" "$FONTS declared"

TINY=$(grep -rnE '[0-9]+\.sp' "$THEME/Type.kt" 2>/dev/null | grep -oE '\b([0-9]|1[0-2])\.sp' | head -3)
[ -z "$TINY" ] && ok C "C6 nothing under 13sp" || no C "C6 nothing under 13sp" "$TINY"

echo "═══ D · JUICE ═══"

grep -qE 'scale|graphicsLayer' "$COMPONENTS/GameButton.kt" 2>/dev/null \
  && ok D "D1 button press-scale" || no D "D1 button press-scale" "no scale animation in GameButton"

FB=$(find "$SRC/platform" -name 'Feedback.kt' 2>/dev/null | head -1)
if [ -n "$FB" ] && grep -qi 'soundpool' "$FB" && grep -qiE 'vibrat' "$FB"; then
  grep -qiE '40|rateLimit|throttle' "$FB" \
    && ok D "D2 haptics + sound fire together, tap rate-limited" \
    || no D "D2 haptics + sound fire together, tap rate-limited" "no 40ms tap throttle — rapid taps queue vibrations"
else
  no D "D2 haptics + sound fire together" "Feedback.kt missing, or it does not use both SoundPool and Vibrator"
fi

grep -q 'AnimatedGameBackground' "$COMPONENTS/ScreenScaffold.kt" 2>/dev/null \
  && ok D "D3 animated background on every screen" \
  || no D "D3 animated background on every screen" "ScreenScaffold does not include AnimatedGameBackground"

grep -rq 'AnimatedCounter' "$SCREENS" 2>/dev/null \
  && ok D "D4 AnimatedCounter in use" || no D "D4 AnimatedCounter in use" "numbers snap instead of counting"

grep -rqE 'AnimatedContent|Crossfade|AnimatedVisibility' "$SRC" 2>/dev/null \
  && ok D "D5 animated screen transitions" || no D "D5 animated screen transitions" ""

grep -rq 'rememberShake' "$SRC" 2>/dev/null \
  && ok D "D6 shake wired to impact" || no D "D6 shake wired to impact" "rememberShake defined but never used"

grep -rqE 'ParticleSystem|\.burst\(' "$SRC" 2>/dev/null \
  && ok D "D7 particles wired to reward" || no D "D7 particles wired to reward" ""

man "D8 all 3 signature juice moments from the brief are actually built — name them"

echo "═══ E · FEEL ═══"

grep -rq 'coerceAtMost' "$SRC/game" 2>/dev/null \
  && ok E "E1 dt clamped" \
  || no E "E1 dt clamped" "no clamp — a GC pause or resume will teleport entities through colliders"

grep -rq 'withFrameNanos' "$SRC" 2>/dev/null \
  && ok E "E2 frame loop uses withFrameNanos" || no E "E2 frame loop uses withFrameNanos" ""

none E "E3 no per-frame allocation in GameState" \
     grep -nE 'listOf\(|arrayListOf\(|\.map *\{|\.filter *\{|\.sortedBy *\{' "$SRC/game/GameState.kt"

none E "E4 GameState has no Compose dependency" \
     grep -n 'androidx.compose' "$SRC/game/GameState.kt"

man "E5 playable in 3s · difficulty ramps smoothly · deaths are readable — judge from the smoke test"

echo "═══ F · DONE ═══"

want="Splash Home HowToPlay Game Pause Result Settings"; miss=""
for s in $want; do ls "$SCREENS" 2>/dev/null | grep -qi "^$s" || miss="$miss $s"; done
[ -z "$miss" ] && ok F "F1 all 7 screens present" || no F "F1 all 7 screens present" "missing:$miss"

grep -rq 'BackHandler' "$SRC" 2>/dev/null \
  && ok F "F2 BackHandler present (must open Pause, not exit)" || no F "F2 BackHandler present" ""

grep -rqi 'highscore' "$SRC/platform" 2>/dev/null \
  && ok F "F3 highscore persisted" || no F "F3 highscore persisted" ""

if grep -rqi 'soundOn' "$SRC/platform" 2>/dev/null && grep -rqi 'hapticsOn' "$SRC/platform" 2>/dev/null; then
  ok F "F4 sound + haptics toggles persisted"
else
  no F "F4 sound + haptics toggles persisted" "Prefs is missing soundOn or hapticsOn"
fi

grep -rqiE 'newHighscore|isNewBest|newBest|isRecord' "$SRC" 2>/dev/null \
  && ok F "F5 highscore run is visibly distinguished" \
  || no F "F5 highscore run is visibly distinguished" "Result screen treats a record like any other run"

{ [ -f README.md ] && [ -f ATTRIBUTION.md ]; } \
  && ok F "F6 README + ATTRIBUTION present" || no F "F6 README + ATTRIBUTION present" ""

echo
echo "─────────────────────────────────────────────"
line=""
for c in A B C D E F; do
  t=$(( ${CAT_PASS[$c]} + ${CAT_FAIL[$c]} ))
  line="$line$c ${CAT_PASS[$c]}/$t  "
done
echo "$line"
echo "MEASURED $pass/$((pass+fail))   FAIL $fail   MANUAL $manual (judge these yourself, with evidence)"
[ $fail -eq 0 ] && echo "RESULT: clean — every mechanical check passed." \
                || echo "RESULT: $fail FAIL — fix and re-run. Do not report a score you did not measure."
exit $(( fail > 0 ? 1 : 0 ))
