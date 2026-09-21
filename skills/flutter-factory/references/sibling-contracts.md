# Sibling skill contracts

What each preferred skill really expects, what it leaves behind, and the
trap that stops a pipeline run if you forget it. Verified against the
installed skills on 2026-09-21 — re-check the sibling's `SKILL.md` when a
contract looks stale.

## The shared trap: "Repo Sync Before Edits"

`idea-validator`, `prd-generator`, `tad-generator`, `tasks-generator`,
`test-coverage`, `release-manager`, `code-review` (cleanup/clean modes) and
`dont-make-me-think` (redesign mode) all run a mandatory
`git fetch origin && git pull --rebase origin <branch>` and **stop to ask
the user if `origin` is missing**. Most pipeline runs start in a local repo
with no remote. Always add to their prompt:

> Local git repo with no remote — skip the Repo Sync step, commit locally,
> do not push.

Several of them also `git push origin <branch>` at the end. Same line covers
it. If the repo *does* have a remote and the user has not asked to push,
say so explicitly ("do not push").

## Planning family

| Skill | Needs | Leaves | Map into pipeline |
|-------|-------|--------|-------------------|
| `idea-validator` | an idea (text) or `idea.md`; writes into a project folder | `idea.md`, `validate.md` | Point it at `.pipeline/artifacts/idea/`. If it asks for `IDEAS_ROOT`, pass that folder. |
| `prd-generator` | folder containing `idea.md` **and** `validate.md` (both required) | `prd.md` in that folder | Run after `idea` is approved; copy/symlink the two files into `.pipeline/artifacts/planning/` or pass the idea folder and move `prd.md` afterwards. If `validate.md` does not exist (idea done inline), write a short one first — it will not start without it. |
| `tasks-generator` | path to `prd.md` | `tasks.md` (sprint markdown, 30–80 tasks for big PRDs) | Convert to `tasks.json` per `tasks-schema.md`; cap MVP to what `idea.md` lists; add `files` + `verify` per task — the generator does not produce them. |
| `tad-generator` | folder containing `prd.md` | `tad.md` (+ may spawn research agents) | Feed as input to `architecture.md`; it does not know Flutter specifics or `org` — those are still yours. Existing `tad.md` → it switches to modify mode. |

## Design family

| Skill | Needs | Leaves | Notes |
|-------|-------|--------|-------|
| `dont-make-me-think` | screenshot / URL / HTML / **verbal description** | usability report | **Evidence for the design review**: orchestrator runs it on `ux.md` + `ui.md` (description input, nothing to install) → `artifacts/design/evidence/dmmt-report.md`; pass `references/krug-principles.md` to the reviewer as methodology. Redesign mode writes code — never enable it here. |
| `frontend-design` | a brief (product, audience, tone) | design direction + code | Web-oriented; keep the *direction* (tokens, type, colour), encode it into `design-system.md`, and implement in Flutter yourself. |
| `logo-designer` | project context | 7 SVG variants + showcase | Optional; convert the chosen SVG to launcher icons in implementation. |

## Flutter family

| Skill | Needs | Leaves | Trap |
|-------|-------|--------|------|
| `flutter-init` | `project_name` (snake_case), **`org` (required, no default)**, `platforms` = `android` \| `ios` \| both | project dir, clean-arch folders, git init, pinned SDK levels | Web is **not** in its contract — run `flutter create --platforms web .` afterwards if `release_build: web`. Placeholder org → downstream skills block. It may install Flutter/Android SDK — that is allowed here (task T01). |
| `firebase-auth-setup` | Firebase project name, platforms | Firebase project, web config, service-account key | Needs network + gcloud/firebase CLI auth; only when `DECISION-*` says Firebase Auth. Google sign-in needs an extra OAuth client. Never commit `google-services.json` — `.gitignore` it. |
| `test-coverage` | runnable project + coverage command (`flutter test --coverage`) | added tests on a `feat/test-coverage` branch | It creates a **branch**; merge it back to the working branch before the `test` gate. Write structure-defining tests yourself first — it fills gaps. Repo Sync trap applies. |
| `code-review` | project path, `mode:review` (default) | findings report, **no code changes** | **Evidence for the QA review**: orchestrator runs `mode:review` → `artifacts/qa/evidence/code-review-report.md`; the reviewer confirms each hit at `file:line` before it becomes an `F-nn`. Pass `references/review-mode.md` + `code-smells.md` as methodology. `mode:cleanup` writes code — only during a bugfix cycle, and only when a QA finding asks for it. |
| `flutter-store-compliance` | project dir (+ optional `features`, `target_audience`) | `compliance-report.json` + markdown | Only when `store_bound: true`. Orchestrator runs it before the QA review and copies the JSON to `artifacts/qa/evidence/compliance-report.json`; the reviewer treats its BLOCK rows as `critical` findings after confirming them. |
| `release-manager` | clean tree, version scheme, remote | version bump, changelog, tag, GitHub release, publish | Heavy for a first release; without a remote just do bump + tag yourself. Repo Sync trap applies. |
| `auto-push` | committed changes, remote | pushed branch | Only if the user asked to push. |

## Skills intentionally *not* invoked here

`flutter-signing`, `flutter-build`, `flutter-store-metadata`,
`flutter-publish`, `appstore-review-checker` — they belong to the
store-bound path after this pipeline ends. `verify-gate.sh --build apk`
proves buildability with a debug-signed artifact; release signing is
`flutter-signing`'s job. List them under "Next steps" in `notes.md`.

## Reviewer backends

| Skill | Role |
|-------|------|
| `opencode-runner` | sets up `opencode` CLI + free cloud models for `reviewer_backend: opencode` |
| `herdr-agent` | spawn / prompt / wait / read a Herdr pane for `reviewer_backend: herdr` |

Both: check `command -v opencode` / herdr availability **before** the first
review; fall back to `subagent` and log it rather than failing the stage.
