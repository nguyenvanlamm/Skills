# Sibling skill contracts

What each preferred skill really expects, what it leaves behind, and the
trap that stops a pipeline run if you forget it. Verified against the
installed skills on 2026-09-23 (`flutter-ui-revamp` v1.4.0) — re-check the sibling's `SKILL.md` when a
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
| `flutter-init` | `project_name` (snake_case), **`org` (required, no default)**, `platforms` = `android` \| `ios` \| both | project dir, clean-arch folders, git init, pinned SDK levels | Web is **not** in its contract — run `flutter create --platforms web .` afterwards if `release_build: web`. Placeholder org → downstream skills block. It may install Flutter/Android SDK — that is allowed here (task T01). It always runs `git init` — if the workspace is already inside a git repo (SKILL.md → Git layout), tell it to skip that step (or remove the nested `.git` it created before the first commit). Afterwards re-run `pipeline-state.sh init --project <dir>`. With `ios_release: true` pass `platforms: android,ios` **even on Linux** — its "non-macOS → android only" rule is about building; creating `ios/` works anywhere, and the iOS kit task needs it. |
| `flutter-ios-release` | project, bundle id, team id (or none → provided on the Mac), display name, device family, encryption answer, one English usage string per permission — all from the iOS `DECISION-*` and PRD features | edited `ios/` (Info.plist, pbxproj, `PrivacyInfo.xcprivacy`), `ios-release/{build-ios.sh,ExportOptions.plist,README.md,prep-report.json}`, `.gitignore` | **Last task when `ios_release: true`** (schema rule 10). Runs on any OS; builds nothing. Its `ios_prep_check.py` is the task `verify`, the QA evidence (`--out artifacts/qa/evidence/ios-prep.json`) and the release gate step (`verify-gate --check ios_kit='python3 <skill>/scripts/ios_prep_check.py --project .'`). Never report an IPA as built: only `ios-release/build-ios.sh` on macOS (Xcode 26+) produces and verifies it, and it never uploads. A `BLOCK` for the app icon (alpha / default) is fixed by regenerating launcher icons, not by the script. |
| `appstore-review-checker` | project path (static) | guideline report with PASS/FAIL per item | **Evidence for the QA review** when `ios_release: true`: prompt "static analysis only, report only — do not offer or apply fixes" (it otherwise asks per FAIL id), save as `artifacts/qa/evidence/appstore-review.md`. The reviewer confirms each FAIL in the code before it becomes an `F-nn`. |
| `flutter-ui-revamp` (v1.4) | `project`, `style`, `seed`, `scope`, `keep` — pass **all five**: `style`/`seed` from the `design-system.md` header lines, `scope` = "every screen in ux.md" (explicit, so Step 1 does not stop to propose 3–5 screens when `lib/` has ≥ 12 Dart files); **clean git tree** | branch `ui-revamp/<date>`, `lib/theme/*`, `lib/widgets/*`, `assets/**` + `assets/CREDITS.md`, `.revamp/{audit,design-direction,report}.md`, grouped English commits | **Last screen-affecting task** (schema rule 9 — its `files`, `verify` and merge commit are defined there). Every stop it makes for the user must be pre-answered in the prompt, or the run halts mid-task: **Step 0** STOPs on a dirty tree — run it right after the previous task's commit (`.pipeline/` is in `.git/info/exclude`; confirm with `git status --short`). **Step 2** asks for explicit agreement on `.revamp/design-direction.md` — say "the approved `design-system.md` is the agreed direction: write design-direction.md from it and continue without asking". **Step 3** waits for licence approval — pre-answer: "accept only CC0 / MIT / ISC / OFL / Apache-2.0; reject GPL, CC-BY-NC, all-rights-reserved and no-licence art without asking; CC BY-SA only if used unmodified (never recoloured to the seed — trap 8), else pick the CC0/MIT alternative; judge the **upstream** art licence, not the pub wrapper's (trap 11 — e.g. `solar_icons`/`iconsax_flutter` are rejected, `animated_emoji` is CC BY); nothing under the Remix Icon License goes into the launcher icon, splash or store icon (trap 12); fetch only from the *Direct download URLs* sections, hand-download-only sources via `--local`, never guessed URLs"; an attribution-only asset the design needs → `ask_user_question` (it then adds an About/Credits screen — allowed). The icon set must expose const `IconData` (Lucide/Phosphor per the recipe) — `font_awesome_flutter`, `iconoir_flutter`, `hugeicons` need a widget-level refactor that `apply_icons.py` cannot do, so do not pick them unless the task budgets that refactor. **Step 4** uses `fetch_asset.py --filename` for generic basenames (Noto `lottie.json`, Material Symbols `24px.svg`, DiceBear `svg`) and `--strip N` for nested archives; it refuses `.7z`/`.rar` and Mixkit previews — a refusal means pick another source, not work around it. It adds packages — `lucide_icons_flutter` (never the frozen `lucide_icons`), `rive` 0.14 (needs `RiveNative.init()` in `main`), `flutter_gen` ≥ 5.15, fonts: each needs a dependency-table row + `DECISION-NNN` before the task is done (per-task self-check). **Step 5** may rebuild `lib/theme/` — pass `keep: "extend the existing lib/theme tokens and l10n setup, do not replace them"`; strings it adds go to `app_en.arb` (rule 9). **Step 6** wants the user to approve the `apply_icons.py` dry-run diff — the orchestrator reviews it itself (every `unmapped`, `DROPPED` and `COLLISION` line resolved, e.g. tint the selected glyph) and authorises `--apply --yes` in the prompt; then fixes widget tests whose `find.byIcon` targets changed. **Step 7** `--analyze-size` needs an Android SDK — without one it is `skipped_env`, not a failure. Afterwards: copy `.revamp/report.md` → `artifacts/implementation/evidence/revamp-report.md` and `.revamp/audit.md` → `evidence/revamp-audit.md`, merge per schema rule 9 (untrack `.revamp/`), `verify-gate --no-test`. `assets/CREDITS.md` (columns incl. `Credit` = `on-screen \| license-page \| none`) stays in the project — QA `[sec] [E]` checks it. |
| `firebase-auth-setup` | Firebase project name, platforms | Firebase project, web config, service-account key | Needs network + gcloud/firebase CLI auth; only when `DECISION-*` says Firebase Auth. Google sign-in needs an extra OAuth client. Never commit `google-services.json` — `.gitignore` it. |
| `test-coverage` | runnable project + coverage command (`flutter test --coverage`) | added tests on a `feat/test-coverage` branch | It creates a **branch**; merge it back to the working branch before the `test` gate. Write structure-defining tests yourself first — it fills gaps. Its own coverage figure is not evidence — the reviewer reads `coverage` from `verify-gate --coverage`'s `verify.json`. Repo Sync trap applies. |
| `code-review` | project path, `mode:review` (default) | `CODE_REVIEW.md` **in the project root**, no code changes | **Evidence for the QA review**: orchestrator runs `mode:review`, then `mv <project>/CODE_REVIEW.md .pipeline/artifacts/qa/evidence/code-review-report.md` — leaving it in the project pollutes the next bugfix diff and `git status`. The reviewer confirms each hit at `file:line` before it becomes an `F-nn`. Pass `references/review-mode.md` + `code-smells.md` as methodology. `mode:cleanup` writes code — only during a bugfix cycle, and only when a QA finding asks for it. |
| `flutter-store-compliance` | project dir (+ optional `features`, `target_audience`) | `<project>/store-metadata/compliance-report.{json,md}` | Only when `store_bound: true`. Orchestrator runs it before the QA review and copies `store-metadata/compliance-report.json` to `artifacts/qa/evidence/compliance-report.json` (the `store-metadata/` folder may stay — `flutter-publish` gates on it later — but commit it right away, e.g. `chore(store): compliance report`, then **re-run `verify-gate --stage test --coverage`** on that commit before spawning the QA reviewer: the commit moves HEAD, and `advance qa` refuses a test `verify.json` for an older sha); the reviewer treats its BLOCK rows as `critical` findings after confirming them. |
| `release-manager` | clean tree, version scheme, remote | version bump, changelog, tag, GitHub release, publish | Heavy for a first release; without a remote just do bump + tag yourself. Repo Sync trap applies. |
| `auto-push` | committed changes, remote | pushed branch | Only if the user asked to push. |

## Skills intentionally *not* invoked here

`flutter-signing`, `flutter-build`, `flutter-store-metadata`,
`flutter-publish` — they belong to the store-bound path after this
pipeline ends. `verify-gate.sh --build apk` proves buildability with a
debug-signed artifact; release signing is `flutter-signing`'s job. The iOS
counterpart is `ios-release/build-ios.sh` on a Mac. List them under "Next
steps" in `notes.md`.

## Reviewer backends

| Skill | Role |
|-------|------|
| `opencode-runner` | sets up `opencode` CLI + free cloud models for `reviewer_backend: opencode` |
| `herdr-agent` | spawn / prompt / wait / read a Herdr pane for `reviewer_backend: herdr` |

Both: check `command -v opencode` / herdr availability **before** the first
review; fall back to `subagent` and log it rather than failing the stage.
