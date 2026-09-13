# Changelog

## v1.1.0 — 2026-09-13

### Added
- `references/mini-prompt-examples.md`: 4 worked mini-prompts (backend bug fix, Flutter UI, Python CLI feature, behavior removal) plus an anti-pattern table.
- `references/verification.md`: stack detection, scoped-then-wide commands per stack, runtime checks when no test suite exists, failure loop.

### Improved
- Verify step: run narrowest check first, then widen; report pre-existing unrelated failures instead of fixing them silently.

## v1.0.0 — 2026-09-13

### Added
- Initial release: Analyze → Mini-Prompt → Implement → Verify → Result flow for natural-language change requests.
- Mini-prompt template (Task / Context / Expected Result / Constraints / Implementation), generated per request and kept internal.
- Verification matrix (tests, type check, lint, build, runtime, project commands) with mandatory fix-and-retry loop.
- Result template (Changed / Verification / Notes).
