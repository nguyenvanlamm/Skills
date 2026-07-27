# Manual upload — Play Console walkthrough

Use for a first release, or any time no service account is configured. Fill every `<placeholder>` from `store-metadata/store-listing.json` before showing this to the user; a guide with unsubstituted variables is worse than no guide.

Console: https://play.google.com/console/

## Prerequisite: developer account

$25 one-time registration, plus identity verification (personal accounts) or D-U-N-S verification (organization accounts). Verification can take days — if the user has not registered yet, tell them to start that now, in parallel with everything else here.

The account **type** matters later: see `testing-track.md`.

## 1. Create the app (first release only)

**All apps → Create app.**

| Field | Value | Changeable later? |
|-------|-------|-------------------|
| App name | `<name>` (≤ 30 chars) | Yes |
| Default language | `<default_locale>` | Yes |
| App or game | — | Yes |
| Free or paid | — | **Free → paid is not possible after publish.** Decide now. |

Then accept the Developer Program Policies and US export law declarations.

## 2. App content declarations

**Dashboard → Policy → App content.** Every applicable section must be green before the app can be submitted. This is where submissions stall, not at the upload.

| Section | What to answer | Source |
|---------|----------------|--------|
| **Privacy policy** | Public HTTPS URL | Host `store-metadata/privacy-policy/privacy-policy.html` (GitHub Pages works). A local file is not acceptable. |
| **App access** | Whether any part is login-gated | If yes, provide `test_credentials` + step-by-step reach instructions. **Missing this is a top rejection cause** — a reviewer who cannot get past the login rejects the app. |
| **Ads** | Contains ads, yes/no | Count third-party SDK ads. Mismatch with reality is a policy violation. |
| **Content rating** | Questionnaire | Cannot be automated. Answer honestly; a wrong rating is grounds for removal. |
| **Target audience and content** | Age groups | Including under-13 triggers the full Families policy. |
| **Data safety** | Every data type collected/shared | Import `store-metadata/data-safety.csv` from `flutter-store-compliance`. **Must match the privacy policy** — inconsistency is a frequent rejection. |
| **Advertising ID** | Whether the app uses AD_ID | Declare yes if any analytics/ads SDK is present. |
| **Government apps** | Usually No | — |
| **Financial features** | Payments, lending, crypto | If yes, expect extra verification and regional restrictions. |
| **Health apps** | Health data or claims | Extra declarations. |
| **News apps** | Only if the app is a news app | — |
| **Sensitive permissions** | e.g. SMS, Call Log, all-files access, background location | Requires a Permissions Declaration Form and Google approval; can add weeks. Check `android/app/src/main/AndroidManifest.xml` and warn the user *before* they build the release plan. |

## 3. Store listing

**Grow → Store presence → Main store listing.**

| Asset | Requirement | Source |
|-------|-------------|--------|
| App name | ≤ 30 chars | `store-listing.json` |
| Short description | ≤ 80 chars | `store-metadata/description/short_description.txt` |
| Full description | ≤ 4000 chars | `store-metadata/description/full_description.txt` |
| App icon | 512×512 PNG, 32-bit | `store-metadata/icon/icon-512.png` |
| Feature graphic | 1024×500 | `store-metadata/icon/feature-graphic.png` |
| Phone screenshots | 2 minimum, 8 maximum, 16:9 or 9:16, 320–3840 px | `store-metadata/screenshots/phone/` |
| Tablet screenshots | Optional, but required to be shown as tablet-optimized | — |
| Category + tags | — | `store-listing.json` |
| Contact email | Required and public | — |

Keyword-stuffed descriptions and screenshots that misrepresent the app are both policy violations — the ASO temptation is real and the penalty is a suspension.

## 4. Create the release

**Test and release → <track> → Create new release.**

Track choice, in the order most apps should use them:

| Track | Use |
|-------|-----|
| **Internal testing** | Up to 100 testers, available in minutes, no review wait. Start here always. |
| **Closed testing** | Required for production access on personal accounts. See `testing-track.md`. |
| **Open testing** | Public beta, listed on Play. |
| **Production** | Live. |

Steps:

1. **Play App Signing** — accept when prompted (first release). Play then holds the app signing key and the local keystore becomes the *upload* key only, which makes key loss recoverable. Declining is a decision the user cannot reverse.
2. Upload `<aab_path>`.
3. Release name — defaults to the version name; leave it.
4. Release notes — paste `store-metadata/whats-new/en-US.txt` inside the existing `<en-US>` tags, and each other locale in its own tag.
5. **Next → Review release**, then check the warnings panel. Warnings there are Play telling you what review will find.
6. **Start rollout to <track>.**

For production, set a staged rollout (start at 10–20%) unless the user asks otherwise. A staged rollout can be halted; a 100% rollout can only be rolled forward with a new version code.

## 5. After rollout

- Internal track builds are installable within minutes via the opt-in URL; other tracks wait for review.
- **Release → Pre-launch report** runs the app on real devices. Read it — it catches crashes and accessibility issues before users do.
- First review typically takes a few days and can take up to 7; updates are usually faster. Google states no SLA.
- Do not resubmit while a review is pending; it restarts the queue.

Tell the user which of these steps you completed and which remain. You cannot complete the questionnaires, the consents, or the rollout button for them.
