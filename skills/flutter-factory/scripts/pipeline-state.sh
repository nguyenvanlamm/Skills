#!/usr/bin/env bash
# flutter-factory — .pipeline/ state helper. Every transition goes through here so
# the .pipeline/ folder alone tells the whole story of a run.
#
#   bash pipeline-state.sh init   [--root <dir>] [--project <flutter-dir>]   create .pipeline/ (idempotent)
#   bash pipeline-state.sh status [--root <dir>]                             print state.yaml + last 10 events
#   bash pipeline-state.sh get    <key>                                      print value ("" if unset), exit 1 if unset
#   bash pipeline-state.sh set    <key> <value>                              upsert `key: value` in state.yaml + log
#   bash pipeline-state.sh bump   <key>                                      integer +1 (unset → 1) + log
#   bash pipeline-state.sh log    "<message>"                                append to events.log with UTC timestamp
#
# state.yaml is FLAT: dotted keys such as `revisions.planning`, `gates.idea`, `task.T04`.
# --root defaults to $PWD (the dir that contains .pipeline/). Exit 2 on usage error.
set -uo pipefail

ROOT="$PWD"; PROJECT=""; ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --root) ROOT="$2"; shift 2;;
    --project) PROJECT="$2"; shift 2;;
    -h|--help) sed -n '2,13p' "$0"; exit 0;;
    *) ARGS+=("$1"); shift;;
  esac
done
CMD="${ARGS[0]:-}"; [ -n "$CMD" ] || { sed -n '2,13p' "$0" >&2; exit 2; }
P="$ROOT/.pipeline"; STATE="$P/state.yaml"; EVENTS="$P/events.log"
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
need_state() { [ -f "$STATE" ] || { echo "no $STATE — run: pipeline-state.sh init" >&2; exit 2; }; }
valid_key() { [[ "$1" =~ ^[A-Za-z0-9_.-]+$ ]] || { echo "bad key: $1" >&2; exit 2; }; }
log_line() { mkdir -p "$P"; printf '%s %s\n' "$(ts)" "$1" >> "$EVENTS"; }

case "$CMD" in
  init)
    mkdir -p "$P"/{artifacts,reviews,bugfix,decisions,skills}
    for s in env idea planning design architecture implementation test qa release; do mkdir -p "$P/artifacts/$s"; done
    [ -f "$P/config.yaml" ] || cat > "$P/config.yaml" <<'EOF'
human_gates: [idea, planning, release]   # pause + ask user after these reviews pass
max_revisions: 3                         # per stage; then ESCALATE
max_bugfix_cycles: 8                     # QA REVISE → fix → test → re-QA loops
parallel_implementation: false           # true → disjoint tasks via parallel subagents
reviewer_backend: subagent               # subagent | opencode | herdr
review_timeout_min: 15                   # async backends: no report by then → retry once → subagent
panel_stages: [qa]                       # multi-lens panel stages (references/reviewer-prompt.md)
release_build: apk                       # apk | appbundle | web | none
store_bound: false                       # true → QA also runs flutter-store-compliance
EOF
    [ -f "$P/constitution.md" ] || cat > "$P/constitution.md" <<'EOF'
# Constitution

Project rules that outrank every later decision, task and skill.
Fill in with the user (or derive from the repo) before the idea stage.

- Language of artifacts and UI:
- Target platforms / min OS:
- Non-negotiables (privacy, offline-first, no paid packages, ...):
- Definition of "done" for a feature:
EOF
    if [ -f "$STATE" ]; then
      echo "exists: $STATE (not overwritten)"; log_line "init: re-run, state kept"
    else
      { echo "status: running"; echo "stage: env"; echo "bugfix_cycles: 0"; echo "reviewer_backend: subagent"
        echo "started_at: $(ts)"; [ -n "$PROJECT" ] && echo "project_dir: $PROJECT"; } > "$STATE"
      log_line "init: workspace created${PROJECT:+ project_dir=$PROJECT}"
      echo "created: $P"
    fi
    ;;
  status)
    need_state
    echo "== $STATE"; cat "$STATE"
    echo; echo "== last events"; tail -n 10 "$EVENTS" 2>/dev/null || echo "(none)"
    ;;
  get)
    need_state; K="${ARGS[1]:-}"; [ -n "$K" ] || { echo "usage: get <key>" >&2; exit 2; }; valid_key "$K"
    V=$(awk -v k="$K" 'index($0, k ": ")==1 {sub("^" k ": ", ""); print; exit}' "$STATE")
    printf '%s\n' "$V"; [ -n "$V" ]
    ;;
  set)
    need_state; K="${ARGS[1]:-}"; V="${ARGS[2]:-}"
    [ -n "$K" ] && [ ${#ARGS[@]} -ge 3 ] || { echo "usage: set <key> <value>" >&2; exit 2; }; valid_key "$K"
    TMP=$(mktemp)
    awk -v k="$K" -v v="$V" 'BEGIN{done=0} index($0, k ": ")==1 {print k ": " v; done=1; next} {print} END{if(!done) print k ": " v}' "$STATE" > "$TMP" && mv "$TMP" "$STATE"
    log_line "set $K=$V"; echo "$K: $V"
    ;;
  bump)
    need_state; K="${ARGS[1]:-}"; [ -n "$K" ] || { echo "usage: bump <key>" >&2; exit 2; }; valid_key "$K"
    CUR=$(awk -v k="$K" 'index($0, k ": ")==1 {sub("^" k ": ", ""); print; exit}' "$STATE")
    [[ "$CUR" =~ ^[0-9]+$ ]] || CUR=0
    "$0" --root "$ROOT" set "$K" "$((CUR + 1))"
    ;;
  log)
    M="${ARGS[*]:1}"; [ -n "$M" ] || { echo "usage: log <message>" >&2; exit 2; }
    log_line "$M"; echo "logged"
    ;;
  *) echo "unknown command: $CMD" >&2; sed -n '2,13p' "$0" >&2; exit 2;;
esac
