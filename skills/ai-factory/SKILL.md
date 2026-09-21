---
name: ai-factory
description: >-
  Drive AIFactory — the visual multi-agent software factory — end to end:
  init a project, run the orchestrated pipeline (idea → review → plan →
  review → design → review → architecture → review → parallel
  implementation → test → ui-polish → QA → release)
  with dynamic skill discovery, autonomous review loops and Herdr/Mock
  runtimes. Use when asked to "build/run an app with aifactory", orchestrate
  a Flutter build pipeline, manage workflow runs, skills or tasks.
capabilities:
  - orchestration
  - workflow
  - agents
  - flutter
  - skill-discovery
version: "1.0.0"
permissions:
  filesystem: { read: true, write: true }
  shell: { enabled: true }
  network: { enabled: false }
  secrets: { required: false }
---

# ai-factory — operating the software factory

AIFactory is the orchestration brain; Herdr is the runtime (agent processes,
panes, worktrees); skills are reusable capabilities discovered dynamically.
Never re-implement terminal/process management — that is Herdr's job.

## Setup

```bash
cd <aifactory repo>
make dev        # create .venv + install
make web        # build the frontend (needed once before `aifactory run`)
```

CLI is `.venv/bin/aifactory` (or `aifactory` if installed).

## Drive a project end to end

```bash
aifactory init my-app --idea "offline-first gold miner game, 50 levels"
cd my-app
aifactory run                 # opens web editor at http://127.0.0.1:4600
aifactory run --auto          # web UI + start immediately
aifactory run --supervised    # headless terminal run (MockRuntime default)
aifactory resume              # continue a PAUSED run headless (not a waiting gate)
aifactory status              # stage, progress, review status
aifactory approve [--stage x]           # pass a human gate → run resumes
aifactory reject [--stage x] [--note y] # gate → revision loop with feedback
```

Default runs are NOT fully autonomous: `human_gates` defaults to
`["idea", "planning", "release"]`, so the run pauses at
`waiting_approval` after a gated stage's review passes. Resolve gates
with `approve`/`reject` above; `resume` does NOT clear them. For a fully
autonomous run set `human_gates: []` in `.aifactory/config.yaml` first.

Reviewers are spawned at 5 points (idea, plan, design, architecture,
final QA) plus a conditional 6th — the testing stage only spawns a QA
agent when the project has no Flutter checkout. Each reviewer is an
independent process (Herdr pane / Mock cmd) that receives the stage
output plus project constitution and decisions, returns
`approve|revise|block|escalate` + feedback, and a revise spawns a
revision task for the stage. The loop repeats until approve or
`max_revisions` is exhausted.

## Review points

| After stage | Reviewer checks | Preferred skills (capability-matched) |
|---|---|---|
| `idea` | scope clarity, feasibility, market fit | `idea-validator` |
| `plan` | covers the idea, ordered + measurable tasks | `prd-generator` |
| `design` | usability, consistency, aesthetics, accessibility | `dont-make-me-think` + `frontend-design` |
| `architecture` | decisions vs PRD/constitution, feasibility | `tad-generator` |
| `test` | tests run green, coverage of edge cases | `test-coverage` |
| `QA` | bugs, security, performance, clean code | `code-review` (all modes); + `flutter-store-compliance` / `appstore-review-checker` for store-bound apps |

Skills are selected by capability like any other stage — a missing
preferred skill falls back to the reviewer's native ability.

## Dynamic skill discovery

Skills are discovered — never hardcoded — from (highest priority first):

1. `<root>/.aifactory/skills/<id>/` (project — created by `init`)
2. `~/.aifactory/skills/<id>/` (global)
3. environment dirs: `<root>/.devin/skills/`, `<root>/.agents/skills/`,
   `~/.config/devin/skills/`, plus `skills.extra_dirs` in
   `.aifactory/config.yaml` for arbitrary extra directories

```bash
aifactory skills                        # list discovered skills + capabilities
aifactory skills inspect <id>           # metadata, permissions, instructions
aifactory task <TASK-ID>                # shows selected_skills + reasons
aifactory run --skills flutter,testing  # force skill ids
aifactory run --no-skill <id>           # deny a skill
aifactory run --supervised --skills x   # same overrides for headless
```

Skill format: `SKILL.md` with YAML frontmatter — `name`, `description`,
`capabilities`, optional `id`, `version`, `requires`, `conflicts`,
`decisions`, `priority`, `permissions`. Each workflow stage declares
required *capabilities*; the SkillSelector ranks exact capability matches
first, then token-subset matches — within a tier: project > global >
environment, then `-priority`, then id. It resolves `requires`, drops
conflicting skills, and injects only the selected instructions into the
agent prompt. Prefix a capability with `!` to make it critical — the task
fails loudly instead of faking success.

## Rules

- Project constitution > approved architecture > decisions > task > skills.
  A skill must never silently override a project decision.
- Reviewers are independent — a generator never reviews its own output.
- If a required skill is missing, record it and fall back to the agent's
  native ability; if critical (`!`), escalate instead of pretending.
- Check `aifactory logs` / `aifactory explain` for the event trail
  (`skills.selected`, `agent.started/completed/cleaned`, `review.approved`,
  `review.rejected`).
