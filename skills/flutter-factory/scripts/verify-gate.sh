#!/usr/bin/env bash
# flutter-factory — the gate every stage transition must pass. Runs real Flutter
# commands and writes a machine-readable verify.json; nothing here trusts a claim.
#
#   bash verify-gate.sh --project <flutter-dir> [--root <dir-with-.pipeline>] [--stage <name>]
#                       [--no-test] [--build apk|appbundle|web|none] [--release] [--dart-define K=V]...
#
# Steps, in order:  pub_get analyze test build [release checks: app_id secrets]
# Status per step:  ok | fail | skipped_env | skipped_user
#   skipped_user = disabled by flag (--no-test, --build none)
#   skipped_env  = environment cannot run it (no Android SDK, no Chrome …) — report ⚠️, never ✅/❌
#   fail         = ran and exited non-zero — read <root>/.pipeline/artifacts/<stage>/logs/<step>.log
# --release adds: applicationId must not be com.example.*; secrets grep over lib/ must be empty.
# Writes <root>/.pipeline/artifacts/<stage>/verify.json (stage defaults to "gate").
# Exit 0 = no fail. Exit 1 = at least one fail. Exit 2 = usage/tooling error.
set -uo pipefail

PROJECT=""; ROOT="$PWD"; STAGE="gate"; RUN_TEST=true; BUILD=""; RELEASE=false; DEFINES=()
while [ $# -gt 0 ]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2;;
    --root) ROOT="$2"; shift 2;;
    --stage) STAGE="$2"; shift 2;;
    --no-test) RUN_TEST=false; shift;;
    --build) BUILD="$2"; shift 2;;
    --release) RELEASE=true; shift;;
    --dart-define) DEFINES+=("--dart-define=$2"); shift 2;;
    -h|--help) sed -n '2,15p' "$0"; exit 0;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
[ -n "$PROJECT" ] || PROJECT="$PWD"
[ -f "$PROJECT/pubspec.yaml" ] || { echo "not a Flutter project: $PROJECT" >&2; exit 2; }
command -v flutter >/dev/null || { echo "flutter not on PATH" >&2; exit 2; }
case "$BUILD" in ""|none|apk|appbundle|web) ;; *) echo "--build must be apk|appbundle|web|none" >&2; exit 2;; esac

OUT="$ROOT/.pipeline/artifacts/$STAGE"; LOGS="$OUT/logs"; mkdir -p "$LOGS"
REPORT="$OUT/verify.json"
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
for cand in "$SDK" "$HOME/Android/Sdk" "$HOME/Library/Android/sdk"; do
  [ -n "$cand" ] && [ -d "$cand/platforms" ] && { SDK="$cand"; break; }
done

j() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }
declare -a ROWS; FAILED=0
row() { # step status exit secs detail
  ROWS+=("{\"step\":\"$1\",\"status\":\"$2\",\"exit\":$3,\"seconds\":$4,\"detail\":\"$(j "$5")\"}")
  case "$2" in ok) ic="✅";; fail) ic="❌"; FAILED=1;; *) ic="⚠️";; esac
  printf '%-10s %s %-12s %s\n' "$1" "$ic" "$2" "$5" >&2
}
run() { # step cmd...
  local step="$1"; shift; local t0=$SECONDS
  ( cd "$PROJECT" && "$@" ) > "$LOGS/$step.log" 2>&1; local rc=$?
  if [ $rc -eq 0 ]; then row "$step" ok 0 $((SECONDS-t0)) "$*"
  else row "$step" fail $rc $((SECONDS-t0)) "log: $LOGS/$step.log"; fi
  return $rc
}

run pub_get flutter pub get
run analyze flutter analyze --no-pub

if $RUN_TEST; then
  if [ -d "$PROJECT/test" ] || [ -d "$PROJECT/integration_test" ]; then
    run test flutter test --no-pub
  else
    row test fail 1 0 "no test/ directory — project gap, not env"
  fi
else row test skipped_user 0 0 "--no-test"; fi

case "$BUILD" in
  ""|none) row build skipped_user 0 0 "--build none";;
  apk|appbundle)
    if [ ! -d "$PROJECT/android" ]; then row build skipped_env 0 0 "no android/ folder"
    elif [ -z "$SDK" ]; then row build skipped_env 0 0 "Android SDK not found"
    else
      rm -rf "$PROJECT/build/app/outputs/flutter-apk" "$PROJECT/build/app/outputs/bundle"
      run build flutter build "$BUILD" --release --no-pub "${DEFINES[@]}"
    fi;;
  web)
    if [ ! -d "$PROJECT/web" ]; then row build skipped_env 0 0 "no web/ folder — flutter create --platforms web ."
    else rm -rf "$PROJECT/build/web"; run build flutter build web --release --no-pub "${DEFINES[@]}"; fi;;
esac

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
  printf '{"stage":"%s","project":"%s","release":%s,"at":"%s","passed":%s,"steps":[' \
    "$(j "$STAGE")" "$(j "$PROJECT")" "$RELEASE" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$([ $FAILED -eq 0 ] && echo true || echo false)"
  (IFS=,; printf '%s' "${ROWS[*]}")
  printf ']}\n'
} > "$REPORT"
echo "report: $REPORT" >&2
exit $FAILED
