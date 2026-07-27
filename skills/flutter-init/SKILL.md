---
name: flutter-init
description: "Initialize a Flutter project from scratch: detect OS, install Flutter SDK + Android SDK (if missing), create the project scaffold with clean architecture folders, and init Git. Use when the user says 'flutter init', 'bắt đầu flutter', 'create flutter project', 'cài flutter'. Skip for existing Flutter projects or non-Flutter stacks."
license: MIT
metadata:
  version: 2.0.0
---

# Flutter Init

Steps 2–3 of the Flutter → Google Play pipeline: from a bare machine to a project that will still build when it reaches Play.

## Core principle

> **Decisions made here are the ones that cannot be undone later.** The application ID is permanent after first publish, and the SDK versions installed now decide whether the release build is accepted eight steps from here. Everything else in this skill is scaffolding that can be rewritten any time.

So two things get real scrutiny: the **organization prefix** and the **SDK levels**. The folder layout does not.

## Input

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `project_name` | ✅ | — | Directory and Dart package name; lowercase_with_underscores |
| `org` | ✅ | — | Reverse-domain prefix, e.g. `com.acme` — **no default** |
| `platforms` | ❌ | `android` | `android`, `ios`, or both |
| `description` | ❌ | — | pubspec description |

`org` has no default on purpose. It becomes `applicationId = <org>.<project_name>`, which is **permanent once the app is published** and cannot be reused if someone else registered it. A placeholder prefix (`com.example`, `com.tenapp`, `com.myapp`) means the app has to be rebuilt under a new ID before it can ever ship — `flutter-build` and `flutter-publish` both block on `com.example.*` for this reason.

Ask for a domain the user controls, or a unique identifier they are content to keep forever. Explain the permanence once; do not pick for them.

## Workflow

### Step 1 — Inspect the machine

```bash
uname -s                                              # Linux / Darwin / MINGW*
flutter --version 2>/dev/null || echo "flutter NOT_FOUND"
java -version 2>&1 | head -1 || echo "java NOT_FOUND"
echo "ANDROID_HOME=${ANDROID_HOME:-unset}"
ls ~/Android/Sdk ~/Library/Android/sdk 2>/dev/null
adb version 2>/dev/null || echo "adb NOT_FOUND"
```

Report what exists before installing anything. `adb` matters beyond this skill — `flutter-store-metadata` needs it to capture real screenshots, so a missing `platform-tools` here becomes placeholder screenshots later.

| Found | Action |
|-------|--------|
| Flutter, recent | Skip install; offer `flutter upgrade` |
| Flutter, old (< 3.22) | Upgrade — 16 KB page support and current AGP need it |
| No Flutter | Step 2 |
| No Android SDK | Step 3 |
| JDK ≠ 17 | Warn: AGP 8.x expects JDK 17, and a newer JDK breaks Gradle in confusing ways |

### Step 2 — Install Flutter

Read `references/toolchain.md` § Flutter. Prefer the tarball over `snap` on Linux: the snap has a history of lagging behind stable and of path problems with the Android SDK. Verify with `flutter doctor -v` and report each unmet dependency rather than only the summary line.

### Step 3 — Install the Android SDK

Read `references/toolchain.md` § Android SDK. Three things the naive version gets wrong, all of which break the install:

- `cmdline-tools` must end up at `cmdline-tools/latest/`, not `cmdline-tools/` — `sdkmanager` will not run otherwise
- the download URL is OS-specific (`commandlinetools-linux-…` vs `-mac-` vs `-win-`)
- `platform-tools` must be installed explicitly, or there is no `adb`

Install platform **36** and matching build-tools, not 34. Play requires new apps and updates to target API 36 from 31 Aug 2026; scaffolding against 34 produces a project that fails at the last step of the pipeline.

### Step 4 — Create the project

```bash
flutter create --org "$ORG" --platforms "$PLATFORMS" \
  ${DESCRIPTION:+--description "$DESCRIPTION"} "$PROJECT_NAME"
```

Then confirm the ID that was actually written — `flutter create` sanitises names, so what you asked for is not always what you got:

```bash
grep applicationId "$PROJECT_NAME/android/app/build.gradle"*
```

If the directory already exists, ask: overwrite, abort, or use in place. Never delete a non-empty directory without an explicit yes.

### Step 5 — Pin the Android build configuration

`flutter create` leaves `targetSdk`, `compileSdk`, and `ndkVersion` implicit (`flutter.targetSdkVersion`), which means they silently follow the Flutter SDK version. `flutter-build` reports those as "cannot verify", and `flutter-store-compliance` cannot audit them at all.

Set them explicitly in `android/app/build.gradle{,.kts}`:

```groovy
compileSdk 36
ndkVersion "28.0.13004108"     // r28+; older NDKs misalign .so for 16 KB pages

defaultConfig {
    targetSdk 36
    minSdk 23
}
```

Use whichever NDK r28+ version `sdkmanager --list | grep ndk` shows as installed rather than copying the string above. `minSdk` is an engineering choice — 23 is a reasonable default; higher trades reach for fewer compatibility branches.

### Step 6 — Scaffold

Read `references/scaffold.md` for the folder layout and the file contents. Keep it minimal: entry point, app widget, theme, routes, and empty feature folders. No feature code, no state management choice, no dependency added that the user did not ask for — those decisions belong to whoever writes the app.

### Step 7 — Git

```bash
cd "$PROJECT_NAME"
git init -b main
```

`flutter create` writes a `.gitignore` that covers Dart and build outputs but **not credentials**. Append:

```
# Signing and release credentials
*.jks
*.keystore
android/key.properties
service-account.json
```

This is the cheapest possible moment to prevent a committed keystore — `flutter-signing` and `flutter-publish` both check for one, but by then the exposure has already happened.

Then make the first commit, so there is a clean baseline to diff against:

```bash
git add -A && git commit -m "chore: initial Flutter scaffold"
```

### Step 8 — Verify and report

```bash
flutter analyze
flutter doctor
```

`flutter analyze` must be clean on a fresh scaffold. If it is not, the scaffold is wrong — fix it rather than reporting it as a known issue.

```
FLUTTER INIT — OK

Project     task_flow at ./task_flow
App ID      com.acme.task_flow   ← permanent once published
Flutter     3.35.2 (stable)
Android     compileSdk 36 · targetSdk 36 · minSdk 23 · NDK r28
Tooling     JDK 17 · adb present · flutter doctor clean
Git         initialised, first commit, credentials gitignored

Next: flutter-signing → flutter-build
```

Report the application ID prominently. It is the one value from this step that cannot be changed later, and the user should see it before writing any code.

## Reference files

| File | Read when |
|------|-----------|
| `references/toolchain.md` | Steps 2–3 — installing Flutter and the Android SDK per OS |
| `references/scaffold.md` | Step 6 — folder layout and scaffold file contents |

## OS support

| OS | Level |
|----|-------|
| Linux | Full — tarball install, SDK via cmdline-tools |
| macOS | Full — Homebrew, plus Xcode check when iOS is in `platforms` |
| Windows | Partial — guided; automate what winget covers, hand the rest to the user |

iOS builds require macOS with Xcode. On any other OS, create the project with `--platforms android` and say why.

## Scope

Does: install the toolchain, create the project, pin the Android build configuration, scaffold, and initialise Git.

Does not: install Android Studio; register a Play developer account ($25, manual); configure signing (`flutter-signing`); write features; build (`flutter-build`).
