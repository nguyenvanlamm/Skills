# Changelog

## v2.2.0 — 2026-09-13

### Added
- `scripts/preflight.sh` — all ten gates as one script emitting `store-metadata/preflight.json` (`OK/WARN/BLOCK/UNVERIFIED`): provenance vs `build-info.json`, compliance verdict (JSON, with v1-markdown fallback parsing FAIL before PASS), artifact checks delegated to `flutter-build/scripts/verify-artifact.sh`, version code vs `publish-state.json` incl. `pending_upload` and app-id drift, credentials in index and history, store assets per locale + `unresolved`. Exit 1 on any BLOCK.
- Deterministic AAB selection: explicit `--aab`, single candidate, `build/release/app-release.aab`, or stop and list — replaces `find … | head -1`, which contradicted the reference's own "never silently take the first".

### Fixed
- `console-guide.md` and `troubleshooting.md` told the user to import `store-metadata/data-safety.csv` — a file `flutter-store-compliance` deliberately does **not** produce (versioned schema, false-declaration risk). Now points at `data-safety.md` as an answer sheet.
- Gate 10 and the console guide read descriptions from `store-metadata/description/*.txt`; the metadata skill writes `description/<locale>/`. Paths aligned; `unresolved` is checked too.

### Breaking Changes
- None.

## v2.1.0
- Missing-state handling, `pending_upload`, upload recorded only when confirmed.
