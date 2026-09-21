# Changelog

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
