#!/usr/bin/env bash
# Phase 10 — run the full verification chain and write a machine-readable report.
#   bash build-all.sh --project <dir> [--only <step>] [--skip <step>[,<step>]] [--dart-define K=V]...
# Steps, in order:  pub_get analyze test web apk appbundle ios
# Status per step:  ok | fail | skipped_env | skipped_user
#   skipped_env  = the environment cannot run it (no Android SDK, not macOS …) — report as ⚠️, never ✅/❌
#   fail         = it ran and exited non-zero — read build/flutter-all-platform/logs/<step>.log, fix, rerun --only <step>
# Stale artifacts are deleted before each build so a green line always refers to THIS run.
# Exit code: 0 if no step failed (skips are not failures), 1 otherwise.
set -uo pipefail

PROJECT=""; ONLY=""; SKIP=""; DEFINES=()
while [ $# -gt 0 ]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2;;
    --only) ONLY="$2"; shift 2;;
    --skip) SKIP="$2"; shift 2;;
    --dart-define) DEFINES+=("--dart-define=$2"); shift 2;;
    -h|--help) sed -n '2,10p' "$0"; exit 0;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
[ -n "$PROJECT" ] || PROJECT="$PWD"
[ -f "$PROJECT/pubspec.yaml" ] || { echo "not a Flutter project: $PROJECT" >&2; exit 2; }
cd "$PROJECT" || exit 2
command -v flutter >/dev/null || { echo "flutter not on PATH" >&2; exit 2; }

OUT="build/flutter-all-platform"; LOGS="$OUT/logs"; mkdir -p "$LOGS"
REPORT="$OUT/build-report.json"
IS_MAC=false; [ "$(uname -s)" = "Darwin" ] && IS_MAC=true
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
for cand in "$SDK" "$HOME/Android/Sdk" "$HOME/Library/Android/sdk"; do
  [ -n "$cand" ] && [ -d "$cand/platforms" ] && { SDK="$cand"; break; }
done
HAS_XCODE=false; $IS_MAC && xcodebuild -version >/dev/null 2>&1 && HAS_XCODE=true

j() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }
in_list() { case ",$2," in *",$1,"*) return 0;; esac; return 1; }

declare -A STATUS EXITC REASON ARTIFACT SECS PREV_ROW
STEPS="pub_get analyze test web apk appbundle ios"

env_block() {   # prints a reason if the step cannot run in this environment
  case "$1" in
    web) [ -d web ] || echo "no web/ folder — run: flutter create --platforms web .";;
    apk|appbundle) [ -d android ] || { echo "no android/ folder"; return; }
                   [ -n "$SDK" ] || echo "Android SDK not found";;
    ios) [ -d ios ] || { echo "no ios/ folder"; return; }
         $IS_MAC || { echo "not macOS — iOS build cannot run here"; return; }
         $HAS_XCODE || echo "Xcode not installed";;
    test) [ -d test ] || [ -d integration_test ] || echo "no test/ directory — write tests first (Phase 7), this is a project gap not an env gap";;
  esac
}

artifact_of() {
  case "$1" in
    web) echo "build/web/index.html";;
    apk) ls build/app/outputs/flutter-apk/app-release.apk 2>/dev/null || ls build/app/outputs/flutter-apk/*.apk 2>/dev/null | head -1;;
    appbundle) echo "build/app/outputs/bundle/release/app-release.aab";;
    ios) echo "build/ios/iphoneos/Runner.app";;
  esac
}

clean_stale() {
  case "$1" in
    web) rm -rf build/web;;
    apk) rm -rf build/app/outputs/flutter-apk;;
    appbundle) rm -rf build/app/outputs/bundle;;
    ios) rm -rf build/ios/iphoneos;;
  esac
}

cmd_of() {
  case "$1" in
    pub_get) echo "flutter pub get";;
    analyze) echo "flutter analyze --no-pub";;
    test) echo "flutter test --no-pub";;
    web) echo "flutter build web --release --no-pub ${DEFINES[*]+"${DEFINES[*]}"}";;
    apk) echo "flutter build apk --release --no-pub ${DEFINES[*]+"${DEFINES[*]}"}";;
    appbundle) echo "flutter build appbundle --release --no-pub ${DEFINES[*]+"${DEFINES[*]}"}";;
    ios) echo "flutter build ios --release --no-codesign --no-pub ${DEFINES[*]+"${DEFINES[*]}"}";;
  esac
}

run_step() {
  local s="$1" start end reason cmd
  if [ -n "$ONLY" ] && ! in_list "$s" "$ONLY"; then STATUS[$s]="skipped_user"; REASON[$s]="not in --only"; return; fi
  if [ -n "$SKIP" ] && in_list "$s" "$SKIP"; then STATUS[$s]="skipped_user"; REASON[$s]="--skip"; return; fi
  reason=$(env_block "$s")
  if [ -n "$reason" ]; then
    # a missing test/ dir is a project failure by the skill's definition of done, not an env skip
    if [ "$s" = "test" ]; then STATUS[$s]="fail"; EXITC[$s]=1; else STATUS[$s]="skipped_env"; fi
    REASON[$s]="$reason"; printf '%-10s %-12s %s\n' "$s" "${STATUS[$s]}" "$reason" >&2; return
  fi
  clean_stale "$s"
  cmd=$(cmd_of "$s")
  printf '%-10s running      %s\n' "$s" "$cmd" >&2
  start=$(date +%s)
  # shellcheck disable=SC2086
  $cmd >"$LOGS/$s.log" 2>&1; local ec=$?
  end=$(date +%s); SECS[$s]=$((end-start)); EXITC[$s]=$ec
  if [ $ec -eq 0 ]; then
    local a; a=$(artifact_of "$s")
    if [ -n "$a" ] && [ ! -e "$a" ]; then STATUS[$s]="fail"; REASON[$s]="exit 0 but artifact missing: $a"
    else STATUS[$s]="ok"; ARTIFACT[$s]="$a"; fi
  else
    STATUS[$s]="fail"; REASON[$s]="see $LOGS/$s.log — last line: $(tail -n 1 "$LOGS/$s.log" | cut -c1-160)"
  fi
  printf '%-10s %-12s exit %s  %ss\n' "$s" "${STATUS[$s]}" "$ec" "${SECS[$s]}" >&2
}

FAILED=0
for s in $STEPS; do
  run_step "$s"
  [ "${STATUS[$s]}" = "fail" ] && FAILED=1
  # a broken pub get or analyze makes every later step noise — stop there unless the user asked for one step
  if [ -z "$ONLY" ] && [ "${STATUS[$s]}" = "fail" ] && { [ "$s" = "pub_get" ] || [ "$s" = "analyze" ]; }; then
    for rest in $STEPS; do [ -z "${STATUS[$rest]+x}" ] && { STATUS[$rest]="skipped_user"; REASON[$rest]="blocked by $s failure"; }; done
    break
  fi
done

# merge with previous report when --only is used, so one rerun does not erase the other rows
if [ -n "$ONLY" ] && [ -f "$REPORT" ]; then
  for s in $STEPS; do
    if [ "${STATUS[$s]}" = "skipped_user" ] && [ "${REASON[$s]}" = "not in --only" ]; then
      prev=$(grep -oE "\"$s\":\{[^}]*\}" "$REPORT" | head -1)
      PREV_ROW[$s]="$prev"
    fi
  done
fi

FLUTTER_VER=$(flutter --version 2>/dev/null | sed -nE 's/^Flutter ([0-9.]+).*/\1/p' | head -1)
{
  echo "{"
  echo "  \"project\": \"$(j "$PWD")\", \"flutter\": \"$(j "$FLUTTER_VER")\", \"os\": \"$(uname -s)\", \"at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
  echo "  \"steps\": {"
  first=true
  for s in $STEPS; do
    $first || echo ","; first=false
    if [ -n "${PREV_ROW[$s]+x}" ] && [ -n "${PREV_ROW[$s]}" ]; then printf '    %s' "${PREV_ROW[$s]}"; continue; fi
    printf '    "%s":{"status":"%s","exit":%s,"seconds":%s,"command":"%s","artifact":"%s","reason":"%s","log":"%s"}' \
      "$s" "${STATUS[$s]}" "${EXITC[$s]:-null}" "${SECS[$s]:-null}" "$(j "$(cmd_of "$s")")" \
      "$(j "${ARTIFACT[$s]:-}")" "$(j "${REASON[$s]:-}")" "$LOGS/$s.log"
  done
  echo; echo "  },"
  echo "  \"failed\": $FAILED"
  echo "}"
} > "$REPORT"

echo >&2; echo "Report: $REPORT" >&2
for s in $STEPS; do printf '  %-10s %s\n' "$s" "${STATUS[$s]}" >&2; done
exit $FAILED
