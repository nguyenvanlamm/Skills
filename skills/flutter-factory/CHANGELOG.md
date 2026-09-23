# Changelog

## v2.6.1 — 2026-09-23

The contract is now aligned with `flutter-ui-revamp` v1.4.0, which added about 40 licence-verified sources, direct download URLs and new `fetch_asset.py` behaviour.

### Changed
- `sibling-contracts.md`: the `flutter-ui-revamp` row now targets v1.4.
  - The Step 3 licence pre-answer rejects no-licence art.
  - CC BY-SA assets are allowed only if used unmodified, never recoloured (trap 8).
  - The licence judged is the **upstream** art's licence, not the pub wrapper's (trap 11). So `solar_icons` and `iconsax_flutter` are rejected, and `animated_emoji` counts as CC BY.
  - Nothing under the Remix Icon License may be used as a launcher, splash or store icon (trap 12).
  - Assets are fetched only through the *Direct download URLs* sections or `--local`, never from guessed URLs.
  - The icon set must expose const `IconData`, so `apply_icons.py` can swap it.
  - Step 4 uses `--filename` for generic basenames and `--strip N` for nested archives. When `fetch_asset.py` refuses a download, the fix is to pick another source.
- Checklists: the design `[cons]` assets line and the QA `[sec] [E]` asset-licence line now check the upstream licence, unmodified BY-SA assets and the Remix app-icon rule. The design line also checks for const `IconData`.

## v2.6.0 — 2026-09-23

A run now also ends with an App Store-ready iOS kit, prepared on any OS (including Linux). The IPA itself is built later on a Mac with one command, and nothing is uploaded. The iOS logic lives in the new sibling skill `flutter-ios-release`; flutter-factory only wires it in and gates on it.

### Added
- **`ios_release: true`** is on by default in `config.yaml`.
  - T01 creates `ios/` even on Linux, which overrides `flutter-init`'s "non-macOS → android only" rule.
  - Architecture records an iOS `DECISION-*`: bundle id, team id or "at build time", device family, deployment target, encryption exemption.
  - A final implementation task (`tasks-schema.md` rule 10, example T13, `files` = `ios/**`, `ios-release/**`, `.gitignore`) runs `flutter-ios-release`. It never touches `lib/`, so rule 9 now reads "last *screen-affecting* task is UI polish".
- **`verify-gate.sh --check NAME=COMMAND`** (repeatable): a generic extra gate step that runs in the project dir and passes on exit 0. The release gate uses it as `--check ios_kit='python3 <flutter-ios-release>/scripts/ios_prep_check.py --project .'`.
- **`advance` out of `release`** requires an `ok` `ios_kit` step when `ios_release: true`, unless `fallbacks.flutter-ios-release: inline` is set (then only a note is printed).
- **`evidence-pack.sh` writes `ios.txt`**: Info.plist usage/compliance keys, bundle id/team/device family/deployment target, privacy-manifest registration, and the `ios-release/` listing.
- **QA with `ios_release`**:
  - `ios_prep_check.py --out evidence/ios-prep.json` and `appstore-review-checker` (report only) → `evidence/appstore-review.md`.
  - New `### iOS [sec]` checklist block: no BLOCK, every usage string traces to a feature, privacy manifest matches collected data, confirmed guideline FAILs become findings.
- **Other checklists and templates**:
  - Architecture checklist: iOS decision line.
  - Planning checklist: iOS kit task line.
  - Release self-checklist: `ios_kit` ok, and notes say "ready to build on a Mac", never "IPA built".
  - Report template: `ios_kit` row in §2 and Mac build steps in §7.
- **`sibling-contracts.md`**: rows for `flutter-ios-release` and `appstore-review-checker`. The latter was moved out of "not invoked".

## v2.5.0 — 2026-09-23

An audit of v2.4.0 found that `advance` checked less than the SKILL.md said it did, and that the contract with `flutter-ui-revamp` v1.2.0 had drifted. The last implementation task could not pass its own self-check. The scripts were re-run against a real `flutter create` project (Flutter 3.47.4).

### Fixed
- **`advance` skipped the regression check.** `review_ok` validated the latest review without `--prev`, so a v2 APPROVE that silently dropped a previous finding's Regression row still advanced the stage. From v2 on it now passes `--prev <stage>-v(N-1)-gate.md` (after a human rejection) or `<stage>-v(N-1).md`. A missing previous file blocks.
- **Artifacts edited after APPROVE advanced unreviewed.** `advance` now blocks when any file under `artifacts/<stage>/` is newer than the approving review. That excludes `evidence/`, `logs/` and `verify.json`, and adds `tasks.json` for planning and `decisions/` for architecture.
- **Constitution check missed empty trailing values.** A value left blank after a label (e.g. "additional locales:") passed as filled. Now any `- …:` line that ends with no value blocks. The template asks for "none" explicitly.
- **`evidence-pack.sh`**: an option given without its value died with "unbound variable" (exit 1). It now exits 2 with usage, like the other scripts.
- **The UI-polish task (T12) could not pass its self-check** (`tasks-schema.md` rule 9):
  - Its `files` globs omitted things `flutter-ui-revamp` must touch: the app shell (`theme:` wiring, `RiveNative.init()`), the router/About screen, `lib/l10n/**`, `pubspec.lock` and `test/**`.
  - Its `verify` always built an APK, so the task went `blocked` on machines without an Android SDK. `verify` now follows `release_build` and `env.md`.
  - Its commits carried no task id. The task commit is now the `--no-ff` merge of `ui-revamp/*` with `feat(infra): <title> [<id>]`, and `.revamp/` is untracked in that commit.
- **`flutter-ui-revamp` v1.2 stopped the run for the user.** Its contract row now pre-answers every stop: Step 1 scope proposal (explicit `scope`), Step 2 design-direction agreement, Step 3 licences, and Step 6 dry-run diff (the orchestrator resolves `unmapped`/`DROPPED`/`COLLISION` itself and authorises `--apply --yes`). It also names the packages the skill adds (`lucide_icons_flutter`, `rive` 0.14, `flutter_gen` ≥ 5.15), each of which needs a dependency-table row + `DECISION-*`. Widget tests with icon finders are updated in the same task. Step 7 `--analyze-size` without an SDK counts as `skipped_env`.
- **`store_bound` QA could never advance.** Committing `store-metadata/` moved HEAD away from the test `verify.json`. The test gate is now re-run on that commit before the QA review.

### Changed
- The planning checklist checks the T12 `files`/`verify`. The per-task self-checklist gained a UI-polish line.
- `SKILL.md` is under 500 lines (498). The parallel-worktree procedure and the panel merge rules had been written out in both `SKILL.md` and the references; they now live only in `tasks-schema.md` / `reviewer-prompt.md`. The reviewer-backend table moved to `reviewer-prompt.md`, and the `state.yaml` example is now a one-paragraph key list.

## v2.4.0 — 2026-09-23

The core principle ("a stage never advances on a claim") was prose only; the scripts now enforce it. Every fix below was found by exercising the v2.3.2 scripts and exercised again against a real `flutter create` project.

### Added
- **`pipeline-state.sh advance` / `check`** — the only way to change stage. Refuses (exit 1, reasons listed, refusal logged) unless, for the stage being left: the latest `reviews/<stage>-vN.md` re-validates as APPROVE; `gates.<stage>: approved` when the stage is in `human_gates`; `verify.json` passed on a clean tree whose `git_sha` is the project's HEAD (implementation, test, qa, release); key artifacts exist (filled constitution, `idea.md`, `prd.md` + `tasks.json`, valid `style:`/`seed:` lines, `DECISION-001.md`, no pending task, QA `evidence/index.json`, release notes + `v*` tag on HEAD). `--override "<reason>"` only on explicit user instruction, logged as `OVERRIDE` and reported in `notes.md` §6. `set stage` now warns.
- **`verify.json` is bound to a commit** — `git_sha` + `dirty` (tree state when the gate started, `.pipeline/` excluded).
- **`verify-gate.sh --coverage [--min-coverage <pct>]`** — lcov line coverage in `verify.json` (`coverage.percent`, `min`), a `coverage` step that fails below the PRD target, and `tests` pass/skip/fail counts parsed from `flutter test` for every run. The test checklist's coverage and counts lines are now answerable (`[E]`) instead of failing by construction.
- **`review-verdict.sh --prev <previous report>`** (mandatory from v2): exactly one Regression row per previous finding, no invented rows, a `resolved` id may not stay in Findings, new ids must exceed the previous maximum. Also validates `## Checklist results` as `- [pass|fail|n.a.] …` bullets and rejects more `[fail]` lines than findings (except ESCALATE). v2.3.2 accepted a v2 report that silently dropped F-02…F-05 and restarted numbering.
- **Git layout** section: the project repo is the only repo committed to; `.pipeline/` never enters it. `init` adds `.pipeline/` to `.git/info/exclude` of the repo containing root/project and is re-run after T01 (records `project_dir`). No nested repo inside an existing one (`flutter-init` trap documented). Gates run on committed code.
- **Human-gate rejection file** `reviews/<stage>-vN-gate.md` (REVISE, the user's note as a `major` finding) so the next review has a `--prev` target.

### Fixed
- **Parallel implementation could not work**: several subagents cannot hold different `task/<id>` branches in one checkout. Now one `git worktree` per task (`../wt-<id>`), merged in id order by the orchestrator, then removed.
- **bash 3.2 (macOS `/bin/bash`)**: `review-verdict.sh` used `declare -A`; `verify-gate.sh` expanded an empty `DEFINES[@]` under `set -u` ("unbound variable") on every build without `--dart-define`. Both removed; options missing their value now exit 2 instead of looping.
- **`integration_test/`**: with only `integration_test/`, `flutter test` looked for `test/` and failed; with both, integration tests never ran although the checklist demanded one `[E]`. The gate now runs `flutter test test`; `integration_test/` runs only with `--integration-device <id>` (else `skipped_env`). The primary flow is a headless widget flow test in `test/flows/`.
- **Release gate verified a different commit than the one tagged** (verify → bump → commit → tag). New order: bump + commit → verify on that commit → notes → human gate → tag → `advance`.
- **`release` human gate had no defined moment** ("after its review approves" — release has no reviewer). Now: after the release verify and notes, before the tag.
- **Constitution was never filled at a defined point**, yet reviewers score contradictions with it as `critical`. It is now filled at `env` (derived, guesses marked `(assumed)`); `advance` refuses empty fields.
- Coverage percentage is computed with `LC_ALL=C` so a comma-decimal locale (e.g. `vi_VN`) cannot produce invalid JSON.

### Changed
- `state.yaml`: reviewer APPROVE is `review.<stage>`; `gates.<stage>` is only the human answer (they used to share a key, so an APPROVE could stand in for the human gate).
- Reviewer prompt: test stage also gets the project dir; `verify.json` fields explained; Checklist results format fixed.
- Bugfix cycle and test stage: commit first, then gate. `flutter-store-compliance`'s `store-metadata/` must be committed before the release commit.

## v2.3.2 — 2026-09-22

### Added
- **`flutter-ui-revamp` as the mandatory last implementation task** (`tasks-schema.md` rule 9, example `T12`): runs once every screen exists and the tree is clean, takes `style`/`seed`/`keep` from the approved `design-system.md`, merges its `ui-revamp/*` branch back and re-runs the gate. Planning checklist rejects a plan without it; inline fallback when the skill is absent. Wiring: `design-system.md` must open with `style:` (one of the five `flutter-ui-revamp` recipes) and `seed: #RRGGBB` (design stage note + `[cons]` checklist line); `sibling-contracts.md` row lists its traps (dirty-tree STOP, licence-approval pre-answer, `keep:` so it extends rather than rebuilds `lib/theme/`, branch merge, `.revamp/` → evidence); QA `[sec] [E]` line audits `assets/CREDITS.md` for licence and on-screen attribution.
- **Rule 9 — the app speaks English first.** Every generated app ships English as its default and first locale: user-facing copy is authored in English in `lib/l10n/app_en.arb` (`flutter gen-l10n`), `en` is first in `supportedLocales`, and other locales — including the user's own — are additional ARBs added only when the PRD lists them. Dart identifiers/comments are English. Pipeline artifacts stay in the user's language. Wired through: `idea` assumption line, planning NFR check, design `[cons]` copy check, architecture `[fit]` l10n line, qa `[cor]` no-hardcoded-strings line, per-task self-check, and the constitution template (`pipeline-state.sh init`).
- **Rule 8 — English commit messages.** Every commit the pipeline makes (scaffold, per-task, bugfix, release) or delegates to sibling skills / parallel subagents is written in English, regardless of the language of the user, `idea.md` or the PRD. `tasks.json` `title`/`feature` are English because they are interpolated into `feat(<feature>): <title> [<id>]`; `tasks-schema.md` rule 8 says to translate when converting `tasks-generator` output. Self-checklists (per task, bugfix, release) each gained a line; release commit is `chore(release): v<version>`, bugfix commits `fix(<feature>): <summary> [F-nn, …]`.

## v2.3.1 — 2026-09-21

Script fixes found by exercising the v2.3 scripts against edge cases, plus contract drift against the installed sibling skills.

### Fixed
- `scripts/review-verdict.sh` rejected a valid `ESCALATE` that carried only minor (or zero) findings — the exact shape the Scope rule asks for when an upstream artifact is defective. The "only minor findings" check now applies to `REVISE`/`BLOCK` only; the orchestrator no longer burns its two re-runs and self-escalates for a format reason.
- `scripts/evidence-pack.sh` — the "components without explicit `exported`" awk skipped every self-closing single-line component (`<activity … />`) and merged its block into the next tag, so the `[sec] [E]` manifest line could pass on a component that had no `android:exported`. Rewritten to evaluate the opening tag on the same line; `activity-alias` added; prints `(none)` instead of nothing.
- `scripts/verify-gate.sh` — a stale `ANDROID_HOME`/`ANDROID_SDK_ROOT` (set but without `platforms/`) survived the candidate loop, so `--build apk` ran and reported `fail` instead of `skipped_env`. SDK is now empty unless a candidate actually exists.

### Changed
- `sibling-contracts.md`, `SKILL.md`, `reviewer-prompt.md`: `code-review mode:review` writes `<project>/CODE_REVIEW.md` — the orchestrator must **move** it into `evidence/`, otherwise it lands in the next bugfix diff. `flutter-store-compliance` output path named (`store-metadata/compliance-report.json`). `dont-make-me-think` removed from the Repo Sync trap list — only its Redesign mode syncs, and the pipeline never uses that mode.
- `report-template.md` no longer hardcodes `v2.0.0` in the run header.

## v2.3.0 — 2026-09-21

Review skills now actually take part in reviews. Until now `code-review`, `dont-make-me-think` and `flutter-store-compliance` were listed as "preferred skills" for the qa/design stages, but the reviewer runs as `subagent_explore` (no `skill` tool, no shell) and nobody was told to run them — so they never ran.

### Added
- `scripts/evidence-pack.sh` — side-effect-free fact collection for the QA reviewer: `analyze.txt`, `outdated.json`, `deps.txt`, `secrets.txt`, `manifest.txt` (permissions, `exported`, cleartext, debuggable, deep-link data), `gradle.txt` (ids, SDK levels, minify), `patterns.txt` (context-after-await, bare `!`, print, `http://`, bare `CircularProgressIndicator` in features, `// ignore:`, `badCertificateCallback`, SharedPreferences+token, double-for-money, unawaited-looking calls) and `index.json`. Never modifies the project.
- **Evidence pack contract**: the orchestrator runs the script plus the installed review skills (`code-review mode:review` → `code-review-report.md`; `flutter-store-compliance` → `compliance-report.json` when `store_bound`; `dont-make-me-think` on `ux.md`/`ui.md` → `dmmt-report.md`) into `artifacts/<stage>/evidence/` **before** spawning the reviewer.
- **Methodology hand-off**: reviewer prompt receives absolute paths to `code-review/references/review-mode.md`, `code-smells.md`, `dont-make-me-think/references/krug-principles.md` to read and apply as an extension of the checklist.
- `→ file` hints on every `[E]` qa line in `review-checklists.md` pointing at the evidence file/section that normally proves it.

### Changed
- Reviewer stays read-only. Rule made explicit: checklist = verdict contract; skill reports = inputs; a skill's finding becomes an `F-nn` only after the reviewer confirms the `file:line`; a skill's own severity/verdict is not binding.
- `sibling-contracts.md` rows for the three review skills describe the evidence flow; pipeline table separates "generate" skills from "evidence for review" skills.

## v2.2.0 — 2026-09-21

Every review point now has a checklist that fits it.

### Added
- `qa` checklist rebuilt from 7 bundled bullets into 26 single-answer lines in four groups (Correctness, Performance, Security & data, Fidelity & clean code) with Flutter-specific checks: `BuildContext` after `await`/`mounted`, unawaited futures, disposal/`autoDispose`, money-as-double, isolates for heavy work, `android:exported`, `usesCleartextTraffic`, `debuggable`, R8, `flutter pub outdated` advisories, deep-link input validation.
- **Lens tags** on every panel-stage line — `[sec]`/`[cor]` (qa), `[feas]`/`[fit]` (architecture), `[use]`/`[cons]` (design) — so each panel member knows which lines it owns; `reviewer-prompt.md` lens table uses the same ids.
- **Self-checklists** for review points that have no reviewer: *implementation — per task* (recorded in `artifacts/implementation/tasks-log.md`), *bugfix cycle* (top of `fix-NNN.md`), *release* (`notes.md` §2).
- Gaps filled in existing lists — idea: success signal, data sensitivity, IP/content rights · planning: data model sketch, external dependencies + failure mode, risks, test strategy · design: responsive breakpoints, back behaviour, destructive-action confirm, semantics labels, asset licences · architecture: error/logging strategy, offline/sync + migrations, test seams, CI · test: no real network/clock, flaky patterns, coverage figure quoted.

### Changed
- `SKILL.md` stage notes for implementation, bugfix and release point at their self-checklists.

## v2.1.0 — 2026-09-21

Reviewer hardening — every change targets a way the v2.0 review loop could fail to converge or be rubber-stamped.

### Added
- `scripts/review-verdict.sh` — validates a review report: verdict line, `F-nn` ids unique and well-formed, valid severities, REVISE/BLOCK need ≥ 1 finding, APPROVE forbids critical/major, unresolved regression rows must reappear in Findings, required headings. Prints `VERDICT critical= major= minor= …` (or `--json`); exit 1 lists every `MALFORMED:` reason for the reviewer re-run. Orchestrator no longer parses verdicts by hand.
- **Regression list** — from revision v2 the reviewer receives the previous revision's Findings table (facts, not reasoning) and must return a `## Regression` table marking each `F-nn` resolved/unresolved. Finding ids continue across revisions so `bugfix/fix-NNN.md` references stay unambiguous.
- **Panel review** — `panel_stages` (default `[qa]`): parallel reviewers with different lenses (`qa`: security + correctness; `architecture`: feasibility + constitution-fit; `design`: usability + consistency), merged by strictest verdict and union of findings. Cheap diversity when the backend is the same model.
- **Timeout + fallback** for async backends — `review_timeout_min` (default 15): no report file → re-run once → fall back to `subagent`, logged.
- **Scope rule** — approved upstream artifacts are context, not subject; a defect found there → ESCALATE naming it, never a REVISE of the current stage.
- **`[E]` evidence-required lines** in `review-checklists.md` (11 lines: security, tests exist, architecture fidelity, org, secrets path, tasks schema …) — a `pass` without quoted file:line / command / `verify.json` step counts as `fail`.
- Human-gate question now carries the reviewer Summary + artifact paths so the user judges the artifact, not the chat.

### Changed
- `reviewer-prompt.md` rewritten around a "given / withheld" table; `report-template.md` records panel stages, malformed re-runs and severity totals.

## v2.0.0 — 2026-09-21

### Added
- `scripts/pipeline-state.sh` — `init · status · get · set · bump · log` over a flat, dotted-key `state.yaml` plus an append-only `events.log`; `init` is idempotent and also seeds `config.yaml` and a `constitution.md` template.
- `scripts/verify-gate.sh` — `pub get → analyze → test → build` with `ok | fail | skipped_env | skipped_user` per step, writes `.pipeline/artifacts/<stage>/verify.json`; `--release` additionally blocks on `com.example.*` applicationId and secret literals in `lib/`. Exit 1 on any fail.
- `references/review-checklists.md` — per-stage checklists (idea, planning, design, architecture, test, qa) and a shared critical/major/minor severity scale mapped to verdicts.
- `references/reviewer-prompt.md` — the complete stateless reviewer briefing, the mandatory report format (`## Verdict`, numbered `F-nn` findings table), and orchestrator-side parsing/fallback rules.
- `references/tasks-schema.md` — `tasks.json` schema (`id`, `depends_on`, `files`, `verify`, `parallel_safe`), T01-is-scaffold rule, parallel-safety rules, and the implementation loop.
- `references/sibling-contracts.md` — real inputs/outputs of every preferred sibling and the traps: planning skills' mandatory `git pull --rebase` (stops without `origin`), `prd-generator` needing `validate.md`, `flutter-init` `org` with no default and no web platform, `test-coverage` creating a branch, `code-review` modes.
- `references/report-template.md` — release notes skeleton filled only from `verify.json`, `state.yaml`, `events.log`, `reviews/`, `tasks.json`.
- Stage 0 `env` (`flutter doctor -v`) and config keys `release_build`, `store_bound`.
- "When to use which orchestrator" table disambiguating from `flutter-all-platform`, `idea-to-play-store`, `ai-factory`.

### Changed
- **Skill discovery** no longer filters on frontmatter `capabilities` (only ~9/67 installed skills declare it, so v1 fell back to inline work for almost everything). Now: preferred skill **by name** via the `skill` tool → capability keyword search → `capabilities` only as a tie-breaker → inline fallback recorded in state. Filesystem probing is limited to `.pipeline/skills/`.
- Pipeline table is Flutter-aware: `org` is asked at `architecture` (`DECISION-001`), `flutter-init` is task T01, `verify-gate --no-test` runs after every implementation task, `test`/`release` gates run real `flutter analyze/test/build`, release ends in a tagged build-verified commit and hands off to `flutter-signing → flutter-build → store skills`.
- Preferred skills extended: `tasks-generator`, `logo-designer`, `flutter-init`, `firebase-auth-setup`, `release-manager`, `auto-push`, `flutter-store-compliance` (when `store_bound`).
- Reviewer contract now requires numbered findings with severity + `file:line`; the QA bugfix loop maps `fix-NNN.md` to those numbers.
- Parallel implementation defines branch-per-task (`task/<id>`), orchestrator-side merge in id order, and gate after each merge.
- Frontmatter aligned with the repo (`license`, `effort`, `metadata.version/author`); description gained Vietnamese triggers and a "Don't use for" clause; `network: enabled: true` (pub get, opencode backend).

### Breaking Changes
- `state.yaml` is flat with dotted keys (`revisions.planning: 2`, `gates.idea: approved`) instead of nested maps, and must be written through `pipeline-state.sh`. v1 nested state files are not read — re-run `init` and set the keys.

## v1.0.0 — 2026-09-21

### Added
- Initial single-file skill: 8-stage review-gated pipeline, `.pipeline/` workspace, reviewer backends (`subagent | opencode | herdr`), human gates, capability-based skill discovery.
