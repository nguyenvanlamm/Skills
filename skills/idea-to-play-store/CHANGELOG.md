# Changelog

## v2.1.0 — 2026-09-13

### Fixed
- **Contracts re-checked against the installed siblings' SKILL.md**: `idea-validator` takes no output dir (steer with `IDEAS_ROOT`), `tasks-generator` takes the `prd.md` *file* path, and the four planning skills stop on a missing git `origin` unless told the repo is local-only.
- **Non-existent skill/agent calls**: `/agent feature-gen-crud` (no such agent) → features are generated from `references/feature-templates.md`, optionally in parallel subagents. `social-poster` note kept.
- **Wrong sibling contracts**: `prd-generator` was given a `validate.md` path; it needs `idea.md` + `validate.md` in one directory. `deploy-render --db postgres` (flag does not exist) → default DB, `--no-db` to opt out, `--health-path /api/health`. `flutter-init --platforms "android,ios"` on an Android-only pipeline → `android`.
- Phase 1 ran `idea-validator` **again** after `trend-ideas` had already validated — a second, different score. Removed.
- Heading said `auto_route`, code used `go_router`. Now go_router throughout.
- Backend template: `allow_origins=["*"]` and a hardcoded `service-account.json` path → env-driven `ALLOWED_ORIGINS` and `GOOGLE_APPLICATION_CREDENTIALS`.
- `needs_backend` derived by `grep -qi "api\|sync"` matched "capital", "asynchronous". Now read from the PRD feature list.
- Google sign-in code was generated unconditionally; `firebase-auth-setup` enables `email` only by default. Now gated on `auth_providers`.
- Phase 3b claimed `firebase-auth-setup` produces `google-services.json` / `firebase_options.dart`; it creates a **Web** app. Added the `flutterfire configure` step and the SHA-1 hand-off from `flutter-signing`.

### Changed
- **Abort no longer deletes `$PRODUCT_DIR`.** It stops and leaves the directory + state file. Deleting is the user's action.
- State file `.idea-play-store-state.json` is now specified (fields, when written) and resume is a first-class path — v2.0 mentioned it in one edge-case row and never defined it.
- SKILL.md 1160 → ~330 lines. Dart/Python templates moved to `references/feature-templates.md` and `references/backend-template.md` (content preserved, placeholders annotated).
- Phase reports must copy numbers from sibling outputs (`validate.md`, `build-info.json`, `compliance-report.json`) — stated as the core principle.

### Added
- "How sibling skills are invoked" contract table; per-phase availability check.
- `org` asked explicitly with the permanence warning (no default).
- Final report "You still have to" list: keystore backup, manual upload, privacy-policy hosting, Data safety from `data-safety.md`, SHA-1 for Google sign-in, closed-test rule, Render DB expiry.
- Edge cases: resume, Firebase quota → `--project-id`, `flutterfire` missing, analyze red after 3 rounds, insist on `production`.

### Breaking Changes
- Abort behaviour (no deletion) — intentional.
- Planning files live in `plan/` with default names (`tad.md`, not `architecture.md`).

## v2.0.0
- Gate before Phase 5, removed the non-existent `social-poster` call.
