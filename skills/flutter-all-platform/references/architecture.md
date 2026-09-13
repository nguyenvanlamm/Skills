# Architecture reference

Read at Phase 3 (decide) and Phase 4–5 (apply). Everything here is a default, not a mandate — drop what the app cannot justify.

## 1. Folder layout (feature-first)

```
lib/
├── main.dart                      runApp + ProviderScope + env bootstrap
├── app/
│   ├── app.dart                   MaterialApp.router, theme, localization
│   ├── router.dart                go_router config, route names, NotFoundScreen
│   └── theme/
│       ├── tokens.dart            colors, spacing, radius, elevation, breakpoints
│       ├── typography.dart        text theme
│       └── app_theme.dart         light/dark ThemeData built from tokens
├── core/
│   ├── config/env.dart            --dart-define reader (API_BASE_URL, FLAVOR)
│   ├── errors/                    AppException hierarchy, Result/Either helper if used
│   ├── network/                   HTTP client, interceptors (only if there is an API)
│   ├── storage/                   local db / prefs / secure storage wrappers
│   ├── platform/                  ⚠️ the ONLY place platform-specific code may live
│   │   ├── file_saver.dart        abstract class + `export 'file_saver_stub.dart'
│   │   │                            if (dart.library.io) 'file_saver_io.dart'
│   │   │                            if (dart.library.html) 'file_saver_web.dart';`
│   │   ├── file_saver_io.dart
│   │   ├── file_saver_web.dart
│   │   └── file_saver_stub.dart
│   ├── utils/                     formatters, validators, extensions
│   └── widgets/                   design-system components + AppScaffold
├── features/
│   └── <feature>/
│       ├── data/                  models, dtos, repository impls, data sources
│       ├── domain/                (optional) entities + repository interfaces — only if data ≠ domain shape
│       └── presentation/          providers/controllers, screens, feature-local widgets
└── l10n/                          arb files (only if the app is multilingual)
```

Rules:

- A feature's `presentation/` never imports another feature's `presentation/`. Cross-feature needs go through providers or `core/`.
- Screens contain layout and wiring only; logic lives in providers/controllers so it is unit-testable without widgets.
- Skip `domain/` when the API/db model *is* the UI model. Add it when mapping is real.
- Platform imports (`dart:html`, `dart:io`, `package:flutter/foundation.dart` `kIsWeb` branching for behaviour) are allowed only in `core/platform/`. `kIsWeb` for *layout* is fine anywhere.

## 2. Default stack — with reasons

| Concern | Default | Why | Skip when |
|---------|---------|-----|-----------|
| State | `flutter_riverpod` (+ `riverpod_annotation` optional) | Compile-safe, testable without widgets, works with go_router redirects | Tiny app with 1–2 screens → plain `ChangeNotifier` |
| Routing | `go_router` | Declarative, URL-based → web deep links and refresh work; typed redirects for auth | Never — web needs URL routing |
| Models | `freezed` + `json_serializable` | Immutable, `copyWith`, equality, JSON in one place | No JSON and few models → hand-written classes with `==` |
| Local data | `drift` (relational, queries, web via wasm) **or** `shared_preferences` (key-value) | Pick by data shape; drift for lists you filter/aggregate | Remote-only app |
| Secure values | `flutter_secure_storage` | Keychain/Keystore; web falls back to encrypted localStorage — note in report | No token/secret stored |
| HTTP | `dio` | Interceptors, cancellation, typed errors | No backend → do not add |
| Formatting | `intl` | Dates, currency, plurals | Never — even single-locale apps format numbers |
| Env | `--dart-define` via `core/config/env.dart` | No secret files in the bundle; CI-friendly | — |
| Icons | `flutter_launcher_icons` (dev) | One source PNG → android/ios/web icons | User supplies all icons |
| Lints | `flutter_lints` (dev) | Baseline; analyze must be clean | — |

Do not add: `get_it` (Riverpod already injects), `provider` alongside Riverpod, `http` alongside `dio`, `hive` alongside `drift`, `equatable` alongside `freezed`. Each package needs a row in `docs/ARCHITECTURE.md` or it is removed in Phase 9.

## 3. Platform abstraction pattern

```dart
// core/platform/file_saver.dart
import 'file_saver_stub.dart'
    if (dart.library.io) 'file_saver_io.dart'
    if (dart.library.html) 'file_saver_web.dart';

abstract class FileSaver {
  Future<void> saveText({required String fileName, required String content});
  factory FileSaver() => createFileSaver();   // each impl exports createFileSaver()
}
```

- `*_io.dart` → `path_provider` + `share_plus` (Android/iOS)
- `*_web.dart` → `Blob` + anchor download
- `*_stub.dart` → throws `UnsupportedError` — keeps analyze happy on every target

Expose it through a Riverpod provider so tests inject a fake. Same pattern for: notifications, camera/file picker, biometrics, deep links, haptics.

## 4. Android pins (when scaffolding without `flutter-init`)

`android/app/build.gradle.kts` (or `.gradle`):

```kotlin
compileSdk = 36
ndkVersion = "28.0.13004108"      // r28+: 16 KB page alignment
defaultConfig {
    minSdk = 23
    targetSdk = 36
}
```

Verify the written IDs before writing any code: `grep -E "applicationId|namespace" android/app/build.gradle*`.

## 5. iOS pins

- `ios/Podfile`: uncomment `platform :ios, '13.0'` (or higher if a plugin requires).
- `ios/Runner/Info.plist`: `CFBundleDisplayName`, every `NS*UsageDescription` for permissions in the platform matrix.
- Bundle identifier = `applicationId`. Check: `grep -m1 PRODUCT_BUNDLE_IDENTIFIER ios/Runner.xcodeproj/project.pbxproj`.
- Signing is left to Xcode on the user's Mac; `flutter build ios --no-codesign` is what the verification script runs.

## 6. Web pins

- `web/index.html`: `<title>`, `<meta name="description">`, theme-color, `<base href="$FLUTTER_BASE_HREF">` left as is.
- `web/manifest.json`: name, short_name, theme/background colors from tokens, icons.
- Routing: `usePathUrlStrategy()` in `main.dart` (from `flutter_web_plugins`) so URLs have no `#`. Hosting must rewrite all paths to `index.html` — say so in the README.
- Renderer: leave default (canvaskit/skwasm auto). Do not hard-code `--web-renderer`; it is deprecated.

## 7. Environment config

```dart
// core/config/env.dart
class Env {
  static const apiBaseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: '');
  static const flavor = String.fromEnvironment('FLAVOR', defaultValue: 'dev');
  static bool get hasBackend => apiBaseUrl.isNotEmpty;
}
```

`.env.example` documents each key. Build with `flutter build web --dart-define=API_BASE_URL=https://…`. No `.env` is read at runtime; nothing secret is compiled in.
