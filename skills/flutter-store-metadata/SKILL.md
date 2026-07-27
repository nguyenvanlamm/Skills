---
name: flutter-store-metadata
description: "Generate Google Play store listing assets: app icon, feature graphic, screenshots, description, privacy policy, and store-listing.json. Use when user says 'store listing', 'metadata', 'store metadata', 'chuẩn bị store', 'tạo metadata', 'screenshots'. Run after flutter-build and before flutter-store-compliance."
license: MIT
metadata:
  version: 2.0.0
---

# Flutter Store Metadata

Step 8 of the Flutter → Google Play pipeline: produce every asset and string the Play Console listing needs.

## Core principle

> **Generated ≠ submittable.** A gradient card with the app's name on it is not a screenshot, and a privacy policy asserting practices the developer does not follow is worse than none. Anything this skill invents rather than derives must be labelled as such, so the next skill can block on it.

Two things are never guessed: **what the app actually does** (derive it from the code) and **what the app looks like** (capture it from a running build).

## Input

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `app_name` | ✅ | — | Listing name, ≤ 30 characters |
| `features` | ✅ | from PRD | Key features, for the description |
| `category` | ✅ | — | Play category, e.g. `PRODUCTIVITY` |
| `locales` | ❌ | `["en-US"]` | Listing locales |
| `short_description` | ❌ | generated | ≤ 80 characters |
| `full_description` | ❌ | generated | ≤ 4000 characters |
| `privacy_policy_url` | ❌ | — | Existing URL; blank → generate the document |
| `contact_email` | ❌ | ask | Public on the listing, required in the policy |
| `target_audience` | ❌ | `general` | `general` or `children` |

Data-collection flags are **not** inputs — they are derived in Step 1. Asking the user "does your app collect data?" and believing the answer is how listings end up contradicting the app.

## Workflow

### Step 1 — Derive the facts

Never take these from user input. Read the project:

```bash
sed -n '/^dependencies:/,/^dev_dependencies:/p' pubspec.yaml
grep -oE 'android:name="android\.permission\.[A-Z_]+"' android/app/src/main/AndroidManifest.xml
grep -E 'android:label' android/app/src/main/AndroidManifest.xml
grep "^version:" pubspec.yaml
```

| Fact | Evidence |
|------|----------|
| Has ads | `google_mobile_ads`, `applovin_max`, `unity_ads`, `facebook_audience_network` |
| Has IAP | `in_app_purchase`, `purchases_flutter`, `flutter_inapp_purchase` |
| Has login | `firebase_auth`, `google_sign_in`, `sign_in_with_apple`, `supabase_flutter` |
| Collects data | `firebase_analytics`, `firebase_crashlytics`, `sentry_flutter`, `amplitude`, `posthog`, `mixpanel` |
| Sensitive permissions | CAMERA, RECORD_AUDIO, ACCESS_FINE_LOCATION, ACCESS_BACKGROUND_LOCATION, READ_CONTACTS, SMS/CALL_LOG |
| Network access | `INTERNET` permission, `http`/`dio` packages |

Record each derived fact **with the evidence that produced it** — `flutter-store-compliance` compares against the same evidence, and a fact without a source cannot be cross-checked.

Also check `app_name` against `android:label`. A listing name that differs from the in-app name is a misleading-metadata rejection; flag the mismatch and ask which is correct.

If `features` was not given, read `prd.md`, `tasks.md`, then `README.md`. Ask rather than invent — descriptions of features the app lacks are the single most common deceptive-listing rejection.

### Step 2 — Icon

Read `references/icon-assets.md`. Use `flutter_launcher_icons`, not a manual `convert` resize: Android 8+ needs adaptive icons (foreground/background layers with a safe zone), Android 13+ wants a monochrome layer, and a plain square resized into `mipmap-*` gets cropped badly on modern launchers.

Outputs: `store-metadata/icon/icon-512.png` (Play listing) plus the generated `mipmap-*` resources in the project.

### Step 3 — Feature graphic

**Required for every listing** — Play will not let the user publish the listing without it. 1024×500, JPEG or 24-bit PNG, **no alpha channel**. See `references/icon-assets.md` § Feature graphic.

Output: `store-metadata/icon/feature-graphic.png`.

### Step 4 — Screenshots

Read `references/screenshots.md`. Order of preference:

1. **Capture from the running app** (`adb exec-out screencap`) — the only kind Play accepts without risk.
2. **Automate with `integration_test`** if the app has flows worth reproducing per release.
3. **Placeholder** only when neither is possible — and then mark them, loudly, in `store-listing.json` and the report.

Play's Deceptive Behavior policy requires store assets to reflect the real app. Generic marketing art in place of the UI is a documented rejection reason, so a placeholder is a **blocking issue to be resolved before submission**, not an asset.

### Step 5 — Description

Short (≤ 80 chars) and full (≤ 4000 chars). Count characters, not bytes:

```bash
wc -m < store-metadata/description/short_description.txt   # NOT wc -c
```

`wc -c` counts bytes, so Vietnamese or emoji text fails the check while being well within Play's limit. Same for `app_name` ≤ 30.

Structure for the full description: value proposition in the first two lines (that is all that shows before "read more"), then features, then a closing line. Every claim must map to a feature derived in Step 1. No keyword stuffing — it is a policy violation, not just bad taste.

For serious keyword work, hand off to the `aso-marketing` skill rather than duplicating it here.

Write one file per locale:

```
store-metadata/description/<locale>/short_description.txt
store-metadata/description/<locale>/full_description.txt
```

### Step 6 — Privacy policy

Read `references/privacy-policy.md` before writing anything. Skip if `privacy_policy_url` was supplied.

The policy is a legal document about the developer's actual practices. Generate it from Step 1's derived facts, never from a fixed template, and **never assert a practice that cannot be verified from the code** — "we perform regular security audits", "we encrypt all data at rest", "we do not sell your data" are claims about the developer, not the app.

Output `store-metadata/privacy-policy/privacy-policy.md` + `.html`. Play requires a public HTTPS URL; a local file does not count, so tell the user where to host it.

### Step 7 — store-listing.json

```json
{
  "app_name": "Task Flow",
  "package": "com.acme.taskflow",
  "category": "PRODUCTIVITY",
  "default_locale": "en-US",
  "locales": ["en-US", "vi-VN"],
  "contact_email": "support@acme.com",
  "privacy_policy_url": null,
  "derived": {
    "has_ads": false,
    "has_iap": true,
    "has_login": true,
    "collects_data": true,
    "sensitive_permissions": ["CAMERA"],
    "evidence": {
      "has_iap": "pubspec.yaml: in_app_purchase ^3.2.0",
      "has_login": "pubspec.yaml: firebase_auth ^5.3.1",
      "collects_data": "pubspec.yaml: firebase_analytics ^11.3.3",
      "sensitive_permissions": "AndroidManifest.xml: android.permission.CAMERA"
    }
  },
  "assets": {
    "icon": "store-metadata/icon/icon-512.png",
    "feature_graphic": "store-metadata/icon/feature-graphic.png",
    "screenshots": {
      "phone": [
        { "path": "store-metadata/screenshots/phone/01-home.png", "source": "captured", "placeholder": false }
      ]
    }
  },
  "unresolved": []
}
```

`source` is `captured`, `automated`, or `placeholder`. Every `placeholder: true` asset also gets an entry in `unresolved` — that array is what `flutter-store-compliance` blocks on.

### Step 8 — Report

```
FLUTTER STORE METADATA — <READY | NEEDS WORK>

Derived    login ✓ (firebase_auth) · IAP ✓ (in_app_purchase) · analytics ✓ (firebase_analytics) · ads ✗
Icon       icon-512.png + adaptive + monochrome
Feature    feature-graphic.png 1024×500, no alpha
Screens    4 phone — CAPTURED from device
Copy       name 9/30 · short 74/80 · full 1820/4000  (en-US, vi-VN)
Privacy    generated → needs hosting at a public HTTPS URL

Unresolved before submission:
  - <each placeholder asset, each unverifiable claim, each mismatch>
```

Never report "COMPLETE" while `unresolved` is non-empty.

## Reference files

| File | Read when |
|------|-----------|
| `references/icon-assets.md` | Step 2–3 — icon and feature graphic |
| `references/screenshots.md` | Step 4 — capture, automation, placeholder rules |
| `references/privacy-policy.md` | Step 6 — deriving a policy that is true |

## Scope

Does: derive what the app does, generate listing assets and copy, and mark anything that is a stand-in.

Does not: upload (`flutter-publish`); audit policy compliance (`flutter-store-compliance`); keyword/ASO strategy (`aso-marketing`); fabricate screenshots of a UI that does not exist.
