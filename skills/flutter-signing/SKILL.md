---
name: flutter-signing
description: "Generate keystore, configure release signing, and back up keys for a Flutter Android project. Use when user says 'signing', 'keystore', 'key store', 'release key', 'sign app', 'ký app', 'flutter signing'. Run after flutter-init and before flutter-build."
license: MIT
metadata:
  version: 2.1.0
---

# Flutter Signing

Step 6 of the Flutter → Google Play pipeline: create an upload key, wire release signing into Gradle, and get the key somewhere it will survive this machine.

## Core principle

> **The keystore outlives the project.** Everything else here can be redone in minutes; a signing key that is lost, or leaked, is a problem with no clean fix. Treat custody as the deliverable and the Gradle config as the easy part.

Read `references/key-custody.md` before telling the user anything about what losing the key costs — the answer depends on Play App Signing, and the common advice ("you lose the app and all its reviews") is wrong for apps enrolled in it.

## Input

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `key_alias` | ❌ | `upload` | Alias inside the keystore |
| `validity_days` | ❌ | `10000` | ~27 years; Play requires validity past 22 Oct 2033 |
| `keysize` | ❌ | `4096` | RSA bits; 2048 is the minimum Play accepts |
| `store_password` | ❌ | generated | 24+ random characters |
| `key_password` | ❌ | generated | Same |
| `dname` | ❌ | `CN=<app or developer name>` | Google does not verify these fields |

Do not interrogate the user for OU/L/ST/C. The distinguished name is never checked by Play; asking for a city and a state adds friction and no value. `CN` alone is fine.

## Workflow

### Step 1 — Inspect what exists

```bash
ls android/app/build.gradle android/app/build.gradle.kts 2>/dev/null
[ -f android/key.properties ] && echo "key.properties EXISTS"
ls android/app/*.jks android/app/*.keystore 2>/dev/null
grep -n "signingConfigs" android/app/build.gradle* 2>/dev/null
```

| Situation | Action |
|-----------|--------|
| Not a Flutter project | Stop: run `flutter-init` first |
| Keystore + `key.properties` already present | **Ask before touching anything.** If the app has ever been uploaded to Play, a new key breaks updates until an upload key reset is approved. Regenerating is rarely what the user means. |
| Kotlin DSL (`build.gradle.kts`) | Use the Kotlin syntax in `references/gradle-config.md` |

### Step 2 — Check the repo for already-leaked material

Before creating anything, find out whether a previous key is already in git:

```bash
git ls-files | grep -E '\.jks$|\.keystore$|key\.properties'
git log --all --oneline -- '*.jks' '*.keystore' 'android/key.properties' | head
```

Anything found means the credential is compromised — add to `.gitignore`, remove from the index, and generate a **new** key rather than reusing it. If the repo was ever pushed, say plainly that deleting the file does not undo the exposure.

### Steps 3–5 — Generate passwords, keystore and key.properties

One script does all three, and does the parts that are easy to get wrong correctly:

```bash
bash <skill-dir>/scripts/generate-keystore.sh --cn "<App Name>" [--alias upload] [--keysize 4096] [--validity 10000]
```

What it guarantees, and why each matters:

- **Passwords never touch `argv` or stdin prompts.** They are generated (`openssl rand`, 30 chars) and handed to keytool through `-storepass:env` / `-keypass:env`. The v2.0 instructions piped two passwords on stdin — but `keytool -genkeypair` prompts *store, re-enter store, key, re-enter key*, so that pipe fed the wrong answers and failed with "passwords don't match" on every run.
- **PKCS12, not JKS.** JKS is deprecated by the JDK (a warning on every use) and its separate store/key passwords are the source of the prompt-sequence trap above. PKCS12 has one password for both; `key.properties` carries it twice and Gradle is happy.
- `key.properties` is written with `umask 077` and `chmod 600`; `.gitignore` gets the credential patterns; `git check-ignore` confirms both files are untracked.
- It **refuses** to overwrite an existing keystore without `--force`, and says why (a published app breaks on a new key). With `--force` the old files are moved to `*.bak.<timestamp>`, never deleted.
- It verifies the keystore opens with the recorded password and prints SHA-1 / SHA-256.

If `keytool` is missing, the JDK is missing — `flutter doctor` will say the same. Install OpenJDK 17 (AGP 8.x expects 17, not the newest available).

`storeFile` is resolved relative to `android/app/`. On Windows, a `.properties` file treats `\` as an escape character — write `C:/keys/upload.jks` or `C:\\keys\\upload.jks`, never a single backslash. A path with one backslash silently resolves to nothing, and Flutter then falls back to **debug signing without failing the build**.

### Step 6 — Gradle configuration

Read `references/gradle-config.md` and apply the block matching the project's DSL. The critical detail: `signingConfig` must be attached to the **release** build type, and the config must fail loudly when `key.properties` is absent rather than falling through to the debug key.

### Step 7 — Back it up

Read `references/key-custody.md`. A copy in `~/.flutter-keys/` on the same disk as the original is not a backup, and passwords stored next to the keystore mean one compromise loses both.

### Step 8 — .gitignore

```
*.jks
*.keystore
android/key.properties
service-account.json
```

Append only what is missing, then confirm the files are actually untracked:

```bash
git check-ignore -v android/key.properties android/app/upload-keystore.jks
```

`.gitignore` does not affect files git already tracks — if Step 2 found any, they must be removed from the index explicitly.

### Step 9 — Verify

```bash
# The keystore opens with the recorded password and contains the alias (the script already did this once)
KS_PASS=$(sed -n 's/^storePassword=//p' android/key.properties) keytool -list -v \
  -keystore android/app/upload-keystore.jks -storepass:env KS_PASS -alias upload | grep -E "Alias|Valid|SHA1|SHA256"

# Gradle picks it up for the release variant
(cd android && ./gradlew signingReport) 2>&1 | grep -A6 "Variant: release"
```

Both must pass. `signingReport` alone is not enough — it will happily report the debug config for the release variant if `signingConfig` was never attached, which is exactly the failure this skill exists to prevent.

Record the **SHA-1 and SHA-256 fingerprints** in the report. They are needed for Firebase, Google Sign-In, and Maps configuration, and digging them back out later is tedious.

### Step 10 — Report

```
FLUTTER SIGNING — OK

Keystore    android/app/upload-keystore.jks  (PKCS12, RSA 4096, alias "upload", valid to 2053-07)
Config      android/key.properties (chmod 600) · signingConfigs.release attached
Verified    keytool -list OK · gradlew signingReport shows release variant signed
Ignored     *.jks, key.properties untracked (git check-ignore confirmed)

Fingerprints (needed for Firebase / Google Sign-In):
  SHA-1    AB:CD:...
  SHA-256  12:34:...

Backup — not done for you:
  ✗ Keystore + passwords are still only on this machine.
    Put them in a password manager now: <what to store, from key-custody.md>

Next: flutter-build
```

Never report backup as complete when the only copy is a second file on the same disk. Say what the user still has to do.

## Reference files

| File | Read when |
|------|-----------|
| `references/gradle-config.md` | Step 6 — Groovy and Kotlin DSL blocks, with the fail-loud variant |
| `references/key-custody.md` | Step 7 — Play App Signing, what loss actually costs, how to store the key |

| Script | Run at |
|--------|--------|
| `scripts/generate-keystore.sh` | Steps 3–5 — passwords via `:env`, PKCS12 keystore, `key.properties`, `.gitignore`, verification, fingerprints |

## Scope

Does: generate an upload key, configure release signing, verify it is actually in effect, and set the user up to keep the key.

Does not: build (`flutter-build`); enrol in Play App Signing (accepted in Console at first upload — see `flutter-publish`); store the key for the user; recover a lost key.
