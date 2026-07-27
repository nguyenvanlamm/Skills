# The eight check groups

Each check states its evidence, its verdict rule, and the fix. Verdicts are `PASS` / `WARN` / `FAIL` / `SKIP` — no other words.

## 1. Restricted content

**Do not grep the description for banned words.** `-i "sex"` matches "unisex" and "Essex"; a real gambling app does not write "gambling" in its marketing copy. Keyword scanning on the listing text produces false positives and misses everything it is meant to catch.

Judge the **app's function**, from `features`, the PRD, and the code:

| Finding | Verdict |
|---------|---------|
| Real-money gambling, or simulated gambling without the required declarations | FAIL |
| Sexual content, graphic violence, hate speech, illegal-goods facilitation | FAIL |
| UGC with no reporting mechanism, no blocking, and no moderation | FAIL — Play requires all three |
| AI-generated content with no in-app disclosure | WARN |
| Health, financial, or medical claims | WARN — these attract extra scrutiny and may need documentation |
| Cannot determine the app's function from the available material | WARN, and say so — do not default to PASS |

## 2. Intellectual property

Verifiable from here: whether third-party assets exist and whether their licences are recorded.

```bash
ls assets/ 2>/dev/null
find assets -name 'LICENSE*' -o -name '*.txt' 2>/dev/null
grep -rn "fonts:" -A5 pubspec.yaml
```

| Finding | Verdict |
|---------|---------|
| Bundled fonts/images/icons with no licence file or attribution | WARN — ask the user to state the source of each |
| App name or icon imitating a known brand | FAIL |
| Otherwise | PASS |

Trademark clearance is **not** verifiable here. Put it under "cannot verify" and point to the `brand-name-checker` skill. Do not report PASS for a check that was never performed.

## 3. Privacy & data

### 3A Privacy policy exists and matches the code

```bash
ls store-metadata/privacy-policy/privacy-policy.md
grep -c "UNRESOLVED" store-metadata/privacy-policy/privacy-policy.md
```

| Finding | Verdict |
|---------|---------|
| Missing, and the evidence shows any collection, login, or sensitive permission | FAIL |
| Missing on a genuinely local-only app | FAIL anyway — Play requires a policy for every app |
| Present but omits a data type the code collects | FAIL — this is the mismatch that fails Data Safety review |
| Contains `UNRESOLVED` markers | FAIL — an incomplete legal document must not be published |
| Only a local file, no public HTTPS URL | FAIL for submission; the reviewer must be able to open it |
| Asserts practices not supported by evidence ("regular security audits") | WARN — flag it; the user must confirm it is true or remove it |

### 3B Data Safety

See `references/data-safety.md`. Verdict is `FAIL` when the intended declaration would contradict the evidence, `WARN` when a data type cannot be classified.

### 3C Permissions

Use the permission classes in `evidence.md`.

| Finding | Verdict |
|---------|---------|
| Restricted permission (SMS, Call Log) present | FAIL until the Permissions Declaration Form is approved |
| Sensitive permission with no in-app prominent disclosure | FAIL |
| Sensitive permission with no code using it | WARN — remove it |
| ACCESS_BACKGROUND_LOCATION | FAIL unless the core feature demonstrably needs it |
| Normal permissions only | PASS |

### 3D Reviewer access

| Finding | Verdict |
|---------|---------|
| Login-gated (auth SDK present) and no `test_credentials` | FAIL — a reviewer who cannot get in rejects the app |
| Credentials provided but never verified to work | WARN — tell the user to log in with them once, on a clean device |
| No login | PASS |

### 3E Target API level

Read `target_sdk` from `build-info.json`, or from the AAB with `bundletool` — not from `grep targetSdkVersion`, which returns nothing on a modern Flutter project using `targetSdk = flutter.targetSdkVersion`. An empty value must be `WARN` ("could not determine"), never a silent pass.

The rule is a dated threshold, not a distance from the newest SDK:

| Condition | Verdict |
|-----------|---------|
| `target_sdk >= 36` | PASS |
| `target_sdk == 35`, before 31 Aug 2026 | WARN — bump before the deadline |
| `target_sdk == 35`, on/after 31 Aug 2026 | FAIL — new apps and updates are blocked |
| `target_sdk <= 34` | FAIL |

Compare against today's date. `minSdkVersion` is an engineering choice, not a Play policy — do not report it as a compliance finding.

## 4. Store listing

```bash
identify -format '%wx%h %[channels]\n' store-metadata/icon/icon-512.png
identify -format '%wx%h %[channels]\n' store-metadata/icon/feature-graphic.png
wc -m < store-metadata/description/en-US/short_description.txt
wc -m < store-metadata/description/en-US/full_description.txt
python3 -c "import json;d=json.load(open('store-metadata/store-listing.json'));print(d.get('unresolved'))"
```

| Check | Rule | Verdict if violated |
|-------|------|--------------------|
| Icon | exactly 512×512 | FAIL |
| Feature graphic | exists, exactly 1024×500, **no alpha** (`srgb`, not `srgba`) | FAIL — required for every listing |
| Phone screenshots | ≥ 2, each side 320–3840 px, aspect ≤ 2:1, no alpha | FAIL |
| Screenshot authenticity | no entry with `placeholder: true`; `unresolved` empty | FAIL — placeholders are deceptive metadata, not assets |
| App name | ≤ 30 **characters** (`wc -m`, not `wc -c`) | FAIL |
| Short description | ≤ 80 characters | FAIL |
| Full description | ≤ 4000 characters | FAIL |
| Listing name vs `android:label` | must match | WARN — mismatch reads as misleading |
| Description claims | every feature named must exist in the app | FAIL if not |
| Keyword stuffing | repeated keywords, unrelated brand names | WARN |
| Category | set and plausible for the app | WARN |

Content rating is Console-only: report it under "cannot verify", never as PASS.

## 5. Monetization

Grepping `android/` for billing finds nothing on a normal Flutter app — the plugin pulls the dependency transitively. Check `pubspec.yaml` instead:

```bash
grep -E "in_app_purchase|purchases_flutter|flutter_stripe|razorpay|paypal" pubspec.yaml
grep -rn "launchUrl\|url_launcher" lib/ | grep -i "pay\|checkout\|subscribe"
```

| Finding | Verdict |
|---------|---------|
| Digital goods or subscriptions billed outside Google Play Billing | FAIL — a core policy violation |
| A payment SDK (Stripe, PayPal) for **physical** goods or services | PASS — permitted; confirm which it is |
| External link steering users to an outside checkout for digital goods | FAIL |
| Subscriptions with no clear terms, price, and renewal period in the app | WARN |
| Ads plus a children's audience | FAIL unless every ad SDK is Families-certified |
| No monetization | PASS |

## 6. Functionality

Do not rebuild the app to test it. Read what upstream already produced:

```bash
cat build/release/build-info.json      # exists ⇒ the release build succeeded and was verified
flutter analyze 2>&1 | tail -5
```

| Finding | Verdict |
|---------|---------|
| No release artifact and no `build-info.json` | FAIL — nothing to submit |
| `flutter analyze` reports errors | WARN |
| App is a shell with no working feature ("broken functionality") | FAIL |
| Runtime crash behaviour | Cannot verify statically — report as unverifiable and point to Play's pre-launch report |

Being honest that runtime behaviour was not tested is more useful than a `PASS` derived from a grep over build output.

## 7. SDKs

For every entry in `dependencies`, classify: known-and-benign, known-and-data-collecting, or unknown.

| Finding | Verdict |
|---------|---------|
| SDK collects data that the Data Safety answers omit | FAIL |
| Unknown/unrecognised SDK | WARN — the user must state what it collects |
| Ad SDK present, ads not declared in the listing | FAIL |
| SDK flagged in the Google Play SDK Index | FAIL |
| Abandoned dependency (no release in years) with network access | WARN |

## 8. Families

`SKIP` unless the audience includes under-13s — from `target_audience`, or from the listing describing a children's app.

| Finding | Verdict |
|---------|---------|
| Content unsuitable for children | FAIL |
| Any non-Families-certified ad SDK | FAIL |
| No privacy policy | FAIL — required even with zero data collection |
| No parental gate on external links, purchases, or social features | FAIL |
| Collects persistent identifiers for advertising | FAIL — prohibited for child audiences |
| No COPPA/GDPR-K statement in the policy | WARN |

Recording `SKIP` requires stating the reason ("audience is general, per store-listing.json").
