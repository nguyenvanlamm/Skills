---
name: flutter-build
description: "Build a Flutter Android appbundle (AAB) or APK for release. Use when user says 'build', 'build app', 'build aab', 'build apk', 'release build', 'build flutter'. Run after flutter-signing and before flutter-store-metadata."
license: MIT
metadata:
  version: 2.1.0
---

# Flutter Build

Step 7 of the Flutter → Google Play pipeline: produce a signed, uploadable release build.

## Core principle

> **A build that Play will reject is a failed build.** Every rule Play enforces at upload is knowable here — from the gradle files before the build, or from the artifact after it. Catching one at `flutter-publish` costs a full rebuild; catching it here costs seconds.

The other half: never report success off a stale artifact. `flutter build` can fail while a perfectly plausible AAB from an earlier run still sits in `build/`.

## Input

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `build_type` | ❌ | `appbundle` | `appbundle` (Play) or `apk` (sideload/testing) |
| `flavor` | ❌ | — | Build flavor, e.g. `prod` |
| `bump` | ❌ | ask | `major`, `minor`, `patch`, `build`, or `none` |
| `obfuscate` | ❌ | `true` | Requires keeping the debug-info — see Step 7 |
| `split_per_abi` | ❌ | `false` | APK only; meaningless for appbundle |
| `clean` | ❌ | auto | Force `flutter clean` first |

## Workflow

### Step 1 — Pre-build gates

Run before spending build time. **BLOCK** = stop, the artifact would be unusable or rejected.

```bash
[ -f pubspec.yaml ] || { echo "Not a Flutter project"; exit 1; }
GRADLE=$(ls android/app/build.gradle android/app/build.gradle.kts 2>/dev/null | head -1)
grep -E "applicationId|targetSdk|ndkVersion|minSdk" "$GRADLE"
ls android/key.properties && grep -c storeFile android/key.properties
```

| Gate | Verdict |
|------|---------|
| `android/key.properties` missing, or `storeFile` points at a nonexistent file | **BLOCK.** Flutter does not fail here — it silently falls back to the **debug key**, producing an AAB that Play refuses. Run `flutter-signing`. |
| `applicationId` starts with `com.example.` | **BLOCK.** Play rejects it permanently and it cannot be changed after first publish. |
| Other placeholder prefix — `com.myapp.`, `com.tenapp.`, `com.test.`, `com.app.` | **BLOCK.** Play accepts these, which is worse: the app ships forever under a name the user does not own. |
| `targetSdk` is a literal < 36 | **BLOCK** from 31 Aug 2026 (WARN before): new apps and updates must target API 36+. |
| `targetSdk = flutter.targetSdkVersion` | Implicit — resolves from the Flutter SDK version. Cannot verify now; Step 6 checks the built artifact. Recommend pinning it explicitly. |
| `ndkVersion` unset or < 28 | **WARN.** NDK < r28 misaligns `.so` files for 16 KB pages, which Play has rejected since 1 Nov 2025. Harmless for pure-Dart apps, fatal with native plugins. Step 6 is the authoritative check. |
| `flutter analyze` reports errors | **WARN**, list them. Errors here often mean the release build fails minutes later. |

Then `flutter pub get`. On a resolution conflict, show the conflicting constraints — not just the raw failure — and suggest `flutter pub upgrade --major-versions` only if the user accepts breaking bumps.

Do **not** block on a dirty git tree. Record the state instead (Step 7); a build from uncommitted work is normal during development, it just has to be labelled.

### Step 2 — Version

The build number in `pubspec.yaml` becomes Android's `versionCode`, and **Play permanently burns every version code it has seen**, including from discarded releases.

```bash
grep "^version:" pubspec.yaml                                    # version: 1.0.0+3
grep -o '"version_code": *[0-9]*' store-metadata/publish-state.json 2>/dev/null
```

If the build number is ≤ the last uploaded version code, it **must** be bumped — otherwise `flutter-publish` blocks and this build is wasted. Ask which bump when `bump` was not given:

| Bump | `1.2.3+7` becomes | Use |
|------|-------------------|-----|
| `build` | `1.2.3+8` | Same release, new upload |
| `patch` | `1.2.4+8` | Fixes |
| `minor` | `1.3.0+8` | Features |
| `major` | `2.0.0+8` | Breaking / milestone |

Edit `pubspec.yaml`. The version name is user-visible on the Play listing; the build number never is.

### Step 3 — Clean (conditional)

`flutter clean` costs minutes, so do not ask by default. Clean automatically when any of these hold, and say why:

- The previous build failed
- Flutter SDK, AGP, or Gradle version changed since the last build (`build/release/build-info.json` records it)
- Switching flavor or build type
- The user passed `clean`

### Step 4 — Build

```bash
START=$(date +%s)
mkdir -p build/release
```

Compose the command:

```bash
flutter build appbundle --release \
  ${FLAVOR:+--flavor "$FLAVOR"} \
  ${OBFUSCATE:+--obfuscate --split-debug-info=build/debug-info} \
  2>&1 | tee build/release/build.log
```

`--obfuscate` without `--split-debug-info` is an error — always pair them. Read `references/obfuscation.md` before enabling it on a project that has never shipped obfuscated; it changes what crash reports look like forever.

With a flavor, verify the dart-define file exists before passing it:

```bash
[ -f "env/$FLAVOR.json" ] && DEFINES="--dart-define-from-file=env/$FLAVOR.json"
```

APK instead: `flutter build apk --release [--split-per-abi]`. `--split-per-abi` produces one APK per architecture for sideloading; it does nothing for appbundle, where Play splits automatically.

On failure, read `references/build-errors.md` and diagnose from `build/release/build.log` — do not just print the tail and give up.

### Step 5 — Locate the artifact

Use the deterministic path, never `find | head -1`:

| Build | Path |
|-------|------|
| appbundle | `build/app/outputs/bundle/${FLAVOR}Release/app-${FLAVOR}-release.aab` (no flavor: `bundle/release/app-release.aab`) |
| apk | `build/app/outputs/flutter-apk/app-release.apk` |
| apk, split | `build/app/outputs/flutter-apk/app-<abi>-release.apk` |

### Step 6 — Verify the artifact

```bash
bash <skill-dir>/scripts/verify-artifact.sh --artifact "$OUT" --started-at "$START" --out build/release/verify.json
```

One script, one JSON, one vocabulary (`OK` · `WARN` · `BLOCK` · `UNVERIFIED`), shared with `flutter-publish`'s preflight so the two never disagree about what "signed" means. It checks:

| Check | Tool | BLOCK when |
|-------|------|-----------|
| `freshness` | mtime vs `--started-at` | artifact predates this build — **never report a stale file as success** |
| `applicationId` | bundletool / aapt2 | `com.example.*`; placeholder prefixes (`com.myapp.`, `com.tenapp.`, `com.test.`, `com.app.`) |
| `targetSdk` | same | below the floor (36; 35 is WARN before 2026-08-31) — compares against today's date |
| `debuggable` | same | `true` |
| `versionCode` | same | > 2,100,000,000 |
| `signing` | `jarsigner` (AAB) / `apksigner` (APK) | unsigned or `CN=Android Debug`. **They are not interchangeable**: jarsigner reads v1 only and AGP omits v1 when `minSdk >= 24` |
| `alignment16k` | `readelf -lW` on every `.so` | any LOAD alignment below `0x4000` — the offending plugin path is named |
| `size` | file size | > 500 MB; WARN > 200 MB; WARN > 60 MB (unusual for Flutter — look at assets) |

`UNVERIFIED` means the tool is missing (bundletool, jarsigner, readelf/llvm-readelf) and is **never** counted as a pass — the script names what to install. Exit 1 on any BLOCK. Portable: `stat`/`readelf` fall back to their macOS spellings.

Read `build/release/verify.json`; the report's `Checks` line is copied from it.

### Step 7 — Save artifacts and provenance

```bash
cp "$OUT" build/release/
[ -d build/debug-info ] && cp -r build/debug-info "build/release/debug-info-$VERSION_CODE"
```

**The debug-info directory is the only thing that can decode crash reports from an obfuscated release.** Keep it per version code, and never delete one for a version still live on Play. See `references/obfuscation.md`.

Write `build/release/build-info.json` — this is what lets `flutter-publish` tell whether the AAB matches the source. `sha256`, `version_code`, `target_sdk` and the alignment result come from `verify.json`, not from a second computation:

```json
{
  "artifact": "app-release.aab",
  "sha256": "<sha256sum>",
  "version_name": "1.2.3",
  "version_code": 8,
  "flavor": null,
  "obfuscated": true,
  "debug_info": "build/release/debug-info-8",
  "git": { "sha": "<git rev-parse HEAD>", "dirty": false, "branch": "main" },
  "flutter": "<flutter --version, first line>",
  "target_sdk": 36,
  "verify": "build/release/verify.json",
  "built_at": "2026-07-27T10:00:00Z",
  "duration_seconds": 214
}
```

### Step 8 — Report

```
FLUTTER BUILD — <OK | FAILED>

Artifact   build/release/app-release.aab  (24 MB)
Version    1.2.3+8   (was 1.2.3+7)
Signing    release key, CN=<owner>
Checks     targetSdk 36 · not debuggable · 16 KB aligned · signed
Source     <git sha> on main (clean)
Time       3m 34s

Debug info build/release/debug-info-8  ← keep; required to read crashes for this release

Next: flutter-store-metadata → flutter-store-compliance → flutter-publish
```

Report gate warnings even on success. If `targetSdk` was implicit and resolved to something below the floor, say so — the user still has to fix it before publishing.

## Reference files

| File | Read when |
|------|-----------|
| `references/build-errors.md` | The build fails |
| `references/obfuscation.md` | Enabling obfuscation, or a crash report is unreadable |

| Script | Run at |
|--------|--------|
| `scripts/verify-artifact.sh` | Step 6 — manifest, signing, debuggable, 16 KB, size → `verify.json`; exit 1 on BLOCK |

## Scope

Does: gate, version, build, verify, and record an Android release artifact.

Does not: generate signing keys (`flutter-signing`); prepare store assets (`flutter-store-metadata`); upload (`flutter-publish`); build for iOS (needs macOS and a separate App Store flow).
