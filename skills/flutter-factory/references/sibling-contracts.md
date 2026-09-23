# Sibling skill contracts

What each preferred skill really expects, what it leaves behind, and the
trap that stops a pipeline run if you forget it. Verified against the
installed skills on 2026-09-22 — re-check the sibling's `SKILL.md` when a
contract looks stale.

## The shared trap: "Repo Sync Before Edits"

`idea-validator`, `prd-generator`, `tad-generator`, `tasks-generator`,
`test-coverage`, `release-manager` and `code-review` (cleanup/clean modes)
all run a mandatory
`git fetch origin && git pull --rebase origin <branch>` and **stop to ask
the user if `origin` is missing**. Most pipeline runs start in a local repo
with no remote. Always add to their prompt:

> Local git repo with no remote — skip the Repo Sync step, commit locally,
> do not push.

Several of them also `git push origin <branch>` at the end. Same line covers
it. If the repo *does* have a remote and the user has not asked to push,
say so explicitly ("do not push"). The read-only modes used for evidence
(`code-review mode:review`, `dont-make-me-think` steps 1–4) do not sync.

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
| `frontend-design` | a brief (product, audience, tone) | design direction + code | Web-oriented; keep the *direction* (tokens, type, colour), encode it into `design-system.md`, and implement in Flutter yourself. Map the direction onto one `flutter-ui-revamp` recipe (`style:` + `seed:` header lines) so the last implementation task has its inputs. |
| `logo-designer` | project context | 7 SVG variants + showcase | Optional; convert the chosen SVG to launcher icons in implementation. |

## Flutter family

| Skill | Needs | Leaves | Trap |
|-------|-------|--------|------|
| `flutter-init` | `project_name` (snake_case), **`org` (required, no default)**, `platforms` = `android` \| `ios` \| both | project dir, clean-arch folders, git init, pinned SDK levels | Web is **not** in its contract — run `flutter create --platforms web .` afterwards if `release_build: web`. Placeholder org → downstream skills block. It may install Flutter/Android SDK — that is allowed here (task T01). It always runs `git init` — if the workspace is already inside a git repo (SKILL.md → Git layout), tell it to skip that step (or remove the nested `.git` it created before the first commit). Afterwards re-run `pipeline-state.sh init --project <dir>`. |
| `flutter-ui-revamp` | `project`, `style`, `seed`, `scope`, `keep` — pass all of them from `design-system.md` (`style:`/`seed:` header lines) so its Step 2 never asks; **clean git tree** | branch `ui-revamp/<date>`, `lib/theme/*`, `lib/widgets/*`, `assets/**` + `assets/CREDITS.md`, `.revamp/{audit,design-direction,report}.md`, grouped English commits | **Last implementation task only** (schema rule 9). Step 0 **STOPs on a dirty tree** — run it right after the previous task's commit; `.pipeline/` never makes the tree dirty because `pipeline-state.sh init` put it in `.git/info/exclude` (check with `git status --short` if in doubt). Step 3 waits for licence approval — pre-answer it in the prompt: "accept only CC0 / MIT / ISC / OFL / Apache-2.0, reject anything attribution-required or GPL / CC-BY-NC without asking"; if a needed asset is attribution-only, `ask_user_question` (it will also add an About/Credits screen — allowed). Step 5 may **rebuild `lib/theme/`** — pass `keep: "extend the existing lib/theme tokens and l10n setup, do not replace them"`. New strings it adds (empty states, credits) must go to `app_en.arb` (rule 9). Afterwards: merge `ui-revamp/*` into the working branch (keep its commits — they are English), `verify-gate --no-test`, copy `.revamp/report.md` → `artifacts/implementation/evidence/revamp-report.md` and `.revamp/audit.md` → `evidence/revamp-audit.md`, then delete or `.gitignore` `.revamp/`; `assets/CREDITS.md` stays in the project — QA `[sec] [E]` checks it. |
| `firebase-auth-setup` | Firebase project name, platforms | Firebase project, web config, service-account key | Needs network + gcloud/firebase CLI auth; only when `DECISION-*` says Firebase Auth. Google sign-in needs an extra OAuth client. Never commit `google-services.json` — `.gitignore` it. |
| `test-coverage` | runnable project + coverage command (`flutter test --coverage`) | added tests on a `feat/test-coverage` branch | It creates a **branch**; merge it back to the working branch before the `test` gate. Write structure-defining tests yourself first — it fills gaps. Its own coverage figure is not evidence — the reviewer reads `coverage` from `verify-gate --coverage`'s `verify.json`. Repo Sync trap applies. |
| `code-review` | project path, `mode:review` (default) | `CODE_REVIEW.md` **in the project root**, no code changes | **Evidence for the QA review**: orchestrator runs `mode:review`, then `mv <project>/CODE_REVIEW.md .pipeline/artifacts/qa/evidence/code-review-report.md` — leaving it in the project pollutes the next bugfix diff and `git status`. The reviewer confirms each hit at `file:line` before it becomes an `F-nn`. Pass `references/review-mode.md` + `code-smells.md` as methodology. `mode:cleanup` writes code — only during a bugfix cycle, and only when a QA finding asks for it. |
| `flutter-store-compliance` | project dir (+ optional `features`, `target_audience`) | `<project>/store-metadata/compliance-report.{json,md}` | Only when `store_bound: true`. Orchestrator runs it before the QA review and copies `store-metadata/compliance-report.json` to `artifacts/qa/evidence/compliance-report.json` (the `store-metadata/` folder may stay — `flutter-publish` gates on it later — but commit it, e.g. `chore(store): compliance report`, before the release commit, or the release gate records `dirty: true` and `advance` refuses); the reviewer treats its BLOCK rows as `critical` findings after confirming them. |
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
