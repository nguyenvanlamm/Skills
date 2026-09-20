---
name: ai-factory
description: >-
  Drive AIFactory — the visual multi-agent software factory — end to end:
  init a project, run the orchestrated pipeline (idea → review → plan →
  review → design → review → architecture → parallel implementation →
  test → QA → release)
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
aifactory resume              # continue a paused / waiting run headless
aifactory status              # stage, progress, review status
```

There are no human gates — the run is fully autonomous. Reviewer commands
are spawned at 5 points; each reviewer is an independent process (Herdr
pane / Mock cmd) that receives the stage output plus project constitution
and decisions, returns `pass` or `fail` + feedback, and a fail spawns a
revision task for the stage. The loop repeats until pass.

## Review points

| After stage | Reviewer checks | Preferred skills (capability-matched) |
|---|---|---|
| `idea` | scope clarity, feasibility, market fit | `idea-validator` |
| `plan` | covers the idea, ordered + measurable tasks | agent native (no dedicated skill) |
| `design` | usability, consistency, accessibility | `dont-make-me-think` |
| `test` | tests run green, coverage of edge cases | `test-coverage` |
| `QA` | bugs, security, performance, clean code | `code-review` (all modes); + `flutter-store-compliance` / `appstore-review-checker` for store-bound apps |

Skills are selected by capability like any other stage — a missing
preferred skill falls back to the reviewer's native ability.

## Dynamic skill discovery

Skills are discovered — never hardcoded — from:

1. the directory containing this skill: sibling skill folders
   `<skills-dir>/<id>/SKILL.md`
   (e.g. `/home/lam/Documents/projects/Skills/skills/`)
2. agent skill dirs of the current environment:
   `.devin/skills/` (workspace) and `~/.config/devin/skills/` (user)

```bash
aifactory skills                        # list discovered skills + capabilities
aifactory skills inspect <id>           # metadata, permissions, instructions
aifactory task <TASK-ID>                # shows selected_skills + reasons
aifactory run --skills flutter,testing  # force skill ids
aifactory run --no-skill <id>           # deny a skill
aifactory run --supervised --skills x   # same overrides for headless
```

Skill format: `SKILL.md` with YAML frontmatter — `name`, `description`,
`capabilities`, optional `version`, `requires`, `conflicts`, `decisions`,
`permissions`. Each workflow stage declares required *capabilities*; the
SkillSelector ranks candidates (skills-dir > environment), resolves
`requires`, drops conflicting skills, and injects only the selected
instructions into the agent prompt. Prefix a capability with `!` to make it
critical — the task fails loudly instead of faking success.

## Rules

- Project constitution > approved architecture > decisions > task > skills.
  A skill must never silently override a project decision.
- Reviewers are independent — a generator never reviews its own output.
- If a required skill is missing, record it and fall back to the agent's
  native ability; if critical (`!`), escalate instead of pretending.
- Check `aifactory logs` / `aifactory explain` for the event trail
  (`skills.selected`, `agent.started/completed/cleaned`, `review.passed`,
  `review.failed`).
