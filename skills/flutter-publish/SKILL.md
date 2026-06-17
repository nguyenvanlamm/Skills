---
name: flutter-publish
description: "Upload a Flutter Android App Bundle (AAB) to Google Play Console and guide the user through submission. Use when user says 'publish', 'upload', 'submit', 'đăng lên chplay', 'publish app', 'push to play store'. Run LAST after all other flutter-* skills pass."
license: MIT
---

# Flutter Publish

Step 9-10 of the Flutter → Google Play pipeline: upload AAB to Google Play Console and prepare for submission.

## Prerequisites

All prior skills must complete successfully:

```
flutter-init        → Project created
flutter-signing     → Keystore + signing configured
flutter-build       → AAB built
flutter-store-metadata  → Store assets ready
flutter-store-compliance → Compliance report PASS or PARTIAL (no FAIL)
```

## Input

| Field | Required | Description |
|-------|----------|-------------|
| `track` | ❌ | Release track: `internal` (default), `closed`, `open`, `production` |
| `aab_path` | ❌ | Path to AAB file (auto-detect if blank) |
| `whats_new` | ❌ | Release notes (auto-generated if blank) |
| `test_credentials` | ❌ | Test account credentials for internal/closed tracks |

## Steps

### Step 1: Pre-flight Compliance Gate

```bash
# Check that flutter-store-compliance was run
if [ ! -f store-metadata/compliance-report.md ]; then
  echo "⚠️ Compliance report not found."
  echo "Run flutter-store-compliance first."
  echo "Proceed anyway?" 
  ask_user || exit 1
fi

# Read compliance verdict
COMPLIANCE_STATUS=$(grep "OVERALL:" store-metadata/compliance-report.md 2>/dev/null | grep -o "PASS\|PARTIAL\|FAIL")
if [ "$COMPLIANCE_STATUS" = "FAIL" ]; then
  echo "❌ Compliance FAILED. Fix issues before publishing."
  echo "See store-metadata/compliance-report.md"
  exit 1
fi
```

**Gate logic:**
- `FAIL` → **Block** publishing. Show compliance report.
- `PARTIAL` → **Warn** but allow user to proceed.
- `PASS` → Allow.

### Step 2: Detect AAB

```bash
# Search for AAB
AAB_FILES=$(find . -name "*.aab" -path "*/build/*" -type f 2>/dev/null)

if [ -z "$AAB_FILES" ]; then
  AAB_FILES=$(find build/release -name "*.aab" -type f 2>/dev/null)
fi

echo "AAB files found:"
echo "$AAB_FILES"
```

If multiple AABs found → let user select.
If none found → run `flutter-build` or ask user to build manually.

### Step 3: Verify AAB

```bash
# Check AAB is valid and signed
AAB_SIGNED=$(unzip -l "$AAB_PATH" 2>/dev/null | grep "META-INF" | wc -l)
AAB_SIZE=$(ls -lh "$AAB_PATH" | awk '{print $5}')

echo "Size: $AAB_SIZE"
echo "Signed: $([ $AAB_SIGNED -gt 3 ] && echo 'Yes' || echo 'CHECK MANUALLY')"
```

**Checks:**
- File extension `.aab` — **FAIL if not**
- File size > 1 MB — **FAIL if smaller**
- Contains signature files in `META-INF/` — **WARNING if unsigned**

### Step 4: Generate Release Notes

If `whats_new` not provided, generate from git history:

```bash
# Get recent commits since last tag
LAST_TAG=$(git tag --sort=-creatordate | head -1)
if [ -n "$LAST_TAG" ]; then
  git log "$LAST_TAG"..HEAD --oneline --no-merges --format="• %s" 2>/dev/null
else
  git log --oneline --no-merges -10 --format="• %s" 2>/dev/null
fi
```

Write to `store-metadata/whats-new.txt`:

```
• $FEATURE_1
• $FEATURE_2
• Bug fixes and performance improvements
```

Max 500 characters. Include `en-US` as default locale. For multiple locales, create files:

```
store-metadata/whats-new/
├── en-US.txt
├── vi-VN.txt
```

### Step 5: Guide Manual Upload (Primary Method)

Google Play no longer offers a simple upload API for personal developer accounts without service account setup. The primary method is manual via Play Console.

Provide the user with a step-by-step guide:

```
══════════════════════════════════════════
  UPLOAD TO GOOGLE PLAY CONSOLE
══════════════════════════════════════════

  Step 1: Open Google Play Console
    → https://play.google.com/console/

  Step 2: Create a new app (first time only)
    → Click "Create app"
    → Name: "$APP_NAME"
    → Default language: English
    → App or game: App
    → Free or Paid: Choose

  Step 3: Set up Store Listing
    → Copy from store-metadata/store-listing.json
    → Upload screenshots from store-metadata/screenshots/
    → Icon auto-detected from build
    → Category: $CATEGORY
    → Tags: Optional

  Step 4: Complete App content
    → Privacy Policy: Use store-metadata/privacy-policy/
    → Ads declaration: Yes/No
    → Target audience: Set appropriately
    → Content rating: Complete questionnaire
    → Data safety: Import data-safety.csv

  Step 5: Upload AAB
    → Go to Production / Internal testing / Closed testing
    → Click "Create new release"
    → Upload file: $AAB_PATH
    → Release notes: Copy from store-metadata/whats-new.txt

  Step 6: Review & Submit
    → Review pre-launch report
    → Check for any warnings
    → Submit for review

  ⏱ Review time: Typically 1-3 days (could be up to 7 days)
```

### Step 6: Optional — Google Play Developer API Upload

If user has a service account set up, offer automated upload:

```bash
# Check if service account JSON exists
SERVICE_ACCOUNT=$(ls service-account.json ~/.google-play/service-account.json 2>/dev/null | head -1)
if [ -n "$SERVICE_ACCOUNT" ]; then
  echo "Service account found at $SERVICE_ACCOUNT"
  echo "Automated upload available."
  ask_user "Upload via API?" && do_api_upload
fi
```

**API upload requirements:**
- Google Play Developer API enabled in GCP project
- Service account with "Release Manager" role in Play Console
- `googleapiclient` Python lib or similar

**Note:** Service account setup is a manual one-time process. Document it:

```
To set up automated uploads:
1. Go to https://play.google.com/console/developers/account
2. API Access → Create Service Account
3. In Google Cloud Console, create key (JSON)
4. Add service account email to Play Console with "Admin" role
5. Save JSON key as service-account.json in project root
```

### Step 7: Internal/Closed Testing Guidance

For new developer accounts (after Nov 2023), Google requires:

> **New personal developer accounts** must complete app testing requirements:
> - 20 testers for 14 consecutive days
> - Closed testing track with opt-in URL
> - Test feedback must be addressed

Guide the user:

```
══════════════════════════════════════════
  TESTING REQUIREMENTS (New Accounts)
══════════════════════════════════════════

  Google Play now requires new developer accounts to:
  
  1. Set up a CLOSED TESTING track
  2. Add at least 20 testers
  3. Run the test for 14 consecutive days
  4. Address all feedback

  To set up:
  → Play Console → Testing → Closed testing
  → Create new track
  → Upload AAB
  → Add tester emails (20+)
  → Copy opt-in URL and share with testers
  
  After 14 days:
  → Request production access
  → Wait for review (up to 2 weeks)
```

### Step 8: Report

```
══════════════════════════════════════════
  FLUTTER PUBLISH — COMPLETE
══════════════════════════════════════════

  ✓ Compliance gate: PASS
  ✓ AAB verified: $AAB_PATH ($AAB_SIZE, signed)
  ✓ Release notes generated: store-metadata/whats-new.txt

  ┌────────────────────────────────────────┐
  │                                        │
  │   MANUAL STEPS REQUIRED                │
  │                                        │
  │   Open Google Play Console:            │
  │   https://play.google.com/console/     │
  │                                        │
  │   1. Create app in Play Console        │
  │   2. Fill Store Listing from           │
  │      store-metadata/store-listing.json │
  │   3. Upload $AAB_PATH                  │
  │   4. Complete App content section      │
  │   5. Submit for review                 │
  │                                        │
  └────────────────────────────────────────┘

  ⚠️ Tester requirements:
     If this is a NEW developer account, 
     you MUST complete 14-day closed testing
     before production release.

  📄 Store assets: store-metadata/
  📦 AAB file: $AAB_PATH
  📝 Release notes: store-metadata/whats-new.txt
  🔐 Compliance: store-metadata/compliance-report.md
```

## What This Skill Does NOT Do

- ❌ Submit the app automatically (no service account by default)
- ❌ Complete Content Rating questionnaire (must be done in Play Console UI)
- ❌ Handle app rejections or appeals (see Google Play Help Center)
- ❌ Replace the need for real human testing

## Edge Cases

| Problem | Handling |
|---------|----------|
| No AAB found | Prompt to run `flutter-build` first |
| Compliance gate blocks | Show report, exit |
| User has no Play Console account | Guide to register ($25) |
| App already published (update) | Guide to "Create new release" on existing app |
| iOS not supported | iOS publishing requires separate App Store process on macOS |
| New account testing requirements | Guide through 14-day closed testing process |
| App rejected after submission | Show common rejection reasons and how to fix |

## Acceptance Criteria

- [ ] Compliance gate checked before allowing publish
- [ ] AAB file verified (exists, signed, reasonable size)
- [ ] Release notes generated with git history
- [ ] Step-by-step manual upload guide provided
- [ ] Testing requirements explained for new accounts
- [ ] All paths leading to publish documented and ready for user
