# Changelog

## v2.1.0 — 2026-09-13

### Added
- `scripts/inspect-toolchain.sh` — Step 1 as a script: Flutter version/channel, JDK major, SDK path and layout (`cmdline-tools/latest`), platforms, build-tools, NDKs, adb + devices; prints verdict lines and JSON. Never installs.
- `scripts/pin-android-config.sh` — Step 5 as a script: pins `compileSdk`/`targetSdk`/`minSdk`/`ndkVersion` in **Groovy or Kotlin DSL**, auto-selects the newest installed NDK r28+, keeps a `.bak`, fails instead of guessing on a non-template file. Tested on both DSL shapes.
- `lib/features/home/home_screen.dart` in the scaffold: `routes.dart` referenced `HomeScreen` without defining or importing it, so a scaffold written verbatim did not analyze clean.

### Fixed
- Step 5 showed Groovy-only syntax (`compileSdk 36`) while `flutter create` now emits `build.gradle.kts`, where that line is a syntax error. Both DSLs are covered; the shown form (`key = value`) is valid in both.

### Breaking Changes
- None.

## v2.0.0
- Permanent-decision focus (applicationId, SDK levels), API 36 / NDK r28, credentials gitignored at init.
