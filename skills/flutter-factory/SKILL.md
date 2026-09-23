---
name: flutter-factory
description: >-
  Self-contained, review-gated Flutter build pipeline with no external
  orchestrator: idea → review → plan → review → design → review →
  architecture → review → implementation → test → QA → release, plus an App
  Store-ready iOS kit (IPA built later on a Mac). The agent executes every
  stage itself, spawns fresh-context subagents as independent reviewers
  (APPROVE | REVISE | BLOCK | ESCALATE), pauses at human gates, gates every
  transition on real `flutter analyze / test / build` exit codes, and
  discovers sibling skills by name and description. Use when asked to
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
  version: 2.6.1
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

Four consequences:

- **Reviewer independence** — the reviewer receives artifact paths, the
  constitution, decisions, the stage checklist and (from v2) the previous
  Findings table. Never the draft discussion, never previous attempts'
  reasoning. Reports are machine-validated before they count.
- **Verified transitions** — `scripts/verify-gate.sh` (pub get → analyze →
  test → optional build) must pass before `implementation`, `test`, `qa`
  and `release` advance, on a clean tree at the commit being advanced
  (`verify.json` records `git_sha` + `dirty`). A step the environment
  cannot run is `skipped_env`, reported as ⚠️ — never ✅, never a failure.
- **Transitions are enforced, not narrated** — the stage only changes via
  `pipeline-state.sh advance`, which re-validates the latest review file,
  the human gate and `verify.json` and refuses (exit 1) while anything is
  missing. `pipeline-state.sh check` lists the blockers without moving.
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

flutter-factory ends at a **tagged, build-verified release commit** that
(with `ios_release`) also carries an App Store-ready iOS kit — the IPA
itself is built later on a Mac. Store metadata, signing for upload and
publishing are handed off in the release notes' "Next steps".

## Workspace

On start, run `bash <skill-dir>/scripts/pipeline-state.sh init [--project <dir>]`
(idempotent — never overwrites an existing `state.yaml`):

```
.pipeline/
  config.yaml          # human_gates, max_revisions, … (defaults below)
  constitution.md      # project rules — filled at the env stage (derive, mark guesses "(assumed)")
  state.yaml           # resume point — ALWAYS read first if it exists
  events.log           # append-only: every transition, verdict, fallback
  artifacts/<stage>/   # stage outputs (+ verify.json where a gate ran)
  reviews/             # <stage>-vN.md review reports (+ -<lens>.md panel members, -gate.md human rejections)
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
ios_release: true                        # App Store-ready iOS kit (flutter-ios-release); IPA built later on macOS
```

`state.yaml` is flat, dotted keys, written only through the script:
`status` (running | waiting_user | blocked | done) · `stage` (changed ONLY
by `advance`) · `project_dir` (set after T01) · `revisions.<stage>` ·
`bugfix_cycles` · `review.<stage>` (informational — `advance` re-reads the
file) · `gates.<stage>` (approved | rejected | stopped) ·
`fallbacks.<skill>: inline` · `reviewer_backend` (effective) · `task.<id>`.

```bash
bash scripts/pipeline-state.sh status                 # print state + last 10 events
bash scripts/pipeline-state.sh check                  # what still blocks leaving the current stage
bash scripts/pipeline-state.sh advance                # move to the next stage — refused while check fails
bash scripts/pipeline-state.sh bump revisions.design  # +1
bash scripts/pipeline-state.sh log "design-v2 REVISE: 3 findings"
```

`advance` requires, for the stage being left: the latest
`reviews/<stage>-vN.md` validating as APPROVE (idea, planning, design,
architecture, test, qa — from v2 with `--prev <stage>-v(N-1)[-gate].md`)
and no stage artifact edited after it · `gates.<stage>: approved` when the stage is in
`human_gates` · a passing `verify.json` for a clean tree at the project's
current HEAD (implementation, test, qa — the test gate re-run after the
last bugfix — and release) · the stage's key artifacts (filled
constitution + `env.md`; `idea.md`; `prd.md` + `tasks.json`; valid
`style:`/`seed:` lines; `architecture.md` + `DECISION-001.md`; no
pending task; QA `evidence/index.json`; release notes + `v*` tag on HEAD
+ an `ok` `ios_kit` step when `ios_release`).
`--override "<reason>"` exists **only** for an explicit user instruction;
it is logged as `OVERRIDE` and listed in the release report.

Resume rule: if `state.yaml` exists, run `status` then `check`, continue
from `stage`, never restart a finished stage, never delete `.pipeline/` or
the project without a fresh, explicit yes. Near the context limit, put the
current step's result on disk and resume from `.pipeline/`, not memory.

### Git layout

- The project's repo is the **only** repo committed to; `.pipeline/` never
  enters it (`init` puts it in `.git/info/exclude` — **re-run `init
  --project <dir>` right after T01** so the new repo gets it too).
- Fresh run: project at `./<slug>`, created with its repo by T01. Existing
  Flutter repo: `project_dir: .`. Workspace already inside a repo: no
  nested `git init` (tell `flutter-init` / `flutter create`).
- Gates run on committed code: commit, then `verify-gate` — `advance`
  rejects a `verify.json` whose `git_sha` is not HEAD or whose tree was dirty.

## Pipeline

Track stages with `todo_write`. For each stage: **discover skills → produce
artifacts → commit (code stages) → verify gate (where listed) → review →
human gate (if listed) → `pipeline-state.sh advance`**. If `advance`
refuses, fix what it lists — never `set stage` by hand.

| # | Stage | Produces | Verify gate | Reviewer checks | Preferred skills |
|---|-------|----------|-------------|-----------------|------------------|
| 0 | `env` | `artifacts/env/env.md`, filled `constitution.md` | `flutter doctor -v` | — | — |
| 1 | `idea` | `artifacts/idea/idea.md` (+ `validate.md`) | — | scope clarity, feasibility, market fit, MVP ≤ 6 features | `idea-validator` |
| 2 | `planning` | `artifacts/planning/prd.md`, `tasks.json` | — | PRD covers the idea; tasks ordered, measurable, each with `verify` | `prd-generator`, `tasks-generator` |
| 3 | `design` | `artifacts/design/{ux,ui,design-system,states}.md` | — | usability, consistency, tokens, loading/error/empty per screen, a11y | generate: `frontend-design`, `logo-designer` · evidence for review: `dont-make-me-think` |
| 4 | `architecture` | `artifacts/architecture/{architecture,folder-structure,coding-rules}.md`, `DECISION-001.md` (org, stack) | — | decisions vs PRD/constitution, dependency table, feasibility | `tad-generator` |
| 5 | `implementation` | Flutter project at `project_dir` | `verify-gate --no-test` after **every** task, and once more on the final commit | — (reviewed by QA) | `flutter-init` (task 1), `firebase-auth-setup`, `frontend-design`, matched per task, `flutter-ui-revamp` (last screen task), `flutter-ios-release` (last task when `ios_release`) |
| 6 | `test` | `test/`, `artifacts/test/report.md` | `verify-gate --coverage [--min-coverage <PRD target>]` (analyze + test + counts + coverage) | tests green, edge cases, primary flow covered | `test-coverage` |
| 7 | `qa` | `artifacts/qa/evidence/`, `reviews/qa-vN.md` | `evidence-pack.sh` | bugs, security, performance, clean code, secrets scan | evidence for review: `code-review` (`mode:review`), + `flutter-store-compliance` when `store_bound`, + `appstore-review-checker` / `ios_prep_check.py` when `ios_release` |
| 8 | `release` | release commit, `artifacts/release/notes.md`, `verify.json`, tag | `verify-gate --build <release_build> --release [--check ios_kit=…]` on the release commit | — | `release-manager`, `auto-push` |

### Stage notes

**env** — record Flutter/Dart version, Android SDK, JDK, Chrome, Xcode
(if any), OS. This decides which `release_build` values are possible; if
the user's choice is impossible here, ask. Then fill `constitution.md` —
its only moment; reviewers treat a contradiction with it as `critical`.
Derive each field from the request, the repo (`README`, `AGENTS.md`,
`analysis_options.yaml`, `pubspec.yaml`) and `env.md`; mark guesses
`(assumed)`. Ask only if a stated rule conflicts with rules 8–9.

**idea** — one sentence from the user is enough. Fill gaps with
assumptions and list them in `idea.md` under `## Assumptions`. Do not ask
the user to complete a brief. The app's UI language is always an
assumption you state, never ask: "English (default); additional locales:
<none | list from the idea>" (rule 9).

**planning** — `tasks.json` follows `references/tasks-schema.md`. Task 1 is
always the scaffold (`flutter-init` or inline `flutter create`, with `ios`
when `ios_release`); UI polish (`flutter-ui-revamp`) follows every screen
task (rule 9); with `ios_release` the iOS kit is the very last task (rule
10). Every task has a `verify`; a task without one is a REVISE finding.

**design** — `design-system.md` must open with two machine-readable
lines, `style: <minimal-modern | playful-rounded | neo-brutalism |
casual-game | dark-premium>` and `seed: #RRGGBB` — the exact inputs
`flutter-ui-revamp` takes at the last implementation task, so it never
has to ask the user again. Pick the recipe from
`flutter-ui-revamp/references/style-recipes.md` when that skill is
installed; otherwise name the closest one.

**architecture** — this is where **`org`** (reverse-domain, e.g. `com.acme`)
is asked via `ask_user_question` and recorded as `DECISION-001.md`. No
default, ever: `flutter-init`, `flutter-build` and `flutter-publish` all
block `com.example.*`. Also fix: state management, routing, persistence,
minSdk/targetSdk, localisation (`gen-l10n`, `app_en.arb` first, extra
locales per PRD — rule 9), and the dependency table (package · why · what
breaks without it). With `ios_release`, one iOS `DECISION-*`: bundle id
(default = `applicationId`), Apple team id (ask once; "at build time" is
fine), device family (iPhone-only unless the PRD needs iPad), deployment
target, encryption exemption.

**implementation** — execute `tasks.json` in order. Right after T01,
re-run `pipeline-state.sh init --project <dir>` (records `project_dir`,
excludes `.pipeline/` from the new repo — see Git layout). After each task
run the *implementation — per task (self)* checklist in
`review-checklists.md`: `verify-gate --no-test` `ok`, `task.verify` green,
diff inside `files`, no new dependency without a table row, then `git
commit` with the task id in the message (`feat(<feature>): <title> [<id>]`,
**in English** — see rule 8), `pipeline-state.sh set task.<id> done`, and
one line in `artifacts/implementation/tasks-log.md`. After the last task
(and its merge) run `verify-gate --no-test --stage implementation` once
more on the committed tree — that is the `verify.json` `advance` checks.

The UI-polish task (`flutter-ui-revamp`) stops for the user four times
unless its prompt pre-answers them, adds packages that need
dependency-table rows, and lands as a merge commit — follow schema rule 9
and its contract row exactly. The iOS kit task (rule 10) prepares
`ios/` + `ios-release/` on any OS and never claims an IPA.

If `parallel_implementation: true`, delegate tasks whose `files` sets are
disjoint to parallel `subagent_general` agents, **one git worktree per
task**, merged by the orchestrator in id order with `verify-gate
--no-test` after each merge — procedure in `tasks-schema.md` →
Orchestrator loop.

**test** — write tests yourself first (unit: models/validators/repos;
widget: each design-system component + each form + loading/error/empty;
flow: the primary flow from `ux.md` as a **widget-level flow test in
`test/flows/`** that pumps the app with fakes — it runs headless, so the
gate actually executes it), then invoke `test-coverage` to fill gaps.
`integration_test/` on a device is optional; without
`--integration-device` the gate reports it `skipped_env`. Red → fix the
cause, not the assertion; 3 rounds per failing test, then a recorded
blocker. Commit the tests, then run `verify-gate --stage test --coverage`
(add `--min-coverage <n>` with the PRD target) — `verify.json` then
carries the pass/skip/fail counts and the coverage figure the reviewer
and the report quote.

**qa** — reviewers are read-only and cannot invoke skills, so the
orchestrator builds an **evidence pack** first: `bash scripts/evidence-pack.sh
--project <dir> --stage qa` (analyze, pub outdated, deps, secrets, manifest,
gradle, risky Dart patterns → `artifacts/qa/evidence/`), then, if installed,
`code-review mode:review` (writes `<project>/CODE_REVIEW.md` — **move** it to
`evidence/code-review-report.md`) and, when `store_bound`,
`flutter-store-compliance` (copy `store-metadata/compliance-report.json` →
`evidence/compliance-report.json`, commit `store-metadata/`, then re-run
`verify-gate --stage test --coverage` — the commit moved HEAD). With
`ios_release`: `ios_prep_check.py --out evidence/ios-prep.json` and
`appstore-review-checker` (report only) → `evidence/appstore-review.md`.
The reviewer gets the evidence dir plus the skills' methodology files
(`code-review/references/review-mode.md`, `code-smells.md`) and reads the
code, `artifacts/test/report.md` and `verify.json`. Skill reports are inputs
to `[E]` checklist lines, never verdicts to copy. Findings are numbered
(`F-01`, `F-02`, …) with severity — the bugfix loop depends on that numbering.
Same pattern for `design`: run `dont-make-me-think` on `ux.md`/`ui.md` →
`evidence/dmmt-report.md`, pass `krug-principles.md` as methodology.

**release** — the build that gets verified is the commit that gets
tagged, so the order is fixed:

1. Bump `version:` in `pubspec.yaml` (+ project `CHANGELOG.md` if any),
   commit `chore(release): v<version>` (English).
2. `verify-gate --build <release_build> --release --stage release` on that
   clean commit — must be `ok` (it also blocks on `com.example`, leaked
   secrets and a red test suite); with `ios_release` add `--check
   ios_kit='python3 <flutter-ios-release>/scripts/ios_prep_check.py --project .'`.
3. Write `notes.md` from `references/report-template.md` (it lives in
   `.pipeline/`, so writing it does not dirty the project) and answer the
   *release (self)* checklist in its §2.
4. **Human gate** (`release` is in `human_gates` by default): ask with the
   notes path, version and the §2/§6 summary. Reject → fix, new commits,
   back to step 2.
5. Approved → `git tag v<version>` on that commit → `pipeline-state.sh
   advance` (checks verify.json sha = HEAD = tagged commit).

Push only if the user says so (`auto-push` / `release-manager` if
present). "Next steps" lists `flutter-signing → flutter-build →
flutter-store-metadata → flutter-store-compliance → flutter-publish`, and
for iOS `bash ios-release/build-ios.sh` on a Mac (Xcode 26+).

## Review loop

Each review is run by an independent reviewer built from
`references/reviewer-prompt.md` with the stage checklist from
`references/review-checklists.md`. The reviewer receives only:

- the stage artifact paths (and, for `qa`, the project dir + latest `verify.json`)
- `artifacts/<stage>/evidence/` — tool output and sibling-skill reports the
  orchestrator produced (facts), plus paths to the review skills'
  methodology files; the reviewer itself cannot run skills or commands
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
bash scripts/review-verdict.sh .pipeline/reviews/<stage>-vN.md [--prev .pipeline/reviews/<stage>-v(N-1)[-gate].md]
# stdout: REVISE critical=0 major=2 minor=1 findings=3 regression_unresolved=1   (exit 0)
# exit 1: MALFORMED: <reason>  → re-run the reviewer once quoting the reason; twice → ESCALATE
```

`--prev` is **mandatory from v2 on** — it is what proves the regression
list was honoured: one Regression row per previous finding, no invented
rows, no `resolved` id still in Findings, new ids above the previous
maximum. Pass the previous merged report, or the `-gate.md` file when the
previous round ended in a human rejection. The validator also requires
`- [pass|fail|n.a.] …` lines under Checklist results and a finding for
every `[fail]` (except on ESCALATE).

Async backends are bounded by `review_timeout_min` (no file → re-run once
→ fall back to `subagent`). **Panel review** — for stages in
`panel_stages` (default `[qa]`), one reviewer per lens in parallel, each
writing `<stage>-vN-<lens>.md`, merged into `<stage>-vN.md` (the file
`advance` reads). Timeout, lenses and merge rules: `reviewer-prompt.md`.

Handling (of the validated, merged file):

- **APPROVE** → `set review.<stage> approved`, log, then the human gate if
  the stage is listed, then `advance`
- **REVISE** → redo the stage with the Findings table as the requirements
  list, `bump revisions.<stage>`, re-review with that table as
  `previous_findings`. After `max_revisions` failed cycles → treat as
  ESCALATE.
  Exception — at `qa`, REVISE starts a **bugfix cycle** (QA produces no
  code): write `bugfix/fix-NNN.md` mapping each `F-nn` → change, fix the
  code, commit, re-run `verify-gate --stage test` on that commit (must be
  `ok`), answer the *bugfix cycle (self)* checklist at the top of the
  file, then re-review QA. Each loop `bump bugfix_cycles`; exceeding
  `max_bugfix_cycles` → ESCALATE.
- **BLOCK** → `set status blocked`, write `artifacts/<stage>/BLOCKED.md`
  with the reviewer's reason, stop.
- **ESCALATE** → `set status waiting_user`, ask the user (see human gates).

**Reviewer backends** (`reviewer_backend`): `subagent` (default,
`subagent_explore`, read-only), `opencode`, `herdr` — table and
availability check in `reviewer-prompt.md`. Missing backend → `subagent`,
logged. Rules are identical across backends; only the transport differs.

## Human gates

For each stage in `human_gates`, after its review approves, `set status
waiting_user` and call `ask_user_question`. The question text carries the
reviewer's Summary, the Nits count and the artifact paths — the user judges
the artifact, not the chat. Options: **approve** (continue) / **reject** /
**stop**. Record the answer as `gates.<stage>: approved|rejected|stopped`
— `advance` refuses anything but `approved`. `human_gates: []` = fully
autonomous.

- **reject** → write `reviews/<stage>-vN-gate.md` (N = the approved
  review's number) in the reviewer format: `## Verdict: REVISE`, Summary
  "Rejected at the human gate", one `major` finding holding the user's
  note verbatim with the next free id, and `- [fail] human gate`
  under Checklist results. Redo the stage with it as the requirements
  list; the next review is v(N+1) with that file as `previous_findings`
  and `--prev`.
- **stop** → keep `status: waiting_user`, log `gate <stage> stopped`, end
  the run; resume only when the user says so.
- **`release` has no reviewer** — its gate is asked after `verify-gate
  --release` passed on the release commit and `notes.md` is written, and
  **before** the tag (see the release stage note).

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
   The stage changes only through `advance`; `--override` only when the
   user explicitly tells you to bypass a named blocker, and every override
   appears in `notes.md` §6.
6. Keep going end to end: stop only on BLOCK, a rejected/stopped gate,
   exhausted revisions or bugfix cycles, or explicit user interrupt.
7. Smallest architecture that stays testable — no `domain/` layers, DI
   containers or use-cases the PRD cannot justify.
8. **Every git commit message is written in English** — subject and body,
   whatever language the user, the idea or the artifacts use. This applies
   to every commit the pipeline makes (scaffold, per-task, bugfix, release)
   and to commits made by sibling skills or parallel subagents on its
   behalf; pass the English message explicitly when delegating. Task
   `title`/`feature` in `tasks.json` are English for the same reason.
9. **The app speaks English first.** Every generated app ships with
   English (`en`) as its default and first locale: all user-facing copy
   (UI strings, error messages, empty states, store-facing text) is
   written in English, lives in `lib/l10n/app_en.arb` (`flutter gen-l10n`,
   `flutter_localizations`), and `supportedLocales` lists `en` first.
   Other locales — including the user's own language — are **additional**
   ARB files added only when the PRD asks for them, never in place of
   English. Dart identifiers, comments and log messages are English too.
   Pipeline artifacts (`idea.md`, `prd.md`, reviews, `notes.md`) stay in
   the user's language; this rule is about the product, not the paperwork.

## Definition of done

```
.pipeline/
  state.yaml            status: done, stage: done (reached via `advance`), gates.<h>: approved for every human gate
  reviews/              one APPROVE per reviewed stage, qa-vN APPROVE last
  artifacts/release/    notes.md + verify.json (analyze ok · test ok · build ok|skipped_env · dirty false)
<project_dir>/
  lib/ test/            flutter analyze clean, flutter test green (test/flows/ covers the primary flow)
  pubspec.yaml          version bumped, git tag v<version> on the commit verify.json names
  android/app/build.gradle*   applicationId = <org>.<slug>, not com.example
  ios-release/          (ios_release) build-ios.sh + ExportOptions.plist + README.md, ios_prep_check no BLOCK
```

## Reference files

| File | Read when |
|------|-----------|
| `references/review-checklists.md` | Every review point — reviewer checklists (idea…qa, lens-tagged), self-checklists (per task, bugfix, release), severity scale |
| `references/reviewer-prompt.md` | Spawning a reviewer — backends, prompt template, regression list, panel lenses + merge, report format, timeout/fallback |
| `references/tasks-schema.md` | Planning + implementation — `tasks.json` schema, UI-polish task (rule 9), parallel worktrees, example |
| `references/sibling-contracts.md` | Before invoking a sibling skill — inputs, outputs, traps |
| `references/report-template.md` | Release — `notes.md` skeleton, filled from `verify.json` + state |

| Script | Run at |
|--------|--------|
| `scripts/pipeline-state.sh` | Every transition — `init · status · get · set · bump · log · check · advance`; `advance` refuses while a gate is unmet (review re-validated with `--prev`, stale artifacts, verify sha) |
| `scripts/verify-gate.sh` | implementation (per task + final, `--no-test`), test (`--coverage [--min-coverage n]`), release (`--build … --release [--check ios_kit=…]`) — writes `verify.json` with `git_sha`, `dirty`, test counts, coverage; exit 1 on any `fail` |
| `scripts/evidence-pack.sh` | Before the `qa` review — analyze, pub outdated, deps, secrets, manifest, gradle, iOS facts, risky-pattern greps → `artifacts/qa/evidence/` + `index.json`; never modifies the project |
| `scripts/review-verdict.sh` | After every review (`--prev` from v2) — validates the report file and its regression list, prints verdict + severity counts, exit 1 = malformed (re-run reviewer) |

All scripts are bash 3.2-compatible (macOS `/bin/bash`).

## Scope

Does not: sign for upload, generate store assets, check store policy
(unless `store_bound`), publish or upload — hand off per release notes §7.
Does not install Flutter (`flutter-init` in T01) or build/sign an IPA (it
prepares the kit; a Mac builds it).
