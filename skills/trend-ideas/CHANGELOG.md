# Changelog

## v2.2.0 — 2026-09-13

### Added
- `fetch_trends.py`: `--limit`, `--min-volume`, `--retries` (3× exponential backoff on network errors / 429 / 5xx), `--save-raw` and `--from-file` for offline, reproducible re-runs. `fetched_at` and `requested` in the output envelope.
- **Per-idea output contract**: `ideas/<n>-<slug>/{idea.md, validate.md}`, and the winner copied to `<output_dir>/idea.md` + `validate.md` — exactly the pair `prd-generator` consumes. Orchestrators no longer re-extract the idea from prose or re-run `idea-validator`.
- Input table (`output`, `output_dir`, `limit`, `from_file`).
- Edge case: `validate.md` missing a rating → idea marked `incomplete`, excluded from selection, disclosed.
- Edge case: existing `<output_dir>/idea.md` → ask before overwriting.

### Fixed
- **Topic URLs 404'd**: built as `explodingtopics.com/<path>`; pages live at `/topic/<path>`.
- **Growth semantics verified against live topic pages**: the field is a multiplier (2.12 → +212%); `99` is the upstream "+99X+" cap, now labelled `capped 99x+ (upstream cap, not a measurement)` instead of being reported as 9900% measured growth. The old "ratio vs already-percent overlap" caveat described a case that does not occur.
- **Contradiction removed**: Step 1 said "stop on fetch failure", Edge Cases said "scrape explodingtopics.com HTML". The page is client-rendered; scraped numbers are not the API's numbers. Now: stop, offer `--from-file`, no scraping.
- Script path was `python scripts/fetch_trends.py` (relative to cwd, which is never the skill dir). Now resolved from the skill directory; `python3` explicit.
- `docs/README.md` hardcoded `~/.config/opencode/skills/idea-validator/` — contradicted SKILL.md's "do not probe a path". Removed.
- Script tolerates `growth` as a scalar or dict, `trends`/`data` envelope, non-numeric volume.

### Improved
- Core principle stated: every number is copied from the script or from `idea-validator`; the skill never scores.
- Report header carries `count/requested`, `source`, `fetched_at`; topic table carries `growth_basis` so a 100× misread is visible.

### Breaking Changes
- None for callers. Output adds files (`ideas/`, `idea.md`, `validate.md`) but the report format is a superset of v2.1.

## v2.1.0
- Previous release: growth normalisation with `growth_basis`, host-agnostic idea-validator invocation.
