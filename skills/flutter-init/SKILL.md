---
name: flutter-init
description: "Initialize a Flutter project from scratch: detect OS, install Flutter SDK + Android SDK (if missing), create project scaffold with clean architecture folders, and init Git. Use when the user says 'flutter init', 'bắt đầu flutter', 'create flutter project', 'cài flutter'. Skip for existing Flutter projects or non-Flutter stacks."
license: MIT
---

# Flutter Init

Automate steps 2-3 of the Flutter → Google Play pipeline: from a clean machine → Flutter project ready to code.

## Prerequisites

- Internet connection
- `sudo` access (for Linux package installation)
- For iOS targets: macOS with Xcode

## Input

Ask the user for these fields if not provided in `$ARGUMENTS`:

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `project_name` | ✅ | — | App name (e.g. `chplay`) |
| `org` | ❌ | `com.tenapp` | Bundle ID prefix |
| `platforms` | ❌ | `android,ios` | `android`, `ios`, or both |
| `ios_only` | ❌ | `false` | Skip Android setup if true |

## Steps

### Step 1: Detect OS & Installed Tools

```bash
# OS detection
uname -s   # Linux / Darwin / MINGW*
```

Check these tools:

```bash
# Flutter
which flutter && flutter --version 2>/dev/null || echo "NOT_FOUND"

# Android SDK
echo "ANDROID_HOME: ${ANDROID_HOME:-NOT_SET}"
ls "$ANDROID_HOME" 2>/dev/null || echo "ANDROID_HOME dir NOT_FOUND"
ls ~/Android/Sdk 2>/dev/null && echo "Found ~/Android/Sdk" || true
ls ~/Library/Android/Sdk 2>/dev/null && echo "Found ~/Library/Android/Sdk" || true

# Java
which java && java --version 2>/dev/null || echo "NOT_FOUND"

# Xcode (macOS only)
which xcodebuild && xcodebuild -version 2>/dev/null || echo "NOT_FOUND"

# CocoaPods (macOS only)
which pod && pod --version 2>/dev/null || echo "NOT_FOUND"
```

**Decision logic:**
- If Flutter ≥ 3.0 found → skip Step 2, offer `flutter upgrade`
- If Flutter found but < 3.0 → run `flutter upgrade`
- If Flutter not found → proceed to Step 2
- If Android SDK not found → proceed to Step 3
- If Xcode not found on macOS → warn iOS build unavailable

### Step 2: Install Flutter SDK

**Linux:**
```bash
# Prefer snap (recommended by Flutter team for Linux)
snap install flutter --classic

# Fallback: manual install
FLUTTER_VERSION=$(curl -s https://raw.githubusercontent.com/flutter/flutter/master/releases/latest_linux.json | grep -oP '"version": "\K[^"]+' | head -1)
cd ~/development
curl -O "https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_${FLUTTER_VERSION}-stable.tar.xz"
tar xf "flutter_linux_${FLUTTER_VERSION}-stable.tar.xz"
echo 'export PATH="$PATH:$HOME/development/flutter/bin"' >> ~/.bashrc
```

**macOS:**
```bash
brew install --cask flutter
```

**Windows:**
```bash
# Download and install via winget or manual
# Instruct user if unable to automate
```

After install:
```bash
flutter doctor 2>&1
```

Parse `flutter doctor` output for missing dependencies. Report each one clearly.

### Step 3: Install/Configure Android SDK (if missing)

```bash
# Download Android command-line tools
ANDROID_SDK_ROOT="$HOME/Android/Sdk"
mkdir -p "$ANDROID_SDK_ROOT"
cd "$ANDROID_SDK_ROOT"
curl -O https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
unzip commandlinetools-*.zip

# Accept licenses
yes | "$ANDROID_SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" --licenses

# Install required SDK packages
"$ANDROID_SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" \
  "platforms;android-34" \
  "build-tools;34.0.0"

# Set env vars (if not already set)
# Add to ~/.bashrc if missing
```

**Detection:** Check if `echo $ANDROID_HOME` is already set. If not, prompt to set it.

### Step 4: Create Flutter Project

```bash
flutter create \
  --org "$ORG" \
  --platforms "$PLATFORMS" \
  "$PROJECT_NAME"
```

**Edge cases:**
- Directory already exists → ask user: overwrite? (delete + recreate) / abort / use existing
- `flutter create` fails → print stderr, suggest fixes (e.g., space in path, invalid characters)

### Step 5: Create Clean Architecture Scaffold

After `flutter create`, build a maintainable folder structure:

```
lib/
  main.dart
  app.dart               # MaterialApp + theme + routing
  config/
    theme.dart           # ThemeData definition
    routes.dart          # Route configuration
  features/
    example/             # Example feature (remove in real app)
      screens/
      widgets/
      providers/
  core/
    constants/
      app_colors.dart
      app_strings.dart
    utils/
      validators.dart
    widgets/
      app_button.dart
  l10n/                  # If localization is desired
test/
  widget_test.dart       # Default test updated
```

Update files:

**lib/main.dart** — entry point clean:
```dart
import 'package:flutter/material.dart';
import 'app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MyApp());
}
```

**lib/app.dart** — root widget with theme and routing:
```dart
import 'package:flutter/material.dart';
import 'config/theme.dart';
import 'config/routes.dart';

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '$PROJECT_NAME',
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.system,
      initialRoute: AppRoutes.home,
      onGenerateRoute: AppRoutes.onGenerateRoute,
    );
  }
}
```

**lib/config/theme.dart** — theme template:
```dart
import 'package:flutter/material.dart';

class AppTheme {
  static ThemeData get light => ThemeData(
    useMaterial3: true,
    colorSchemeSeed: Colors.blue,
    brightness: Brightness.light,
  );

  static ThemeData get dark => ThemeData(
    useMaterial3: true,
    colorSchemeSeed: Colors.blue,
    brightness: Brightness.dark,
  );
}
```

**lib/config/routes.dart** — route template:
```dart
import 'package:flutter/material.dart';

class AppRoutes {
  static const String home = '/';

  static Route<dynamic> onGenerateRoute(RouteSettings settings) {
    switch (settings.name) {
      case home:
        return MaterialPageRoute(builder: (_) => const Placeholder());
      default:
        return MaterialPageRoute(
          builder: (_) => Scaffold(
            body: Center(child: Text('No route: ${settings.name}')),
          ),
        );
    }
  }
}
```

**Do NOT** generate any feature code — only scaffold + config.

### Step 6: Git Init

```bash
git init
```

Check `.gitignore` was created by `flutter create` (it should be). Add these if missing:

```
# Flutter
.dart_tool/
.packages
build/

# Android signing
android/app/upload-keystore.jks
android/key.properties

# IDE
.idea/
.vscode/
*.iml

# OS
.DS_Store
Thumbs.db
```

### Step 7: Report

```
══════════════════════════════════════════
  FLUTTER INIT — COMPLETE
══════════════════════════════════════════

  ✓ Flutter 3.x installed
  ✓ Android SDK configured (API 34)
  ✓ Project "$PROJECT_NAME" created at $PWD
  ✓ Clean architecture scaffold applied
  ✓ Git repo initialized

  ⚠ iOS setup skipped (not on macOS)

  Next steps:
    cd $PROJECT_NAME
    flutter run                    # run on connected device
    # or use flutter-signing skill to configure keystore
```

## What This Skill Does NOT Do

- ❌ Install Android Studio GUI (only command-line tools)
- ❌ Register Google Play Developer account ($25 manual step)
- ❌ Configure signing keys (see `flutter-signing`)
- ❌ Code any app features
- ❌ Build APK/AAB (see `flutter-build`)

## OS Support

| OS | Support Level |
|----|:-------------:|
| Linux (Ubuntu/Debian) | ✅ Full (snap + cmdline) |
| macOS | ✅ Full (brew + Xcode check) |
| Windows | ⚠️ Partial (winget or guided manual) |

## Edge Cases

| Problem | Handling |
|---------|----------|
| Flutter already installed | Detect version, skip install, offer upgrade |
| No sudo access | Fall back to manual tar install per user |
| ANDROID_HOME not set | Auto-detect paths, prompt to add to shell rc |
| Project dir exists | Ask: overwrite / abort / use existing |
| No internet | Abort with clear message |
| `flutter create` fails on iOS (no Xcode) | Still create project with `--platforms android` only |
| Space in project path | Warn user spaces may cause issues; use `_` or `-` instead |
| snap unavailable (WSL, VM) | Fall back to manual install |

## Acceptance Criteria

- [ ] Project compiles without errors (`flutter analyze` passes)
- [ ] Clean architecture scaffold in place (config/features/core folders)
- [ ] Git repo initialized with proper `.gitignore`
- [ ] User can run `flutter run` and see default app
- [ ] All installed tool versions reported clearly
