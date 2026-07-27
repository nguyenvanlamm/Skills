# Diagnosing build failures

The full log is `build/release/build.log`. Gradle's real error is rarely in the last 20 lines — it is usually 50–200 lines above, followed by a wall of "Try:" boilerplate. Search for the cause first:

```bash
grep -nE "FAILURE:|error:|Execution failed|Caused by:|^e: |AAPT" build/release/build.log | head -30
```

Then read ~15 lines around the first hit. Report *that*, not the tail.

## Gradle / toolchain

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Execution failed for task ':app:lintVitalRelease'` | Lint error only in release mode | Fix the reported lint issue. Disabling `lintVital` hides real problems; suggest it only as a temporary unblock. |
| `Could not find method X()` | Gradle DSL vs AGP version mismatch, often Groovy syntax in a `.kts` file | Check `android/settings.gradle` plugin versions and `gradle/wrapper/gradle-wrapper.properties` |
| `Unsupported class file major version` | JDK too new for Gradle | Match JDK to AGP (JDK 17 for AGP 8.x); set `org.gradle.java.home` in `android/gradle.properties` |
| `Minimum supported Gradle version is X` | Wrapper too old | Bump `distributionUrl` in `gradle-wrapper.properties` |
| `SDK location not found` | `ANDROID_HOME` unset and no `local.properties` | Write `sdk.dir=/path/to/Android/sdk` into `android/local.properties` |
| `Failed to install the following Android SDK packages` | Missing platform/build-tools | `sdkmanager "platforms;android-36" "build-tools;36.0.0"` |
| `NDK not configured` / `No version of NDK matched` | `ndkVersion` names an uninstalled NDK | `sdkmanager --list \| grep ndk`, install **r28 or newer** (r25/r26/r27 misalign `.so` for 16 KB pages), then set `ndkVersion` in `android/app/build.gradle` |

## Memory and performance

| Symptom | Fix |
|---------|-----|
| `OutOfMemoryError` / `GC overhead limit` / daemon killed | `org.gradle.jvmargs=-Xmx4g -XX:MaxMetaspaceSize=1g` in `android/gradle.properties`. On a 8 GB machine use `-Xmx2g` — over-allocating makes it worse, not better. |
| `Daemon disappeared unexpectedly` | Usually the OOM killer. Same fix, plus close other builds. |
| Build takes > 10 minutes | Normal for a first release build (AOT compile for every ABI). Only investigate if a *repeat* build is slow — then check `org.gradle.caching=true` and that antivirus is not scanning `build/`. |

## Resources and assets

| Symptom | Cause | Fix |
|---------|-------|-----|
| `AAPT: error: resource ... not found` | Missing or misnamed resource | Filenames in `res/` must be lowercase, digits, underscore only |
| `Asset not found` / blank images at runtime | Path missing from `pubspec.yaml` | Add to `flutter: assets:`; a directory entry needs the trailing `/` and does not recurse |
| `Duplicate class` | Two plugins pulling different versions of the same library | `flutter pub deps | grep <lib>`, then pin a version or drop one plugin |
| `Manifest merger failed` | Conflicting attribute between the app and a plugin manifest | The error names the attribute; add `tools:replace="..."` in `AndroidManifest.xml` |

## Signing

| Symptom | Cause | Fix |
|---------|-------|-----|
| Build succeeds but the artifact is debug-signed | `key.properties` missing or `storeFile` unresolvable — Flutter falls back silently | Rerun `flutter-signing`. `storeFile` is relative to `android/app/`. |
| `Keystore was tampered with, or password was incorrect` | Wrong password, or a corrupted `.jks` | Verify with `keytool -list -keystore <file>`. If the password is lost and the app is already published, Play Console → Setup → App signing → request an upload key reset. |
| `Failed to read key ... from store` | Wrong `keyAlias` | `keytool -list -keystore <file>` shows the real aliases |

## Dart / Flutter

| Symptom | Fix |
|---------|-----|
| Compiles in debug, fails in release only | Almost always tree-shaking or obfuscation. Test with `--release` but no `--obfuscate` to isolate — see `obfuscation.md`. |
| `Tree-shaking icons` fails on non-constant `IconData` | Pass `--no-tree-shake-icons`, or make the icon reference constant (preferred — the flag adds ~1 MB) |
| `version solving failed` | Read the reported constraint pair. `flutter pub upgrade --major-versions` only with the user's consent — it accepts breaking changes. |
| `Target of URI doesn't exist` for generated files | Run the generator: `dart run build_runner build --delete-conflicting-outputs` |

## When nothing matches

In order, cheapest first:

1. `flutter doctor -v` — a broken toolchain explains a lot of nonsense errors
2. `flutter clean && flutter pub get` and rebuild
3. `cd android && ./gradlew assembleRelease --stacktrace` — Gradle's own error is often clearer than Flutter's wrapper
4. `rm -rf ~/.gradle/caches/` — last resort, forces a full re-download

Report what was tried and what the actual error said. Do not report "build failed, try flutter clean" as a diagnosis.
