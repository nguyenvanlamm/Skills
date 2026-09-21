#!/usr/bin/env bash
# flutter-factory — validate a reviewer report so the orchestrator never parses verdicts by hand.
#
#   bash review-verdict.sh <reviews/stage-vN.md> [--json]
#
# stdout (exit 0):  VERDICT critical=<n> major=<n> minor=<n> findings=<n> regression_unresolved=<n>
#                   (or a JSON object with --json)
# exit 1 = malformed report — reasons on stderr, one per line. Re-run the reviewer with them.
# exit 2 = usage.
#
# Checks: verdict line present & valid · finding ids F-nn unique · severities valid ·
# REVISE/BLOCK need ≥1 finding · APPROVE forbids critical/major · every `unresolved`
# regression row also appears in Findings · required headings present.
set -uo pipefail

FILE="${1:-}"; JSON=false; [ "${2:-}" = "--json" ] && JSON=true
[ -n "$FILE" ] && [ -f "$FILE" ] || { sed -n '2,13p' "$0" >&2; exit 2; }

ERR=(); err() { ERR+=("$1"); }

VERDICT=$(grep -m1 -E '^## Verdict:' "$FILE" | sed -E 's/^## Verdict:[[:space:]]*//; s/[[:space:]]*$//')
case "$VERDICT" in
  APPROVE|REVISE|BLOCK|ESCALATE) ;;
  "") err "missing '## Verdict:' line"; VERDICT="NONE";;
  *) err "invalid verdict '$VERDICT' (APPROVE|REVISE|BLOCK|ESCALATE)";;
esac

for h in "## Summary" "## Findings" "## Checklist results"; do
  grep -qE "^$h" "$FILE" || err "missing heading '$h'"
done

# section extractor: lines between a heading and the next '## '
section() { awk -v h="^## $1" '$0 ~ h {on=1; next} /^## / {on=0} on' "$FILE"; }

# Findings table rows: | F-nn | severity | where | finding | fix |
FIND_ROWS=$(section "Findings" | grep -E '^\|[[:space:]]*F-[0-9]+[[:space:]]*\|' || true)
N_FIND=0; N_CRIT=0; N_MAJ=0; N_MIN=0; declare -A SEEN
while IFS= read -r line; do
  [ -n "$line" ] || continue
  id=$(printf '%s' "$line" | awk -F'|' '{gsub(/[[:space:]]/,"",$2); print $2}')
  sev=$(printf '%s' "$line" | awk -F'|' '{gsub(/[[:space:]]/,"",$3); print tolower($3)}')
  [[ "$id" =~ ^F-[0-9]{2,}$ ]] || err "bad finding id '$id' (expect F-01 style)"
  [ -n "${SEEN[$id]:-}" ] && err "duplicate finding id $id"; SEEN[$id]=1
  case "$sev" in
    critical) N_CRIT=$((N_CRIT+1));; major) N_MAJ=$((N_MAJ+1));; minor) N_MIN=$((N_MIN+1));;
    *) err "$id: invalid severity '$sev' (critical|major|minor)";;
  esac
  N_FIND=$((N_FIND+1))
done <<< "$FIND_ROWS"

case "$VERDICT" in
  REVISE|BLOCK) [ $N_FIND -ge 1 ] || err "$VERDICT with zero findings";;
  APPROVE) [ $((N_CRIT+N_MAJ)) -eq 0 ] || err "APPROVE with $N_CRIT critical / $N_MAJ major findings — verdict must be REVISE or BLOCK";;
esac
[ "$VERDICT" != "APPROVE" ] && [ $N_FIND -gt 0 ] && [ $((N_CRIT+N_MAJ)) -eq 0 ] && err "$VERDICT with only minor findings — should be APPROVE (or explain in an ESCALATE)"

# Regression table (optional): unresolved rows must reappear in Findings
N_UNRES=0
if grep -qE '^## Regression' "$FILE"; then
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    id=$(printf '%s' "$line" | awk -F'|' '{gsub(/[[:space:]]/,"",$2); print $2}')
    st=$(printf '%s' "$line" | awk -F'|' '{gsub(/[[:space:]]/,"",$3); print tolower($3)}')
    case "$st" in
      resolved) ;;
      unresolved) N_UNRES=$((N_UNRES+1)); [ -n "${SEEN[$id]:-}" ] || err "regression $id unresolved but absent from Findings";;
      *) err "regression $id: status '$st' (resolved|unresolved)";;
    esac
  done <<< "$(section "Regression" | grep -E '^\|[[:space:]]*F-[0-9]+[[:space:]]*\|' || true)"
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
