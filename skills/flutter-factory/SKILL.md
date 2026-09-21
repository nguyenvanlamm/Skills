---
name: flutter-factory
description: >-
  Run an end-to-end, review-gated software pipeline with no external
  orchestrator: idea → review → plan → review → design → review →
  architecture → review → implementation → test → QA → release. The agent
  executes every stage itself, uses fresh-context subagents as independent
  reviewers (approve | revise | block | escalate), asks the user at human
  gates, and discovers capability-matched skills dynamically. Use when
  asked to "build an app end to end", "run the full pipeline", "idea to
  release with reviews".
capabilities:
  - orchestration
  - workflow
  - review-gates
  - skill-discovery
version: "1.0.0"
permissions:
  filesystem: { read: true, write: true }
  shell: { enabled: true }
  network: { enabled: false }
  secrets: { required: false }
---

# flutter-factory — self-contained review-gated build pipeline

No external tool required. The agent IS the orchestrator: it produces each
stage's artifacts, spawns an independent reviewer per gate, loops on
feedback, and asks the user at human gates via `ask_user_question`.
All state lives in `.pipeline/` so an interrupted run can resume.

## Workspace

On start (or `init`):

```
.pipeline/
  config.yaml          # human_gates, max_revisions (see defaults below)
  constitution.md      # project rules — ask the user or derive from repo
  state.yaml           # resume point — ALWAYS read first if it exists
  artifacts/<stage>/   # stage outputs
  reviews/             # <stage>-vN.md review reports
  bugfix/              # fix-NNN.md — one file per bugfix cycle
  decisions/           # DECISION-NNN.md — binding choices made mid-run
  tasks.json           # implementation task list
```

Default `config.yaml`:

```yaml
human_gates: [idea, planning, release]   # pause + ask user after these reviews pass
max_revisions: 3                         # per stage; then escalate
parallel_implementation: false           # true → disjoint tasks via parallel subagents
reviewer_backend: subagent               # subagent | opencode | herdr
max_bugfix_cycles: 8                     # QA findings → fix → re-QA loops
```

`state.yaml`:

```yaml
status: running        # running | waiting_user | blocked | done
stage: planning        # stage currently in progress
revisions: {planning: 1}
bugfix_cycles: 0
gates: {idea: approved}
```

Resume rule: if `.pipeline/state.yaml` exists, read it and continue from
`stage` — never restart a finished stage. Update it after every transition.

## Pipeline

Track stages with `todo_write`. For each stage: produce artifacts → review
→ (human gate if listed) → advance.

| # | Stage | Produces | Reviewer checks | Preferred skills |
|---|-------|----------|-----------------|------------------|
| 1 | `idea` | `artifacts/idea/idea.md` | scope clarity, feasibility, market fit | `idea-validator` |
| 2 | `planning` | `artifacts/planning/prd.md`, `tasks.json` | covers the idea, ordered + measurable tasks | `prd-generator` |
| 3 | `design` | `artifacts/design/{ux,ui,design-system,states}.md` | usability, consistency, aesthetics, accessibility | `dont-make-me-think`, `frontend-design` |
| 4 | `architecture` | `artifacts/architecture/{architecture,folder-structure,coding-rules}.md` | decisions vs PRD/constitution, feasibility | `tad-generator` |
| 5 | `implementation` | code in the project | — (reviewed by QA) | matched per task |
| 6 | `test` | test suite + `artifacts/test/report.md` | tests run green, edge cases covered | `test-coverage` |
| 7 | `qa` | `reviews/qa-vN.md` | bugs, security, performance, clean code | `code-review`; + `flutter-store-compliance` / `appstore-review-checker` for store-bound apps |
| 8 | `release` | git commit/tag, `artifacts/release/notes.md` | — | — |

Implementation: execute `tasks.json` in order. If
`parallel_implementation: true`, delegate disjoint tasks to parallel
`subagent_general` agents — each receives constitution + architecture +
decisions + its task only. Sequential otherwise.

## Review loop

A generator never reviews its own output. Each review is run by an
independent reviewer (backend below) that receives only:

- the stage artifacts (paths, not the generating reasoning)
- `constitution.md` + `decisions/*.md`
- the review checklist for that stage

Every backend has the same contract: the reviewer writes
`reviews/<stage>-vN.md` starting with a verdict line, and returns a
completion signal. **The file is the durable callback** — the return value
only says "done"; if output is lost or truncated, read the file.

```
## Verdict: APPROVE | REVISE | BLOCK | ESCALATE
```

### Reviewer backends (`reviewer_backend`)

| Backend | How | Result delivery | Model diversity |
|---|---|---|---|
| `subagent` (default) | `run_subagent` with `subagent_explore` (read-only) — foreground blocks until done; background notifies via `read_subagent` | synchronous / completion notification | none — same model as the session |
| `opencode` | `opencode run "<review prompt>"` as a shell command; invoke the `opencode-runner` skill for setup | stdout when the command exits | yes — free cloud models |
| `herdr` | spawn an agent pane via the `herdr-agent` skill, send the review prompt, `wait` + capture pane output | async — orchestrator must wait + capture | yes — whatever model the pane runs |

Fallback: if `reviewer_backend` is not `subagent`, check the tool exists
first (`command -v opencode`, herdr CLI/socket). Missing → fall back to
`subagent` and record the fallback in `state.yaml`. Reviewer quality rules
stay identical regardless of backend — only the transport differs.

Then handle:

- **APPROVE** → record in `state.yaml`, advance (via human gate if gated)
- **REVISE** → redo the stage with the feedback as requirements, bump `vN`,
  re-review. After `max_revisions` failed cycles → treat as ESCALATE.
  Exception — at stage `qa`, REVISE does NOT re-run QA (it produces no
  code): start a **bugfix cycle** instead — write `.pipeline/bugfix/fix-NNN.md`
  addressing every numbered finding in the QA report, fix the code, re-run
  the `test` stage (must be green), then re-review QA. Each loop bumps
  `bugfix_cycles`; exceeding `max_bugfix_cycles` → ESCALATE.
- **BLOCK** → stop the run, write a blocker report, set `status: blocked`
- **ESCALATE** → ask the user (see human gates) how to proceed

## Human gates

For each stage in `human_gates`, after its review approves, call
`ask_user_question`: approve (continue) / reject (revision loop with the
user's note as feedback) / stop. `human_gates: []` = fully autonomous.

## Dynamic skill discovery

Before each stage, scan for `SKILL.md` files (highest priority first):

1. `.pipeline/skills/<id>/` (project-local)
2. `.devin/skills/`, `.agents/skills/` (workspace)
3. `~/.config/devin/skills/` (user)

Read frontmatter `capabilities`. Rank: exact capability match > token-subset
match; within a tier: project > workspace > user, then `-priority`, then id.
Apply `requires`, drop `conflicts`. A missing preferred skill falls back to
the agent's native ability — record it. Prefix `!` = critical: fail loudly
instead of faking success. Invoke chosen skills via the `skill` tool.

## Rules

- Constitution > approved architecture > decisions > task > skills. A
  skill never silently overrides a project decision — record a
  `DECISION-NNN.md` when a choice binds future stages.
- Reviewer independence: the reviewer (any backend) gets artifacts +
  context docs only — never the draft reasoning or previous attempts'
  discussion.
- Every verdict, gate result, and skill fallback goes into `state.yaml` or
  a review file — the `.pipeline/` dir must tell the whole story alone.
- Keep going end to end: only stop on BLOCK, a rejected gate, exhausted
  revisions, or explicit user interrupt.
