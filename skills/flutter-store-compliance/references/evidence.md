# Evidence gathering

Run this first. Every finding must cite a row from the table it produces.

## Sources

```bash
# Dependencies
sed -n '/^dependencies:/,/^dev_dependencies:/p' pubspec.yaml

# Permissions (all manifests, not just main — plugins and flavors add their own)
grep -rhoE 'android:name="android\.permission\.[A-Z_]+"' android/app/src/main/

# App identity
grep -E 'android:label|package=' android/app/src/main/AndroidManifest.xml
grep -E 'applicationId|targetSdk|minSdk' android/app/build.gradle*

# Upstream artefacts — prefer these over recomputing
cat build/release/build-info.json      2>/dev/null   # flutter-build v2
cat store-metadata/store-listing.json  2>/dev/null   # flutter-store-metadata v2
ls   store-metadata/privacy-policy/    2>/dev/null
```

If `build-info.json` is missing, `flutter-build` v1 or a manual build produced the artifact — derive targetSdk and signing from the AAB with `bundletool` rather than trusting the gradle files, and note the reduced confidence in the report.

**Never run `flutter build` as part of the audit.** It costs minutes and proves nothing about runtime behaviour.

## Signal → fact

| Signal | Derived fact |
|--------|--------------|
| `google_mobile_ads`, `applovin_max`, `unity_ads`, `facebook_audience_network` | Serves ads; collects Advertising ID |
| `in_app_purchase`, `purchases_flutter`, `flutter_inapp_purchase` | Digital purchases |
| `firebase_auth`, `google_sign_in`, `sign_in_with_apple`, `supabase_flutter` | Accounts; requires reviewer credentials and an account-deletion route |
| `firebase_analytics`, `amplitude`, `mixpanel`, `posthog` | Usage/analytics collection |
| `firebase_crashlytics`, `sentry_flutter` | Crash logs, diagnostics, device identifiers |
| `firebase_messaging`, `onesignal` | Push tokens; notification policy applies |
| `geolocator`, `location` + LOCATION permission | Location collection |
| `image_picker`, `camera` + CAMERA | Photos/media |
| `contacts_service` + READ_CONTACTS | Contacts — sensitive |
| `http`, `dio`, `web_socket_channel` + INTERNET | Data can leave the device; a "nothing leaves your phone" claim needs proof |
| No network packages, no INTERNET | Genuinely local-only; a short privacy policy is correct and sufficient |

Do not stop at this list. Anything unrecognised in `dependencies` is an **unknown SDK** — a `WARN` requiring the user to state what it collects. An unfamiliar package is not evidence of safety.

## Permission classes

| Class | Permissions | Consequence |
|-------|-------------|-------------|
| Restricted | SEND_SMS, RECEIVE_SMS, READ_SMS, READ_CALL_LOG, WRITE_CALL_LOG, PROCESS_OUTGOING_CALLS | Permissions Declaration Form + Google approval; only for apps whose core function needs it |
| Sensitive | ACCESS_FINE_LOCATION, ACCESS_BACKGROUND_LOCATION, CAMERA, RECORD_AUDIO, READ_CONTACTS, MANAGE_EXTERNAL_STORAGE, QUERY_ALL_PACKAGES | Prominent in-app disclosure + runtime request; background location needs separate justification |
| Normal | INTERNET, VIBRATE, WAKE_LOCK, POST_NOTIFICATIONS | No declaration |

Cross-check each permission against the code that uses it:

```bash
grep -rl "Permission.camera\|ImagePicker\|CameraController" lib/
```

A permission with no corresponding usage is a `WARN` — Play flags unused sensitive permissions, and removing one is free.

Note that plugins inject permissions through manifest merging, so a permission may be present that the app's own code never uses. Check the merged manifest in the build output before telling the user to delete a line they never wrote:

```bash
find build -name AndroidManifest.xml -path '*merged*' 2>/dev/null
```

## Output

Produce a table like this, and carry it into every check:

| Fact | Value | Evidence |
|------|-------|----------|
| has_ads | false | no ad SDK in pubspec.yaml |
| has_iap | true | pubspec.yaml: `in_app_purchase ^3.2.0` |
| collects_data | true | pubspec.yaml: `firebase_analytics ^11.3.3` |
| sensitive_permissions | CAMERA | AndroidManifest.xml:14 |
| target_sdk | 36 | build-info.json |
| unknown_sdks | `acme_tracker` | pubspec.yaml:31 |

Then compare it against `store-listing.json` → `derived`. That comparison is Step 3 of the audit, and any row that disagrees is a finding.
