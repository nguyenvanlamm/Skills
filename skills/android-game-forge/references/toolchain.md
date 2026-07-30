# Toolchain, Gradle files, and build triage

## Non-negotiable targets

| Setting | Value | Why |
|---------|-------|-----|
| `compileSdk` / `targetSdk` | **36** | From **31 Aug 2026** Google Play refuses new submissions and updates targeting below API 36 (extensions available to 1 Nov 2026). Generating a game at 35 today ships it unpublishable. |
| `minSdk` | 24 | Covers ~99% of active devices and lets AGP skip v1 APK signing. |
| JVM target | 17 | AGP 8's floor. JDK 21 also builds fine. |
| Orientation | portrait, locked | The virtual 1000×1778 world assumes it. |
| Display | edge-to-edge | Mandatory on API 35+; opting out is deprecated. |

## Versions: resolve, don't trust a pin

Hardcoded versions rot, and a stale pin fails at dependency resolution — minutes into a build, with an error that looks like a network fault. Run:

```bash
bash scripts/resolve-versions.sh > gradle/libs.versions.toml
```

It queries Google's and Maven Central's `maven-metadata.xml` for the newest stable AGP, Kotlin, and Compose BOM, and falls back to pinned values offline. Known-good fallbacks as of July 2026: **Kotlin 2.4.10** (the Compose compiler plugin version always equals the Kotlin version), **Compose BOM 2026.06.01**, AGP **8.13.2**. AGP's newest stable moves monthly — let the script fetch it.

Prefer the newest stable **8.x** AGP over 9.x for generated projects: AGP 9 removed `kotlinOptions` and several variant APIs, so half the Gradle snippets in circulation break against it.

```toml
[versions]
agp = "…"            # newest stable 8.x
kotlin = "2.4.10"
composeBom = "2026.06.01"
coreKtx = "1.19.0"
activityCompose = "1.13.0"

[libraries]
androidx-core-ktx = { group = "androidx.core", name = "core-ktx", version.ref = "coreKtx" }
androidx-activity-compose = { group = "androidx.activity", name = "activity-compose", version.ref = "activityCompose" }
compose-bom = { group = "androidx.compose", name = "compose-bom", version.ref = "composeBom" }
compose-ui = { group = "androidx.compose.ui", name = "ui" }
compose-ui-graphics = { group = "androidx.compose.ui", name = "ui-graphics" }
compose-ui-tooling-preview = { group = "androidx.compose.ui", name = "ui-tooling-preview" }
compose-material3 = { group = "androidx.compose.material3", name = "material3" }

[plugins]
android-application = { id = "com.android.application", version.ref = "agp" }
kotlin-android = { id = "org.jetbrains.kotlin.android", version.ref = "kotlin" }
kotlin-compose = { id = "org.jetbrains.kotlin.plugin.compose", version.ref = "kotlin" }
```

Three plugins, and only the three. `org.jetbrains.kotlin.plugin.compose` is required from Kotlin 2.0 on — the old `composeOptions { kotlinCompilerExtensionVersion }` block is dead, and leaving it in produces a confusing "Compose Compiler not found" failure.

Compose artifacts carry no version: the BOM sets them. A version on `compose-ui` silently overrides the BOM and desynchronises the set.

## app/build.gradle.kts essentials

```kotlin
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "com.yourname.yourgame"     // must equal the package in every .kt file
    compileSdk = 36
    defaultConfig {
        applicationId = "com.yourname.yourgame"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1.0.0"
    }
    buildFeatures { compose = true }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlin { compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) } }
    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
}
```

`namespace`, `applicationId`, the directory path under `src/main/java/`, and every file's `package` line must agree. A mismatch compiles and then fails at runtime with a missing-Activity crash — which the Step 7 smoke test is there to catch.

**`applicationId` must never start with `com.example.`** — Play rejects it permanently, and it cannot be changed after first publish. Placeholder prefixes like `com.myapp.` or `com.test.` are worse: Play accepts them, and the game ships forever under a name the user does not own.

`gradle.properties`:

```properties
org.gradle.jvmargs=-Xmx3072m -Dfile.encoding=UTF-8
org.gradle.caching=true
org.gradle.parallel=true
android.useAndroidX=true
kotlin.code.style=official
```

## AndroidManifest.xml

```xml
<uses-permission android:name="android.permission.VIBRATE"/>

<application android:label="@string/app_name" android:icon="@mipmap/ic_launcher"
             android:roundIcon="@mipmap/ic_launcher_round" android:theme="@style/Theme.Game">
    <activity android:name=".MainActivity" android:exported="true"
              android:screenOrientation="portrait"
              android:configChanges="orientation|screenSize|keyboardHidden">
        <intent-filter>
            <action android:name="android.intent.action.MAIN"/>
            <category android:name="android.intent.category.LAUNCHER"/>
        </intent-filter>
    </activity>
</application>
```

`VIBRATE` is the only permission a game like this needs. Every extra permission is a Play data-safety question the user has to answer, so do not add network, storage, or ads permissions "for later".

All user-visible strings go in `res/values/strings.xml`. `Theme.Game` extends `Theme.Material3.DayNight.NoActionBar` with a transparent status bar — the Compose theme does the real work.

## Launcher icon

Ship a real adaptive icon: `mipmap-anydpi-v26/ic_launcher.xml` with `<background>` as a palette-coloured drawable and `<foreground>` as a vector glyph inset to the safe zone (the outer ~18% on each side gets masked away by the launcher).

The default green Android robot makes the entire build look unfinished, and it is the first thing the user sees. Draw the glyph from the game's core shape in one or two palette colours; a monochrome vector beats a detailed raster here because every launcher masks it into a different silhouette.

## Build triage

Read the real error before editing anything: `grep -nE "^e: |error:|FAILURE|Caused by" /tmp/build-a.log | head -30`

| Symptom | Cause and fix |
|---------|---------------|
| `Unresolved reference: <Composable or token>` | The #1 failure in generated Compose projects. Missing import, not missing code. Write **every** import explicitly — `androidx.compose.foundation.layout.*` does not cover `Canvas`, `animateFloatAsState`, `withFrameNanos`, or `graphicsLayer`. |
| `Unresolved reference: R` | The `R` import is missing, or an earlier resource error killed generation. Fix the resource error first; `R` failures are usually a symptom. |
| `resource raw/x not found` / `font/y not found` | Something references an asset that was never created. Create the file or stub the call. Never leave a dangling `R.*`. |
| `Compose Compiler not found` / plugin errors | `org.jetbrains.kotlin.plugin.compose` is missing, or its version does not equal the Kotlin version. |
| `Minimum supported Gradle version is X` | `./gradlew wrapper --gradle-version X` then rebuild. |
| `Unsupported class file major version` | JDK mismatch. AGP 8 needs JDK 17+; check `java -version` and `JAVA_HOME`. |
| `Failed to resolve: androidx.…` | Offline, or a version that does not exist. Re-run `scripts/resolve-versions.sh` with network. |
| `SDK location not found` | Write `sdk.dir=$ANDROID_HOME` into `local.properties` — and keep `local.properties` out of git. |
| `licences have not been accepted` | `sdkmanager --licenses`. |
| Build succeeds, app crashes on launch | Almost always a namespace/package/`.MainActivity` mismatch. Read `adb logcat -d -b crash`. |

Two rules that save the most time: fix errors **top-down** — the first Kotlin error frequently causes the next twenty — and after any Gradle-file edit, re-run the full `assembleDebug` rather than trusting an incremental pass.
