# Changelog

## v2.1.0 — 2026-09-13

### Added
- `scripts/derive-facts.sh` — Step 1 as a script. Direct (non-dev) dependencies, every manifest under `android/app/src/`, gradle identity → `derived.json` with `pubspec.yaml:<line>` evidence per fact, restricted/sensitive/normal permission classes, `unknown_sdks`, `local_only`, `identity`. `flutter-store-compliance` v2.1 runs the same script for its cross-check, so the two skills can no longer disagree about what the app does.
- Facts added: `crash_reporting` (counts as data collection), `push_notifications`, `uses_location/camera/contacts` (package **or** permission), `network_access`, `local_only`.

### Fixed
- The prose derivation read `dependencies:` through `dev_dependencies:` with `sed`, which included dev-only packages (e.g. `google_mobile_ads` in dev deps → `has_ads: true`). The script stops at the next top-level key.
- Permissions were read from `main/AndroidManifest.xml` only; flavor manifests under `android/app/src/<flavor>/` were missed.

### Breaking Changes
- `store-listing.json → derived` is now the script's full object (superset of v2.0's fields; `evidence` is an object of arrays instead of strings).

## v2.0.0
- Derived facts, placeholder tracking via `unresolved[]`, evidence-based privacy policy.
