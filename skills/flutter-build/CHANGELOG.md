# Changelog

## v2.1.0 — 2026-09-13

### Added
- `scripts/verify-artifact.sh` — Step 6 as one deterministic script emitting `build/release/verify.json`: freshness vs build start, applicationId placeholders, targetSdk against today's date, debuggable, versionCode ceiling, signing (`jarsigner` for AAB, `apksigner` for APK — correctly distinguished), 16 KB LOAD alignment per `.so` with the offending path, size tiers. Vocabulary `OK/WARN/BLOCK/UNVERIFIED`; a missing tool is `UNVERIFIED`, never `OK`. Shared with `flutter-publish` preflight.
- `build-info.json` gains `verify` (path to `verify.json`); provenance fields are copied from it instead of recomputed.

### Fixed
- Step 6 used `stat -c %Y` and `readelf` (GNU-only); on macOS both failed silently. The script falls back to `stat -f %m` and `llvm-readelf`/`greadelf`, and reports `UNVERIFIED` rather than passing when neither exists.
- The 16 KB check accepted only `0x4000`; `0x8000`+ alignments (valid) were flagged. Now any alignment ≥ 16 KB passes.

### Breaking Changes
- None.

## v2.0.0
- Pre-build gates, stale-artifact detection, debug-info retention per version code.
