---
name: flutter-store-compliance
description: "Audit a Flutter project against Google Play Developer Program Policies before submission. Covers 8 policy areas: restricted content, IP, privacy & data, store listing, monetization, functionality, SDKs, and Families. Use when user says 'compliance', 'policy check', 'kiểm tra policy', 'review trước khi submit', 'pre-launch check'. Run before flutter-publish."
license: MIT
---

# Flutter Store Compliance

Pre-submission audit skill. Checks the Flutter project against all Google Play policies to catch rejection risks before uploading.

## Prerequisites

- Completed app with `store-metadata/` directory (from `flutter-store-metadata`)
- AAB or APK build (from `flutter-build`)
- Signing configured (from `flutter-signing`)

## Input

Ask the user for these if not in `$ARGUMENTS`:

| Field | Required | Description |
|-------|----------|-------------|
| `features` | ✅ | List of app features |
| `has_login` | ✅ | Does app require user login? |
| `collects_data` | ✅ | Does app collect any user data? |
| `has_ads` | ✅ | Does app contain advertisements? |
| `has_inapp_purchase` | ✅ | Does app have in-app purchases? |
| `target_children` | ✅ | Is app targeted at children under 13? |
| `has_ugc` | ✅ | Does app contain user-generated content? |
| `uses_sensitive_permissions` | ✅ | Does app use SMS/Call Log/Location/etc? |
| `data_types` | ❌ | List of data types collected (see Data Safety form) |
| `data_purposes` | ❌ | List of data usage purposes |

## 8 Audit Groups

### 1. Restricted Content

```bash
# Check app description for prohibited content
grep -i "violence\|nude\|sex\|gambling\|illegal\|drug\|weapon\|hate" \
  store-metadata/description/full_description.txt 2>/dev/null

# Check feature list
echo "$FEATURES" | grep -i "violence\|gambling\|adult"
```

**PASS** — No prohibited content found.
**FAIL** — App contains restricted content (child endangerment, inappropriate content, gambling, illegal activities).
**WARNING** — App has UGC (need in-app reporting + filtering) or AI-generated content (need label).

**Action on FAIL:** List the specific violations. Suggest removing/modifying content.

### 2. Intellectual Property

```bash
# Check app name for trademark issues (call brand-name-checker)
# Check if assets use copyrighted material
ls assets/ 2>/dev/null
grep -r "assets" pubspec.yaml 2>/dev/null
```

**PASS** — No IP conflicts detected.
**FAIL** — App appears to use copyrighted/ trademarked material without permission.
**WARNING** — Suggest reviewing all assets for proper licensing.

**Action on FAIL:** Identify specific IP conflicts. Recommend removal or proper licensing.

### 3. Privacy & Data

This is the most detailed check. It covers 5 sub-areas.

#### 3A. Privacy Policy

```bash
# Check if privacy policy exists
PRIVACY_FILE="store-metadata/privacy-policy/privacy-policy.md"
if [ -f "$PRIVACY_FILE" ]; then
  # Verify it covers required sections
  for section in "Information We Collect" "How We Use" "Data Sharing" "Data Security" "Contact"; do
    grep -q "$section" "$PRIVACY_FILE" && echo "✓ $section" || echo "✗ MISSING: $section"
  done
fi
```

**Check rules:**
- Must exist if app collects any data (even anonymously) — **FAIL if missing**
- Must cover all data types collected — **FAIL if mismatch**
- Apps with login or sensitive permissions MUST have privacy policy — **FAIL if missing**
- Must be on active URL (not local file) for production — **WARNING if local**

#### 3B. Data Safety Form

Generate `store-metadata/data-safety.csv` for direct import into Play Console.

**Question flow:**

```csv
Question ID,Response,Response value
# Data Types
PSL_DATA_TYPES_LOCATION,PSL_APPROX_LOCATION,TRUE/FALSE
PSL_DATA_TYPES_LOCATION,PSL_PRECISE_LOCATION,TRUE/FALSE
PSL_DATA_TYPES_PERSONAL,PSL_NAME,TRUE/FALSE
PSL_DATA_TYPES_PERSONAL,PSL_EMAIL,TRUE/FALSE
PSL_DATA_TYPES_PERSONAL,PSL_USER_IDS,TRUE/FALSE
PSL_DATA_TYPES_PERSONAL,PSL_PHONE,TRUE/FALSE
PSL_DATA_TYPES_PERSONAL,PSL_ADDRESS,TRUE/FALSE
PSL_DATA_TYPES_FINANCIAL,PSL_USER_PAYMENT_INFO,TRUE/FALSE
PSL_DATA_TYPES_FINANCIAL,PSL_PURCHASE_HISTORY,TRUE/FALSE
PSL_DATA_TYPES_APP_ACTIVITY,PSL_APP_INTERACTIONS,TRUE/FALSE
PSL_DATA_TYPES_APP_ACTIVITY,PSL_INSTALLED_APPS,TRUE/FALSE
PSL_DATA_TYPES_APP_ACTIVITY,PSL_OTHER_USER_GENERATED_CONTENT,TRUE/FALSE
PSL_DATA_TYPES_APP_INFO_PERFORMANCE,PSL_CRASH_LOGS,TRUE/FALSE
PSL_DATA_TYPES_APP_INFO_PERFORMANCE,PSL_DIAGNOSTICS,TRUE/FALSE
PSL_DATA_TYPES_DEVICE_IDS,PSL_DEVICE_IDS,TRUE/FALSE
# Encryption in transit
PSL_DATA_COLLECTION_AND_SECURITY,PSL_ENCRYPTION_IN_TRANSIT,TRUE
# Data deletion
PSL_DATA_COLLECTION_AND_SECURITY,PSL_DATA_DELETION,TRUE
# Purposes per data type
PSL_DATA_USAGE_COLLECTION_PURPOSE,PSL_APP_FUNCTIONALITY,TRUE
PSL_DATA_USAGE_COLLECTION_PURPOSE,PSL_ANALYTICS,TRUE
PSL_DATA_USAGE_COLLECTION_PURPOSE,PSL_FRAUD_PREVENTION,TRUE/FALSE
PSL_DATA_USAGE_COLLECTION_PURPOSE,PSL_ANALYTICS_FRAUD_PREVENTION,TRUE/FALSE
```

Set each field based on user's input about data collection.

**PASS** — CSV generated with all required fields.
**WARNING** — Some data types unclear (marked as FALSE, user should verify).
**FAIL** — No data types declared but app has login/permissions (mismatch).

#### 3C. Permissions

```bash
# Check AndroidManifest for sensitive permissions
grep -E "SEND_SMS|RECEIVE_SMS|READ_SMS|READ_CALL_LOG|READ_CONTACTS|CAMERA|RECORD_AUDIO|ACCESS_FINE_LOCATION|ACCESS_BACKGROUND_LOCATION" \
  android/app/src/main/AndroidManifest.xml 2>/dev/null
```

**PASS** — No sensitive permissions, or permissions justified by features.
**FAIL** — SMS/Call Log permissions — these are heavily restricted, need explicit declaration in Play Console.
**WARNING** — Location/Camera/Microphone — need prominent disclosure in-app.
**WARNING** — Permissions declared but not used in code — should be removed.

**Action on FAIL:** Point to "Permissions Declaration Form" in Play Console.

#### 3D. Sign-in Details for Reviewers

```bash
# Check if app has login
if [ "$HAS_LOGIN" = "true" ]; then
  echo "App requires login. Reviewer needs test account."
fi
```

**PASS** — No login required, or test account credentials documented.
**FAIL** — App has login but no test credentials for Google reviewer.

**Action on FAIL:** Generate test account credentials or tell user to provide them.

#### 3E. Target API Level

```bash
# Extract targetSdkVersion from build.gradle
TARGET_SDK=$(grep "targetSdkVersion" android/app/build.gradle* | grep -o "[0-9]\+" | tail -1)
LATEST_API=36  # Android 16 expected by 2026

echo "Target SDK: $TARGET_SDK"
echo "Latest SDK: $LATEST_API"
```

**PASS** — `targetSdkVersion >= LATEST_API - 1`
**WARNING** — `targetSdkVersion` is one version behind (update recommended)
**FAIL** — `targetSdkVersion < LATEST_API - 2` (Google Play will block submission)

Also check:
```bash
compileSdkVersion >= targetSdkVersion
minSdkVersion >= 23  # reasonable lower bound
```

### 4. Store Listing

```bash
# Icon check
identify store-metadata/icon/icon-512.png 2>/dev/null
# Screenshots count
ls store-metadata/screenshots/phone/*.png 2>/dev/null | wc -l
# Description lengths
SHORT_LEN=$(cat store-metadata/description/short_description.txt 2>/dev/null | wc -c)
FULL_LEN=$(cat store-metadata/description/full_description.txt 2>/dev/null | wc -c)
```

**Checklist:**
- ✅ Icon 512x512px — **FAIL if not**
- ✅ Screenshots ≥ 2 phone — **FAIL if < 2**
- ✅ Short description ≤ 80 chars — **FAIL if > 80**
- ✅ Full description ≤ 4000 chars — **FAIL if > 4000**
- ✅ No spammy keywords in description — **WARNING if excessive repetition**
- ✅ Google Play category valid — **WARNING if uncategorized**
- ✅ Content Rating questionnaire done — **WARNING** (must do in Play Console)
- ✅ Has ads declared correctly — **FAIL if ads but not declared**
- ✅ No MISLEADING metadata — **FAIL if icon/desc doesn't reflect app**

### 5. Monetization

```bash
# Check for Google Play Billing
grep -r "com.android.billing" android/ 2>/dev/null
grep -r "billing_client\|purchase" lib/ 2>/dev/null
```

**PASS** — No monetization, or uses Google Play Billing correctly.
**FAIL** — In-app purchases not using Google Play Billing (policy violation).
**FAIL** — Subscription without `recurring` declaration.
**WARNING** — Has ads but no ad SDK review.
**WARNING** — Target children + ads → need Families-certified Ad SDK only.

**Action on FAIL:** Point to Google Play Billing requirements. Suggest `in_app_purchase` Flutter package.

### 6. Functionality & UX

```bash
# Check app compiles
flutter analyze 2>&1 | tail -5

# Check for crash
flutter build apk --debug 2>&1 | grep -i "error\|crash\|exception"
```

**PASS** — App compiles, no static analysis errors, runs without crash.
**FAIL** — App does not compile or crashes on launch.
**FAIL** — App has no functionality (empty shell with no features).
**WARNING** — Frequent push notifications may be considered spam.
**WARNING** — App size is very small (< 1MB) — possible minimal functionality issue.

### 7. SDK Check

```bash
# List Flutter dependencies
grep -A200 "^dependencies:" pubspec.yaml | grep -v "^dev_dependencies" | head -50

# Check for known problematic SDKs
grep -i "firebase\|admob\|amplitude\|mixpanel\|adjust\|appsflyer" pubspec.yaml
```

**PASS** — All SDKs are well-known and policy-compliant.
**WARNING** — Custom/unknown SDKs — need to verify their data handling policies.
**WARNING** — SDKs that collect data not declared in Data Safety form (mismatch).
**FAIL** — SDK with known policy violations (from Google Play SDK Index).

**Action:** For each SDK, note the data it collects and ensure it's declared in the Data Safety CSV.

### 8. Families (if targeting children)

Only run if `target_children = true`.

```bash
grep -ri "child\|kid\|under.*13\|parent" store-metadata/description/ 2>/dev/null
```

**PASS** — App follows Families policy (no inappropriate content, no non-certified ad SDKs).
**FAIL** — Content not appropriate for children.
**FAIL** — Ad SDK not Families-certified.
**FAIL** — No privacy policy (required for children's apps even without data collection).
**WARNING** — No parental gate for external links/transactions.
**WARNING** — No COPPA compliance statement.

## Output: Report

```
═══════════════════════════════════════════════
  FLUTTER STORE COMPLIANCE REPORT
═══════════════════════════════════════════════

  1. RESTRICTED CONTENT     ✅ PASS
  2. INTELLECTUAL PROPERTY  ✅ PASS | ℹ️ Review icon assets
  3. PRIVACY & DATA         ⚠️ PARTIAL
     3A. Privacy Policy     ✅ Covers all required sections
     3B. Data Safety Form   ✅ data-safety.csv generated
     3C. Permissions        ⚠️ CAMERA declared but unused
     3D. Test Credentials   ✅ N/A (no login required)
     3E. Target API Level   ✅ compileSdk 34, targetSdk 34
  4. STORE LISTING          ⚠️ PARTIAL
     - Icon                  ✅ 512x512
     - Screenshots           ❌ 1/2 minimum (add 1 more)
     - Short Description     ✅ 78/80 chars
     - Full Description      ✅ 2340/4000 chars
     - Content Rating        ⚠️ Not completed in Play Console
     - Ads Declaration       ✅ No ads
  5. MONETIZATION           ✅ PASS (no IAP)
  6. FUNCTIONALITY & UX     ✅ PASS
  7. SDK CHECK              ✅ PASS (Firebase, Admob)
  8. FAMILIES               SKIP (not targeting children)

═══════════════════════════════════════════════
  OVERALL: ⚠️ PASS WITH ISSUES
═══════════════════════════════════════════════

  ❌ MUST FIX (blocking submission):
     - Add at least 1 more phone screenshot to store-metadata/screenshots/

  ⚠️ SHOULD FIX (recommended before submission):
     - Remove unused CAMERA permission
     - Complete Content Rating questionnaire in Play Console

  📄 Generated: store-metadata/data-safety.csv (import to Play Console)
```

## Severity Levels

| Level | Meaning | Gate |
|-------|---------|------|
| ✅ PASS | All checks pass | Can proceed to publish |
| ⚠️ PARTIAL | Minor issues, non-blocking | User decides |
| ❌ FAIL | Must fix before publish | Blocked until resolved |

## Integration with Other Skills

| Skill | Input from / Output to |
|-------|----------------------|
| `flutter-store-metadata` | Reads `store-metadata/` directory |
| `flutter-signing` | Reads signing config from `android/key.properties` |
| `flutter-build` | Reads AAB file from `build/release/` |
| `flutter-publish` | Only allows publish if compliance report is PASS or PARTIAL |

## Acceptance Criteria

- [ ] All 8 audit groups produce a PASS/WARNING/FAIL verdict
- [ ] `data-safety.csv` generated with correct question IDs
- [ ] Clear output of blocking vs. non-blocking issues
- [ ] Obeys gate: prevents publish if FAIL level found
