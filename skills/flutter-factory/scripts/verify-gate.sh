#!/usr/bin/env bash
# flutter-factory — the gate every stage transition must pass. Runs real Flutter
# commands and writes a machine-readable verify.json; nothing here trusts a claim.
#
#   bash verify-gate.sh --project <flutter-dir> [--root <dir-with-.pipeline>] [--stage <name>]
#                       [--no-test] [--coverage] [--min-coverage <pct>] [--integration-device <id>]
#                       [--build apk|appbundle|web|none] [--release] [--dart-define K=V]...
#                       [--check NAME=COMMAND]...
#
# Steps, in order:  pub_get analyze test [coverage] [integration] build [checks] [release checks: app_id secrets]
# --check runs COMMAND with bash in the project dir as step NAME (exit 0 = ok) — e.g. a sibling
# skill's static checker: --check ios_kit='python3 <flutter-ios-release>/scripts/ios_prep_check.py --project .'
# Status per step:  ok | fail | skipped_env | skipped_user
#   skipped_user = disabled by flag (--no-test, --build none)
#   skipped_env  = environment cannot run it (no Android SDK, no device …) — report ⚠️, never ✅/❌
#   fail         = ran and exited non-zero — read <root>/.pipeline/artifacts/<stage>/logs/<step>.log
# test runs `flutter test test` (headless; integration_test/ is NOT part of it). Test counts
# (passed/skipped/failed) are parsed from its summary line. --coverage adds lcov line coverage;
# --min-coverage fails the coverage step below the given percent (PRD target).
# integration_test/ runs only with --integration-device <id>; otherwise skipped_env.
# --release adds: applicationId must not be com.example.*; secrets grep over lib/ must be empty.
# verify.json records git_sha (HEAD) and dirty (tree state when the gate STARTED, .pipeline/
# excluded) — `pipeline-state.sh advance` refuses a verify.json that is not for a clean HEAD.
# Writes <root>/.pipeline/artifacts/<stage>/verify.json (stage defaults to "gate").
# Exit 0 = no fail. Exit 1 = at least one fail. Exit 2 = usage/tooling error. Bash 3.2 compatible.
set -uo pipefail

usage() { sed -n '2,25p' "$0" >&2; exit 2; }
PROJECT=""; ROOT="$PWD"; STAGE="gate"; RUN_TEST=true; COVERAGE=false; MIN_COV=""; IDEV=""
BUILD=""; RELEASE=false; DEFINES=(); CHECKS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --project|--root|--stage|--build|--dart-define|--min-coverage|--integration-device|--check) [ $# -ge 2 ] || usage;;
  esac
  case "$1" in
    --project) PROJECT="$2"; shift 2;;
    --root) ROOT="$2"; shift 2;;
    --stage) STAGE="$2"; shift 2;;
    --no-test) RUN_TEST=false; shift;;
    --coverage) COVERAGE=true; shift;;
    --min-coverage) MIN_COV="$2"; COVERAGE=true; shift 2;;
    --integration-device) IDEV="$2"; shift 2;;
    --build) BUILD="$2"; shift 2;;
    --release) RELEASE=true; shift;;
    --dart-define) DEFINES+=("--dart-define=$2"); shift 2;;
    --check) [[ "$2" =~ ^[a-z][a-z0-9_]*=.+ ]] || { echo "--check needs NAME=COMMAND (name: a-z0-9_)" >&2; exit 2; }
             CHECKS+=("$2"); shift 2;;
    -h|--help) usage;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
[ -n "$PROJECT" ] || PROJECT="$PWD"
[ -f "$PROJECT/pubspec.yaml" ] || { echo "not a Flutter project: $PROJECT" >&2; exit 2; }
command -v flutter >/dev/null || { echo "flutter not on PATH" >&2; exit 2; }
case "$BUILD" in ""|none|apk|appbundle|web) ;; *) echo "--build must be apk|appbundle|web|none" >&2; exit 2;; esac
[ -z "$MIN_COV" ] || [[ "$MIN_COV" =~ ^[0-9]+(\.[0-9]+)?$ ]] || { echo "--min-coverage must be a number" >&2; exit 2; }

OUT="$ROOT/.pipeline/artifacts/$STAGE"; LOGS="$OUT/logs"; mkdir -p "$LOGS"
REPORT="$OUT/verify.json"
SDK=""
for cand in "${ANDROID_HOME:-}" "${ANDROID_SDK_ROOT:-}" "$HOME/Android/Sdk" "$HOME/Library/Android/sdk"; do
  [ -n "$cand" ] && [ -d "$cand/platforms" ] && { SDK="$cand"; break; }
done

# Tree state BEFORE any step runs (steps create build/, coverage/, pubspec.lock changes).
GIT_SHA=""; DIRTY=null
if git -C "$PROJECT" rev-parse --git-dir >/dev/null 2>&1; then
  GIT_SHA=$(git -C "$PROJECT" rev-parse HEAD 2>/dev/null || true)
  if [ -n "$(git -C "$PROJECT" status --porcelain -- . ':(exclude).pipeline' 2>/dev/null)" ]; then DIRTY=true; else DIRTY=false; fi
fi

j() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }
ROWS=(); FAILED=0; TESTS=null; COV=null
row() { # step status exit secs detail
  ROWS+=("{\"step\":\"$1\",\"status\":\"$2\",\"exit\":$3,\"seconds\":$4,\"detail\":\"$(j "$5")\"}")
  case "$2" in ok) ic="✅";; fail) ic="❌"; FAILED=1;; *) ic="⚠️";; esac
  printf '%-12s %s %-12s %s\n' "$1" "$ic" "$2" "$5" >&2
}
run() { # step cmd...
  local step="$1"; shift; local t0=$SECONDS
  ( cd "$PROJECT" && "$@" ) > "$LOGS/$step.log" 2>&1; local rc=$?
  if [ $rc -eq 0 ]; then row "$step" ok 0 $((SECONDS-t0)) "$*"
  else row "$step" fail $rc $((SECONDS-t0)) "log: $LOGS/$step.log"; fi
  return $rc
}
# `00:04 +61 ~2 -1: Some tests failed.` → {"passed":61,"skipped":2,"failed":1}
test_counts() {
  local last p s f
  last=$(grep -E '^[0-9:]+ \+[0-9]+' "$1" | tail -1)
  [ -n "$last" ] || return 0
  p=$(printf '%s' "$last" | sed -nE 's/^[0-9:]+ \+([0-9]+).*/\1/p')
  s=$(printf '%s' "$last" | sed -nE 's/^[0-9:]+ \+[0-9]+ ~([0-9]+).*/\1/p')
  f=$(printf '%s' "$last" | sed -nE 's/^[0-9:]+ \+[0-9]+( ~[0-9]+)? -([0-9]+).*/\2/p')
  TESTS="{\"passed\":${p:-0},\"skipped\":${s:-0},\"failed\":${f:-0}}"
}

run pub_get flutter pub get
run analyze flutter analyze --no-pub

if $RUN_TEST; then
  if [ -d "$PROJECT/test" ]; then
    TARGS=(--no-pub); $COVERAGE && { rm -f "$PROJECT/coverage/lcov.info"; TARGS+=(--coverage); }
    run test flutter test "${TARGS[@]}" test; TRC=$?
    test_counts "$LOGS/test.log"
    if $COVERAGE && [ $TRC -eq 0 ]; then   # red suite: the test row already fails the gate
      LCOV="$PROJECT/coverage/lcov.info"
      if [ ! -s "$LCOV" ]; then row coverage fail 1 0 "flutter test --coverage produced no coverage/lcov.info"
      else
        read -r LF LH PCT <<< "$(LC_ALL=C awk -F: '/^LF:/{f+=$2} /^LH:/{h+=$2} END{printf "%d %d %.1f", f, h, (f ? h*100/f : 0)}' "$LCOV")"
        COV="{\"lines_found\":$LF,\"lines_hit\":$LH,\"percent\":$PCT,\"min\":${MIN_COV:-null}}"
        if [ -n "$MIN_COV" ] && LC_ALL=C awk -v p="$PCT" -v m="$MIN_COV" 'BEGIN{exit !(p < m)}'; then
          row coverage fail 1 0 "$PCT% ($LH/$LF lines) < min $MIN_COV%"
        else row coverage ok 0 0 "$PCT% ($LH/$LF lines)${MIN_COV:+ ≥ min $MIN_COV%}"; fi
      fi
    fi
  else
    row test fail 1 0 "no test/ directory — project gap, not env"
  fi
  if [ -d "$PROJECT/integration_test" ]; then
    if [ -n "$IDEV" ]; then run integration flutter test --no-pub integration_test -d "$IDEV"
    else row integration skipped_env 0 0 "integration_test/ present, no --integration-device given"; fi
  fi
else row test skipped_user 0 0 "--no-test"; fi

case "$BUILD" in
  ""|none) row build skipped_user 0 0 "--build none";;
  apk|appbundle)
    if [ ! -d "$PROJECT/android" ]; then row build skipped_env 0 0 "no android/ folder"
    elif [ -z "$SDK" ]; then row build skipped_env 0 0 "Android SDK not found"
    else
      rm -rf "$PROJECT/build/app/outputs/flutter-apk" "$PROJECT/build/app/outputs/bundle"
      run build flutter build "$BUILD" --release --no-pub ${DEFINES[@]+"${DEFINES[@]}"}
    fi;;
  web)
    if [ ! -d "$PROJECT/web" ]; then row build skipped_env 0 0 "no web/ folder — flutter create --platforms web ."
    else rm -rf "$PROJECT/build/web"; run build flutter build web --release --no-pub ${DEFINES[@]+"${DEFINES[@]}"}; fi;;
esac

for c in ${CHECKS[@]+"${CHECKS[@]}"}; do run "${c%%=*}" bash -c "${c#*=}"; done

if $RELEASE; then
  APPID=$(cat "$PROJECT"/android/app/build.gradle* 2>/dev/null | sed -n 's/.*applicationId[ =]*["'"'"']\([^"'"'"']*\)["'"'"'].*/\1/p' | head -1)
  if [ -z "$APPID" ]; then row app_id skipped_env 0 0 "no android/app/build.gradle*"
  elif [[ "$APPID" == com.example.* ]]; then row app_id fail 1 0 "applicationId $APPID is a placeholder — DECISION org"
  else row app_id ok 0 0 "$APPID"; fi

  SECRET_RE="(api[_-]?key|secret|password|token|private[_-]?key)[[:space:]]*[:=][[:space:]]*['\"][^'\"]{8,}"
  grep -rniE "$SECRET_RE" "$PROJECT/lib" > "$LOGS/secrets.log" 2>/dev/null
  HITS=$(wc -l < "$LOGS/secrets.log" | tr -d ' ')
  if [ "$HITS" = "0" ]; then row secrets ok 0 0 "0 matches in lib/"
  else row secrets fail 1 0 "$HITS possible secret literal(s) — $LOGS/secrets.log"; fi
fi

{
  printf '{"stage":"%s","project":"%s","release":%s,"at":"%s","git_sha":"%s","dirty":%s,"passed":%s,"tests":%s,"coverage":%s,"steps":[' \
    "$(j "$STAGE")" "$(j "$PROJECT")" "$RELEASE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$GIT_SHA" "$DIRTY" \
    "$([ $FAILED -eq 0 ] && echo true || echo false)" "$TESTS" "$COV"
  (IFS=,; printf '%s' "${ROWS[*]}")
  printf ']}\n'
} > "$REPORT"
echo "report: $REPORT" >&2
[ "$DIRTY" = true ] && echo "note: tree was dirty when the gate started — commit, then re-run before 'pipeline-state.sh advance'" >&2
exit $FAILED
