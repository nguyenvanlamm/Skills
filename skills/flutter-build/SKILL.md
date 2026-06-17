---
name: flutter-build
description: "Build a Flutter Android appbundle (AAB) or APK for release. Use when user says 'build', 'build app', 'build aab', 'build apk', 'release build', 'build flutter'. Run after flutter-signing and before flutter-store-metadata."
license: MIT
---

# Flutter Build

Step 7 of the Flutter → Google Play pipeline: produce a signed release build.

## Prerequisites

- Flutter project with signing configured (or run `flutter-signing` first)
- Clean `pubspec.yaml` with all dependencies resolved

## Input

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `build_type` | ❌ | `appbundle` | `appbundle` (recommended) or `apk` |
| `flavor` | ❌ | — | Build flavor: `dev`, `staging`, `prod` |
| `split_per_abi` | ❌ | `false` | APK only: split by CPU architecture |
| `target_platform` | ❌ | `android-arm,android-arm64,android-x64` | Target platforms for APK |
| `obfuscate` | ❌ | `true` | Enable code obfuscation |
| `track_widget_creation` | ❌ | `false` | Track widget creation (debugging) |

## Steps

### Step 1: Pre-flight Checks

```bash
# Ensure Flutter project
ls pubspec.yaml || { echo "Not a Flutter project"; exit 1; }

# Ensure signing configured
if [ ! -f android/key.properties ]; then
  echo "WARNING: No android/key.properties found"
  echo "Run flutter-signing first or configure manually."
  echo "Build will likely fail or produce unsigned APK."
  ask_user "Continue anyway?" || exit 1
fi

# Git clean check
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  echo "Uncommitted changes detected."
  ask_user "Proceed with dirty working tree?" || exit 1
fi

# Get dependencies
flutter pub get 2>&1 | tail -5
```

**Edge cases:**
- pubspec has dependency resolution conflict → print error, suggest `flutter pub upgrade`
- No signing key → warn user build will be unsigned / use debug key

### Step 2: Clean Build Cache (Optional)

Ask user:
> "Clean build cache? This deletes `build/` and `flutter pub get` will re-run."
> Options: Yes / No

```bash
if ask_user "Clean build cache?"; then
  flutter clean
  flutter pub get
fi
```

### Step 3: Build Command

**AppBundle (recommended for Google Play):**

```bash
if [ "$OBFUSCATE" = "true" ]; then
  flutter build appbundle --release --obfuscate --split-debug-info=build/debug-info
else
  flutter build appbundle --release
fi
```

**With flavor:**

```bash
flutter build appbundle --release --flavor "$FLAVOR" \
  --dart-define-from-file="env/$FLAVOR.json"
```

**APK (alternative):**

```bash
if [ "$SPLIT_PER_ABI" = "true" ]; then
  flutter build apk --release --split-per-abi
else
  flutter build apk --release
fi
```

### Step 4: Parse Build Result

```bash
# Find output file
if [ "$BUILD_TYPE" = "appbundle" ]; then
  OUTPUT=$(find . -name "*.aab" -path "*/build/*" -type f 2>/dev/null | head -1)
else
  OUTPUT=$(find . -name "*.apk" -path "*/build/*" -type f 2>/dev/null)
fi
```

**Check for errors in output:**
- `FAILURE: Build failed with an exception` → parse error lines, suggest fix
- `Out of memory` → increase heap in `gradle.properties`
- `AAPT: error` → resource issue
- `Could not find method` → Gradle config issue

**Common fixes:**

| Error | Fix |
|-------|-----|
| Build failed w/ Gradle exception | Show last 20 lines of error. Suggest `flutter clean && flutter pub get` |
| Out of memory | Add `org.gradle.jvmargs=-Xmx4g` to `android/gradle.properties` |
| Could not find signingConfig | Run `flutter-signing` first |
| AAPT resource error | Check `res/` files for invalid characters |
| Asset not found | Check paths in `pubspec.yaml` assets section |

### Step 5: Verify Output

```bash
ls -lh "$OUTPUT"
file "$OUTPUT"
```

Check:
- File exists and has reasonable size (> 1 MB for release AAB)
- File is signed (for APK, run `jarsigner -verify -certs "$OUTPUT"`)

**Edge case:** AAB size > 150 MB → warn user Google Play limits

### Step 6: Copy Output to Build Directory

```bash
mkdir -p build/release
cp "$OUTPUT" "build/release/"
```

### Step 7: Report

```
══════════════════════════════════════════
  FLUTTER BUILD — COMPLETE
══════════════════════════════════════════

  ✓ flutter pub get
  ✓ flutter build $BUILD_TYPE (--release)
  ✓ Signing: confirmed (release key)

  Output:
    $OUTPUT
    Size: $(ls -lh "$OUTPUT" | awk '{print $5}')
    Time: $BUILD_TIME

  Copy: build/release/$(basename "$OUTPUT")

  Next steps:
    flutter-store-metadata    # Prepare store listing
    flutter-store-compliance  # Check Google Play policies
    flutter-publish           # Upload to Google Play
```

## Edge Cases

| Problem | Handling |
|---------|----------|
| Build fails | Show last 20 lines of Gradle output. Suggest common fixes. |
| Out of memory during build | Add `org.gradle.jvmargs=-Xmx4g` to `android/gradle.properties` |
| Gradle version incompatible | Suggest updating: `flutter upgrade --force` |
| Android NDK missing | Install via sdkmanager: `sdkmanager "ndk;25.0.8775105"` |
| Very slow build | Suggest `--no-tree-shake-icons` for debug; first release build is slow |
| `flutter build` not found | Not in Flutter project directory |
| iOS build on Linux | Warn: iOS builds require macOS |
| AAB > 150MB | Warn about Google Play 150MB limit; suggest asset compression |

## What This Skill Does NOT Do

- ❌ Generate signing keys (see `flutter-signing`)
- ❌ Upload to Google Play (see `flutter-publish`)
- ❌ Build for iOS (separate process on macOS)

## Acceptance Criteria

- [ ] Release AAB/APK produced without errors
- [ ] Output file is properly signed with release key
- [ ] Build time and file size reported
- [ ] File copied to `build/release/`
