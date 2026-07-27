# Gradle release signing

## The failure this configuration must prevent

Flutter's default template has no release `signingConfig`. When one is missing, `flutter build appbundle --release` does **not** fail — it signs with the debug key and reports success. The resulting AAB is rejected by Play, and nothing before the upload says why.

So the config below does two things: attach the release signing config, and **fail the build** when `key.properties` is absent. A loud failure at build time is worth far more than a silent fallback discovered at upload time.

## Groovy — `android/app/build.gradle`

Above the `android {` block:

```groovy
def keystoreProperties = new Properties()
def keystorePropertiesFile = rootProject.file('key.properties')
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}
```

Inside `android { }`:

```groovy
signingConfigs {
    release {
        if (keystorePropertiesFile.exists()) {
            keyAlias keystoreProperties['keyAlias']
            keyPassword keystoreProperties['keyPassword']
            storeFile file(keystoreProperties['storeFile'])
            storePassword keystoreProperties['storePassword']
        }
    }
}

buildTypes {
    release {
        if (!keystorePropertiesFile.exists()) {
            throw new GradleException(
                "android/key.properties not found — release build would be signed with the debug key. Run the flutter-signing skill.")
        }
        signingConfig signingConfigs.release
        minifyEnabled true
        shrinkResources true
    }
}
```

`rootProject.file('key.properties')` resolves to `android/key.properties`, while `storeFile` resolves relative to `android/app/`. The two are different base directories — a common source of "keystore not found" when someone moves one but not the other.

## Kotlin DSL — `android/app/build.gradle.kts`

At the top of the file:

```kotlin
import java.util.Properties
import java.io.FileInputStream

val keystorePropertiesFile = rootProject.file("key.properties")
val keystoreProperties = Properties().apply {
    if (keystorePropertiesFile.exists()) load(FileInputStream(keystorePropertiesFile))
}
```

Inside `android { }`:

```kotlin
signingConfigs {
    create("release") {
        if (keystorePropertiesFile.exists()) {
            keyAlias = keystoreProperties["keyAlias"] as String
            keyPassword = keystoreProperties["keyPassword"] as String
            storeFile = file(keystoreProperties["storeFile"] as String)
            storePassword = keystoreProperties["storePassword"] as String
        }
    }
}

buildTypes {
    getByName("release") {
        check(keystorePropertiesFile.exists()) {
            "android/key.properties not found — release build would be signed with the debug key."
        }
        signingConfig = signingConfigs.getByName("release")
        isMinifyEnabled = true
        isShrinkResources = true
    }
}
```

## Editing an existing file

Do not paste a whole `android { }` block over one that already exists — flavors, `ndkVersion`, `compileSdk`, and plugin blocks live there. Insert only the missing pieces:

1. Is `keystoreProperties` already loaded at the top? If yes, reuse it.
2. Does `signingConfigs { release { … } }` exist? If yes, check it reads from `key.properties` rather than hardcoding a path or a password.
3. Does `buildTypes { release { … } }` set `signingConfig`? This is the line most often missing.

A hardcoded password in `build.gradle` is a finding, not a working config — move it to `key.properties` and treat the old value as leaked if the file was ever committed.

## Flavors

With product flavors, each release variant needs the signing config. Setting it once on the `release` build type covers all flavors; per-flavor keys need `productFlavors { … signingConfig signingConfigs.<name> }` instead.

## Verify, do not assume

```bash
(cd android && ./gradlew signingReport) 2>&1 | grep -A6 "Variant: release"
```

The `Store:` line must point at the keystore and `Alias:` at the configured alias. If it shows `debug.keystore`, the config is not attached — regardless of what the file looks like.
