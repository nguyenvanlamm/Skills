# Changelog

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
