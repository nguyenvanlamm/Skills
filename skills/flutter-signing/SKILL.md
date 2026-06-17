---
name: flutter-signing
description: "Generate keystore, configure release signing, and backup keys for a Flutter Android project. Use when user says 'signing', 'keystore', 'key store', 'release key', 'sign app', 'ký app', 'flutter signing'. Run after flutter-init and before flutter-build."
license: MIT
---

# Flutter Signing

Step 6 of the Flutter → Google Play pipeline: create a keystore, configure `build.gradle`, and backup signing credentials.

## Prerequisites

- Flutter project already created (`flutter create` run)
- Java 17+ (checked by `flutter doctor`)

## Input

Ask the user for these if not in `$ARGUMENTS`:

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `key_alias` | ❌ | `upload` | Alias for the key in keystore |
| `validity_days` | ❌ | `10000` | Key validity (~27 years) |
| `keysize` | ❌ | `2048` | RSA key size in bits |
| `store_password` | ❌ | Auto-generated | Keystore password (20+ random chars) |
| `key_password` | ❌ | Auto-generated | Key password (20+ random chars) |
| `dname` | ❌ | Derived from project | Distinguished name (CN/OU/O/L/ST/C) |

## Steps

### Step 1: Detect Project & Existing Signing

```bash
# Detect project type
ls android/app/build.gradle 2>/dev/null && BUILD_FILE="android/app/build.gradle"
ls android/app/build.gradle.kts 2>/dev/null && BUILD_FILE="android/app/build.gradle.kts"

# Detect existing signing
[ -f android/key.properties ] && echo "EXISTS"
grep -n "signingConfigs" "$BUILD_FILE" 2>/dev/null
```

**Branch:**
- No Flutter project → abort with message: "Run `flutter-init` first"
- Signing already configured → ask: overwrite? (WARNING: will invalidate existing app updates)
- `build.gradle.kts` (Kotlin DSL) detected → use Kotlin syntax

### Step 2: Generate Passwords

Generate cryptographically strong passwords:

```bash
# Generate 24-char passwords
STORE_PASS=$(openssl rand -base64 18 | tr -d '+/=' | cut -c1-24)
KEY_PASS=$(openssl rand -base64 18 | tr -d '+/=' | cut -c1-24)
```

**Fallback** if `openssl` unavailable: use `/dev/urandom` + `tr`.

### Step 3: Generate Keystore

```bash
keytool -genkey -v \
  -keystore android/app/upload-keystore.jks \
  -keyalg RSA \
  -keysize $KEYSIZE \
  -validity $VALIDITY_DAYS \
  -alias "$KEY_ALIAS" \
  -storepass "$STORE_PASS" \
  -keypass "$KEY_PASS" \
  -dname "CN=$CN, OU=$OU, O=$O, L=$L, ST=$ST, C=$C"
```

Derive `$dname` from project context:
```
CN = Developer name (prompt if unknown)
OU = "Development"
O  = Organization name (from org field)
L  = City (ask user)
ST = State (ask user)
C  = "VN" (or user's country)
```

**Edge case:** `keytool` not found → `flutter doctor` needs `java`. Install OpenJDK:
```bash
sudo apt install openjdk-17-jdk -y  # Linux
brew install openjdk@17              # macOS
echo 'export JAVA_HOME=$(/usr/libexec/java_home)' >> ~/.zshrc
```

### Step 4: Create key.properties

Write to `android/key.properties`:

```properties
storePassword=$STORE_PASS
keyPassword=$KEY_PASS
keyAlias=$KEY_ALIAS
storeFile=upload-keystore.jks
```

Set restrictive permissions:
```bash
chmod 600 android/key.properties
```

### Step 5: Update build.gradle / build.gradle.kts

**For build.gradle (Groovy):**

Add before `android {` block (if not already present):

```groovy
def keystoreProperties = new Properties()
def keystorePropertiesFile = rootProject.file('key.properties')
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}

android {
    ...
    signingConfigs {
        release {
            keyAlias keystoreProperties['keyAlias']
            keyPassword keystoreProperties['keyPassword']
            storeFile keystoreProperties['storeFile'] ? file(keystoreProperties['storeFile']) : null
            storePassword keystoreProperties['storePassword']
        }
    }

    buildTypes {
        release {
            signingConfig signingConfigs.release
            ...
        }
    }
}
```

**For build.gradle.kts (Kotlin DSL):**

```kotlin
import java.util.Properties
import java.io.FileInputStream

val keystoreProperties = Properties()
val keystorePropertiesFile = rootProject.file("key.properties")
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(FileInputStream(keystorePropertiesFile))
}

android {
    ...
    signingConfigs {
        create("release") {
            keyAlias = keystoreProperties["keyAlias"].toString()
            keyPassword = keystoreProperties["keyPassword"].toString()
            storeFile = keystoreProperties["storeFile"]?.let { file(it) }
            storePassword = keystoreProperties["storePassword"].toString()
        }
    }

    buildTypes {
        getByName("release") {
            signingConfig = signingConfigs.getByName("release")
            ...
        }
    }
}
```

### Step 6: Backup Keystore

```bash
PROJECT_NAME=$(basename $(pwd))
BACKUP_DIR="$HOME/.flutter-keys/$PROJECT_NAME"
mkdir -p "$BACKUP_DIR"
cp android/app/upload-keystore.jks "$BACKUP_DIR/"
echo "$STORE_PASS" > "$BACKUP_DIR/store-password.txt"
echo "$KEY_PASS" > "$BACKUP_DIR/key-password.txt"
chmod 600 "$BACKUP_DIR"/*.txt
```

### Step 7: Update .gitignore

Ensure these lines exist in `.gitignore`:

```
android/app/upload-keystore.jks
android/key.properties
```

**Append if not present.**

### Step 8: Verify Signing

```bash
cd android
./gradlew signingReport 2>&1 | grep -A5 "Variant: release"
```

Check output contains `SigningConfig` with your key alias.

### Step 9: Report

```
══════════════════════════════════════════
  FLUTTER SIGNING — COMPLETE
══════════════════════════════════════════

  ✓ Keystore:       android/app/upload-keystore.jks
  ✓ Key alias:      upload
  ✓ Key size:       2048-bit RSA
  ✓ Config:         android/key.properties
  ✓ build.gradle:   signingConfigs.release configured
  ✓ .gitignore:     keystore excluded from Git

  Backup location:
    ~/.flutter-keys/$PROJECT_NAME/
    (keystore + passwords)

  ⚠️ ⚠️ ⚠️  CRITICAL WARNING  ⚠️ ⚠️ ⚠️
    If you LOSE this keystore:
    • App updates will be REJECTED by Google Play
    • You must create a NEW app (losing all ratings/reviews)
    
    Backup to a safe place outside this machine:
    • USB drive
    • Password manager (1Password, Bitwarden)
    • Cloud vault (Google Drive encrypted)

  Next step:
    flutter build appbundle       # or use flutter-build skill
```

## Edge Cases

| Problem | Handling |
|---------|----------|
| No Java installed | Install OpenJDK 17, then retry |
| Keystore exists | Warn of consequences, ask overwrite |
| Kotlin DSL (build.gradle.kts) | Auto-detect and use Kotlin syntax |
| openssl not available | Use `/dev/urandom` + `tr` for password |
| Windows paths | Use `\` in key.properties storeFile |
| User wants specific passwords | Accept as input, don't generate |
| Gradle signingReport fails | Print full error, suggest `cd android && ./gradlew signingReport` manually |

## What This Skill Does NOT Do

- ❌ Build APK/AAB (see `flutter-build`)
- ❌ Upload to Google Play (see `flutter-publish`)
- ❌ Register as Google Play App Signing (manual step in Play Console)

## Acceptance Criteria

- [ ] `android/app/upload-keystore.jks` created
- [ ] `android/key.properties` created with correct passwords
- [ ] `build.gradle` or `build.gradle.kts` updated with release signing config
- [ ] Keystore backed up to `~/.flutter-keys/<project>/`
- [ ] `.gitignore` updated to exclude keystore + key.properties
- [ ] `./gradlew signingReport` shows release variant with signing config
