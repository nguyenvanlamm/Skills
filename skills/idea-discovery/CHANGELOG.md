# Changelog

## v2.1.0 — 2026-09-13

### Added
- `research-log.md` output: every query both agents ran, hit or miss, with source URL. Makes "no data found" auditable and the "nothing worth building" verdict defensible.
- `queries_run[]` and `sources[]` in both research agents' output contracts (mandatory even when empty).
- **Minimum bar** in the synthesizer: a candidate needs a linked Pain or Demand signal ≥ 6 and a named competitor with looked-up rating/last-update. Below the bar → "No viable opportunity", no `idea.md`.
- Dimensions without evidence score `—` (no data) instead of an implicit 5; totals show `N dims scored`.
- Explicit execution modes: parallel subagents when the host has a task tool, inline sequential otherwise — same output contract. The report says which ran.
- Research budget per agent (5–8 keywords; 8–10 Reddit queries + 3–5 apps).

### Fixed
- **Contradiction**: SKILL.md forbade estimates, but all three agent files had a "use general knowledge, label low confidence" fallback. Those fallbacks produced confident-looking matrices with no data behind them. Removed; agents now return empty results with `status: unavailable`/`no_data`.
- `pain-point-miner` declared an optional `keyword_gaps` input from `keyword-researcher` while both were launched in parallel — the field could never be populated. Removed; cross-referencing is the synthesizer's job (where it already was).
- Subagent launch instructions were host-specific (`task` tool). Now capability-based.

### Improved
- Core principle spells out the one legitimate use of prior knowledge: choosing what to search for.
- Acceptance criteria accept a "no viable opportunity" outcome as a pass when the log shows why.

### Breaking Changes
- Agents no longer emit "low confidence" fabricated findings. A run with no reachable sources now ends with an honest "no data" instead of an `idea.md`. This is the intended behaviour change.

## v2.0.0
- Previous release: parallel research agents, opportunity matrix, evidence-first idea.md.
