---
name: flutter-factory
description: >-
  Self-contained, review-gated Flutter build pipeline with no external
  orchestrator: idea → review → plan → review → design → review →
  architecture → review → implementation → test → QA → release. The agent
  executes every stage itself, spawns fresh-context subagents as independent
  reviewers (APPROVE | REVISE | BLOCK | ESCALATE), pauses at human gates,
  gates every transition on real `flutter analyze / test / build` exit codes,
  and discovers sibling skills by name and description. Use when asked to
  "build a Flutter app end to end with reviews", "run the full pipeline",
  "idea to release with reviews", "flutter factory", "chạy pipeline có
  review", "build app từ idea đến release có kiểm duyệt". Don't use for
  Web+Android+iOS builds without review gates (flutter-all-platform), Play
  Store publishing pipelines (idea-to-play-store), driving the external
  AIFactory tool (ai-factory), or non-Flutter stacks.
license: MIT
effort: max
capabilities:
  - orchestration
  - workflow
  - review-gates
  - skill-discovery
  - flutter
metadata:
  version: 2.1.0
  author: "Nguyen Van Lam"
permissions:
  filesystem: { read: true, write: true }
  shell: { enabled: true }
  network: { enabled: true }   # pub get, optional opencode reviewer backend
  secrets: { required: false }
---

# flutter-factory — self-contained review-gated Flutter pipeline

No external tool required. The agent IS the orchestrator: it produces each
stage's artifacts, spawns an independent reviewer per gate, loops on
feedback, verifies with real Flutter commands, and asks the user at human
gates via `ask_user_question`. All state lives in `.pipeline/` so an
interrupted run resumes exactly where it stopped.

## Core principle

> **A generator never reviews its own output, and a stage never advances on
> a claim.** Every review is done by a reviewer that has not seen the
> drafting reasoning; every "green" is a command that ran in this session
> and exited 0. Missing sibling skills lower the ceiling — they never stop
> the run.

Three consequences:

- **Reviewer independence** — the reviewer receives artifact paths, the
  constitution, decisions, the stage checklist and (from v2) the previous
  Findings table. Never the draft discussion, never previous attempts'
  reasoning. Reports are machine-validated before they count.
- **Verified transitions** — `scripts/verify-gate.sh` (pub get → analyze →
  test → optional build) must pass before `test`, `qa` and `release`
  advance. A step the environment cannot run is `skipped_env`, reported as
  ⚠️ — never ✅, never a failure.
- **`.pipeline/` tells the whole story** — every verdict, gate answer, skill
  fallback and decision is on disk. Someone reading only that folder can
  reconstruct the run.

## When to use which orchestrator

| You want | Use |
|----------|-----|
| Independent reviews between stages, human gates, resumable state | **flutter-factory** |
| Web + Android + iOS project fast, no review loop | `flutter-all-platform` |
| End at a Google Play upload with store assets + compliance | `idea-to-play-store` |
| Drive the AIFactory/Herdr product | `ai-factory` |

flutter-factory ends at a **tagged, build-verified release commit**. Store
metadata, signing for upload and publishing are handed to the flutter-*
store skills in the release notes' "Next steps", not run here.

## Workspace

On start, run `bash <skill-dir>/scripts/pipeline-state.sh init [--project <dir>]`
(idempotent — never overwrites an existing `state.yaml`):

```
.pipeline/
  config.yaml          # human_gates, max_revisions, … (defaults below)
  constitution.md      # project rules — ask the user or derive from the repo
  state.yaml           # resume point — ALWAYS read first if it exists
  events.log           # append-only: every transition, verdict, fallback
  artifacts/<stage>/   # stage outputs (+ verify.json where a gate ran)
  reviews/             # <stage>-vN.md review reports
  bugfix/              # fix-NNN.md — one file per bugfix cycle
  decisions/           # DECISION-NNN.md — binding choices made mid-run
  tasks.json           # implementation task list (references/tasks-schema.md)
  skills/<id>/SKILL.md # optional project-local skills (highest priority)
```

Default `config.yaml`:

```yaml
human_gates: [idea, planning, release]   # pause + ask user after these reviews pass
max_revisions: 3                         # per stage; then ESCALATE
max_bugfix_cycles: 8                     # QA REVISE → fix → test → re-QA loops
parallel_implementation: false           # true → disjoint tasks via parallel subagents
reviewer_backend: subagent               # subagent | opencode | herdr
review_timeout_min: 15                   # async backends: no report file by then → retry once → subagent
panel_stages: [qa]                       # stages reviewed by a multi-lens panel (see reviewer-prompt.md)
release_build: apk                       # apk | appbundle | web | none — built by verify-gate at release
store_bound: false                       # true → QA also runs flutter-store-compliance
```

`state.yaml` (flat, dotted keys — written only through the script):

```yaml
status: running          # running | waiting_user | blocked | done
stage: planning          # stage currently in progress
project_dir: ./spendly   # Flutter project root (set at implementation)
revisions.planning: 1
bugfix_cycles: 0
gates.idea: approved
fallbacks.idea-validator: inline   # skill missing → done natively
reviewer_backend: subagent         # effective backend after fallback
```

```bash
bash scripts/pipeline-state.sh status                 # print state + last 10 events
bash scripts/pipeline-state.sh set stage design       # update a key
bash scripts/pipeline-state.sh bump revisions.design  # +1
bash scripts/pipeline-state.sh log "design-v2 REVISE: 3 findings"
```

Resume rule: if `state.yaml` exists, read it and continue from `stage`.
Never restart a finished stage; never delete `.pipeline/` or the project
directory without a fresh, explicit yes.

## Pipeline

Track stages with `todo_write`. For each stage: **discover skills → produce
artifacts → verify gate (where listed) → review → human gate (if listed) →
advance**.

| # | Stage | Produces | Verify gate | Reviewer checks | Preferred skills |
|---|-------|----------|-------------|-----------------|------------------|
| 0 | `env` | `artifacts/env/env.md` | `flutter doctor -v` | — | — |
| 1 | `idea` | `artifacts/idea/idea.md` (+ `validate.md`) | — | scope clarity, feasibility, market fit, MVP ≤ 6 features | `idea-validator` |
| 2 | `planning` | `artifacts/planning/prd.md`, `tasks.json` | — | PRD covers the idea; tasks ordered, measurable, each with `verify` | `prd-generator`, `tasks-generator` |
| 3 | `design` | `artifacts/design/{ux,ui,design-system,states}.md` | — | usability, consistency, tokens, loading/error/empty per screen, a11y | `dont-make-me-think`, `frontend-design`, `logo-designer` |
| 4 | `architecture` | `artifacts/architecture/{architecture,folder-structure,coding-rules}.md`, `DECISION-001.md` (org, stack) | — | decisions vs PRD/constitution, dependency table, feasibility | `tad-generator` |
| 5 | `implementation` | Flutter project at `project_dir` | `verify-gate --no-test` after **every** task | — (reviewed by QA) | `flutter-init` (task 1), `firebase-auth-setup`, `frontend-design`, matched per task |
| 6 | `test` | `test/`, `artifacts/test/report.md` | `verify-gate` (analyze + test) | tests green, edge cases, primary flow covered | `test-coverage` |
| 7 | `qa` | `reviews/qa-vN.md` | — | bugs, security, performance, clean code, secrets scan | `code-review`; + `flutter-store-compliance` when `store_bound` |
| 8 | `release` | tag, `artifacts/release/notes.md`, `verify.json` | `verify-gate --build <release_build> --release` | — | `release-manager`, `auto-push` |

### Stage notes

**env** — record Flutter/Dart version, Android SDK, JDK, Chrome, OS. This
decides which `release_build` values are even possible; if the user's
choice is impossible here, ask before continuing.

**idea** — one sentence from the user is enough. Fill gaps with
assumptions and list them in `idea.md` under `## Assumptions`. Do not ask
the user to complete a brief.

**planning** — `tasks.json` follows `references/tasks-schema.md`. Task 1 is
always the scaffold (`flutter-init` or inline `flutter create`). Every task
has a `verify` command; a task without one is a planning REVISE finding.

**architecture** — this is where **`org`** (reverse-domain, e.g. `com.acme`)
is asked via `ask_user_question` and recorded as `DECISION-001.md`. No
default, ever: `flutter-init`, `flutter-build` and `flutter-publish` all
block `com.example.*`. Also fix: state management, routing, persistence,
minSdk/targetSdk, and the dependency table (package · why · what breaks
without it).

**implementation** — execute `tasks.json` in order. After each task:
`verify-gate --no-test` must be `ok`, then `git commit` with the task id in
the message, then `pipeline-state.sh set task.<id> done`. If
`parallel_implementation: true`, delegate tasks whose `files` sets are
disjoint to parallel `subagent_general` agents — each receives
constitution + architecture + decisions + its task only, commits on its
own branch `task/<id>`, and the orchestrator merges in task order and
re-runs the gate after each merge.

**test** — write tests yourself first (unit: models/validators/repos;
widget: each design-system component + each form + loading/error/empty;
integration: the primary flow), then invoke `test-coverage` to fill gaps.
Red → fix the cause, not the assertion; 3 rounds per failing test, then a
recorded blocker.

**qa** — the QA reviewer reads the code, `artifacts/test/report.md` and the
`verify.json`. Findings are numbered (`F-01`, `F-02`, …) with severity —
the bugfix loop depends on that numbering.

**release** — `verify-gate --build <release_build> --release` must be `ok`
(it also blocks on `com.example`, leaked secrets and a red test suite).
Then bump version in `pubspec.yaml`, write `notes.md` from
`references/report-template.md`, commit, tag `v<version>`. Push only if the
user says so (`auto-push` / `release-manager` if present). "Next steps"
lists `flutter-signing → flutter-build → flutter-store-metadata →
flutter-store-compliance → flutter-publish`.

## Review loop

Each review is run by an independent reviewer built from
`references/reviewer-prompt.md` with the stage checklist from
`references/review-checklists.md`. The reviewer receives only:

- the stage artifact paths (and, for `qa`, the project dir + latest `verify.json`)
- `constitution.md` + `decisions/*.md`
- approved upstream artifacts as **context, not subject** — a defect there
  → ESCALATE, never a REVISE of this stage
- for revision v ≥ 2: the previous revision's **Findings table only**, as a
  regression list (each `F-nn` must come back `resolved` / `unresolved`)
- the checklist for that stage; `[E]` lines pass only with quoted evidence

Never: the drafting reasoning, chat history, earlier reviews' Summary/Nits,
or anything in `bugfix/`. Independence = no shared reasoning, not no shared
facts.

Every backend has the same contract: the reviewer writes
`reviews/<stage>-vN.md` starting with a verdict line and numbered
findings (ids continue across revisions — v1 ends at F-05, v2 starts at
F-06), then returns a completion signal. **The file is the durable
callback**; validate it, never parse it by hand:

```bash
bash scripts/review-verdict.sh .pipeline/reviews/<stage>-vN.md
# stdout: REVISE critical=0 major=2 minor=1 findings=3 regression_unresolved=1   (exit 0)
# exit 1: MALFORMED: <reason>  → re-run the reviewer once quoting the reason; twice → ESCALATE
```

Waiting: `review_timeout_min` (default 15) bounds `opencode` / `herdr`
reviewers (`timeout`, `wait`). No file after the limit → re-run once →
still nothing → fall back to `subagent` for the rest of the run and log it.

**Panel review** — for stages in `panel_stages` (default `[qa]`), spawn
one reviewer per lens in parallel (`qa`: `security` + `correctness`; see
`reviewer-prompt.md` for the other stages), each writing
`<stage>-vN-<lens>.md`. Merge into `<stage>-vN.md`: strictest verdict,
union of findings de-duplicated and re-numbered, a regression item is
`resolved` only if every member agrees. Lens diversity is the cheap
substitute for model diversity when the backend is `subagent`.

Handling (of the validated, merged file):

- **APPROVE** → `set gates.<stage> approved`, log, advance (via human gate if listed)
- **REVISE** → redo the stage with the Findings table as the requirements
  list, `bump revisions.<stage>`, re-review with that table as
  `previous_findings`. After `max_revisions` failed cycles → treat as
  ESCALATE.
  Exception — at `qa`, REVISE starts a **bugfix cycle** (QA produces no
  code): write `bugfix/fix-NNN.md` mapping each `F-nn` → change, fix the
  code, re-run the `test` gate (must be `ok`), then re-review QA. Each loop
  `bump bugfix_cycles`; exceeding `max_bugfix_cycles` → ESCALATE.
- **BLOCK** → `set status blocked`, write `artifacts/<stage>/BLOCKED.md`
  with the reviewer's reason, stop.
- **ESCALATE** → `set status waiting_user`, ask the user (see human gates).

### Reviewer backends (`reviewer_backend`)

| Backend | How | Result delivery | Model diversity |
|---|---|---|---|
| `subagent` (default) | `run_subagent` profile `subagent_explore` (read-only), foreground | synchronous | none — same model as the session |
| `opencode` | `opencode run "<review prompt>"`; set up via the `opencode-runner` skill | stdout when the command exits | yes — free cloud models |
| `herdr` | spawn a pane via the `herdr-agent` skill, send the prompt, `wait` + capture | async — orchestrator waits + captures | yes — whatever the pane runs |

If the backend is not `subagent`, check it exists first (`command -v
opencode`, herdr CLI/socket). Missing → fall back to `subagent`, `set
reviewer_backend subagent`, log the fallback. Reviewer rules are identical
across backends — only the transport differs.

## Human gates

For each stage in `human_gates`, after its review approves, `set status
waiting_user` and call `ask_user_question`. The question text carries the
reviewer's Summary, the Nits count and the artifact paths — the user judges
the artifact, not the chat. Options: **approve** (continue) / **reject**
(revision loop with the user's note as the only finding, id continuing the
sequence) / **stop**. Record the answer as
`gates.<stage>: approved|rejected|stopped`. `human_gates: []` = fully
autonomous.

## Skill discovery

Discover, don't assume — and **never decide a skill is absent by probing
filesystem paths** (except `.pipeline/skills/`, which only this pipeline
knows about). Before each stage:

1. **By name** — for every entry in the stage's *Preferred skills* column,
   try the `skill` tool (`invoke`, or `search` with the name as keyword).
   Found → use it.
2. **By capability** — if a preferred skill is missing, `skill search` with
   the stage's capability keywords (e.g. `prd`, `requirements`; `test`,
   `coverage`; `review`, `security`). Also `skill search --path .pipeline`
   for project-local skills, which win over anything else.
3. **Tie-break** — several candidates: prefer one whose frontmatter
   `capabilities` contains the keyword exactly, then project-local >
   workspace > user, then name. (Only some skills declare `capabilities`;
   it is a tie-breaker, never a filter.)
4. **Fallback** — nothing found → do the work inline with the agent's
   native ability and `set fallbacks.<skill> inline`. A preferred skill
   prefixed `!` in `config.yaml` is critical: missing → BLOCK instead of
   faking success.

Read `references/sibling-contracts.md` before invoking a sibling — it
lists the inputs each one really needs and the traps (planning skills'
`git pull --rebase`, `flutter-init` `org`, `flutter-build` signing) that
otherwise stop a run mid-stage.

## Rules

1. Constitution > approved architecture > decisions > task > skills. A
   skill never silently overrides a project decision — record a
   `DECISION-NNN.md` when a choice binds future stages.
2. Reviewer independence: artifacts + context docs only — never the draft
   reasoning or previous attempts' discussion. Same model is acceptable;
   same context is not.
3. ✅ only for a command that ran and exited 0 now. Environment limits are
   `skipped_env`, reported separately from project failures.
4. `org` is asked, never defaulted; secrets never in source (`verify-gate`
   greps for them at release).
5. Every verdict, gate answer, fallback and decision goes through
   `pipeline-state.sh` — the `.pipeline/` dir must tell the whole story.
6. Keep going end to end: stop only on BLOCK, a rejected/stopped gate,
   exhausted revisions or bugfix cycles, or explicit user interrupt.
7. Smallest architecture that stays testable — no `domain/` layers, DI
   containers or use-cases the PRD cannot justify.

## Definition of done

```
.pipeline/
  state.yaml            status: done, every gates.<stage>: approved
  reviews/              one APPROVE per gated stage, qa-vN APPROVE last
  artifacts/release/    notes.md + verify.json (analyze ok · test ok · build ok|skipped_env)
<project_dir>/
  lib/ test/            flutter analyze clean, flutter test green
  pubspec.yaml          version bumped, git tag v<version> on the release commit
  android/app/build.gradle*   applicationId = <org>.<slug>, not com.example
```

## Reference files

| File | Read when |
|------|-----------|
| `references/review-checklists.md` | Building any reviewer prompt — per-stage checklist + severity scale |
| `references/reviewer-prompt.md` | Spawning a reviewer — prompt template, regression list, panel lenses, report format, timeout/fallback |
| `references/tasks-schema.md` | Planning — `tasks.json` schema, parallel-safety rules, example |
| `references/sibling-contracts.md` | Before invoking a sibling skill — inputs, outputs, traps |
| `references/report-template.md` | Release — `notes.md` skeleton, filled from `verify.json` + state |

| Script | Run at |
|--------|--------|
| `scripts/pipeline-state.sh` | Every transition — `init · status · get · set · bump · log` |
| `scripts/verify-gate.sh` | implementation (per task, `--no-test`), test, release (`--build … --release`) — writes `verify.json`, exit 1 on any `fail` |
| `scripts/review-verdict.sh` | After every review — validates the report file, prints verdict + severity counts, exit 1 = malformed (re-run reviewer) |

## Scope

Does: orchestrate idea → release with independent reviews, human gates,
resumable state, and build-verified transitions for a Flutter project.

Does not: sign for upload, generate store assets, check store policy
(unless `store_bound`), or publish — hand off to `flutter-signing`,
`flutter-build`, `flutter-store-metadata`, `flutter-store-compliance`,
`flutter-publish`. Does not install Flutter (that is `flutter-init`'s job
inside task 1) or claim an iOS build off macOS.
