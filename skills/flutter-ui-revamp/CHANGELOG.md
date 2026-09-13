# Changelog

## v1.1.0 — audited 2026-09-13, no code changes needed

Audit of the 1.1.0 release (committed separately). This entry records what was verified and why nothing was changed.

### Verified in this audit
- `scan_project.py` on a synthetic project: detects `NO_DARK_MODE`, `HARDCODED_COLORS`, `INLINE_TEXTSTYLE`, `PLAIN_LOADER`, `MISSING_ASSETS` (pubspec entry pointing at a nonexistent dir), density/WebP/vector findings; `derived.ui_framework` and `state_management` correct.
- `generate_icon_map.py` → `apply_icons.py` dry run: swaps `Icons.home`/`Icons.settings`, adds the import once, **leaves `Icons.*` inside comments and string literals untouched** (the `dart_lex` tokenizer works).
- `optimize_flutter.py` dry run prints the pubspec snippet with only existing directories.
- `fetch_asset.py` refuses `GPL-3.0` without `--force`, as documented.
- All five scripts compile and answer `--help`; `dart_lex.py` self-test passes.

### Why no further changes
The skill already has what the other skills in this repo were missing: deterministic scripts for every mechanical step, dry-run-by-default writes, a safety step that refuses to run on a dirty tree, and a report whose numbers come from the audit rather than from memory. Its remaining risks (font not actually loading at runtime, contrast on hand-edited slots) are already called out in Step 7 with the honest "only a screenshot proves it". Nothing found justified a change.

### Added (1.1.0, from the installed copy)
- `references/style-recipes.md`, `scripts/generate_icon_map.py`, Cupertino/mixed theme path, priority-screen proposal for large apps, const-hazard detection in `apply_icons.py`.

## v1.0.0
- Initial release.
