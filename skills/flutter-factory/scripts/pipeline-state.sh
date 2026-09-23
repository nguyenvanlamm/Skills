#!/usr/bin/env bash
# flutter-factory — .pipeline/ state helper. Every transition goes through here so
# the .pipeline/ folder alone tells the whole story of a run.
#
#   bash pipeline-state.sh init    [--root <dir>] [--project <flutter-dir>]  create .pipeline/ (idempotent; re-run after T01)
#   bash pipeline-state.sh status  [--root <dir>]                            print state.yaml + last 10 events
#   bash pipeline-state.sh get     <key>                                     print value ("" if unset), exit 1 if unset
#   bash pipeline-state.sh set     <key> <value>                             upsert `key: value` in state.yaml + log
#   bash pipeline-state.sh bump    <key>                                     integer +1 (unset → 1) + log
#   bash pipeline-state.sh log     "<message>"                               append to events.log with UTC timestamp
#   bash pipeline-state.sh check                                             list what blocks leaving the current stage (exit 1 if any)
#   bash pipeline-state.sh advance [--override "<user's reason>"]            leave the current stage for the next one — refused
#                                                                            (exit 1) while `check` reports a blocker
#
# state.yaml is FLAT: dotted keys such as `revisions.planning`, `review.idea`, `gates.idea`, `task.T04`.
# Stage order: env idea planning design architecture implementation test qa release → done.
# `advance` checks: latest reviews/<stage>-vN.md validates as APPROVE (reviewed stages; from v2 with
# --prev <stage>-v(N-1)[-gate].md) and no stage artifact is newer than it · gates.<stage>
# = approved (stages in config human_gates) · verify.json passed, for a clean tree at the project's
# current HEAD (implementation, test, qa, release) · stage-specific artifacts (see check_stage) ·
# release with config ios_release: true → verify.json step ios_kit ok (unless the skill fell back inline).
# --override bypasses the checks ONLY on the user's explicit instruction; it is logged as OVERRIDE.
# init also adds `.pipeline/` to .git/info/exclude of the repo containing --root / --project.
# --root defaults to $PWD (the dir that contains .pipeline/). Exit 2 on usage error. Bash 3.2 compatible.
set -uo pipefail

usage() { sed -n '2,24p' "$0" >&2; exit 2; }
SELF_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT="$PWD"; PROJECT=""; OVERRIDE=""; ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --root|--project|--override) [ $# -ge 2 ] || usage;;
  esac
  case "$1" in
    --root) ROOT="$2"; shift 2;;
    --project) PROJECT="$2"; shift 2;;
    --override) OVERRIDE="$2"; shift 2;;
    -h|--help) sed -n '2,24p' "$0"; exit 0;;
    *) ARGS+=("$1"); shift;;
  esac
done
CMD="${ARGS[0]:-}"; [ -n "$CMD" ] || usage
P="$ROOT/.pipeline"; STATE="$P/state.yaml"; EVENTS="$P/events.log"; CONFIG="$P/config.yaml"
STAGES="env idea planning design architecture implementation test qa release done"
REVIEWED="idea planning design architecture test qa"
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
need_state() { [ -f "$STATE" ] || { echo "no $STATE — run: pipeline-state.sh init" >&2; exit 2; }; }
valid_key() { [[ "$1" =~ ^[A-Za-z0-9_.-]+$ ]] || { echo "bad key: $1" >&2; exit 2; }; }
log_line() { mkdir -p "$P"; printf '%s %s\n' "$(ts)" "$1" >> "$EVENTS"; }
sget() { awk -v k="$1" 'index($0, k ": ")==1 {sub("^" k ": ", ""); print; exit}' "$STATE"; }
sset() {
  local tmp; tmp=$(mktemp)
  awk -v k="$1" -v v="$2" 'BEGIN{done=0} index($0, k ": ")==1 {print k ": " v; done=1; next} {print} END{if(!done) print k ": " v}' "$STATE" > "$tmp" && mv "$tmp" "$STATE"
  log_line "set $1=$2"
}
has() { case " $1 " in *" $2 "*) return 0;; esac; return 1; }
exclude_pipeline() { # dir — add .pipeline/ to the local exclude file of the repo containing dir
  local ex
  [ -d "$1" ] && git -C "$1" rev-parse --git-dir >/dev/null 2>&1 || return 0
  ex=$(cd "$1" && git rev-parse --git-path info/exclude); case "$ex" in /*) ;; *) ex="$1/$ex";; esac
  mkdir -p "$(dirname "$ex")"
  grep -qxF '.pipeline/' "$ex" 2>/dev/null || { echo '.pipeline/' >> "$ex"; log_line "init: .pipeline/ added to $ex"; }
}

# ---- advance / check ---------------------------------------------------------------------------
BLOCKERS=()
block() { BLOCKERS+=("$1"); }
project_path() { local pd; pd=$(sget project_dir); [ -n "$pd" ] || return 1; case "$pd" in /*) printf '%s' "$pd";; *) printf '%s' "$ROOT/$pd";; esac; }
latest_review() { # stage → path of highest reviews/<stage>-vN.md (panel members and -gate files excluded)
  local best="" bn=-1 f n
  for f in "$P/reviews/$1"-v*.md; do
    [ -f "$f" ] || continue
    n=${f##*-v}; n=${n%.md}; [[ "$n" =~ ^[0-9]+$ ]] || continue
    [ "$n" -gt "$bn" ] && { bn=$n; best=$f; }
  done
  printf '%s' "$best"
}
review_ok() { # latest review must validate as APPROVE — from v2 on with --prev, like the orchestrator ran it
  local f v n prev="" stale args
  f=$(latest_review "$1")
  [ -n "$f" ] || { block "$1: no reviews/$1-vN.md — run the independent review"; return; }
  n=${f##*-v}; n=${n%.md}; args=("$f")
  if [ "$n" -ge 2 ]; then
    prev="$P/reviews/$1-v$((n-1))-gate.md"; [ -f "$prev" ] || prev="$P/reviews/$1-v$((n-1)).md"
    [ -f "$prev" ] || { block "$1: $(basename "$f") has no $1-v$((n-1))[-gate].md — its regression list cannot be checked"; return; }
    args+=(--prev "$prev")
  fi
  v=$(bash "$SELF_DIR/review-verdict.sh" "${args[@]}" 2>/dev/null | awk '{print $1}')
  [ "$v" = APPROVE ] || block "$1: latest review $(basename "$f") is ${v:-MALFORMED}, not APPROVE — reasons: review-verdict.sh ${prev:+--prev $(basename "$prev") }$(basename "$f")"
  # an artifact edited after the approving review was never reviewed
  stale=$( { find "$P/artifacts/$1" -type f -newer "$f" ! -path '*/evidence/*' ! -path '*/logs/*' ! -name verify.json 2>/dev/null
             [ "$1" = planning ] && find "$P/tasks.json" -newer "$f" 2>/dev/null
             [ "$1" = architecture ] && find "$P/decisions" -type f -newer "$f" 2>/dev/null; } | sed "s|^$P/||" | tr '\n' ' ' | sed 's/ $//')
  [ -z "$stale" ] || block "$1: edited after $(basename "$f") was written — re-review: $stale"
}
human_gate_ok() {
  local gates g
  gates=$(grep -E '^human_gates:' "$CONFIG" 2>/dev/null | sed 's/#.*//; s/.*\[//; s/\].*//' | tr ',' ' ')
  for g in $gates; do
    [ "$g" = "$1" ] || continue
    [ "$(sget "gates.$1")" = approved ] || block "$1: human gate is '$(sget "gates.$1")' — ask the user (ask_user_question), then set gates.$1"
  done
}
verify_ok() { # stage [required-step]
  local vj="$P/artifacts/$1/verify.json" proj sha head
  [ -f "$vj" ] || { block "$1: no artifacts/$1/verify.json — run verify-gate.sh --stage $1"; return; }
  grep -q '"passed":true' "$vj" || block "$1: verify.json passed=false — fix and re-run the gate"
  [ -z "${2:-}" ] || grep -q "{\"step\":\"$2\",\"status\":\"ok\"" "$vj" || block "$1: verify.json step '$2' is not ok"
  grep -q '"dirty":false' "$vj" || block "$1: gate ran on a dirty or non-git tree — commit, then re-run the gate"
  proj=$(project_path) || { block "project_dir not set — pipeline-state.sh set project_dir <dir>"; return; }
  sha=$(sed -n 's/.*"git_sha":"\([^"]*\)".*/\1/p' "$vj")
  head=$(git -C "$proj" rev-parse HEAD 2>/dev/null || true)
  [ -n "$sha" ] && [ "$sha" = "$head" ] || block "$1: verify.json is for commit '${sha:-none}', project HEAD is '${head:-none}' — re-run the gate on HEAD"
}
need_file() { [ -s "$P/$1" ] || block "$2: missing or empty .pipeline/$1"; }
check_stage() { # stage
  local s="$1" proj f
  has "$REVIEWED" "$s" && review_ok "$s"
  human_gate_ok "$s"
  case "$s" in
    env)
      need_file artifacts/env/env.md env; need_file constitution.md env
      if [ -f "$P/constitution.md" ]; then
        # any `- …:` line whose last label has no value (also "additional locales:" — write "none" if there are none)
        while IFS= read -r f; do block "env: constitution.md value left empty — '$f' (fill it; mark guesses '(assumed)')"; done \
          < <(grep -E '^- .*:[[:space:]]*$' "$P/constitution.md")
      fi;;
    idea) need_file artifacts/idea/idea.md idea;;
    planning) need_file artifacts/planning/prd.md planning; need_file tasks.json planning;;
    design)
      f="$P/artifacts/design/design-system.md"
      grep -qE '^style: (minimal-modern|playful-rounded|neo-brutalism|casual-game|dark-premium)[[:space:]]*$' "$f" 2>/dev/null \
        || block "design: design-system.md has no valid 'style:' line"
      grep -qE '^seed: #[0-9A-Fa-f]{6}[[:space:]]*$' "$f" 2>/dev/null || block "design: design-system.md has no 'seed: #RRGGBB' line";;
    architecture) need_file artifacts/architecture/architecture.md architecture; need_file decisions/DECISION-001.md architecture;;
    implementation)
      verify_ok implementation
      if [ -f "$P/tasks.json" ]; then
        grep -qE '"status"[[:space:]]*:[[:space:]]*"(pending|in_progress)"' "$P/tasks.json" \
          && block "implementation: tasks.json still has pending/in_progress tasks"
        grep -qE '"status"[[:space:]]*:[[:space:]]*"blocked"' "$P/tasks.json" \
          && echo "note: tasks.json has blocked tasks — they must have been escalated and must appear in notes.md §6" >&2
      fi;;
    test) verify_ok test test;;
    qa) verify_ok test test; need_file artifacts/qa/evidence/index.json qa;;
    release)
      verify_ok release
      grep -q '"release":true' "$P/artifacts/release/verify.json" 2>/dev/null || block "release: verify.json was not produced with --release"
      need_file artifacts/release/notes.md release
      if grep -qE '^ios_release:[[:space:]]*true' "$CONFIG" 2>/dev/null; then
        if [ "$(sget fallbacks.flutter-ios-release)" = inline ]; then
          echo "note: ios_release with flutter-ios-release inline — the iOS kit is unverified by script; say so in notes.md §2/§6" >&2
        else
          grep -q '{"step":"ios_kit","status":"ok"' "$P/artifacts/release/verify.json" 2>/dev/null \
            || block "release: ios_release is on but verify.json has no ok 'ios_kit' step — verify-gate --check ios_kit='python3 <flutter-ios-release>/scripts/ios_prep_check.py --project .'"
        fi
      fi
      proj=$(project_path) && { git -C "$proj" tag --points-at HEAD 2>/dev/null | grep -q '^v' \
        || block "release: no v<version> tag on HEAD — tag after the human gate approves"; };;
  esac
}

case "$CMD" in
  init)
    mkdir -p "$P"/{artifacts,reviews,bugfix,decisions,skills}
    for s in env idea planning design architecture implementation test qa release; do mkdir -p "$P/artifacts/$s"; done
    [ -f "$CONFIG" ] || cat > "$CONFIG" <<'EOF'
human_gates: [idea, planning, release]   # pause + ask user after these reviews pass
max_revisions: 3                         # per stage; then ESCALATE
max_bugfix_cycles: 8                     # QA REVISE → fix → test → re-QA loops
parallel_implementation: false           # true → disjoint tasks via parallel subagents (git worktrees)
reviewer_backend: subagent               # subagent | opencode | herdr
review_timeout_min: 15                   # async backends: no report by then → retry once → subagent
panel_stages: [qa]                       # multi-lens panel stages (references/reviewer-prompt.md)
release_build: apk                       # apk | appbundle | web | none
store_bound: false                       # true → QA also runs flutter-store-compliance
ios_release: true                        # App Store-ready iOS kit (flutter-ios-release); the IPA is built later on macOS
EOF
    [ -f "$P/constitution.md" ] || cat > "$P/constitution.md" <<'EOF'
# Constitution

Project rules that outrank every later decision, task and skill.
Filled at the env stage: derive from the repo and the user's request; a value
you had to guess ends with "(assumed)". `advance` refuses an empty field.

- Language of pipeline artifacts (idea, PRD, reviews, notes):
- App UI language: English (default, `app_en.arb`, first in supportedLocales) — additional locales (or "none"):
- Git commit messages and code identifiers: English
- Target platforms / min OS:
- Non-negotiables (privacy, offline-first, no paid packages, ...):
- Definition of "done" for a feature:
EOF
    if [ -f "$STATE" ]; then
      echo "exists: $STATE (not overwritten)"; log_line "init: re-run, state kept"
      [ -n "$PROJECT" ] && [ -z "$(sget project_dir)" ] && sset project_dir "$PROJECT"
    else
      { echo "status: running"; echo "stage: env"; echo "bugfix_cycles: 0"; echo "reviewer_backend: subagent"
        echo "started_at: $(ts)"; [ -n "$PROJECT" ] && echo "project_dir: $PROJECT"; } > "$STATE"
      log_line "init: workspace created${PROJECT:+ project_dir=$PROJECT}"
      echo "created: $P"
    fi
    exclude_pipeline "$ROOT"
    PD=$(project_path 2>/dev/null) && exclude_pipeline "$PD"
    ;;
  status)
    need_state
    echo "== $STATE"; cat "$STATE"
    echo; echo "== last events"; tail -n 10 "$EVENTS" 2>/dev/null || echo "(none)"
    ;;
  get)
    need_state; K="${ARGS[1]:-}"; [ -n "$K" ] || { echo "usage: get <key>" >&2; exit 2; }; valid_key "$K"
    V=$(sget "$K"); printf '%s\n' "$V"; [ -n "$V" ]
    ;;
  set)
    need_state; K="${ARGS[1]:-}"; V="${ARGS[2]:-}"
    [ -n "$K" ] && [ ${#ARGS[@]} -ge 3 ] || { echo "usage: set <key> <value>" >&2; exit 2; }; valid_key "$K"
    [ "$K" = stage ] && [ "$(sget stage)" != "$V" ] && echo "warning: use 'advance' to change stage — 'set stage' skips every gate (logged)" >&2
    sset "$K" "$V"; echo "$K: $V"
    ;;
  bump)
    need_state; K="${ARGS[1]:-}"; [ -n "$K" ] || { echo "usage: bump <key>" >&2; exit 2; }; valid_key "$K"
    CUR=$(sget "$K"); [[ "$CUR" =~ ^[0-9]+$ ]] || CUR=0
    sset "$K" "$((CUR + 1))"; echo "$K: $((CUR + 1))"
    ;;
  log)
    M="${ARGS[*]:1}"; [ -n "$M" ] || { echo "usage: log <message>" >&2; exit 2; }
    log_line "$M"; echo "logged"
    ;;
  check|advance)
    need_state; CUR=$(sget stage)
    has "$STAGES" "$CUR" && [ "$CUR" != done ] || { echo "stage '$CUR' cannot be advanced" >&2; exit 2; }
    NEXT=$(printf '%s\n' $STAGES | awk -v c="$CUR" 'f {print; exit} $0 == c {f=1}')
    check_stage "$CUR"
    if [ ${#BLOCKERS[@]} -gt 0 ]; then
      printf 'BLOCKED: %s\n' "${BLOCKERS[@]}" >&2
      if [ "$CMD" = check ] || [ -z "$OVERRIDE" ]; then
        [ "$CMD" = advance ] && log_line "advance $CUR→$NEXT refused: ${#BLOCKERS[@]} blocker(s)"
        exit 1
      fi
      log_line "OVERRIDE advance $CUR→$NEXT — reason: $OVERRIDE — bypassed: $(IFS=';'; echo "${BLOCKERS[*]}")"
      sset "override.$CUR" "$OVERRIDE"
    fi
    if [ "$CMD" = check ]; then echo "ready: $CUR → $NEXT"; exit 0; fi
    sset stage "$NEXT"
    if [ "$NEXT" = done ]; then sset status done; sset finished_at "$(ts)"; else sset status running; fi
    log_line "advance $CUR→$NEXT"; echo "stage: $NEXT"
    ;;
  *) echo "unknown command: $CMD" >&2; usage;;
esac
