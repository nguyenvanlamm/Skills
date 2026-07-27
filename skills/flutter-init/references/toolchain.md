# Installing the toolchain

## Flutter

### Linux

Prefer the tarball. The `snap` package has repeatedly lagged behind the stable channel and confines file access in ways that break Android SDK integration; it works, but when it does not, the failure is hard to diagnose.

```bash
mkdir -p ~/development && cd ~/development
# Resolve the current stable build from the official release index
curl -s https://storage.googleapis.com/flutter_infra_release/releases/releases_linux.json \
  | python3 -c "import json,sys;d=json.load(sys.stdin);h=d['current_release']['stable'];print(d['base_url']+'/'+next(r['archive'] for r in d['releases'] if r['hash']==h and r['channel']=='stable'))"
```

Download that URL, `tar xf` it, then put it on PATH in the shell's rc file (`~/.bashrc`, `~/.zshrc` — check `$SHELL`, do not assume bash):

```bash
export PATH="$PATH:$HOME/development/flutter/bin"
```

Editing an rc file only affects new shells. Either `source` it or tell the user to open a new terminal — a "flutter: command not found" immediately after a successful install is almost always this.

### macOS

```bash
brew install --cask flutter
```

If `platforms` includes `ios`, also verify Xcode and CocoaPods:

```bash
xcodebuild -version || echo "Xcode missing — install from the App Store"
sudo xcodebuild -license accept
pod --version || sudo gem install cocoapods
```

### Windows

Automate what is safe, hand over the rest:

```powershell
winget install --id=Google.Flutter -e
```

If winget is unavailable, give the user the download link and the PATH instructions rather than attempting to script an installer.

### After installing

```bash
flutter doctor -v
```

Report every unmet dependency with its remedy, not just the summary. Common ones: Android licences not accepted, cmdline-tools missing, no connected device.

```bash
flutter doctor --android-licenses    # interactive; the user must accept
```

## Android SDK

Only needed when there is no existing SDK. If Android Studio is installed, its SDK is already at `~/Android/Sdk` (Linux) or `~/Library/Android/sdk` (macOS) — use it rather than installing a second copy.

### 1. Download the OS-specific archive

```bash
case "$(uname -s)" in
  Linux)  CLT_OS=linux ;;
  Darwin) CLT_OS=mac ;;
  *)      CLT_OS=win ;;
esac
```

Take the current build number from https://developer.android.com/studio#command-line-tools-only — the filename embeds it and a hardcoded one goes stale:

```
https://dl.google.com/android/repository/commandlinetools-${CLT_OS}-<build>_latest.zip
```

### 2. Put it at `cmdline-tools/latest/`

**This is the step that breaks most scripted installs.** The zip extracts to a directory named `cmdline-tools`; `sdkmanager` requires it to live at `<sdk>/cmdline-tools/latest/`. Unzipping directly into the SDK root produces `<sdk>/cmdline-tools/bin/sdkmanager`, and every later command fails with a message that does not mention the layout.

```bash
export ANDROID_HOME="$HOME/Android/Sdk"
mkdir -p "$ANDROID_HOME/cmdline-tools"
unzip -q commandlinetools-*.zip -d /tmp/clt
mv /tmp/clt/cmdline-tools "$ANDROID_HOME/cmdline-tools/latest"
```

Verify before continuing:

```bash
ls "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager"
```

### 3. Install the packages

```bash
SDKMANAGER="$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager"
yes | "$SDKMANAGER" --licenses
"$SDKMANAGER" \
  "platform-tools" \
  "platforms;android-36" \
  "build-tools;36.0.0" \
  "ndk;28.0.13004108"
```

| Package | Why |
|---------|-----|
| `platform-tools` | Provides `adb`. Without it there is no device screenshot capture, no `flutter run` on a physical device, and no logcat. Easy to forget because nothing fails until much later. |
| `platforms;android-36` | Play requires new apps and updates to target API 36 from 31 Aug 2026 |
| `build-tools;36.0.0` | Also provides `apksigner`, which `flutter-build` uses to verify APK signatures |
| `ndk;28.x` | r28+ aligns native libraries for 16 KB pages, required by Play since 1 Nov 2025 |

Check what is actually available rather than pasting a version string:

```bash
"$SDKMANAGER" --list | grep -E "^\s+(ndk|build-tools;36|platforms;android-36)"
```

### 4. Environment

Add to the shell rc file:

```bash
export ANDROID_HOME="$HOME/Android/Sdk"
export PATH="$PATH:$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin"
```

`ANDROID_SDK_ROOT` is the deprecated spelling of the same thing; if it is already set to a different path, resolve the conflict rather than adding a second variable.

Then point Flutter at it and confirm:

```bash
flutter config --android-sdk "$ANDROID_HOME"
flutter doctor
adb version
```

## JDK

AGP 8.x expects **JDK 17**. A newer JDK produces `Unsupported class file major version` from Gradle, which reads as a Gradle problem rather than a Java one.

```bash
# Linux
sudo apt install -y openjdk-17-jdk
# macOS
brew install openjdk@17
```

If multiple JDKs are installed, pin the one Gradle uses in `android/gradle.properties` rather than changing the system default:

```properties
org.gradle.java.home=/usr/lib/jvm/java-17-openjdk-amd64
```
