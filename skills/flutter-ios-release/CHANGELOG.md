# Changelog

## v1.0.0 — 2026-09-23

### Added
- `scripts/ios_prep_check.py`: a static App Store readiness check that runs on any OS and has no dependencies beyond the standard library. It checks:
  - bundle id, team, signing style, deployment target;
  - device family and iPad orientations (ITMS-90474);
  - display name, pubspec version → IPA version, export-compliance key, launch screen;
  - usage strings for 27 permission plugins (ITMS-90683);
  - privacy manifest bundling;
  - the 1024 icon: size, alpha (ITMS-90717), and whether it is still the Flutter default;
  - Guideline 4.8 hint, tracked signing secrets, kit completeness.

  Output is JSON, one level per check (`OK | WARN | BLOCK | INFO`). Exit 1 on any `BLOCK`.
- `scripts/ios_prep_apply.py`: an idempotent editor for the `flutter create` layout. It sets:
  - bundle id (with `.RunnerTests`), `DEVELOPMENT_TEAM`, `TARGETED_DEVICE_FAMILY`, deployment target (plus the Podfile line);
  - display name, `ITSAppUsesNonExemptEncryption`, usage strings;
  - creates `PrivacyInfo.xcprivacy` and registers it in the Runner group and Resources phase;
  - adds the signing-secret patterns to `.gitignore`;
  - writes `ios-release/`.

  Tested against Flutter 3.47.4 `flutter create` output; the patched `project.pbxproj` re-parses with the independent `pbxproj` library.
- `templates/build-ios.sh` (macOS, bash 3.2): requires Xcode ≥ 26 (iOS 26 SDK is the App Store Connect minimum since 2026-04-28).
  - Runs `flutter build ios --config-only`, then `xcodebuild archive` and `-exportArchive` with `-allowProvisioningUpdates`. It authenticates through the Xcode Apple ID or an App Store Connect API key (`ASC_*` env).
  - Verifies the IPA: bundle id, version = pubspec, SDK ≥ 26, Apple Distribution signature, embedded profile, privacy manifest bundled. Result goes to `ios-release/build-verify.json` with `git_sha` and `dirty`.
  - Never uploads. On Linux it only exercised the environment guard (exit 2); the archive/export path has not been run yet.
- `templates/README.md`: one-time Apple setup, build, optional upload, and the listing items App Store Connect still needs.
