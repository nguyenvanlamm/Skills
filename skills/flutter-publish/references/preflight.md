# Preflight gates

Run every check. Report as one table: `check | value | verdict`. **BLOCK** means Play will reject the upload or the review — stop. **WARN** means it will upload but is likely to cost the user something later.

## Tooling

Most checks read the AAB's real manifest, which is protobuf — `unzip`/`grep` cannot read it. Use `bundletool`:

```bash
command -v bundletool || ls ~/bundletool.jar
```

If missing, install (`brew install bundletool`, or download `bundletool-all-*.jar` from https://github.com/google/bundletool/releases and use `java -jar bundletool.jar …`). If it cannot be installed, fall back to reading `android/app/build.gradle{,.kts}` and `pubspec.yaml` and **mark those results as unverified** — the gradle files describe what *should* have been built, not what is in the AAB.

Define once:

```bash
AAB="${aab_path:-$(find build/release . -name '*.aab' -path '*build*' -type f 2>/dev/null | head -1)}"
BT() { command -v bundletool >/dev/null && bundletool "$@" || java -jar ~/bundletool.jar "$@"; }
MF() { BT dump manifest --bundle="$AAB" --xpath="$1" 2>/dev/null; }
```

If multiple AABs are found, list them with size and mtime and let the user pick. Never silently take the first.

## Gate 0 — Provenance — WARN

`flutter-build` (v2+) writes `build/release/build-info.json`. Use it to confirm the AAB is the one that was actually built and verified:

```bash
sha256sum "$AAB"
grep -E '"sha256"|"git"|"dirty"|"version_code"' build/release/build-info.json
```

- Checksum mismatch, or file missing → **WARN**: this AAB's provenance is unknown, so run every gate below rather than trusting anything upstream.
- `"dirty": true` → **WARN**: built from uncommitted work, so the released binary cannot be reproduced from any commit.

## Gate 1 — Compliance verdict — BLOCK on FAIL

`flutter-store-compliance` v2 writes a machine-readable verdict. Read that, not the prose:

```bash
python3 -c "
import json; r = json.load(open('store-metadata/compliance-report.json'))
print(r['overall'], r['counts'])
for c in r['checks']:
    if c['verdict'] in ('FAIL','WARN'): print(c['verdict'], c['id'], '-', c['summary'])
"
```

| `overall` | Action |
|-----------|--------|
| `FAIL` | **BLOCK.** List every FAIL check with its `fix`. |
| `WARN` | **WARN.** List them; the user decides. |
| `PASS` | OK. |

Fallbacks, in order:

- JSON missing but `compliance-report.md` present → a v1 report. Grep `OVERALL:` and parse **FAIL first**, then `PASS WITH ISSUES`/`PARTIAL` → WARN, then `PASS` → OK. Checking for `PASS` first is wrong: it is a substring of `PASS WITH ISSUES`. Recommend re-running the audit for a gateable verdict.
- Neither file → **WARN**: the audit never ran. Offer to run it now; publishing unaudited is the user's call.

## Gate 2 — Application ID — BLOCK

```bash
MF "/manifest/@package"
```

- Starts with `com.example.` → **BLOCK**. Play permanently rejects it, and the ID cannot be changed after first publish. Fix `applicationId` in `android/app/build.gradle{,.kts}` and rebuild.
- Other placeholder prefixes — `com.myapp.`, `com.tenapp.`, `com.test.`, `com.app.` — → **BLOCK** too. Play accepts them, which is worse: the app ships under a name the user does not control and can never change. Ask for a reverse-domain they own.
- Contains `test`, `demo`, or `temp` elsewhere in the ID → **WARN**, same permanence argument.
- Differs from `publish-state.json` `app_id` → **BLOCK**. A changed ID is a different app on Play, not an update.

## Gate 3 — Target API level — BLOCK

```bash
MF "/manifest/uses-sdk/@android:targetSdkVersion"
```

| Target | Verdict |
|--------|---------|
| ≥ 36 | OK |
| 35 | **BLOCK from 31 Aug 2026** — after that date new apps and updates must target API 36+. Before it: WARN, and recommend bumping now. An extension to 1 Nov 2026 can be requested in Play Console. |
| ≤ 34 | **BLOCK.** Also invisible to users on newer Android even where accepted. |

Compare against today's date, not against a date hardcoded here. Fix by setting `targetSdk`/`compileSdk` in `android/app/build.gradle{,.kts}` and rebuilding.

## Gate 4 — 16 KB page alignment — BLOCK if targeting Android 15+

Since 1 Nov 2025 Play rejects uploads whose native libraries are not 16 KB aligned when the app targets Android 15+.

```bash
WORK=$(mktemp -d); unzip -q -o "$AAB" -d "$WORK"
find "$WORK" -name '*.so' | while read -r so; do
  printf '%s %s\n' "$(readelf -lW "$so" | awk '$1=="LOAD"{print $NF}' | sort -u | tail -1)" "$so"
done
```

Every LOAD alignment must be `0x4000` (16 KB) or larger. `0x1000` (4 KB) → **BLOCK**.

A pure-Dart Flutter app with no `.so` output beyond the engine's is fine on Flutter 3.22+. Misalignment almost always comes from a plugin's prebuilt `.so`. Fix: upgrade Flutter and AGP (≥ 8.5), set NDK r28+, upgrade or drop the offending plugin — identify it from the path printed above.

## Gate 5 — Version code — BLOCK on collision

```bash
MF "/manifest/@android:versionCode"; MF "/manifest/@android:versionName"
```

- Must be strictly greater than `publish-state.json` → `last_uploaded.version_code`. Equal or lower → **BLOCK**: Play refuses a reused version code, and a code that was uploaded once is burned even if that release was discarded.
- Must be ≤ 2,100,000,000.
- Fix by bumping the build number in `pubspec.yaml` (`version: 1.0.0+2` → versionCode 2) and rebuilding.
- A `pending_upload` entry with this version code means a previous run prepared it but the user never confirmed the upload landed. Ask before proceeding: if it did land, the code is burned and must be bumped; if it did not, reuse is fine.
- On a first release with no state file, any value is fine — but confirm with the user that the app really is new (see Step 1). Note the baseline in the report either way.

## Gate 6 — Signing — BLOCK if unsigned or debug-signed

```bash
jarsigner -verify "$AAB" 2>&1 | head -3
keytool -printcert -jarfile "$AAB" 2>/dev/null | grep -E "Owner|Valid"
```

- Not `jar verified` → **BLOCK**, unsigned. Check `android/key.properties` and rerun `flutter-signing`.
- Owner contains `CN=Android Debug` → **BLOCK**, debug-signed.
- Certificate expiring within a year → **WARN**.
- Also confirm the keystore backup exists (`flutter-signing` writes it). Losing the upload key is recoverable via Play support; losing it *without* Play App Signing enabled is not. **WARN** if no backup is found.

## Gate 7 — Debuggable — BLOCK

```bash
MF "/manifest/application/@android:debuggable"
```

Empty output is the expected result. `true` → **BLOCK**: it is a Play policy violation and leaks the app to any debugger.

## Gate 8 — Size — WARN

```bash
du -m "$AAB"
```

The AAB file size is not what Play measures — Play limits *compressed download size* (base module 500 MB), and warns users on mobile data above 200 MB. For the real number:

```bash
BT build-apks --bundle="$AAB" --output=/tmp/app.apks --mode=default
BT get-size total --apks=/tmp/app.apks
```

**WARN** above 200 MB, **BLOCK** above 500 MB base module. For a typical Flutter app, anything over ~60 MB is worth questioning — usually uncompressed assets.

## Gate 9 — Release credentials not committed — BLOCK

A service account key grants release authority over the app; a keystore is unrecoverable if published. Both end up in the working tree, so check before an upload draws attention to the repo:

```bash
git ls-files | grep -E 'service-account.*\.json|\.jks$|\.keystore$|key\.properties'
git log --all --oneline -- '*service-account*.json' '*.jks' 'android/key.properties' | head
```

- Tracked in HEAD → **BLOCK.** Remove from the index, add to `.gitignore`, and **rotate the key** — deleting a file does not un-publish it if the repo was ever pushed. For a service account: delete the key in Google Cloud IAM and issue a new one.
- Present in history but not in HEAD → **BLOCK** the same way if the remote is public. History rewriting is the user's decision; rotating the credential is not optional.
- Untracked and gitignored → OK.

Report the finding without printing any of the file contents.

## Gate 10 — Store assets present — WARN

Play blocks submission (not upload) on missing assets. Check what `flutter-store-metadata` produced:

```bash
ls store-metadata/icon/icon-512.png store-metadata/icon/feature-graphic.png 2>&1
ls store-metadata/screenshots/phone/*.png 2>/dev/null | wc -l   # need ≥ 2, 8 recommended
wc -m store-metadata/description/short_description.txt           # ≤ 80
wc -m store-metadata/description/full_description.txt            # ≤ 4000
ls store-metadata/privacy-policy/ 2>&1                           # required for every app
```

Report each missing item as a **WARN** with the exact file that must exist — the user will be blocked in Console otherwise, just later.
