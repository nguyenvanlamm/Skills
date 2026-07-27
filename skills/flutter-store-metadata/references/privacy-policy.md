# Generating a privacy policy

## The rule that governs everything here

> **Never write a claim you cannot support from the code.**

A privacy policy is a legal statement about what the developer does. Sentences like *"We perform regular security audits"*, *"We encrypt all data at rest"*, or *"We do not sell your personal information"* are assertions about the company's practices — nothing in the repository can establish them. Generating them puts a false legal statement under the user's name and, if it contradicts Data Safety, creates a policy violation on top.

When a section needs a fact only the user has, leave an explicit marker and list it in `unresolved`:

```markdown
## Data Retention

<!-- UNRESOLVED: how long is user data kept after account deletion? -->
```

Do **not** fill it with a plausible default. An empty marker is visible; a wrong 30-day retention claim is not.

## Derive the contents

Build the policy from Step 1's evidence, not a fixed template. Each derived fact maps to specific sections:

| Derived fact | Sections it requires |
|--------------|---------------------|
| No network, no SDKs | A short policy stating no data leaves the device. This is legitimate and complete — do not pad it. |
| `firebase_analytics` / `posthog` / `mixpanel` | Usage data collection, analytics purpose, the third-party processor by name |
| `firebase_crashlytics` / `sentry_flutter` | Crash logs and diagnostics, device identifiers |
| `firebase_auth` / `google_sign_in` | Account data (email, user ID), authentication purpose, account deletion route |
| `google_mobile_ads` | Advertising ID, ad personalisation, opt-out route, link to the ad partner's policy |
| `in_app_purchase` | Purchase history; note payment details go to Google, not the developer |
| CAMERA / RECORD_AUDIO / LOCATION | What is captured, whether it leaves the device, and why |
| Children in the audience | COPPA section, no behavioural advertising, parental rights |

Name every third-party processor explicitly. "We may share data with partners" is precisely the vagueness Play's Data Safety review flags.

## Required structure

Play requires the policy to be comprehensive and to cover the app specifically — a generic policy that never names the app is a rejection reason.

1. **Identity and contact** — developer name and a working email. Ship no `[developer-email]` placeholder; ask for the address and stop if it is not given.
2. **What is collected** — one entry per derived data type, with the SDK that collects it.
3. **Why** — purpose per data type, matching the Data Safety purposes.
4. **Sharing** — each third party by name, with a link to their policy.
5. **Retention and deletion** — how long, and how a user requests deletion. Play requires an in-app account deletion route (and a web route) for any app with account creation.
6. **User rights** — access, deletion, withdrawal of consent; GDPR/CCPA specifics if distributed in the EU/California.
7. **Children** — required if the audience includes under-13s.
8. **Changes and effective date.**

## Output

```bash
store-metadata/privacy-policy/privacy-policy.md
store-metadata/privacy-policy/privacy-policy.html
```

HTML conversion:

```bash
pandoc privacy-policy.md -s -o privacy-policy.html --metadata title="Privacy Policy"
```

Without pandoc, write minimal HTML directly rather than shipping raw markdown — the URL a reviewer opens must render as a readable page.

## Hosting

Play requires a **public HTTPS URL**, reachable without a login. A local file, a Google Doc requiring sign-in, or a 404 all fail review.

Cheapest workable options: GitHub Pages on the project repo, or a static host. Tell the user the URL must stay live for the app's lifetime — the policy link is checked again on every update.

Set `privacy_policy_url` in `store-listing.json` once hosted; until then leave it `null` and keep it in `unresolved`.

## Consistency

Three artefacts must agree, and `flutter-store-compliance` cross-checks them:

```
SDKs and permissions in the code
        ↕
Data Safety declaration in Play Console
        ↕
This privacy policy
```

A mismatch in any direction is a policy violation, and it is the most common reason a Data Safety review comes back. Generating the policy from the same derived evidence the compliance skill uses is what keeps them aligned.
