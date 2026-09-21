#!/usr/bin/env bash
# flutter-factory — collect side-effect-free facts about the project for the QA reviewer.
# The reviewer is read-only and cannot run commands; the orchestrator runs this BEFORE the
# qa review and the reviewer cites these files as evidence for [E] checklist lines.
#
#   bash evidence-pack.sh --project <flutter-dir> [--root <dir-with-.pipeline>] [--stage qa]
#
# Writes <root>/.pipeline/artifacts/<stage>/evidence/:
#   analyze.txt          flutter analyze output (all infos)
#   outdated.json        flutter pub outdated --json
#   deps.txt             flutter pub deps --style=compact
#   secrets.txt          grep for secret-looking literals in lib/  (empty = clean)
#   manifest.txt         AndroidManifest facts: permissions, exported, cleartext, debuggable
#   gradle.txt           applicationId, minSdk/targetSdk/compileSdk, minifyEnabled/shrinkResources
#   patterns.txt         grep hits for risky Dart patterns (context after await, bare `!`, print, http://, bare CircularProgressIndicator, ignore:)
#   index.json           one line per file: name, lines, ok|fail|skipped_env
# Never modifies the project. Exit 0 always unless usage error (exit 2) — the facts, not this
# script, decide the verdict. `skipped_env` marks a fact a tool could not produce here.
set -uo pipefail

PROJECT=""; ROOT="$PWD"; STAGE="qa"
while [ $# -gt 0 ]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2;;
    --root) ROOT="$2"; shift 2;;
    --stage) STAGE="$2"; shift 2;;
    -h|--help) sed -n '2,18p' "$0"; exit 0;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
[ -n "$PROJECT" ] || PROJECT="$PWD"
[ -f "$PROJECT/pubspec.yaml" ] || { echo "not a Flutter project: $PROJECT" >&2; exit 2; }
command -v flutter >/dev/null || { echo "flutter not on PATH" >&2; exit 2; }

OUT="$ROOT/.pipeline/artifacts/$STAGE/evidence"; mkdir -p "$OUT"
declare -a IDX
j() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }
note() { # file status detail
  local n=0; [ -f "$OUT/$1" ] && n=$(wc -l < "$OUT/$1" | tr -d ' ')
  IDX+=("{\"file\":\"$1\",\"status\":\"$2\",\"lines\":$n,\"detail\":\"$(j "$3")\"}")
  printf '%-14s %-12s %s\n' "$1" "$2" "$3" >&2
}
runf() { # file cmd...   (runs in project, captures stdout+stderr)
  local f="$1"; shift
  ( cd "$PROJECT" && "$@" ) > "$OUT/$f" 2>&1 && note "$f" ok "$*" || note "$f" fail "$* (exit $?) — output kept"
}

runf analyze.txt flutter analyze --no-pub
runf outdated.json flutter pub outdated --json --no-dependency-overrides
runf deps.txt flutter pub deps --style=compact

SECRET_RE="(api[_-]?key|secret|password|token|private[_-]?key)[[:space:]]*[:=][[:space:]]*['\"][^'\"]{8,}"
grep -rniE "$SECRET_RE" "$PROJECT/lib" > "$OUT/secrets.txt" 2>/dev/null
note secrets.txt ok "$(wc -l < "$OUT/secrets.txt" | tr -d ' ') match(es); empty = clean"

MAN="$PROJECT/android/app/src/main/AndroidManifest.xml"
if [ -f "$MAN" ]; then
  {
    echo "# $MAN"; echo "## uses-permission"; grep -n 'uses-permission' "$MAN" || echo "(none)"
    echo "## android:exported"; grep -n 'android:exported' "$MAN" || echo "(none declared)"
    echo "## components without explicit exported"; awk '
      /<(activity|activity-alias|service|receiver|provider)[ >\/]/ {blk=$0; ln=NR; inb=1}
      inb && !/<(activity|activity-alias|service|receiver|provider)[ >\/]/ {blk=blk" "$0}
      inb && />/ { if (blk !~ /android:exported/) print ln": "blk; inb=0 }' "$MAN" || echo "(none)"
    echo "## usesCleartextTraffic"; grep -n 'usesCleartextTraffic' "$MAN" || echo "(not set — default false on API 28+)"
    echo "## debuggable"; grep -n 'android:debuggable' "$MAN" || echo "(not set)"
    echo "## intent-filter data"; grep -n '<data ' "$MAN" || echo "(none)"
  } > "$OUT/manifest.txt"; note manifest.txt ok "permissions/exported/cleartext/debuggable/deep links"
else note manifest.txt skipped_env "no AndroidManifest.xml"; fi

if ls "$PROJECT"/android/app/build.gradle* >/dev/null 2>&1; then
  grep -nE 'applicationId|namespace|minSdk|targetSdk|compileSdk|minifyEnabled|shrinkResources|signingConfig|debuggable' \
    "$PROJECT"/android/app/build.gradle* > "$OUT/gradle.txt" 2>/dev/null
  note gradle.txt ok "ids, sdk levels, minify"
else note gradle.txt skipped_env "no android/app/build.gradle*"; fi

LIB="$PROJECT/lib"
sec() { echo "## $1"; }
hits() { local out; out=$(cat); [ -n "$out" ] && printf '%s\n' "$out" || echo "(none)"; echo; }
{
  sec "context/Navigator used within 3 lines after an await (candidates — confirm mounted check)"
  grep -rnE -A3 '\bawait ' "$LIB" 2>/dev/null | grep -E 'context\.|Navigator\.|ScaffoldMessenger\.|showDialog\(' | hits
  sec "bare null-assert !";                      grep -rnE '([A-Za-z0-9_)]|\])![.;,) ]' "$LIB" 2>/dev/null | hits
  sec "print / debugPrint";                      grep -rnE '\b(print|debugPrint)\(' "$LIB" 2>/dev/null | hits
  sec "http:// literals";                        grep -rnE "['\"]http://" "$LIB" 2>/dev/null | hits
  sec "bare CircularProgressIndicator in features/"; grep -rnE 'CircularProgressIndicator\(' "$LIB" 2>/dev/null | grep '/features/' | hits
  sec "// ignore: lines";                        grep -rnE '// ?ignore(_for_file)?:' "$LIB" 2>/dev/null | hits
  sec "badCertificateCallback";                  grep -rn 'badCertificateCallback' "$LIB" 2>/dev/null | hits
  sec "SharedPreferences with token/password/secret"; grep -rniE 'SharedPreferences.*(token|password|secret)|(token|password|secret).*SharedPreferences' "$LIB" 2>/dev/null | hits
  sec "double used for money-like names";        grep -rniE 'double\s+(price|amount|total|balance|cost)|(price|amount|total|balance|cost)[A-Za-z]*\s*:\s*double' "$LIB" 2>/dev/null | hits
  sec "unawaited-looking calls (Future returned, not awaited — candidates)"; grep -rnE '^\s*[a-zA-Z_][a-zA-Z0-9_.]*\((.*)\);\s*$' "$LIB" 2>/dev/null | grep -E '(save|load|fetch|delete|update|insert|write|send|sync|refresh)\(' | grep -v await | hits
} > "$OUT/patterns.txt"
note patterns.txt ok "risky Dart patterns — candidates, reviewer confirms file:line"

{
  printf '{"stage":"%s","project":"%s","at":"%s","files":[' "$(j "$STAGE")" "$(j "$PROJECT")" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  (IFS=,; printf '%s' "${IDX[*]}")
  printf ']}\n'
} > "$OUT/index.json"
echo "evidence: $OUT" >&2
