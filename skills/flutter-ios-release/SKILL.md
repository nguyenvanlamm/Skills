---
name: flutter-ios-release
description: >-
  Prepare a Flutter project's iOS side so it builds into an App Store
  Connect–ready IPA on a Mac with one command — from any OS, including Linux.
  Sets bundle id, team, device family, deployment target, Info.plist usage
  strings, export-compliance key and privacy manifest; statically checks
  what App Store Connect and review reject (alpha icon, missing usage strings,
  placeholder ids, tracked signing secrets); writes ios-release/ with
  build-ios.sh (archive + export + verify, never uploads), ExportOptions.plist
  and a README. Use when the user says 'chuẩn bị bản iOS', 'ios release kit',
  'app store ready', 'prepare ipa', 'build ios later on mac'. Don't use for
  uploading or submitting (Transporter/App Store Connect), App Store
  guideline audits (appstore-review-checker), Android signing/builds
  (flutter-signing, flutter-build), or non-Flutter iOS apps.
license: MIT
effort: high
metadata:
  version: 1.0.0
  author: "Nguyen Van Lam"
permissions:
  filesystem: { read: true, write: true }
  shell: { enabled: true }
  network: { enabled: false }
  secrets: { required: false }
---

# flutter-ios-release — App Store–ready iOS kit, built later on a Mac

## Core principle

> **Prepare everywhere, claim an IPA only on macOS.** Everything that is a
> file — bundle id, team, Info.plist, privacy manifest, export options, the
> build script — is done and checked here, on any OS. Signing and archiving
> need Xcode and the user's Apple account, so they happen later, in one
> command, and only `build-ios.sh`'s verification on the Mac may say "the
> IPA is ready".

Consequences:

- A Linux run ends with `ios_prep_check.py` at no `BLOCK` and a committed
  `ios-release/` — reported as "ready to build on a Mac", never as "built".
- Nothing uploads. `ExportOptions.plist` uses `destination: export`; upload
  is a manual step the user takes when they decide to.
- No secret enters the repo: team id is public, but `.p8` / `.p12` /
  `.mobileprovision` are git-ignored and the checker blocks if one is tracked.

## Input

| Field | Required | Default | Notes |
|-------|----------|---------|-------|
| `project` | ✅ | `.` | Flutter project root |
| `bundle_id` | ❌ | Android `applicationId` (`<org>.<slug>`) | never `com.example.*`; permanent once the app exists in App Store Connect |
| `team_id` | ❌ | unset → `IOS_TEAM_ID` on the Mac | 10 chars, developer.apple.com → Membership. Ask once; "later" is a valid answer |
| `display_name` | ❌ | `CFBundleDisplayName` from the template | home-screen name, keep ≤ ~12 chars |
| `device_family` | ❌ | `iphone` | `universal` adds iPad and makes iPad screenshots mandatory |
| `deployment_target` | ❌ | template value (15.0) | raise only if a plugin needs it |
| `encryption` | ❌ | exempt (`false`) | HTTPS / OS crypto only = exempt; custom crypto = ask |
| `usage` | derived | — | one English sentence per permission key, saying *why* the feature needs it |

Do not ask for anything else. The permission list is derived from
`pubspec.yaml` (`scripts/ios_common.py → PERMISSION_MAP`) plus the features in
the PRD/idea; the wording comes from those features.

## Workflow

### Step 1 — iOS platform present

```bash
ls ios/Runner.xcodeproj/project.pbxproj || flutter create --platforms ios .   # works on Linux
```

`flutter create --platforms ios .` only adds `ios/`; it does not touch `lib/`.
Commit it separately if it was missing (`chore(ios): add iOS platform`).

### Step 2 — Scan

```bash
python3 <skill>/scripts/ios_prep_check.py --project .
```

Read every row. `BLOCK` rows are the work list; `WARN` rows go to the report
unless the input already settles them.

### Step 3 — Apply

```bash
python3 <skill>/scripts/ios_prep_apply.py --project . \
  --bundle-id com.acme.spendly [--team-id ABCDE12345] --display-name "Spendly" \
  --device-family iphone --encryption-exempt \
  --usage NSCameraUsageDescription="Take a photo of a receipt to add it as an expense." \
  --usage NSPhotoLibraryUsageDescription="Pick a receipt photo from your library." \
  --privacy-manifest --kit
```

Idempotent (`--dry-run` prints what would change). It edits only the Runner
/ RunnerTests build settings, `Info.plist`, `PrivacyInfo.xcprivacy` (created
and registered in the Runner target's resources), the Podfile platform line
if a Podfile exists, `.gitignore`, and writes `ios-release/`.

Usage strings: English, specific, user-benefit first ("Scan a receipt to add
an expense"), never "This app needs camera access". A key with no feature
behind it is removed, not kept "just in case". If the app ships extra
locales, translate the strings in `ios/Runner/<lang>.lproj/InfoPlist.strings`.

The generated privacy manifest declares no tracking and no collected data.
If the app collects anything (accounts, analytics, crash reports, location),
edit `NSPrivacyCollectedDataTypes` to match — it must agree with the App
Privacy answers in App Store Connect. Plugins ship their own manifests.

Things the scripts cannot fix, and how:

| Row | Fix |
|-----|-----|
| `app_icon` alpha / default | regenerate icons with `flutter_launcher_icons` (`remove_alpha_ios: true`) from the real logo |
| `sign_in_with_apple` | add `sign_in_with_apple` + the capability, or record why Guideline 4.8 does not apply |
| `usage_strings_unused` | remove the key or name the feature that uses it |
| `permission_handler` | list every permission it requests and give each its key |

### Step 4 — Verify and commit

```bash
python3 <skill>/scripts/ios_prep_check.py --project . --out ios-release/prep-report.json   # must exit 0
flutter analyze
git add ios ios-release .gitignore && git commit -m "chore(ios): App Store release kit"
```

### Step 5 — Hand off

Tell the user, from `ios-release/README.md`: the one-time Apple setup (program
membership, app record with the bundle id, Xcode 26+ with an Apple ID or an
App Store Connect API key), then `bash ios-release/build-ios.sh` on the Mac,
which checks Xcode ≥ 26, runs tests, archives with automatic signing, exports
to `build/ios/ipa/`, verifies bundle id / version / SDK / distribution
signature / profile / privacy manifest, and writes
`ios-release/build-verify.json`. Upload stays manual (Transporter or `xcrun
altool`).

## Checks (`ios_prep_check.py`)

| Check | BLOCK when |
|-------|-----------|
| `ios_platform`, `pbxproj` | no `ios/` project or no Runner build configuration |
| `bundle_id` | inconsistent, `com.example.*`, not reverse-DNS, ≠ `--expect-bundle-id` (WARN if ≠ Android id) |
| `team_id` | malformed or inconsistent (WARN if absent) |
| `deployment_target` | missing, inconsistent, < 13 (WARN if Podfile disagrees) |
| `device_family` | universal without 4 iPad orientations / `UIRequiresFullScreen` (WARN: universal needs iPad screenshots) |
| `display_name`, `launch_screen` | missing |
| `version` | pubspec not `x.y.z+n` (WARN if Info.plist ignores the Flutter build vars) |
| `encryption` | — (WARN if `ITSAppUsesNonExemptEncryption` unset) |
| `usage_strings` | a plugin's required key missing, empty, placeholder or < 12 chars |
| `privacy_manifest` | file exists but is not in the Xcode project (WARN if absent) |
| `app_icon` | 1024 icon missing, wrong size, or has alpha (WARN if still the Flutter default) |
| `signing_secrets` | `.p8`/`.p12`/`.mobileprovision`/`.cer`/`AuthKey_*` tracked by git |
| `release_kit` | `ios-release/` incomplete, export method not `app-store-connect`, teamID ≠ project team |

Exit 0 = no BLOCK, 1 = BLOCK, 2 = usage. `--json` / `--out` for machines.

## Output

```
ios/Runner/Info.plist                usage strings, display name, ITSAppUsesNonExemptEncryption
ios/Runner/PrivacyInfo.xcprivacy     registered in Runner → Resources
ios/Runner.xcodeproj/project.pbxproj bundle id, DEVELOPMENT_TEAM, TARGETED_DEVICE_FAMILY, deployment target
ios-release/build-ios.sh             macOS: archive → export → verify → build-verify.json (no upload)
ios-release/ExportOptions.plist      app-store-connect, automatic signing, destination export
ios-release/README.md                one-time Apple setup, build, optional upload, listing checklist
ios-release/prep-report.json         last ios_prep_check.py result
.gitignore                           *.p8 *.p12 *.mobileprovision *.cer *.certSigningRequest
```

## Scope

Does not: upload, create the App Store Connect record, create certificates
or profiles by hand (automatic signing does it on the Mac), produce
screenshots or listing text, or judge App Store guidelines beyond the
mechanical checks above — pair it with `appstore-review-checker` for that.
The pbxproj helpers understand the `flutter create` layout; a heavily
customised Xcode project may need the Xcode UI, and the scripts say so
instead of guessing.
