# Platform Report — <App Name>

Fill from `build/flutter-all-platform/build-report.json` and `.flutter-all-platform-state.json`. Write in the user's language. Never mark ✅ from memory — copy the exit codes.

Legend: ✅ ran and passed in this session · ❌ ran and failed (blocker listed) · ⚠️ configured but not built (environment) · ⏭ not applicable

## 1. Overview

- **App:** <name> — <one line>
- **Target user / problem:** …
- **Application ID / bundle ID:** `<org>.<slug>` (permanent after first publish)
- **Project path:** `<abs path>`
- **Shared Dart code:** ~<n> % (files outside `core/platform/` ÷ total)

## 2. Features

| Feature | Bucket | Status | Screens |
|---------|--------|--------|---------|
| … | MVP | implemented | … |
| … | Extended | interface stubbed | — |
| … | Future | listed only | — |

## 3. Architecture

Feature-first layout: `app/` (router, theme), `core/` (config, widgets, platform, storage), `features/<name>/{data,presentation}`. Platform-specific code isolated in `core/platform/`: <list abstractions>. See `docs/ARCHITECTURE.md`.

## 4. Dependencies

| Package | Why |
|---------|-----|
| flutter_riverpod | … |
| go_router | … |
| … | … |

## 5. Skills

| Capability | Skill used | Notes |
|------------|-----------|-------|
| Scaffold | `flutter-init` ✅ | web added afterwards |
| UI direction | `frontend-design` ✅ | … |
| Tests | — (missing) | written inline |
| … | … | … |

## 6. Platform status

| Platform | Command | Exit | Status | Artifact / reason |
|----------|---------|------|--------|-------------------|
| Analyze | `flutter analyze` | 0 | ✅ | — |
| Tests | `flutter test` | 0 | ✅ | <n> tests |
| Web | `flutter build web` | 0 | ✅ | `build/web/` |
| Android APK | `flutter build apk` | 0 | ✅ | `build/app/outputs/flutter-apk/app-release.apk` (<size>) |
| Android AAB | `flutter build appbundle` | 0 | ✅ | `build/app/outputs/bundle/release/app-release.aab` |
| iOS | `flutter build ios --no-codesign` | — | ⚠️ | configured (Info.plist, Podfile, bundle id); not built — no macOS/Xcode in this environment |

Environment (from `check-env.sh`): Flutter <v> · Dart <v> · JDK <v> · Android SDK <platforms> · Xcode <v or none> · OS <name>

## 7. Platform adaptation summary

- **Web:** path URL strategy, 404 route, manifest, hosting rewrite documented in README, storage = <…>
- **Android:** permissions: <list>, minSdk 23 / target 36, adaptive icon
- **iOS:** usage descriptions: <list>, deployment target <v>, pods <installed | not installed (no macOS)>

## 8. Security

- No secrets in source (grep clean) · `--dart-define` env · credentials gitignored · tokens in secure storage (<web fallback note>) · HTTPS enforced · inputs validated

## 9. Remaining issues / blockers

| # | Item | Class | Detail |
|---|------|-------|--------|
| 1 | iOS build not executed | environment | needs macOS + Xcode; run `flutter build ios` there |
| 2 | … | project / dependency / platform | … |

## 10. Assumptions made

See `docs/ASSUMPTIONS.md` — <n> assumptions (name, currency, default categories, …).

## 11. Build commands

```bash
flutter pub get
flutter analyze
flutter test
flutter build web       --dart-define=API_BASE_URL=…
flutter build apk
flutter build appbundle
flutter build ios       # macOS only
```

## 12. Next steps

1. Release signing → `flutter-signing`, then `flutter-build` for a Play-ready AAB
2. Build iOS on macOS; sign in Xcode; `appstore-review-checker` before submission
3. Store listing → `flutter-store-metadata` → `flutter-store-compliance` → `flutter-publish`
4. <backend if local-first was chosen: `deploy-render` + swap repository impl>
5. Extended features: <list>
