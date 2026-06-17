---
name: flutter-store-metadata
description: "Generate Google Play store listing assets: app icon (via logo-designer), screenshots, description, privacy policy, and store-listing.json. Use when user says 'store listing', 'metadata', 'store metadata', 'chuẩn bị store', 'tạo metadata', 'screenshots'. Run after flutter-build and before flutter-store-compliance."
license: MIT
---

# Flutter Store Metadata

Step 8 of the Flutter → Google Play pipeline: prepare all assets and text needed for the Google Play Console store listing.

## Prerequisites

- `prd.md` or feature list from user (for description generation)
- `logo-designer` skill available for icon generation

## Input

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `app_name` | ✅ | — | Display name on Google Play |
| `short_description` | ❌ | Auto-generated | ≤80 chars |
| `full_description` | ❌ | Auto-generated | ≤4000 chars |
| `features` | ✅ | — | List of key features (from PRD or user) |
| `category` | ✅ | — | Google Play category (e.g. `PRODUCTIVITY`, `SOCIAL`) |
| `collects_data` | ❌ | `false` | Whether app collects user data |
| `collects_personal_info` | ❌ | `false` | Whether app collects email/name/phone |
| `has_login` | ❌ | `false` | Whether app requires login |
| `has_ads` | ❌ | `false` | Whether app contains ads |
| `has_inapp_purchase` | ❌ | `false` | Whether app has IAP |
| `privacy_policy_url` | ❌ | — | Existing URL (if blank → generate policy) |
| `target_audience` | ❌ | `general` | `general` or `children` |

## Steps

### Step 1: Read Project Context

```bash
# Look for PRD to extract features
[ -f prd.md ] && grep -i -A2 "feature\|tính năng" prd.md 2>/dev/null
[ -f tasks.md ] && head -100 tasks.md 2>/dev/null
[ -f README.md ] && head -30 README.md 2>/dev/null
```

If `features` not provided in input, extract from these files or ask user.

### Step 2: Generate App Icon

Call the `logo-designer` skill to generate icons:

```
Input: $app_name
```

From its output, extract required Google Play icon sizes:

```bash
ICON_SRC="store-metadata/icon"

# Create resize script
mkdir -p android/app/src/main/res/mipmap-mdpi
mkdir -p android/app/src/main/res/mipmap-hdpi
mkdir -p android/app/src/main/res/mipmap-xhdpi
mkdir -p android/app/src/main/res/mipmap-xxhdpi
mkdir -p android/app/src/main/res/mipmap-xxxhdpi
mkdir -p android/app/src/main/res/mipmap-anydpi-v26

# Generate required sizes (from logo-designer's icon-512.png)
convert "$ICON_SRC/icon-512.png" -resize 48x48  android/app/src/main/res/mipmap-mdpi/ic_launcher.png
convert "$ICON_SRC/icon-512.png" -resize 72x72  android/app/src/main/res/mipmap-hdpi/ic_launcher.png
convert "$ICON_SRC/icon-512.png" -resize 96x96  android/app/src/main/res/mipmap-xhdpi/ic_launcher.png
convert "$ICON_SRC/icon-512.png" -resize 144x144 android/app/src/main/res/mipmap-xxhdpi/ic_launcher.png
convert "$ICON_SRC/icon-512.png" -resize 192x192 android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png
```

**If ImageMagick not available:** Use Dart script `flutter_launcher_icons`:

Add to `pubspec.yaml`:

```yaml
dev_dependencies:
  flutter_launcher_icons: "^0.14.1"

flutter_launcher_icons:
  android: true
  adaptive_icon_background: "#FFFFFF"
  adaptive_icon_foreground: "store-metadata/icon/icon-foreground.png"
  image_path: "store-metadata/icon/icon-512.png"
```

```bash
flutter pub get
dart run flutter_launcher_icons
```

### Step 3: Generate Screenshots

Create mockup screenshots based on app features:

```
store-metadata/screenshots/phone/
  - 01-home.png              (1080x1920)
  - 02-feature-main.png      (1080x1920)
  - 03-feature-secondary.png (1080x1920)
  - 04-settings.png          (1080x1920)
```

For each feature, generate a simple HTML mockup → PNG:

```bash
# For each screenshot, create a clean UI mockup card
# Using a simple generator or template:
cat > /tmp/screenshot.html << 'EOF'
<div style="
  width: 1080px; height: 1920px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex; flex-direction: column;
  justify-content: center; align-items: center;
  font-family: 'Inter', sans-serif; color: white;
">
  <h1 style="font-size: 64px; margin-bottom: 40px;">FEATURE NAME</h1>
  <p style="font-size: 32px; max-width: 800px; text-align: center;">
    Brief description of this feature
  </p>
  <div style="
    width: 300px; height: 300px;
    background: rgba(255,255,255,0.2);
    border-radius: 40px;
    margin-top: 60px;
    display: flex; align-items: center; justify-content: center;
    font-size: 120px;
  ">📱</div>
</div>
EOF
```

If no headless browser (puppeteer/playwright) available → generate placeholder:

```
Screenshots: Placeholder screenshots created at store-metadata/screenshots/phone/
NOTE: Replace with actual app screenshots before submitting to Google Play.
```

Google Play requires:
- Minimum 2 phone screenshots (recommend 4-8)
- 1080x1920px or 1080x2340px
- JPG or 24-bit PNG (no alpha)
- ≤ 30% text overlay

### Step 4: Write Description

**Short Description** (≤ 80 characters):

Generate from features:

```
Template: "[Action verb] your [noun] to [benefit]"
Example: "Organize your daily tasks with smart reminders"
```

**Full Description** (≤ 4000 characters):

Structure:
```
[Line 1-2: Value proposition + keywords]

KEY FEATURES:
✓ [Feature 1] — [short explanation]
✓ [Feature 2] — [short explanation]
✓ [Feature 3] — [short explanation]
✓ [Feature 4] — [short explanation]

WHY CHOOSE [APP NAME]?
- [Benefit 1]
- [Benefit 2]

Download [APP NAME] today and [CTA].
```

SEO rules:
- Include main keywords in first 2 lines
- Use natural language (no keyword stuffing)
- Mention platform-specific features (Material Design 3, etc.)

### Step 5: Generate Privacy Policy

Based on `collects_data`, `has_login`, etc., generate a complete privacy policy:

Write to `store-metadata/privacy-policy/privacy-policy.md`:

```markdown
# Privacy Policy for $APP_NAME

*Last updated: $(date +%Y-%m-%d)*

## 1. Information We Collect

We collect the following types of information:
$(if has_login)
- **Account Information**: Email address, username, and profile picture
$(endif)
$(if collects_personal_info)
- **Personal Information**: Name, email address
$(endif)
- **Device Information**: Device model, OS version, unique device identifiers
- **Usage Data**: App interactions, crash logs, and performance data

## 2. How We Use Your Information

We use the collected data for:
- Providing and maintaining the app's core functionality
- Improving user experience and app performance
- Sending important notifications (with consent)
- $(if has_ads)Displaying relevant advertisements$(endif)
- Analytics to understand how users interact with the app

## 3. Data Sharing

We do not sell your personal information.
$(if has_ads)
We may share anonymized data with ad partners for advertising purposes.
$(endif)
We may disclose information if required by law.

## 4. Data Security

We implement industry-standard security measures including:
- Encryption in transit (TLS/SSL)
- $(if has_login)Secure authentication protocols$(endif)
- Regular security audits

## 5. Your Rights

You have the right to:
- Access your personal data
- Request deletion of your data
- Opt-out of data collection (where applicable)
- Withdraw consent at any time

## 6. Contact Us

For privacy-related inquiries:
- Email: [developer-email]
- Address: [developer-address]

## 7. Changes to This Policy

We may update this policy periodically. Changes will be posted here.
```

Also generate HTML version:

```bash
pandoc store-metadata/privacy-policy/privacy-policy.md \
  -o store-metadata/privacy-policy/privacy-policy.html
```

**Fallback if pandoc unavailable:** Copy markdown, note "Convert to HTML before publishing."

**If `privacy_policy_url` provided:** Skip generation, note URL.

### Step 6: Generate Store Listing JSON

Write `store-metadata/store-listing.json`:

```json
{
  "app_name": "$APP_NAME",
  "short_description": "$SHORT_DESC",
  "full_description": "$FULL_DESC",
  "category": "$CATEGORY",
  "has_ads": $HAS_ADS,
  "has_inapp_purchase": $HAS_INAPP_PURCHASE,
  "collects_data": $COLLECTS_DATA,
  "privacy_policy_url": "$PRIVACY_POLICY_URL",
  "screenshots": {
    "phone": [
      "store-metadata/screenshots/phone/01-home.png",
      "store-metadata/screenshots/phone/02-feature-main.png",
      "store-metadata/screenshots/phone/03-feature-secondary.png",
      "store-metadata/screenshots/phone/04-settings.png"
    ]
  },
  "icon": "store-metadata/icon/icon-512.png",
  "feature_graphic": "store-metadata/icon/feature-graphic.png"
}
```

### Step 7: Report

```
══════════════════════════════════════════
  FLUTTER STORE METADATA — COMPLETE
══════════════════════════════════════════

  ✓ App icon generated (512px + all mipmap sizes)
  ✓ Screenshots: 4 phone screenshots (1080x1920)
  ✓ Short description: "${SHORT_DESC}" ($(echo $SHORT_DESC | wc -c)/80 chars)
  ✓ Full description: $(echo $FULL_DESC | wc -c)/4000 chars
  ✓ Privacy policy generated (store-metadata/privacy-policy/)
  ✓ store-listing.json exported

  Output directory:
    store-metadata/
    ├── icon/
    ├── screenshots/phone/
    ├── description/
    ├── privacy-policy/
    └── store-listing.json

  Next steps:
    flutter-store-compliance    # Check policies
    flutter-publish            # Upload to Google Play
```

## What This Skill Does NOT Do

- ❌ Upload to Google Play Console (see `flutter-publish`)
- ❌ Take real app screenshots (only generates mockups)
- ❌ Verify policy compliance (see `flutter-store-compliance`)

## Acceptance Criteria

- [ ] App icon generated at all required Android sizes
- [ ] At least 2 phone screenshots created
- [ ] Short description ≤ 80 characters
- [ ] Full description ≤ 4000 characters
- [ ] Privacy policy covers all data collection scenarios
- [ ] `store-listing.json` produced with complete metadata
