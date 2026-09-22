# Changelog

## v2.3.2 — 2026-09-22

### Added
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
