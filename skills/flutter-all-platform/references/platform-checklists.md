# Platform & security checklists

Read at Phase 6 (adapt) and Phase 8 (security). Each item is either verified with the command shown or marked N/A with a reason in `docs/PLATFORM-REPORT.md`. Every permission must trace back to a row in the Phase 2 platform matrix.

## Web

| Check | How |
|-------|-----|
| `web/` exists | `ls web/index.html web/manifest.json` |
| Path URL strategy, no `#` | `grep -r usePathUrlStrategy lib/main.dart` |
| Refresh on a deep route lands on the same screen | `flutter run -d chrome`, navigate, F5 — or reason from go_router config + hosting rewrite note in README |
| 404 route | `NotFoundScreen` registered as `errorBuilder` |
| Title / description / theme-color | `grep -E "<title>|description|theme-color" web/index.html` |
| Manifest name, colors, icons | `cat web/manifest.json` |
| CORS | If there is an API: README states the backend must allow the web origin; the app shows `ErrorView` (not a blank screen) on CORS failure |
| Storage | `shared_preferences` → localStorage; `drift` → wasm + `sqlite3.wasm` in `web/` (`flutter pub run drift_dev` docs) — verified by `flutter build web` |
| File download / share | `core/platform/*_web.dart` impl uses `Blob` + anchor; no `dart:io` outside `core/platform/` |
| Browser permissions | Camera/geolocation prompt handled with a rationale screen; denial → `ErrorView` |
| Desktop layout | ≥ 1200 px shows rail/sidebar and constrained body |
| Mobile browser layout | < 600 px shows bottom `NavigationBar`, no horizontal scroll |
| `dart:io` leakage | `grep -rl "dart:io" lib/ \| grep -v core/platform/` → must be empty |
| Build | `flutter build web` (release) |

## Android

| Check | How |
|-------|-----|
| `applicationId` = `<org>.<slug>`, not `com.example.*` | `grep -E "applicationId\|namespace" android/app/build.gradle*` |
| `compileSdk/targetSdk 36`, `minSdk 23`, NDK r28+ | same file |
| App label | `grep android:label android/app/src/main/AndroidManifest.xml` |
| Permissions match matrix | `grep uses-permission android/app/src/main/AndroidManifest.xml` — `INTERNET` only if there is a network call; remove unused template entries |
| Launcher icon (adaptive) | `ls android/app/src/main/res/mipmap-anydpi-v26/` after `flutter_launcher_icons` |
| Splash | default Flutter splash is fine; if custom, `android/app/src/main/res/drawable*/launch_background.xml` |
| Deep links (if in matrix) | `<intent-filter>` with `android:autoVerify`, `assetlinks.json` noted in README |
| Native integrations | each plugin's Android setup section followed; `flutter pub deps` shows no duplicate plugin |
| Cleartext | no `usesCleartextTraffic="true"` |
| Build | `flutter build apk` and `flutter build appbundle` (debug-signed is acceptable for verification; release signing → `flutter-signing`) |

## iOS

| Check | How |
|-------|-----|
| Bundle identifier = `applicationId` | `grep -m1 PRODUCT_BUNDLE_IDENTIFIER ios/Runner.xcodeproj/project.pbxproj` |
| `CFBundleDisplayName` | `grep -A1 CFBundleDisplayName ios/Runner/Info.plist` |
| Deployment target ≥ 13.0 | `grep IPHONEOS_DEPLOYMENT_TARGET ios/Runner.xcodeproj/project.pbxproj \| sort -u`; `platform :ios` line in `ios/Podfile` |
| Usage descriptions for every permission | `grep UsageDescription ios/Runner/Info.plist` — camera, photos, location, microphone, contacts, Face ID, notifications each need a human sentence |
| Encryption exemption | `ITSAppUsesNonExemptEncryption = false` if only HTTPS is used |
| Pods | on macOS: `cd ios && pod install`; elsewhere: Podfile reviewed, note "pods not installed (no macOS)" |
| Signing | left to Xcode on the user's Mac; report says so |
| Native integrations | each plugin's iOS section followed |
| Build | macOS + Xcode: `flutter build ios --no-codesign`. Otherwise **do not run, do not claim**: report `iOS configuration: done · iOS build: not run — no macOS/Xcode in this environment` |

## Security (Phase 8)

| Check | How |
|-------|-----|
| No secrets in source | `grep -rniE "(api[_-]?key\|secret\|password\|token\|private[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}" lib/ web/ android/app/src ios/Runner` → empty |
| Secrets via `--dart-define` only | `grep -r String.fromEnvironment lib/core/config/env.dart`; `.env.example` present, `.env*` gitignored |
| Credentials gitignored | `.gitignore` contains `*.jks`, `*.keystore`, `android/key.properties`, `service-account.json`, `.env*` |
| Tokens in secure storage | `flutter_secure_storage` wrapper in `core/storage/`; no token in `shared_preferences` |
| HTTPS only | `Env.apiBaseUrl` asserted to start with `https://` outside debug |
| Input validation | every `AppTextField` has a validator; repositories re-validate before persisting |
| No sensitive logs | `grep -rn "print(" lib/` → only in debug guards or removed; no user data/tokens in logs |
| Auth/authz | if auth exists: go_router `redirect` guards private routes; logout clears secure storage and provider state |
| Dependencies | `flutter pub outdated`; no package with known advisory (run `security-setup` if present) |
| CORS / API | documented in README; app never disables certificate checks |

## Environment vs project error (Phase 10 triage)

| Symptom | Class | Action |
|---------|-------|--------|
| Dart compile error, analyzer error, failing test | **project** | fix, rerun step |
| `pub get` version solving failed | **dependency** | pin/upgrade, rerun |
| Gradle: SDK/NDK/JDK version mismatch, missing `INTERNET`, manifest merge | **platform config** | fix gradle/manifest, rerun |
| Missing `NS*UsageDescription`, Podfile platform too low | **platform config** | fix plist/Podfile |
| No Chrome for web | **environment** | `flutter build web` does not need Chrome — only `flutter run -d chrome` does; still build |
| No Android SDK / JDK | **environment** | record `skipped_env`; point to `flutter-init` |
| No macOS / Xcode / CocoaPods | **environment** | record `skipped_env` for iOS build; iOS config still audited |
| Network timeout fetching packages/gradle | **environment** | retry once, then record |
