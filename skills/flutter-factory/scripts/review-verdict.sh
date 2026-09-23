#!/usr/bin/env bash
# flutter-factory — validate a reviewer report so the orchestrator never parses verdicts by hand.
#
#   bash review-verdict.sh <reviews/stage-vN.md> [--prev <reviews/stage-v(N-1).md>] [--json]
#
# stdout (exit 0):  VERDICT critical=<n> major=<n> minor=<n> findings=<n> regression_unresolved=<n>
#                   (or a JSON object with --json)
# exit 1 = malformed report — reasons on stderr, one per line. Re-run the reviewer with them.
# exit 2 = usage.
#
# Checks: verdict line present & valid · finding ids F-nn unique · severities valid ·
# REVISE/BLOCK need ≥1 finding and ≥1 critical/major · APPROVE forbids critical/major ·
# ESCALATE may carry any number of findings (incl. none) · every `unresolved`
# regression row also appears in Findings · required headings present ·
# Checklist results uses `- [pass|fail|n.a.] …` lines and (except ESCALATE) every
# `[fail]` line has a finding.
# --prev (mandatory from revision v2 on; the previous report or the human-gate file):
# every previous finding has exactly one Regression row · no Regression row for an id
# the previous report did not have · a `resolved` id is not still in Findings · new ids
# are greater than the previous maximum (ids continue across revisions).
# Bash 3.2 compatible (macOS /bin/bash).
set -uo pipefail

usage() { sed -n '2,21p' "$0" >&2; exit 2; }
FILE=""; PREV=""; JSON=false
while [ $# -gt 0 ]; do
  case "$1" in
    --prev) [ $# -ge 2 ] || usage; PREV="$2"; shift 2;;
    --json) JSON=true; shift;;
    -h|--help) usage;;
    *) FILE="$1"; shift;;
  esac
done
[ -n "$FILE" ] && [ -f "$FILE" ] || usage
[ -z "$PREV" ] || [ -f "$PREV" ] || { echo "no such file: $PREV" >&2; exit 2; }

ERR=(); err() { ERR+=("$1"); }
# lines between '## <heading>' and the next '## '
section() { awk -v h="^## $1" '$0 ~ h {on=1; next} /^## / {on=0} on' "$2"; }
# `| F-nn | col2 | …` rows of a section → "F-nn col2" (col2 lower-cased, spaces stripped)
rows() { section "$1" "$2" | grep -E '^\|[[:space:]]*F-[0-9]+[[:space:]]*\|' \
  | awk -F'|' '{gsub(/[[:space:]]/,"",$2); gsub(/[[:space:]]/,"",$3); print $2, tolower($3)}'; }
num() { local n; n=$(printf '%s' "${1#F-}" | sed 's/^0*//'); printf '%s' "${n:-0}"; }
has() { case " $1 " in *" $2 "*) return 0;; esac; return 1; }

VERDICT=$(grep -m1 -E '^## Verdict:' "$FILE" | sed -E 's/^## Verdict:[[:space:]]*//; s/[[:space:]]*$//')
case "$VERDICT" in
  APPROVE|REVISE|BLOCK|ESCALATE) ;;
  "") err "missing '## Verdict:' line"; VERDICT="NONE";;
  *) err "invalid verdict '$VERDICT' (APPROVE|REVISE|BLOCK|ESCALATE)";;
esac

for h in "## Summary" "## Findings" "## Checklist results"; do
  grep -qE "^$h" "$FILE" || err "missing heading '$h'"
done

N_FIND=0; N_CRIT=0; N_MAJ=0; N_MIN=0; SEEN=""
while read -r id sev; do
  [ -n "$id" ] || continue
  [[ "$id" =~ ^F-[0-9]{2,}$ ]] || err "bad finding id '$id' (expect F-01 style)"
  has "$SEEN" "$id" && err "duplicate finding id $id"; SEEN="$SEEN $id"
  case "$sev" in
    critical) N_CRIT=$((N_CRIT+1));; major) N_MAJ=$((N_MAJ+1));; minor) N_MIN=$((N_MIN+1));;
    *) err "$id: invalid severity '$sev' (critical|major|minor)";;
  esac
  N_FIND=$((N_FIND+1))
done <<< "$(rows Findings "$FILE")"

case "$VERDICT" in
  REVISE|BLOCK)
    if [ $N_FIND -eq 0 ]; then err "$VERDICT with zero findings"
    elif [ $((N_CRIT+N_MAJ)) -eq 0 ]; then err "$VERDICT with only minor findings — should be APPROVE (or ESCALATE with the reason in Summary)"; fi;;
  APPROVE) [ $((N_CRIT+N_MAJ)) -eq 0 ] || err "APPROVE with $N_CRIT critical / $N_MAJ major findings — verdict must be REVISE or BLOCK";;
esac

# Checklist results: `- [pass] …` / `- [fail] …` / `- [n.a.] …`
RES=$(section "Checklist results" "$FILE" | grep -iE '^[[:space:]]*[-*][[:space:]]*\[(pass|fail|n\.?a\.?)\]' || true)
N_RES=$(printf '%s' "$RES" | grep -c . || true)
N_FAIL=$(printf '%s' "$RES" | grep -ciE '^[[:space:]]*[-*][[:space:]]*\[fail\]' || true)
[ "${N_RES:-0}" -gt 0 ] || err "Checklist results has no '- [pass|fail|n.a.] <line>' entries"
[ "$VERDICT" = ESCALATE ] || [ "${N_FAIL:-0}" -le $N_FIND ] \
  || err "$N_FAIL checklist lines are [fail] but Findings has only $N_FIND rows — every fail needs its own F-nn"

# Regression table: unresolved rows must reappear in Findings
N_UNRES=0; REG=""
if grep -qE '^## Regression' "$FILE"; then
  while read -r id st; do
    [ -n "$id" ] || continue
    REG="$REG $id:$st"
    case "$st" in
      resolved) has "$SEEN" "$id" && err "regression $id marked resolved but still listed in Findings";;
      unresolved) N_UNRES=$((N_UNRES+1)); has "$SEEN" "$id" || err "regression $id unresolved but absent from Findings";;
      *) err "regression $id: status '$st' (resolved|unresolved)";;
    esac
  done <<< "$(rows Regression "$FILE")"
fi

if [ -n "$PREV" ]; then
  PREV_IDS=$(rows Findings "$PREV" | awk '{print $1}' | tr '\n' ' ')
  MAXP=0; for id in $PREV_IDS; do n=$(num "$id"); [ "$n" -gt $MAXP ] && MAXP=$n; done
  for id in $PREV_IDS; do
    c=$(printf '%s\n' $REG | grep -c "^$id:" || true)
    [ "$c" -eq 1 ] || err "regression: expected exactly one row for previous finding $id, found $c"
  done
  for r in $REG; do has "$PREV_IDS" "${r%%:*}" || err "regression row ${r%%:*} is not a finding of $(basename "$PREV")"; done
  NEXT=$(printf 'F-%02d' $((MAXP+1)))
  for id in $SEEN; do
    has "$PREV_IDS" "$id" && continue
    [ "$(num "$id")" -gt $MAXP ] || err "new finding $id reuses an old id — new ids start at $NEXT"
  done
fi

if [ ${#ERR[@]} -gt 0 ]; then
  printf 'MALFORMED: %s\n' "${ERR[@]}" >&2; exit 1
fi
if $JSON; then
  printf '{"verdict":"%s","critical":%d,"major":%d,"minor":%d,"findings":%d,"regression_unresolved":%d}\n' \
    "$VERDICT" $N_CRIT $N_MAJ $N_MIN $N_FIND $N_UNRES
else
  printf '%s critical=%d major=%d minor=%d findings=%d regression_unresolved=%d\n' \
    "$VERDICT" $N_CRIT $N_MAJ $N_MIN $N_FIND $N_UNRES
fi
